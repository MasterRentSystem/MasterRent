import streamlit as st
import pandas as pd
import datetime
import fpdf
from supabase import create_client

# Connessione
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- LOGIN SIMULATO ---
st.sidebar.title("🔑 Accesso Gestore")
aziende_res = supabase.table("aziende").select("*").execute()
lista_aziende = {a['nome_azienda']: a for a in aziende_res.data} if aziende_res.data else {}

if not lista_aziende:
    st.error("Errore: Nessuna azienda trovata nel DB.")
    scelta_azienda = None
else:
    nome_scelto = st.sidebar.selectbox("Seleziona il tuo Noleggio", list(lista_aziende.keys()))
    scelta_azienda = lista_aziende[nome_scelto]

if scelta_azienda:
    st.sidebar.success(f"Loggato: {scelta_azienda['nome_azienda']}")
    menu = st.sidebar.radio("Navigazione", ["Nuovo Contratto", "Archivio & Multe", "Fatturazione SDI"])

    # --- 1. NUOVO CONTRATTO ---
    if menu == "Nuovo Contratto":
        st.header(f"📝 Nuovo Noleggio - {scelta_azienda['nome_azienda']}")
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("NOME E COGNOME CLIENTE")
            cf = st.text_input("CODICE FISCALE")
        with col2:
            targa = st.text_input("TARGA VEICOLO")
            data = st.date_input("DATA INIZIO", datetime.date.today())
        
        foto = st.camera_input("FOTO PATENTE")
        firma = st.checkbox("IL CLIENTE ACCETTA I TERMINI")

        if st.button("💾 SALVA CONTRATTO"):
            if nome and cf and targa and firma:
                # Salvataggio con azienda_id per isolare i dati
                payload = {
                    "cliente": nome, "cf": cf, "targa": targa, 
                    "data_inizio": str(data), "azienda_id": scelta_azienda['id']
                }
                supabase.table("contratti").insert(payload).execute()
                st.success("✅ Salvato con successo!")
            else:
                st.error("Compila tutti i campi obbligatori!")

    # --- 2. ARCHIVIO & GENERAZIONE MULTA ---
    elif menu == "Archivio & Multe":
        st.header("🚨 Gestione Verbali e Multe")
        # Vediamo solo i contratti di QUESTA azienda
        res = supabase.table("contratti").select("*").eq("azienda_id", scelta_azienda['id']).execute()
        
        if res.data:
            df = pd.DataFrame(res.data)
            st.write("Seleziona un contratto per generare il modulo per i Vigili:")
            contratto_scelto = st.selectbox("Cerca per Nome o Targa", df['cliente'] + " - " + df['targa'])
            
            if st.button("📄 GENERA MODULO COMUNE (PDF)"):
                dati = df[(df['cliente'] + " - " + df['targa']) == contratto_scelto].iloc[0]
                
                # Creazione PDF Formale
                pdf = fpdf.FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(200, 10, txt=f"COMUNICAZIONE DATI CONDUCENTE - {scelta_azienda['nome_azienda']}", ln=1, align='C')
                pdf.set_font("Arial", size=12)
                pdf.ln(10)
                pdf.multi_cell(0, 10, txt=f"Spett.le Comando Polizia Municipale,\n\nin riferimento al verbale indicato, si comunica che in data {dati['data_inizio']} il veicolo targa {dati['targa']} era noleggiato al Sig./Sig.ra:\n\nNOME: {dati['cliente']}\nC.F.: {dati['cf']}\n\nSi allega copia del documento d'identità.")
                
                pdf_output = f"Modulo_Multa_{dati['targa']}.pdf"
                pdf.output(pdf_output)
                
                with open(pdf_output, "rb") as f:
                    st.download_button("📥 SCARICA MODULO PRONTO", f, file_name=pdf_output)
        else:
            st.info("Non ci sono ancora contratti registrati per questa azienda.")

    # --- 3. FATTURAZIONE SDI ---
    elif menu == "Fatturazione SDI":
        st.header("🏦 Fatturazione Elettronica")
        st.write(f"Dati Fiscali Azienda: {scelta_azienda['partita_iva']}")
        st.info("Prossimo step: Integrazione con invio automatico SDI.")

