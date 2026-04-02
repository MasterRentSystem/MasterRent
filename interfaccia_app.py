import streamlit as st
import datetime
from fpdf import FPDF
from supabase import create_client

# Connessione
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.title("🛵 MasterRent V80")

# Funzione per pulire il testo dai caratteri speciali che bloccano il PDF
def clean_txt(t):
    return str(t).encode('latin-1', 'ignore').decode('latin-1')

res = supabase.table("contratti").select("*").order("id", desc=True).limit(10).execute()

for r in res.data:
    with st.expander(f"Cliente: {r['cliente']} - {r['targa']}"):
        col1, col2 = st.columns(2)
        
        # --- PDF 1: CONTRATTO ---
        pdf1 = FPDF()
        pdf1.add_page()
        pdf1.set_font("Arial", 'B', 16)
        pdf1.cell(0, 10, "CONTRATTO DI NOLEGGIO", ln=True, align='C')
        pdf1.ln(10)
        pdf1.set_font("Arial", size=12)
        pdf1.cell(0, 10, clean_txt(f"Cliente: {r['cliente']}"), ln=True)
        pdf1.cell(0, 10, clean_txt(f"Targa: {r['targa']}"), ln=True)
        pdf1.ln(20)
        pdf1.cell(0, 10, "Firma: _______________________", ln=True)
        
        # Nuovo metodo per ottenere i byte del PDF
        out1 = bytes(pdf1.output())
        
        col1.download_button(
            label="📜 SCARICA CONTRATTO",
            data=out1,
            file_name=f"Contratto_{r['id']}.pdf",
            mime="application/pdf",
            key=f"btn_c_{r['id']}"
        )

        # --- PDF 2: RICEVUTA ---
        pdf2 = FPDF()
        pdf2.add_page()
        pdf2.set_font("Arial", 'B', 16)
        pdf2.cell(0, 10, "RICEVUTA DI PAGAMENTO", ln=True, align='C')
        pdf2.ln(10)
        pdf2.set_font("Arial", size=12)
        pdf2.cell(0, 10, clean_txt(f"Ricevuto da: {r['cliente']}"), ln=True)
        pdf2.cell(0, 10, clean_txt(f"Importo: {r['prezzo']} Euro"), ln=True)
        
        out2 = bytes(pdf2.output())
        
        col2.download_button(
            label="💰 SCARICA RICEVUTA",
            data=out2,
            file_name=f"Ricevuta_{r['id']}.pdf",
            mime="application/pdf",
            key=f"btn_r_{r['id']}"
        )
