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
        img.thumbnail((800, 800)) # Leggermente più piccola per velocità
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=75)
        nome = f"{tipo}{targa}{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
        supabase.storage.from_("documenti").upload(nome, buf.getvalue(), {"content-type": "image/jpeg"})
        return supabase.storage.from_("documenti").get_public_url(nome)
    except: return None

# --- GENERAZIONE DOCUMENTI PDF ---
def genera_pdf(c, tipo="CONTRATTO"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, safe_text(DITTA), ln=True)
    pdf.set_font("Arial", "", 8)
    pdf.cell(0, 4, safe_text(INDIRIZZO), ln=True)
    pdf.cell(0, 4, safe_text(DATI_IVA), ln=True)
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"{tipo} N. {s(c.get('numero_fattura'))}", ln=True, align="C", border="B")
    pdf.ln(5)
    
    pdf.set_font("Arial", "", 10)
    info = f"""CLIENTE: {s(c.get('nome'))} {s(c.get('cognome'))}
NAZIONALITA: {s(c.get('nazionalita'))} | C.F.: {s(c.get('codice_fiscale'))}
NATO A: {s(c.get('luogo_nascita'))} IL {s(c.get('data_nascita'))}
RESIDENTE: {s(c.get('indirizzo_cliente'))}
TARGA: {s(c.get('targa'))} | PATENTE: {s(c.get('numero_patente'))}
PERIODO: Dal {s(c.get('inizio'))} Al {s(c.get('fine'))} | PREZZO: EUR {s(c.get('prezzo'))}
"""
    pdf.multi_cell(0, 5, safe_text(info))
    
    if tipo == "CONTRATTO":
        pdf.ln(5)
        pdf.set_font("Arial", "I", 8)
        clausole = "Il cliente dichiara di assumersi ogni responsabilita per danni e multe. Accetta i termini ai sensi degli artt. 1341-1342 c.c."
        pdf.multi_cell(0, 4, safe_text(clausole))
        
        if c.get("firma") and len(str(c["firma"])) > 50:
            try:
                pdf.image(io.BytesIO(base64.b64decode(c["firma"])), x=130, y=pdf.get_y()+5, w=40)
            except: pass
            
    out = pdf.output(dest="S")
    return bytes(out) if isinstance(out, bytearray) else out.encode("latin-1", "replace")

# --- LOGIN ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    pw = st.text_input("Password", type="password")
    if st.button("Accedi"):
        if pw == "1234": st.session_state.auth = True; st.rerun()
    st.stop()

# --- INTERFACCIA ---
tab1, tab2 = st.tabs(["🆕 Nuovo Contratto", "📂 Archivio"])

with tab1:
    with st.form("form_noleggio", clear_on_submit=True):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome")
        cognome = c1.text_input("Cognome")
        nazionalita = c2.text_input("Nazionalità")
        codice_fiscale = c2.text_input("Codice Fiscale")
        
        luogo_nascita = c1.text_input("Luogo Nascita")
        data_nascita = c2.text_input("Data Nascita (GG/MM/AAAA)")
        indirizzo_cliente = st.text_area("Indirizzo Residenza")
        
        c3, c4, c5 = st.columns(3)
        targa = c3.text_input("Targa").upper()
        numero_patente = c4.text_input("Patente")
        prezzo = c5.number_input("Prezzo (€)", min_value=0.0)
        
        inizio = st.date_input("Inizio")
        fine = st.date_input("Fine")
        
        f_p = st.file_uploader("Fronte Patente")
        r_p = st.file_uploader("Retro Patente")
        
        st.write("Firma Cliente:")
        canvas = st_canvas(height=150, width=400, stroke_width=3, key="sig")
        accetto = st.checkbox("Il cliente accetta le condizioni e le multe")

        if st.form_submit_button("💾 SALVA NOLEGGIO"):
            if not nome or not targa or not accetto:
                st.error("Dati obbligatori mancanti!")
            else:
                with st.spinner("Salvataggio..."):
                    # Firma
                    img_f = Image.fromarray(canvas.image_data.astype("uint8"))
                    buf_f = io.BytesIO()
                    img_f.save(buf_f, format="PNG")
                    firma_b64 = base64.b64encode(buf_f.getvalue()).decode()
                    
                    # Upload Foto
                    uf = upload_foto(f_p, targa, "F")
                    ur = upload_foto(r_p, targa, "R")
                    num_f = get_prossimo_numero()

                    # Inserimento nel Database (nomi colonne minuscoli)
                    nuovo_contratto = {
                        "nome": nome,
                        "cognome": cognome,
                        "nazionalita": nazionalita,
                        "codice_fiscale": codice_fiscale,
                        "luogo_nascita": luogo_nascita,
                        "data_nascita": data_nascita,
                        "indirizzo_cliente": indirizzo_cliente,
                        "targa": targa,
                        "numero_patente": numero_patente,
                        "prezzo": prezzo,
                        "inizio": str(inizio),
                        "fine": str(fine),
                        "firma": firma_b64,
                        "url_fronte": uf,
                        "url_retro": ur,
                        "numero_fattura": num_f,
                        "created_at": datetime.now().isoformat()
                    }
                    
                    try:
                        supabase.table("contratti").insert(nuovo_contratto).execute()
                        st.success(f"Contratto N. {num_f} registrato!")
                    except Exception as e:
                        st.error(f"Errore tecnico DB: {e}")

with tab2:
    search = st.text_input("Cerca Cognome o Targa").lower()
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    
    for r in res.data:
        if search in f"{r['cognome']} {r['targa']}".lower():
            with st.expander(f"N. {r['numero_fattura']} - {r['targa']} {r['cognome']}"):
                col1, col2, col3 = st.columns(3)
                col1.download_button("📜 Contratto", genera_pdf(r, "CONTRATTO"), f"Contr_{r['id']}.pdf")
                col2.download_button("💰 Fattura", genera_pdf(r, "FATTURA"), f"Fatt_{r['id']}.pdf")
                col3.download_button("🚨 Vigili", genera_pdf(r, "VIGILI"), f"Vigili_{r['id']}.pdf")
                
                if r.get("url_fronte"): st.image(r["url_fronte"], caption="Fronte Patente", width=300)
