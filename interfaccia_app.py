import streamlit as st
import datetime
from fpdf import FPDF
from supabase import create_client
import time

# 1. CONNESSIONE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def clean_t(t):
    if not t or t == "None": return "---"
    r = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in r.items(): t = str(t).replace(k, v)
    return t.encode('latin-1', 'ignore').decode('latin-1')

st.set_page_config(page_title="MasterRent V46", layout="wide")

menu = st.sidebar.radio("Menu", ["📝 Nuovo Noleggio", "🗄️ Archivio"])

if menu == "📝 Nuovo Noleggio":
    st.subheader("Nuovo Noleggio")
    with st.form("f_v46"):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome Cliente")
        targa = c1.text_input("Targa").upper()
        prezzo = c2.number_input("Prezzo (€)", min_value=0.0)
        cf = c2.text_input("Codice Fiscale")
        accetto = st.checkbox("Accetto Privacy")
        if st.form_submit_button("💾 SALVA"):
            if nome and targa and accetto:
                dat = {"cliente": nome, "targa": targa, "prezzo": prezzo, "cf": cf, "data_inizio": str(datetime.date.today())}
                supabase.table("contratti").insert(dat).execute()
                st.success("Salvato!")

elif menu == "🗄️ Archivio":
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"📄 {c['cliente']} - {c['targa']}"):
            col1, col2 = st.columns(2)
            
            # --- PDF CONTRATTO ---
            pdf_c = FPDF()
            pdf_c.add_page()
            pdf_c.set_font("Helvetica", 'B', 16)
            pdf_c.cell(0, 10, "CONTRATTO DI NOLEGGIO", ln=1, align='C')
            pdf_c.set_font("Helvetica", size=10); pdf_c.ln(10)
            pdf_c.multi_cell(0, 7, clean_t(f"CLIENTE: {c['cliente']}\nTARGA: {c['targa']}\nCF: {c['cf']}"))
            
            # Trasformazione sicura in bytearray
            data_c = bytearray(pdf_c.output())
            
            col1.download_button(
                label="📜 CONTRATTO",
                data=data_c,
                file_name=f"C_{c['id']}.pdf",
                mime="application/pdf",
                key=f"c_{c['id']}"
            )

            # --- PDF RICEVUTA ---
            pdf_r = FPDF()
            pdf_r.add_page()
            pdf_r.set_font("Helvetica", 'B', 16)
            pdf_r.cell(0, 10, "RICEVUTA DI PAGAMENTO", ln=1, align='C')
            pdf_r.set_font("Helvetica", size=12); pdf_r.ln(20)
            pdf_r.cell(0, 10, clean_t(f"TOTALE: {c['prezzo']} Euro"), ln=1)
            
            # Trasformazione sicura in bytearray
            data_r = bytearray(pdf_r.output())
            
            col2.download_button(
                label="💰 RICEVUTA",
                data=data_r,
                file_name=f"R_{c['id']}.pdf",
                mime="application/pdf",
                key=f"r_{c['id']}"
            )
