import streamlit as st
import datetime
from PIL import Image
import fpdf

st.set_page_config(page_title="Battaglia Rent - Ischia", page_icon="🛵", layout="wide")

st.title("🛵 BATTAGLIA RENT - Gestione Contratti")

menu = st.sidebar.selectbox("Cosa vuoi fare?", ["Nuovo Contratto", "Invia Multa ai Vigili", "Archivio Fatture"])

if menu == "Nuovo Contratto":
    st.header("📝 Inserimento Dati Cliente")
    
    # SEZIONE 1: ANAGRAFICA COMPLETA
    col1, col2 = st.columns(2)
    with col1:
        nome = st.text_input("NOME E COGNOME")
        data_nascita = st.date_input("DATA DI NASCITA", datetime.date(1990, 1, 1))
        luogo_nascita = st.text_input("LUOGO DI NASCITA")
        cf = st.text_input("CODICE FISCALE")
    with col2:
        residenza = st.text_input("RESIDENZA (Città e Indirizzo)")
        tipo_doc = st.selectbox("TIPO DOCUMENTO", ["Patente", "Carta Identità", "Passaporto"])
        num_doc = st.text_input("NUMERO DOCUMENTO")
        telefono = st.text_input("TELEFONO / WHATSAPP")

    st.markdown("---")
    
    # SEZIONE 2: VEICOLO E NOLEGGIO
    col3, col4 = st.columns(2)
    with col3:
        targa = st.text_input("TARGA SCOOTER / AUTO")
        data_inizio = st.date_input("DATA INIZIO", datetime.date.today())
    with col4:
        prezzo_tot = st.number_input("TOTALE PAGATO (€)", min_value=0)
        km_uscita = st.text_input("KM USCITA")

    st.markdown("---")
    
    # SEZIONE 3: FOTO E FIRMA
    st.subheader("📸 Documentazione e Firma")
    foto_doc = st.camera_input("Scatta foto al Documento o al Cliente")
    
    st.warning("TERMINI LEGALI: Il cliente dichiara di essere responsabile per multe (spese gestione €20), danni e furto. Ai sensi dell'Art. 21 D.Lgs. 82/2005, la firma digitale ha pieno valore legale.")
    
    firma_check = st.checkbox("IL CLIENTE ACCETTA E FIRMA DIGITALMENTE")

    if st.button("💾 GENERA CONTRATTO E FATTURA PDF"):
        if not nome or not cf or not foto_doc or not firma_check:
            st.error("ERRORE: Inserisci tutti i dati, scatta la foto e spunta la firma!")
        else:
            pdf = fpdf.FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, txt="BATTAGLIA RENT - ISCHIA", ln=1, align='C')
            pdf.set_font("Arial", size=10)
            pdf.ln(10)
            pdf.cell(200, 8, txt=f"CONTRATTO N: {datetime.datetime.now().strftime('%Y%m%d%H%M')}", ln=1)
            pdf.cell(200, 8, txt=f"CLIENTE: {nome} (CF: {cf})", ln=1)
            pdf.cell(200, 8, txt=f"NATO A: {luogo_nascita} IL {data_nascita}", ln=1)
            pdf.cell(200, 8, txt=f"RESIDENTE: {residenza}", ln=1)
            pdf.cell(200, 8, txt=f"DOC: {tipo_doc} N. {num_doc}", ln=1)
            pdf.cell(200, 8, txt=f"VEICOLO TARGA: {targa} - KM: {km_uscita}", ln=1)
            pdf.cell(200, 8, txt=f"PREZZO: {prezzo_tot} Euro", ln=1)
            pdf.ln(5)
            pdf.multi_cell(0, 5, txt="Il sottoscritto accetta le condizioni di noleggio e la responsabilità per ogni sanzione amministrativa.")
            
            pdf_path = f"Contratto_{nome.replace(' ','_')}.pdf"
            pdf.output(pdf_path)
            
            with open(pdf_path, "rb") as f:
                st.download_button("📥 SCARICA PDF PER STAMPA/WHATSAPP", f, file_name=pdf_path)
            st.success("Contratto Creato!")
            st.balloons()

elif menu == "Invia Multa ai Vigili":
    st.header("🚨 Gestione Sanzioni")
    st.write("Qui caricheremo i dati del cliente per l'invio automatico ai vigili in caso di multa.")

elif menu == "Archivio Fatture":
    st.header("📁 Archivio Digitale")
    st.write("Qui troverai tutti i PDF salvati automaticamente.")
