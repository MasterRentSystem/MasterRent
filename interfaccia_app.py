import streamlit as st
import datetime
from PIL import Image
import fpdf
from supabase import create_client

# Configurazione Pagina
st.set_page_config(page_title="Battaglia Rent - Ischia", page_icon="🛵", layout="wide")

# Connessione a Supabase usando i Secrets di Streamlit
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except Exception as e:
    st.error("Errore di connessione a Supabase. Controlla i Secrets!")

st.title("🛵 BATTAGLIA RENT - Gestione Contratti")

menu = st.sidebar.selectbox("Cosa vuoi fare?", ["Nuovo Contratto", "Invia Multa ai Vigili", "Archivio Fatture"])

if menu == "Nuovo Contratto":
    st.header("📝 Inserimento Dati Cliente")
    
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
    
    col3, col4 = st.columns(2)
    with col3:
        targa = st.text_input("TARGA SCOOTER / AUTO")
        data_inizio = st.date_input("DATA INIZIO", datetime.date.today())
    with col4:
        prezzo_tot = st.number_input("TOTALE PAGATO (€)", min_value=0)
        km_uscita = st.text_input("KM USCITA")

    st.markdown("---")
    
    st.subheader("📸 Documentazione e Firma")
    foto_doc = st.camera_input("Scatta foto al Documento o al Cliente")
    
    st.warning("TERMINI LEGALI: Il cliente dichiara di essere responsabile per multe, danni e furto.")
    firma_check = st.checkbox("IL CLIENTE ACCETTA E FIRMA DIGITALMENTE")

    if st.button("💾 GENERA CONTRATTO E SALVA NEL DATABASE"):
        if not nome or not cf or not foto_doc or not firma_check:
            st.error("ERRORE: Inserisci tutti i dati obbligatori!")
        else:
            # 1. GENERAZIONE PDF
            pdf = fpdf.FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, txt="BATTAGLIA RENT - ISCHIA", ln=1, align='C')
            pdf.set_font("Arial", size=10)
            pdf.ln(10)
            pdf.cell(200, 8, txt=f"CLIENTE: {nome} (CF: {cf})", ln=1)
            pdf.cell(200, 8, txt=f"VEICOLO TARGA: {targa}", ln=1)
            
            pdf_path = f"Contratto_{nome.replace(' ','_')}.pdf"
            pdf.output(pdf_path)
            
            # 2. INVIO DATI A SUPABASE
            data_db = {
                "cliente": nome,
                "cf": cf,
                "luogo_nascita": luogo_nascita,
                "residenza": residenza,
                "tipo_doc": tipo_doc,
                "num_doc": num_doc,
                "telefono": telefono,
                "targa": targa,
                "prezzo_tot": str(prezzo_tot),
                "km_uscita": km_uscita,
                "data_inizio": str(data_inizio)
            }
            
            try:
                supabase.table("contratti").insert(data_db).execute()
                st.success("✅ Contratto salvato su Supabase!")
                st.balloons()
                with open(pdf_path, "rb") as f:
                    st.download_button("📥 SCARICA PDF", f, file_name=pdf_path)
            except Exception as e:
                st.error(f"Errore Database: {e}")

elif menu == "Invia Multa ai Vigili":
    st.header("🚨 Gestione Sanzioni")

elif menu == "Archivio Fatture":
    st.header("📁 Archivio Digitale")
