import streamlit as st
import datetime
from PIL import Image
import fpdf

st.set_page_config(page_title="Battaglia Rent - Ischia", page_icon="🛵")
st.title("🛵 BATTAGLIA RENT! - Ischia")

nome = st.text_input("NOME E COGNOME CLIENTE")
documento = st.text_input("PATENTE / DOCUMENTO ID")
targa = st.text_input("TARGA VEICOLO")
prezzo = st.number_input("PREZZO TOTALE (€)", min_value=0)
foto_scattata = st.camera_input("Inquadra la Patente")

testo_legale = "1. Stato Veicolo: Ottimo. 2. Multe: Responsabilità cliente + 20€ gestione. 3. Danni: Responsabilità cliente."
st.info(testo_legale)
accetto = st.checkbox("Accetto i termini (Firma Digitale)")

if st.button("💾 GENERA E SCARICA PDF"):
    if not nome or not foto_scattata or not accetto:
        st.error("Mancano dati, foto o accettazione!")
    else:
        pdf = fpdf.FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt="BATTAGLIA RENT - CONTRATTO", ln=1, align='C')
        pdf.set_font("Arial", size=12)
        pdf.ln(10)
        pdf.cell(200, 10, txt=f"Cliente: {nome}", ln=1)
        pdf.cell(200, 10, txt=f"Targa: {targa}", ln=1)
        pdf.multi_cell(0, 10, txt=testo_legale)
        pdf_output = "contratto_corrente.pdf"
        pdf.output(pdf_output)
        with open(pdf_output, "rb") as f:
            st.download_button("📥 SCARICA ORA IL PDF", f, file_name=f"Contratto_{nome}.pdf")
        st.balloons()
