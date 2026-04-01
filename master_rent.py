import streamlit as st
import datetime
from fpdf import FPDF
from supabase import create_client
import time

# CONNESSIONE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)
BUCKET_NAME = "DOCUMENTI_PATENTI"

def clean_t(t):
    if not t or t == "None": return "---"
    r = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'"}
    for k, v in r.items(): t = str(t).replace(k, v)
    return t.encode('latin-1', 'ignore').decode('latin-1')

st.set_page_config(page_title="MasterRent V41", layout="wide")

menu = st.sidebar.radio("Menu", ["Nuovo Noleggio", "Archivio"])

if menu == "Nuovo Noleggio":
    with st.form("form_v41"):
        nome = st.text_input("Nome e Cognome")
        targa = st.text_input("Targa").upper()
        prezzo = st.number_input("Prezzo (€)", min_value=0.0)
        accetto = st.checkbox("Accetto Condizioni e Privacy")
        foto = st.camera_input("Scansiona Patente")
        if st.form_submit_button("SALVA"):
            if accetto and nome and targa:
                dat = {"cliente": nome, "targa": targa, "prezzo": prezzo, "data_inizio": str(datetime.date.today())}
                supabase.table("contratti").insert(dat).execute()
                st.success("Salvato correttamente!")

elif menu == "Archivio":
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"{c['cliente']} - {c['targa']}"):
            col1, col2 = st.columns(2)
            
            # --- CONTRATTO ---
            pdf_c = FPDF()
            pdf_c.add_page()
            pdf_c.set_font("Helvetica", 'B', 20)
            pdf_c.cell(0, 20, "CONTRATTO DI NOLEGGIO", ln=1, align='C')
            pdf_c.set_font("Helvetica", size=12)
            pdf_c.cell(0, 10, clean_t(f"CLIENTE: {c['cliente']}"), ln=1)
            pdf_c.cell(0, 10, clean_t(f"TARGA: {c['targa']}"), ln=1)
            
            col1.download_button("📜 CONTRATTO", pdf_c.output(), f"C_{c['id']}.pdf", key=f"c_{c['id']}_v41")

            # --- RICEVUTA ---
            pdf_r = FPDF()
            pdf_r.add_page()
            pdf_r.set_font("Helvetica", 'B', 20)
            pdf_r.cell(0, 20, "RICEVUTA DI PAGAMENTO", ln=1, align='C')
            pdf_r.set_font("Helvetica", size=12)
            pdf_r.cell(0, 10, clean_t(f"Ricevuto da: {c['cliente']}"), ln=1)
            pdf_r.cell(0, 20, clean_t(f"TOTALE: {c['prezzo']} Euro"), border=1, align='C')
            
            col2.download_button("💰 RICEVUTA", pdf_r.output(), f"R_{c['id']}.pdf", key=f"r_{c['id']}_v41")
