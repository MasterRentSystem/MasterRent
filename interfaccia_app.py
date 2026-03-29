import streamlit as st
import pandas as pd
import datetime
import fpdf
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io
import urllib.parse

# 1. CONNESSIONE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def clean_t(text):
    if not text: return ""
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in repls.items(): text = text.replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

# DATI AZIENDA MARIANNA (Per Modulo Multe)
TITOLARE_INFO = "BATTAGLIA MARIANNA, nata a Berlino (Germania) il 13/01/1987\nResidente a Forio in Via Cognole n. 5\nC.F.: BTTMNN87A53Z112S | P.IVA: 10252601215"

st.sidebar.title("🚀 MasterRent Ischia")
aziende_res = supabase.table("aziende").select("*").execute()
lista_aziende = {a['nome_azienda']: a for a in aziende_res.data} if aziende_res.data else {}

if lista_aziende:
    azienda = lista_aziende[st.sidebar.selectbox("Azienda", list(lista_aziende.keys()))]
    menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Noleggio", "🗄️ Archivio (Cerca Targa)"])

    if menu == "📝 Nuovo Noleggio":
        st.header(f"Nuovo Contratto: {azienda['nome_azienda']}")
        
        # INPUT DATI
        st.subheader("👤 Dati Cliente")
        c1, c2 = st.columns(2)
        cliente = c1.text_input("Nome e Cognome")
        cf_cliente = c2.text_input("Codice Fiscale")
        nascita = c1.text_input("Luogo/Data Nascita")
        residenza = c2.text_input("Indirizzo Residenza")
        num_doc = c1.text_input("Num. Patente")
        telefono = c2.text_input("Cellulare (WhatsApp)")

        st.subheader("🛵 Dati Veicolo e Fattura")
        c3, c4 = st.columns(2)
        targa = c3.text_input("TARGA").upper()
        prezzo = c4.number_input("Prezzo (€)", min_value=0)
        p_iva = c3.text_input("P.IVA (se richiesta)")
        sdi = c4.text_input("SDI / PEC")

        foto_p = st.camera_input("📸 Foto Patente")
        st.subheader("✍️ Firma")
        canvas = st_canvas(fill_color="white", stroke_width=2, height=150, key="sig_v5")

        if st.button("💾 SALVA TUTTO"):
            if cliente and targa and canvas.image_data is not None:
                try:
                    # SALVATAGGIO DB (Includiamo P.IVA e SDI)
                    dat = {
                        "cliente": cliente, "cf": cf_cliente, "targa": targa, 
                        "azienda_id": azienda['id'], "data_inizio": str(datetime.date.today()), 
                        "telefono": telefono, "p_iva": p_iva, "sdi": sdi,
                        "luogo_nascita": nascita, "residenza": residenza, "num_doc": num_doc
                    }
                    res_db = supabase.table("contratti").insert(dat).execute()
                    st.success(f"Noleggio {targa} salvato correttamente!")
                except Exception as e:
                    st.error(f"Errore: {e}")

    elif menu == "🗄️ Archivio (Cerca Targa)":
        st.header("🔎 Ricerca Documentazione")
        targa_search = st.text_input("Inserisci TARGA per generare i moduli", "").upper()
        
        if targa_search:
            res = supabase.table("contratti").select("*").eq("targa", targa_search).execute()
            if res.data:
                for c in res.data:
                    with st.expander(f"Noleggio del {c['data_inizio']} - {c['cliente']}"):
                        st.write(f"*Dati:* {c['cliente']} | CF: {c['cf']}")
                        
                        # GENERAZIONE PDF AL VOLO (I 3 MODULI SEPARATI)
                        # 1. MODULO MULTE (Precompilato)
                        p_mul = fpdf.FPDF()
                        p_mul.add_page()
                        p_mul.set_font("Arial", size=10); p_mul.multi_cell(0, 5, txt=clean_t(TITOLARE_INFO))
                        p_mul.ln(10); p_mul.set_font("Arial", 'B', 12); p_mul.cell(0, 7, "COMUNICAZIONE LOCAZIONE VEICOLO", ln=1, align='C')
                        p_mul.ln(5); p_mul.set_font("Arial", size=10)
                        p_mul.multi_cell(0, 6, txt=clean_t(f"Si comunica che il veicolo {c['targa']} era in locazione a:\n\nNome: {c['cliente']}\nCF: {c['cf']}\nNato a: {c.get('luogo_nascita', '---')}\nResidenza: {c.get('residenza', '---')}\nDoc: {c.get('num_doc', '---')}"))
                        p_mul.ln(10); p_mul.cell(0, 10, "In fede, Marianna Battaglia", align='R')
                        b_mul = p_mul.output(dest='S').encode('latin-1')

                        # 2. MODULO FATTURA
                        p_fat = fpdf.FPDF()
                        p_fat.add_page()
                        p_fat.set_font("Arial", 'B', 14); p_fat.cell(0, 10, "DATI PER FATTURAZIONE", ln=1, align='C')
                        p_fat.set_font("Arial", size=11); p_fat.multi_cell(0, 8, txt=clean_t(f"Cliente: {c['cliente']}\nP.IVA: {c.get('p_iva', '---')}\nSDI: {c.get('sdi', '---')}\nTarga: {c['targa']}\nData: {c['data_inizio']}"))
                        b_fat = p_fat.output(dest='S').encode('latin-1')

                        col1, col2 = st.columns(2)
                        col1.download_button("🚨 Scarica Modulo Multe", b_mul, f"Multe_{c['targa']}_{c['data_inizio']}.pdf")
                        col2.download_button("💰 Scarica Dati Fattura", b_fat, f"Fattura_{c['cliente']}.pdf")
            else:
                st.warning("Nessun noleggio trovato per questa targa.")

