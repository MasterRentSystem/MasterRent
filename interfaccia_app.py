import streamlit as st
import pandas as pd
import datetime
import fpdf
from supabase import create_client
from streamlit_drawable_canvas import st_canvas

# Connessione
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.sidebar.title("🔑 Accesso Gestore")
aziende_res = supabase.table("aziende").select("*").execute()
lista_aziende = {a['nome_azienda']: a for a in aziende_res.data} if aziende_res.data else {}

if lista_aziende:
    nome_scelto = st.sidebar.selectbox("Seleziona il tuo Noleggio", list(lista_aziende.keys()))
    scelta_azienda = lista_aziende[nome_scelto]
    
    menu = st.sidebar.radio("Navigazione", ["Nuovo Contratto", "Archivio & Multe", "Fatturazione SDI"])

    if menu == "Nuovo Contratto":
        st.header(f"📝 Nuovo Contratto - {scelta_azienda['nome_azienda']}")
        
        with st.expander("Anagrafica Cliente", expanded=True):
            col1, col2 = st.columns(2)
            nome = col1.text_input("NOME E COGNOME")
            data_nascita = col2.date_input("DATA DI NASCITA", datetime.date(1990, 1, 1))
            luogo_nascita = col1.text_input("LUOGO DI NASCITA")
            cf = col2.text_input("CODICE FISCALE")
            residenza = col1.text_input("RESIDENZA")
            telefono = col2.text_input("TELEFONO/WHATSAPP")
        
        with st.expander("Dati Veicolo e Noleggio", expanded=True):
            col3, col4 = st.columns(2)
            targa = col3.text_input("TARGA SCOOTER/AUTO")
            km_uscita = col4.text_input("KM USCITA")
            tipo_doc = col3.selectbox("TIPO DOCUMENTO", ["Patente", "Carta Identità", "Passaporto"])
            num_doc = col4.text_input("NUMERO DOCUMENTO")
            prezzo_tot = col3.number_input("TOTALE PAGATO (€)", min_value=0)
            data_inizio = col4.date_input("DATA INIZIO", datetime.date.today())

        st.subheader("📸 Documentazione")
        foto_doc = st.camera_input("Scatta foto al Documento")

        st.subheader("✍️ Firma del Cliente / Customer Signature")
        st.info("Firmare nel riquadro bianco sottostante")
        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 255, 1)",
            stroke_width=3,
            stroke_color="#000000",
            background_color="#FFFFFF",
            height=150,
            key="canvas",
        )

        if st.button("💾 GENERA E SALVA"):
            if nome and cf and targa and canvas_result.image_data is not None:
                # Caricamento dati su Supabase
                payload = {
                    "cliente": nome, "cf": cf, "luogo_nascita": luogo_nascita,
                    "residenza": residenza, "telefono": telefono, "targa": targa,
                    "km_uscita": km_uscita, "tipo_doc": tipo_doc, "num_doc": num_doc,
                    "prezzo_tot": str(prezzo_tot), "data_inizio": str(data_inizio),
                    "azienda_id": scelta_azienda['id']
                }
                supabase.table("contratti").insert(payload).execute()

                # Generazione PDF Bilingue
                pdf = fpdf.FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(200, 10, txt=scelta_azienda['nome_azienda'], ln=1, align='C')
                
                pdf.set_font("Arial", size=10)
                pdf.ln(5)
                pdf.cell(0, 10, txt=f"CONTRATTO DI NOLEGGIO / RENTAL AGREEMENT", ln=1, align='C')
                pdf.ln(5)
                pdf.cell(0, 7, txt=f"Cliente: {nome} | CF: {cf} | Tel: {telefono}", ln=1)
                pdf.cell(0, 7, txt=f"Veicolo: {targa} | KM Uscita: {km_uscita}", ln=1)
                
                pdf.ln(5)
                pdf.set_font("Arial", 'B', 9)
                pdf.cell(0, 5, txt="TERMINI E CONDIZIONI / TERMS AND CONDITIONS", ln=1)
                pdf.set_font("Arial", size=7)
                testo_it = "Il cliente dichiara di ricevere il veicolo in ottimo stato e si assume la responsabilità per multe e danni."
                testo_en = "The customer declares to receive the vehicle in excellent condition and assumes responsibility for fines and damages."
                pdf.multi_cell(0, 5, txt=f"ITA: {testo_it}\nENG: {testo_en}")
                
                pdf_name = f"Contratto_{targa}.pdf"
                pdf.output(pdf_name)
                
                st.success("✅ Contratto salvato e PDF pronto!")
                with open(pdf_name, "rb") as f:
                    st.download_button("📥 SCARICA CONTRATTO FIRMATO", f, file_name=pdf_name)
            else:
                st.error("Assicurati di aver inserito i dati e la firma!")

    elif menu == "Archivio & Multe":
        st.header("🚨 Archivio")
        res = supabase.table("contratti").select("*").eq("azienda_id", scelta_azienda['id']).execute()
        if res.data:
            st.dataframe(pd.DataFrame(res.data))

