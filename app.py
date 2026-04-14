import streamlit as st
from supabase import create_client, Client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from fpdf import FPDF
import io
import base64
from datetime import datetime

# --- CONFIGURAZIONE AZIENDALE ---
DITTA = "BATTAGLIA RENT"
TITOLARE = "BATTAGLIA MARIANNA"
INDIRIZZO = "Via Cognole n. 5, Forio (NA)"
DATI_IVA = "P.IVA: 10252601215 | C.F.: BTTMNN87A53Z112S"

# Connessione Supabase
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- FUNZIONI DI SERVIZIO ---
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
        img.thumbnail((1000, 1000))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        nome_file = f"{tipo}{targa}{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
        supabase.storage.from_("documenti").upload(nome_file, buf.getvalue(), {"content-type": "image/jpeg"})
        return supabase.storage.from_("documenti").get_public_url(nome_file)
    except Exception as e:
        st.error(f"Errore caricamento foto: {e}")
        return None

# --- GENERATORE PDF PROFESSIONALE ---
class ProPDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 6, safe_text(DITTA), ln=True)
        self.set_font("Arial", "", 8)
        self.cell(0, 4, safe_text(f"{INDIRIZZO} | {DATI_IVA}"), ln=True)
        self.line(10, 26, 200, 26)
        self.ln(12)

def genera_pdf_pro(c, tipo="CONTRATTO"):
    pdf = ProPDF()
    pdf.add_page()
    n_doc = s(c.get('numero_fattura'))
    data_c = s(c.get('data_creazione'))[:10] if c.get('data_creazione') else datetime.now().strftime("%d/%m/%Y")

    pdf.set_font("Arial", "B", 14)
    titolo = f"{tipo} DI NOLEGGIO N. {n_doc}"
    if tipo == "VIGILI": titolo = "DICHIARAZIONE CONDUCENTE PER AUTORITÀ"
    pdf.cell(0, 10, safe_text(titolo), ln=True, align="C", border="B")
    pdf.set_font("Arial", "I", 9)
    pdf.cell(0, 8, f"Data: {data_c}", ln=True, align="R")
    
    # Tabella Dati
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, " DATI CONDUTTORE E VEICOLO", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "", 10)
    
    col1, col2 = 95, 95
    pdf.cell(col1, 7, safe_text(f"Cliente: {c.get('nome')} {c.get('cognome')}"), border=1)
    pdf.cell(col2, 7, safe_text(f"Targa: {c.get('targa')}"), border=1, ln=True)
    pdf.cell(col1, 7, safe_text(f"Modello: {c.get('modello')}"), border=1)
    pdf.cell(col2, 7, safe_text(f"Patente: {c.get('numero_patente')}"), border=1, ln=True)
    pdf.cell(col1, 7, safe_text(f"Periodo: {c.get('inizio')} / {c.get('fine')}"), border=1)
    pdf.cell(col2, 7, safe_text(f"Prezzo: {c.get('prezzo')} EUR"), border=1, ln=True)
    pdf.cell(col1, 7, safe_text(f"Benzina: {c.get('benzina')}"), border=1)
    pdf.cell(col2, 7, safe_text(f"Deposito: {c.get('deposito')} EUR"), border=1, ln=True)
    
    pdf.ln(5)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, " NOTE STATO MEZZO / DANNI", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "I", 10)
    pdf.multi_cell(0, 6, safe_text(s(c.get('note_danni')) or "Nessun danno rilevato."), border=1)

    if tipo == "CONTRATTO":
        pdf.ln(5)
        pdf.set_font("Arial", "", 7)
        clausole = "Il cliente accetta la responsabilità per sanzioni (Art. 126 bis CdS) e danni (Artt. 1341-1342 c.c.)."
        pdf.multi_cell(0, 4, safe_text(clausole))
        
        firma_b64 = c.get("firma")
        if firma_b64 and len(str(firma_b64)) > 100:
            try:
                pdf.image(io.BytesIO(base64.b64decode(firma_b64)), x=140, y=pdf.get_y()+2, w=45)
            except: pass

    out = pdf.output(dest="S")
    return bytes(out) if not isinstance(out, str) else out.encode("latin-1", "replace")

# --- APP STREAMLIT ---
st.set_page_config(page_title="Battaglia Rent Gestionale", layout="wide")

if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Password", type="password") == "1234":
        if st.button("ACCEDI"): st.session_state.auth = True; st.rerun()
    st.stop()

