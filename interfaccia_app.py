import streamlit as st
import datetime
import fpdf
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
import time

# 1. CONNESSIONE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)
# Assicurati che questo nome sia IDENTICO a quello su Supabase Storage
BUCKET_NAME = "DOCUMENTI_PATENTI"

def clean_t(text):
    if not text or text == "None": return "---"
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in repls.items(): text = str(text).replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

def genera_pdf_pro(c, tipo="CONTRATTO"):
    pdf = fpdf.FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 11); pdf.set_fill_color(235, 235, 235)
    intestazione = "MASTERRENT DI MARIANNA BATTAGLIA\nVia Cognole 5, Forio (NA)\nP.IVA: 10252601215"
    pdf.multi_cell(0, 6, txt=clean_t(intestazione), border=1, align='L', fill=True)
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 16)
    titoli = {"CONTRATTO": "CONTRATTO DI NOLEGGIO", "FATTURA": "RICEVUTA FISCALE", "VIGILI": "MODULO DATI CONDUCENTE"}
    pdf.cell(0, 10, clean_t(titoli.get(tipo, "DOC")), ln=1, align='C')
    pdf.ln(5); pdf.set_font("Arial", size=10)
    pdf.cell(95, 8, clean_t(f"CLIENTE: {c.get('cliente')}"), border=1)
    pdf.cell(95, 8, clean_t(f"C.F.: {c.get('cf')}"), border=1, ln=1)
    pdf.cell(190, 8, clean_t(f"RESIDENZA: {c.get('residenza')}"), border=1, ln=1)
    pdf.cell(60, 8, clean_t(f"TARGA: {c.get('targa')}"), border=1)
    pdf.cell(65, 8, clean_t(f"DAL: {c.get('data_inizio')}"), border=1)
    pdf.cell(65, 8, clean_t(f"AL: {c.get('data_fine', '---')}"), border=1, ln=1)
    if tipo == "CONTRATTO":
        pdf.ln(5); pdf.set_font("Arial", 'B', 8)
        pdf.multi_cell(0, 4, txt=clean_t("Il cliente accetta responsabilita per danni e multe (Art. 1341-1342 cc). Privacy OK."), border='T')
        pdf.ln(15); pdf.cell(0, 10, "Firma: ______________________", align='R')
    return pdf.output(dest='S').encode('latin-1')

st.set_page_config(page_title="MasterRent SaaS", layout="centered")
menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Noleggio", "🗄️ Archivio", "🚨 Multe"])

if menu == "📝 Nuovo Noleggio":
    st.header("Nuovo Check-in")
    with st.form("form_v9", clear_on_submit=True):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Nome e Cognome")
        cf = col2.text_input("Codice Fiscale")
        nascita = col1.text_input("Luogo/Data Nascita")
        residenza = col2.text_input("Residenza")
        num_pat = col1.text_input("Num. Patente")
        scadenza = col2.date_input("Scadenza Patente")
        targa = col1.text_input("TARGA").upper()
        prezzo = col2.number_input("Prezzo (€)", min_value=0.0)
        foto = st.camera_input("📸 Foto Patente")
        st_canvas(fill_color="white", stroke_width=2, height=120, key="cv_v9")
        if st.form_submit_button("💾 SALVA"):
            path_f = None
            if foto:
                try:
                    fn = f"{targa}_{int(time.time())}.jpg"
                    supabase.storage.from_(BUCKET_NAME).upload(fn, foto.getvalue())
                    path_f = fn
                except Exception as e: st.error(f"Errore Storage: {e}")
            dat = {"cliente": nome, "cf": cf, "luogo_nascita": nascita, "residenza": residenza, 
                   "num_doc": num_pat, "scadenza_patente": str(scadenza), "targa": targa, 
                   "prezzo": prezzo, "data_inizio": str(datetime.date.today()), "foto_path": path_f}
            supabase.table("contratti").insert(dat).execute()
            st.success("Registrato!")

elif menu == "🗄️ Archivio":
    st.header("Archivio")
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"{c['cliente']} - {c['targa']}"):
            c1, c2, c3 = st.columns(3)
            c1.download_button("📜 Contratto", genera_pdf_pro(c, "CONTRATTO"), f"C_{c['id']}.pdf", key=f"c_{c['id']}")
            c2.download_button("💰 Fattura", genera_pdf_pro(c, "FATTURA"), f"F_{c['id']}.pdf", key=f"f_{c['id']}")
            if c.get("foto_path"):
                url_f = supabase.storage.from_(BUCKET_NAME).get_public_url(c["foto_path"])
                c3.link_button("📸 Foto", url_f)

elif menu == "🚨 Multe":
    st.header("Ricerca Multe")
    t_m = st.text_input("Targa").upper()
    if t_m:
        res_m = supabase.table("contratti").select("*").eq("targa", t_m).execute()
        if res_m.data:
            st.success(f"Trovato: {res_m.data[0]['cliente']}")
            st.download_button("📥 Modulo Vigili", genera_pdf_pro(res_m.data[0], "VIGILI"), f"V_{t_m}.pdf")
