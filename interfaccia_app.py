import streamlit as st
import datetime
import fpdf
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
import time
import urllib.parse

# 1. CONNESSIONE SUPABASE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)
BUCKET_NAME = "DOCUMENTI_PATENTI"

# INTESTAZIONE FISSA
INTESTAZIONE_MARIANNA = "BATTAGLIA MARIANNA\nVia Cognole, 5 - 80075 Forio (NA)\nP. IVA 10252601215 | C.F. BTTMNN87A53Z112S"

def clean_t(text):
    if not text or text == "None": return "---"
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in repls.items(): text = str(text).replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

def stampa_intestazione(pdf, titolo):
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, clean_t("BATTAGLIA MARIANNA"), ln=1)
    pdf.set_font("Arial", size=9)
    pdf.multi_cell(0, 5, clean_t(INTESTAZIONE_MARIANNA))
    pdf.line(10, 32, 200, 32)
    pdf.ln(15)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, clean_t(titolo), ln=1, align='C')
    pdf.ln(5)

# --- 1. FUNZIONE SOLO CONTRATTO ---
def genera_pdf_CONTRATTO_v23(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    stampa_intestazione(pdf, "CONTRATTO DI NOLEGGIO")
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 8, clean_t(f"CLIENTE: {c['cliente']}\nC.F.: {c['cf']}\nTARGA: {c['targa']}\nDAL: {c['data_inizio']} AL: {c['data_fine']}"), border=1)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 8); pdf.cell(0, 5, "CONDIZIONI GENERALI (ART. 1-14):", ln=1)
    pdf.set_font("Arial", size=7)
    pdf.multi_cell(0, 4, clean_t("Responsabilita totale danni e furto. Sanzioni C.d.S. a carico cliente + 25.83 euro. Foro Ischia. Casco obbligatorio. Privacy GDPR."), border='T')
    pdf.ln(20); pdf.cell(0, 10, "Firma del Cliente: ______________________", align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- 2. FUNZIONE SOLO RICEVUTA ---
def genera_pdf_RICEVUTA_v23(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    stampa_intestazione(pdf, "RICEVUTA DI PAGAMENTO")
    pdf.set_font("Arial", size=12); pdf.ln(10)
    pdf.cell(0, 10, clean_t(f"Ricevuti da: {c['cliente']}"), ln=1)
    pdf.cell(0, 10, clean_t(f"Per il noleggio del veicolo targa: {c['targa']}"), ln=1)
    pdf.ln(20); pdf.set_font("Arial", 'B', 22)
    pdf.cell(0, 25, clean_t(f"TOTALE PAGATO: Euro {c['prezzo']}"), border=1, ln=1, align='C')
    pdf.ln(10); pdf.set_font("Arial", size=10); pdf.cell(0, 10, clean_t(f"Data: {datetime.date.today()}"), align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- 3. FUNZIONE SOLO VIGILI ---
def genera_pdf_VIGILI_v23(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    stampa_intestazione(pdf, "COMUNICAZIONE DATI CONDUCENTE")
    pdf.set_font("Arial", size=11); pdf.ln(5)
    testo = (
        f"La sottoscritta BATTAGLIA MARIANNA, titolare di MasterRent, dichiara che il veicolo "
        f"targa {c['targa']} nel giorno {c['data_inizio']} era affidato al Sig.:\n\n"
        f"NOME: {c['cliente']}\nC.F.: {c['cf']}\nRESIDENTE: {c['residenza']}\nPATENTE: {c['num_doc']}\n\n"
        f"Si richiede la rinotifica dei verbali al soggetto indicato ai sensi della L. 445/2000."
    )
    pdf.multi_cell(0, 8, clean_t(testo))
    pdf.ln(30); pdf.cell(0, 10, "Timbro e Firma: ______________________", align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- APP STREAMLIT ---
st.set_page_config(page_title="MasterRent Management", layout="wide")
scelta = st.sidebar.radio("Navigazione", ["📝 Nuovo Check-in", "🗄️ Archivio Contratti", "🚨 Verbali Vigili"])

if scelta == "📝 Nuovo Check-in":
    with st.form("form_master_v23"):
        st.subheader("Dati Noleggio")
        c1, c2 = st.columns(2)
        nome = c1.text_input("Cognome e Nome")
        targa = c2.text_input("Targa Mezzo").upper()
        cf = c1.text_input("Codice Fiscale")
        tel = c2.text_input("Telefono Cliente")
        res = c1.text_input("Residenza")
        pat = c2.text_input("N. Patente")
        prezzo = c1.number_input("Prezzo Totale (€)", min_value=0.0)
        
        d1, d2 = st.columns(2)
        di = d1.date_input("Data Inizio")
        df = d2.date_input("Data Fine")
        
        st.write("---")
        st.warning("Il cliente firma per accettazione clausole 1-14 e Privacy.")
        accetto = st.checkbox("CONFERMO ACCETTAZIONE TERMINI E CONDIZIONI")
        foto = st.camera_input("Scansiona Patente")
        st_canvas(height=150, key="firma_v23")
        
        if st.form_submit_button("SALVA E ARCHIVIA"):
            if accetto:
                fn = f"{targa}_{int(time.time())}.jpg"
                if foto: supabase.storage.from_(BUCKET_NAME).upload(fn, foto.getvalue())
                dat = {"cliente": nome, "targa": targa, "cf": cf, "residenza": res, "num_doc": pat, "telefono": tel, "prezzo": prezzo, "data_inizio": str(di), "data_fine": str(df), "foto_path": fn if foto else None}
                supabase.table("contratti").insert(dat).execute()
                st.success("Noleggio salvato correttamente!")
            else: st.error("Bisogna spuntare la casella di accettazione!")

elif scelta == "🗄️ Archivio Contratti":
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"📄 {c['cliente']} - {c['targa']}"):
            col1, col2, col3 = st.columns(3)
            # Pulsanti con chiavi e nomi funzioni univoci per forzare il refresh
            col1.download_button("📜 STAMPA CONTRATTO", genera_pdf_CONTRATTO_v23(c), f"Contratto_{c['id']}.pdf", key=f"btn_c_{c['id']}")
            col2.download_button("💰 STAMPA RICEVUTA", genera_pdf_RICEVUTA_v23(c), f"Ricevuta_{c['id']}.pdf", key=f"btn_r_{c['id']}")
            if c.get("foto_path"):
                url_f = supabase.storage.from_(BUCKET_NAME).get_public_url(c["foto_path"])
                col3.link_button("📸 VEDI PATENTE", url_f)

elif scelta == "🚨 Verbali Vigili":
    t_m = st.text_input("Cerca Targa per rinotifica").upper()
    if t_m:
        res_m = supabase.table("contratti").select("*").eq("targa", t_m).execute()
        if res_m.data:
            st.success(f"Noleggio trovato per {res_m.data[0]['cliente']}")
            st.download_button("🚨 SCARICA MODULO VIGILI", genera_pdf_VIGILI_v23(res_m.data[0]), f"Vigili_{t_m}.pdf")
