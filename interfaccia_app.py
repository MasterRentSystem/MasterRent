import streamlit as st
import datetime
from fpdf import FPDF
from supabase import create_client

# Connessione
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.title("🛵 MasterRent V75")

res = supabase.table("contratti").select("*").order("id", desc=True).limit(10).execute()

for r in res.data:
    with st.expander(f"Cliente: {r['cliente']} - {r['targa']}"):
        col1, col2 = st.columns(2)
        
        # --- PDF 1: CONTRATTO ---
        pdf1 = FPDF()
        pdf1.add_page()
        pdf1.set_font("Arial", 'B', 16)
        pdf1.cell(40, 10, "CONTRATTO DI NOLEGGIO")
        pdf1.ln(20)
        pdf1.set_font("Arial", size=12)
        pdf1.cell(40, 10, f"Cliente: {r['cliente']}")
        pdf1.ln(10)
        pdf1.cell(40, 10, f"Targa: {r['targa']}")
        out1 = pdf1.output(dest='S').encode('latin-1')
        col1.download_button("📜 CONTRATTO", out1, f"C_{r['id']}.pdf", "application/pdf", key=f"c_{r['id']}")

        # --- PDF 2: RICEVUTA ---
        pdf2 = FPDF()
        pdf2.add_page()
        pdf2.set_font("Arial", 'B', 16)
        pdf2.cell(40, 10, "RICEVUTA DI PAGAMENTO")
        pdf2.ln(20)
        pdf2.set_font("Arial", size=12)
        pdf2.cell(40, 10, f"Ricevuto da: {r['cliente']}")
        pdf2.ln(10)
        pdf2.cell(40, 10, f"Importo: {r['prezzo']} Euro")
        out2 = pdf2.output(dest='S').encode('latin-1')
        col2.download_button("💰 RICEVUTA", out2, f"R_{r['id']}.pdf", "application/pdf", key=f"r_{r['id']}")
