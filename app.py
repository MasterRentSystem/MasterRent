import streamlit as st
from supabase import create_client, Client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from fpdf import FPDF
import io
import base64
from datetime import datetime

# --- CONFIGURAZIONE ---
DITTA = "BATTAGLIA RENT"
TITOLARE = "BATTAGLIA MARIANNA"
INDIRIZZO = "Via Cognole n. 5, Forio (NA)"
DATI_IVA = "P.IVA: 10252601215 | C.F.: BTTMNN87A53Z112S"

URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- UTILITY ---
def s(v): return "" if v is None else str(v)

def safe_text(text):
    return s(text).encode("latin-1", "replace").decode("latin-1")

def get_prossimo_numero():
    try:
        res = supabase.table("contratti").select("numero_fattura").order("numero_fattura", desc=True).limit(1).execute()
        if res.data and res.data[0].get("numero_fattura"):
            return int(res.data[0]["numero_fattura"]) + 1
        return 1
    except: return 1

def upload_foto(file, targa, tipo):
    if file is None: return None
    try:
        img = Image.open(file)
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
        img.thumbnail((800, 800))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=75)
        nome = f"{tipo}{targa}{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
        supabase.storage.from_("documenti").upload(nome, buf.getvalue(), {"content-type": "image/jpeg"})
        return supabase.storage.from_("documenti").get_public_url(nome)
    except: return None

# --- GENERAZIONE PDF ---
def genera_pdf(c, tipo="CONTRATTO"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, safe_text(DITTA), ln=True)
    pdf.set_font("Arial", "", 8)
    pdf.cell(0, 4, safe_text(f"{INDIRIZZO} - {DATI_IVA}"), ln=True)
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 14)
    titolo_doc = f"{tipo} N. {s(c.get('numero_fattura'))}"
    pdf.cell(0, 10, safe_text(titolo_doc), ln=True, align="C", border="B")
    pdf.ln(5)
    
    pdf.set_font("Arial", "", 10)
    testo = f"""
CLIENTE: {s(c.get('nome'))} {s(c.get('cognome'))} | TEL: {s(c.get('telefono'))}
NATO A: {s(c.get('luogo_nascita'))} IL {s(c.get('data_nascita'))}
C.F.: {s(c.get('codice_fiscale'))} | NAZIONALITA: {s(c.get('nazionalita'))}
RESIDENZA: {s(c.get('indirizzo_cliente'))}

VEICOLO: {s(c.get('modello'))} | TARGA: {s(c.get('targa'))}
PATENTE: {s(c.get('numero_patente'))}
LIVELLO BENZINA: {s(c.get('benzina'))}
NOTE DANNI: {s(c.get('note_danni'))}

PERIODO: Dal {s(c.get('inizio'))} Al {s(c.get('fine'))}
PREZZO: EUR {s(c.get('prezzo'))} | DEPOSITO: EUR {s(c.get('deposito'))}
"""
    pdf.multi_cell(0, 5, safe_text(testo))
    
    if tipo == "CONTRATTO":
        pdf.ln(5)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(0, 5, "Firma del cliente per accettazione clausole e sanzioni amministrative:", ln=True)
        if c.get("firma") and len(str(c["firma"])) > 50:
            try:
                pdf.image(io.BytesIO(base64.b64decode(c["firma"])), x=130, y=pdf.get_y()+2, w=40)
            except: pass
            
    return pdf.output(dest="S").encode("latin-1", "replace")

# --- LOGIN ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Password", type="password") == "1234":
        if st.button("Accedi"): st.session_state.auth = True; st.rerun()
    st.stop()

# --- APP ---
t1, t2 = st.tabs(["🆕 Nuovo Contratto", "📂 Archivio"])

