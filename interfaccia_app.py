import streamlit as st
import pandas as pd
import datetime
import fpdf
import requests
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
from PIL import Image

# 1. CONNESSIONI
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# Credenziali Aruba (Da inserire nei secrets di Streamlit in futuro)
ARUBA_AUTH_URL = "https://auth.fatturazioneelettronica.aruba.it/auth/signin"
ARUBA_API_URL = "https://api.fatturazioneelettronica.aruba.it/services/invoice/upload"

def clean_t(text):
    if not text: return ""
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '°': 'o', '’': "'"}
    for k, v in repls.items(): text = text.replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

st.sidebar.title("🚀 MasterRent Ischia")
aziende_res = supabase.table("aziende").select("*").execute()
lista_aziende = {a['nome_azienda']: a for a in aziende_res.data} if aziende_res.data else {}

if lista_aziende:
    nome_scelto = st.sidebar.selectbox("Azienda Selezionata", list(lista_aziende.keys()))
    azienda = lista_aziende[nome_scelto]
    menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Contratto", "🚨 Archivio & Multe", "🏦 Fatturazione Aruba"])

    # --- SEZIONI ESISTENTI (Protette) ---
    if menu == "📝 Nuovo Contratto":
        st.header(f"Contratto: {azienda['nome_azienda']}")
        nome = st.text_input("NOME E COGNOME")
        targa = st.text_input("TARGA")
        prezzo = st.number_input("PREZZO (€)", min_value=0)
        st.camera_input("📸 FOTO PATENTE")
        canvas = st_canvas(fill_color="white", stroke_width=3, stroke_color="black", background_color="white", height=150, key="sig")
        if st.button("💾 SALVA CONTRATTO"):
            payload = {"cliente": nome, "targa": targa, "prezzo_tot": str(prezzo), "azienda_id": azienda['id'], "data_inizio": str(datetime.date.today())}
            supabase.table("contratti").insert(payload).execute()
            st.success("Contratto Salvato!")

    elif menu == "🚨 Archivio & Multe":
        st.header("Gestione Verbali")
        res = supabase.table("contratti").select("*").eq("azienda_id", azienda['id']).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            st.selectbox("Seleziona Cliente", df['cliente'] + " (" + df['targa'] + ")")
            st.button("📄 GENERA MODULO VIGILI")

    # --- NUOVA SEZIONE: FATTURAZIONE ARUBA ---
    elif menu == "🏦 Fatturazione Aruba":
        st.header("🏦 Invio SDI tramite Aruba")
        res = supabase.table("contratti").select("*").eq("azienda_id", azienda['id']).execute()
        
        if res.data:
            df = pd.DataFrame(res.data)
            sel_f = st.selectbox("Contratto da fatturare", df['cliente'] + " - " + df['targa'])
            dati = df[(df['cliente'] + " - " + df['targa']) == sel_f].iloc[0]
            
            col_a, col_b = st.columns(2)
            sdi = col_a.text_input("Codice Univoco SDI", value="0000000")
            piva = col_b.text_input("P.IVA/CF Cliente", value=dati.get('cf', ''))
            
            imp = float(dati.get('prezzo_tot', 0))
            iva = imp * 0.22
            totale = imp + iva
            
            st.markdown(f"### Totale da inviare: *€ {totale:.2f}*")
            
            if st.button("🚀 INVIA FATTURA REALE AD ARUBA"):
                # Simulazione chiamata API Aruba
                st.info("🔄 Connessione ai server Aruba in corso...")
                # Qui andrà il codice che invia il file XML ad Aruba
                st.warning("⚠️ Per l'invio finale serve inserire la API KEY di Aruba nei Secrets.")
                st.success(f"Fattura pronta per l'invio a {dati['cliente']}!")
        else:
            st.info("Nessun contratto pronto per la fattura.")

