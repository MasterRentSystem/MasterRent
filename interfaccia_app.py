import streamlit as st
import datetime
from fpdf import FPDF
from io import BytesIO
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
import time

# 1. CONNESSIONE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)
BUCKET_NAME = "DOCUMENTI_PATENTI"

DITTA = "BATTAGLIA MARIANNA"
DITTA_INFO = "Via Cognole, 5 - 80075 Forio (NA)\nP. IVA 10252601215 | C.F. BTTMNN87A53Z112S"

def clean_t(text):
    if not text or text == "None": return "---"
    r = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in r.items(): text = str(text).replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

def header_p(pdf, tit):
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, DITTA, ln=True)
    pdf.set_font("Arial", size=9)
    pdf.multi_cell(0, 5, clean_t(DITTA_INFO))
    pdf.line(10, 32, 200, 32)
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, clean_t(tit), ln=True, align='C')
    pdf.ln(5)

# --- GENERATORI PDF ---
def get_pdf_contratto(c):
    pdf = FPDF()
    pdf.add_page()
    header_p(pdf, "CONTRATTO DI NOLEGGIO")
    pdf.set_font("Arial", size=10)
    testo = f"CLIENTE: {c.get('cliente')}\nNATO A: {c.get('luogo_nascita')}\nRESIDENTE: {c.get('residenza')}\nC.F.: {c.get('cf')}\nPATENTE: {c.get('num_doc')}\nTEL: {c.get('telefono')}\n\nVEICOLO TARGA: {c.get('targa')}\nPERIODO: dal {c.get('data_inizio')} al {c.get('data_fine')}"
    pdf.multi_cell(0, 7, clean_t(testo), border=1)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 8); pdf.cell(0, 5, "CONDIZIONI GENERALI (ART. 1-14):", ln=True)
    pdf.set_font("Arial", size=6.5)
    clausole = "1. Il veicolo viene consegnato in ottimo stato. 2. Il cliente e responsabile di ogni danno o furto. 3. Le contravvenzioni sono a carico del cliente + 25.83 Euro spese gestione. 4. E vietato il sub-noleggio. 5. Obbligo del casco. 6. Foro di Ischia. 7. Privacy GDPR."
    pdf.multi_cell(0, 4, clean_t(clausole), border='T')
    pdf.ln(15); pdf.cell(0, 10, "Firma del Cliente: ______________________", align='R')
    return pdf.output(dest='S').encode('latin-1')

def get_pdf_ricevuta(c):
    pdf = FPDF()
    pdf.add_page()
    header_p(pdf, "RICEVUTA DI PAGAMENTO")
    pdf.set_font("Arial", size=12); pdf.ln(10)
    pdf.cell(0, 10, clean_t(f"Ricevuti da: {c.get('cliente')}"), ln=True)
    pdf.cell(0, 10, clean_t(f"Per noleggio targa: {c.get('targa')}"), ln=True)
    pdf.ln(15); pdf.set_font("Arial", 'B', 20)
    pdf.cell(0, 20, clean_t(f"TOTALE CORRISPOSTO: Euro {c.get('prezzo')}"), border=1, ln=True, align='C')
    return pdf.output(dest='S').encode('latin-1')

def get_pdf_vigili(c):
    pdf = FPDF()
    pdf.add_page()
    header_p(pdf, "COMUNICAZIONE DATI CONDUCENTE")
    pdf.set_font("Arial", size=11); pdf.ln(5)
    t = (f"La sottoscritta BATTAGLIA MARIANNA dichiara che il veicolo targa {c.get('targa')} "
         f"in data {c.get('data_inizio')} era affidato al Sig. {c.get('cliente')}, "
         f"nato a {c.get('luogo_nascita')} e residente in {c.get('residenza')}.\n\n"
         f"Patente: {c.get('num_doc')}. Si richiede rinotifica ai sensi della L. 445/2000.")
    pdf.multi_cell(0, 8, clean_t(t))
    pdf.ln(25); pdf.cell(0, 10, "Firma e Timbro: ______________________", align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- APP ---
st.set_page_config(page_title="MasterRent Ischia", layout="wide")
menu = st.sidebar.radio("Menu", ["📝 Nuovo Noleggio", "🗄️ Archivio", "🚨 Multe"])

if menu == "📝 Nuovo Noleggio":
    with st.form("form_v25"):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Cognome e Nome")
        cf = col2.text_input("Codice Fiscale")
        nascita = col1.text_input("Luogo e Data Nascita")
        res = col2.text_input("Residenza")
        pat = col1.text_input("Num. Patente")
        tel = col2.text_input("Telefono")
        targa = col1.text_input("TARGA").upper()
        prezzo = col2.number_input("Prezzo (€)", min_value=0.0)
        di = st.date_input("Inizio", datetime.date.today())
        df = st.date_input("Fine", datetime.date.today() + datetime.timedelta(days=1))
        
        st.write("---")
        accetto = st.checkbox("Accetto le Condizioni (1-14) e la Privacy")
        foto = st.camera_input("📸 Scansiona Patente")
        st.write("Firma qui sotto:")
        canvas_result = st_canvas(fill_color="white", stroke_width=2, height=150, key="firma_v25")
        
        if st.form_submit_button("💾 SALVA"):
            if accetto:
                fn = f"{targa}_{int(time.time())}.jpg"
                if foto: supabase.storage.from_(BUCKET_NAME).upload(fn, foto.getvalue())
                dat = {"cliente": nome, "cf": cf, "luogo_nascita": nascita, "residenza": res, "num_doc": pat, "targa": targa, "prezzo": prezzo, "data_inizio": str(di), "data_fine": str(df), "telefono": tel, "foto_path": fn if foto else None}
                supabase.table("contratti").insert(dat).execute()
                st.success("Noleggio Salvato!")
            else: st.error("Spunta la casella Accetto!")

elif menu == "🗄️ Archivio":
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"📄 {c['cliente']} - {c['targa']}"):
            col1, col2, col3 = st.columns(3)
            col1.download_button("📜 CONTRATTO", get_pdf_contratto(c), f"Contr_{c['id']}.pdf")
            col2.download_button("💰 RICEVUTA", get_pdf_ricevuta(c), f"Ricev_{c['id']}.pdf")
            if c.get("foto_path"):
                u = supabase.storage.from_(BUCKET_NAME).get_public_url(c["foto_path"])
                col3.link_button("📸 VEDI PATENTE", u)

elif menu == "🚨 Multe":
    t_m = st.text_input("Targa").upper()
    if t_m:
        rm = supabase.table("contratti").select("*").eq("targa", t_m).execute()
        if rm.data:
            st.download_button("🚨 MODULO VIGILI", get_pdf_vigili(rm.data[0]), f"Vigili_{t_m}.pdf")