with t1:
    with st.form("main_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome")
        cognome = c1.text_input("Cognome")
        telefono = c2.text_input("Telefono")
        nazionalita = c2.text_input("Nazionalità")
        
        c3, c4 = st.columns(2)
        luogo_n = c3.text_input("Luogo Nascita")
        data_n = c3.text_input("Data Nascita")
        cf = c4.text_input("Codice Fiscale")
        patente = c4.text_input("N. Patente")
        
        indirizzo = st.text_area("Indirizzo Residenza")
        
        st.write("---")
        c5, c6, c7 = st.columns(3)
        modello = c5.text_input("Modello Scooter")
        targa = c6.text_input("Targa").upper()
        benzina = c7.selectbox("Livello Benzina", ["1/8", "2/8", "3/8", "4/8", "5/8", "6/8", "7/8", "8/8 (Pieno)"])
        
        note_danni = st.text_area("Note Danni (Graffi, ammaccature, ecc.)")
        
        c8, c9, c10 = st.columns(3)
        prezzo = c8.number_input("Prezzo (€)", min_value=0.0)
        deposito = c9.number_input("Deposito/Cauzione (€)", min_value=0.0)
        
        ini = st.date_input("Inizio")
        fin = st.date_input("Fine")
        
        f_p = st.file_uploader("Foto Fronte Patente")
        r_p = st.file_uploader("Foto Retro Patente")
        
        st.write("Firma Cliente:")
        canvas = st_canvas(height=150, width=400, stroke_width=3, key="sig")
        accetto = st.checkbox("Accetto i termini contrattuali e la responsabilità per multe/danni")

        if st.form_submit_button("💾 SALVA CONTRATTO"):
            if not nome or not targa or not accetto:
                st.error("Dati obbligatori mancanti!")
            else:
                with st.spinner("Salvataggio..."):
                    img_f = Image.fromarray(canvas.image_data.astype("uint8"))
                    buf_f = io.BytesIO()
                    img_f.save(buf_f, format="PNG")
                    firma_b64 = base64.b64encode(buf_f.getvalue()).decode()
                    
                    uf = upload_foto(f_p, targa, "F")
                    ur = upload_foto(r_p, targa, "R")
                    num_f = get_prossimo_numero()

                    # Mapping esatto con le tue colonne Supabase
                    nuovo_contratto = {
                        "nome": nome,
                        "cognome": cognome,
                        "telefono": telefono,
                        "nazionalita": nazionalita,
                        "codice_fiscale": cf,
                        "luogo_nascita": luogo_n,
                        "data_nascita": data_n,
                        "indirizzo_cliente": indirizzo,
                        "modello": modello,
                        "targa": targa,
                        "numero_patente": patente,
                        "benzina": benzina,
                        "note_danni": note_danni,
                        "prezzo": prezzo,
                        "deposito": deposito,
                        "inizio": str(ini),
                        "fine": str(fin),
                        "firma": firma_b64,
                        "url_fronte": uf,
                        "url_retro": ur,
                        "numero_fattura": num_f,
                        "data_creazione": datetime.now().isoformat() # Usiamo il tuo nome colonna
                    }
                    
                    try:
                        supabase.table("contratti").insert(nuovo_contratto).execute()
                        st.success(f"Contratto N. {num_f} salvato correttamente!")
                    except Exception as e:
                        st.error(f"Errore tecnico DB: {e}")

with t2:
    search = st.text_input("🔍 Cerca per Cognome o Targa").lower()
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    for r in res.data:
        if search in f"{r['cognome']} {r['targa']}".lower():
            with st.expander(f"📄 N. {r['numero_fattura']} - {r['targa']} {r['cognome']}"):
                c1, c2, c3 = st.columns(3)
                c1.download_button("📜 Contratto", genera_pdf(r, "CONTRATTO"), f"Contr_{r['id']}.pdf")
                c2.download_button("💰 Fattura", genera_pdf(r, "FATTURA"), f"Fatt_{r['id']}.pdf")
                c3.download_button("🚨 Vigili", genera_pdf(r, "VIGILI"), f"Vigili_{r['id']}.pdf")
                if r.get("url_fronte"): st.image(r["url_fronte"], width=300)