tab_n, tab_a = st.tabs(["🆕 Nuovo Contratto", "📂 Archivio"])

with tab_n:
    with st.form("main_form", clear_on_submit=True):
        st.subheader("👤 Dati Cliente")
        c1, c2, c3 = st.columns(3)
        nome = c1.text_input("Nome")
        cognome = c2.text_input("Cognome")
        tel = c3.text_input("Telefono")
        naz = c1.text_input("Nazionalità")
        cf = c2.text_input("Codice Fiscale")
        luo = c3.text_input("Luogo Nascita")
        dat_n = c1.text_input("Data Nascita")
        ind = st.text_input("Indirizzo Residenza")

        st.subheader("🛵 Dati Noleggio")
        c4, c5, c6 = st.columns(3)
        mod = c4.text_input("Modello Scooter")
        tar = c5.text_input("Targa").upper()
        ben = c6.selectbox("Livello Benzina", ["1/8", "1/4", "1/2", "3/4", "PIENO"])
        pat = st.text_input("N. Patente")
        danni = st.text_area("Note Danni / Graffi")

        c7, c8, c9, c10 = st.columns(4)
        prz = c7.number_input("Prezzo (€)", min_value=0.0)
        dep = c8.number_input("Deposito (€)", min_value=0.0)
        ini = c9.date_input("Inizio")
        fin = c10.date_input("Fine")

        st.subheader("📸 Documenti e Firma")
        f_pat = st.file_uploader("Foto FRONTE Patente", type=['png','jpg','jpeg'])
        r_pat = st.file_uploader("Foto RETRO Patente", type=['png','jpg','jpeg'])
        
        canvas = st_canvas(height=150, width=450, stroke_width=3, key="sig_v7")
        accetto = st.checkbox("Dichiaro che il cliente ha accettato i termini legali.")

        if st.form_submit_button("SALVA E GENERA"):
            if not nome or not tar or not accetto:
                st.error("Dati obbligatori mancanti!")
            else:
                with st.spinner("Registrazione in corso..."):
                    # Firma e Foto
                    img_f = Image.fromarray(canvas.image_data.astype("uint8"))
                    buf_f = io.BytesIO()
                    img_f.save(buf_f, format="PNG")
                    f_b64 = base64.b64encode(buf_f.getvalue()).decode()
                    
                    u_f = upload_foto(f_pat, tar, "FRONTE")
                    u_r = upload_foto(r_pat, tar, "RETRO")
                    
                    num = get_prossimo_numero()
                    payload = {
                        "nome": nome, "cognome": cognome, "telefono": tel, "nazionalita": naz,
                        "codice_fiscale": cf, "luogo_nascita": luo, "data_nascita": dat_n,
                        "indirizzo_cliente": ind, "modello": mod, "targa": tar,
                        "numero_patente": pat, "benzina": ben, "note_danni": danni,
                        "prezzo": prz, "deposito": dep, "inizio": str(ini), "fine": str(fin),
                        "firma": f_b64, "url_fronte": u_f, "url_retro": u_r,
                        "numero_fattura": num, "data_creazione": datetime.now().isoformat()
                    }
                    supabase.table("contratti").insert(payload).execute()
                    st.success(f"Contratto N. {num} salvato!")

with tab_a:
    cerca = st.text_input("Cerca Targa o Cognome").lower()
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    for r in res.data:
        if cerca in f"{r['cognome']} {r['targa']}".lower():
            with st.expander(f"N. {r['numero_fattura']} - {r['targa']} ({r['cognome']})"):
                c1, c2, c3 = st.columns(3)
                # Chiavi uniche per evitare errori di duplicazione ID
                c1.download_button("📜 Contratto", genera_pdf_pro(r, "CONTRATTO"), f"C_{r['id']}.pdf", key=f"c_{r['id']}")
                c2.download_button("💰 Ricevuta", genera_pdf_pro(r, "FATTURA"), f"F_{r['id']}.pdf", key=f"f_{r['id']}")
                c3.download_button("🚨 Vigili", genera_pdf_pro(r, "VIGILI"), f"V_{r['id']}.pdf", key=f"v_{r['id']}")
                
                # Mostra le foto salvate
                st.write("---")
                col_f1, col_f2 = st.columns(2)
                if r.get("url_fronte"): col_f1.image(r["url_fronte"], caption="Fronte Patente")
                if r.get("url_retro"): col_f2.image(r["url_retro"], caption="Retro Patente")
