import streamlit as st
import pandas as pd
import datetime
import fpdf
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io

# 1. CONNESSIONE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def clean_t(text):
    if not text: return ""
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '°': 'o', '’': "'"}
    for k, v in repls.items(): text = text.replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

st.sidebar.title("🚀 MasterRent Ischia")
aziende_res = supabase.table("aziende").select("*").execute()
lista_aziende = {a['nome_azienda']: a for a in aziende_res.data} if aziende_res.data else {}

if lista_aziende:
    nome_scelto = st.sidebar.selectbox("Seleziona Azienda", list(lista_aziende.keys()))
    azienda = lista_aziende[nome_scelto]
    menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Contratto", "🚨 Archivio & Multe", "🏦 Fatturazione SDI"])

    # --- SEZIONE CONTRATTO (Invariata per non rompere nulla) ---
    if menu == "📝 Nuovo Contratto":
        st.header(f"Noleggio: {azienda['nome_azienda']}")
        col1, col2 = st.columns(2)
        nome = col1.text_input("NOME E COGNOME")
        targa = col2.text_input("TARGA")
        prezzo = st.number_input("PREZZO TOTALE (€)", min_value=0)
        st.camera_input("📸 FOTO PATENTE")
        canvas = st_canvas(fill_color="white", stroke_width=3, stroke_color="black", background_color="white", height=150, key="sig")
        if st.button("💾 SALVA CONTRATTO"):
            payload = {"cliente": nome, "targa": targa, "prezzo_tot": str(prezzo), "azienda_id": azienda['id'], "data_inizio": str(datetime.date.today())}
            supabase.table("contratti").insert(payload).execute()
            st.success("Contratto Salvato!")

    # --- SEZIONE MULTE (Invariata) ---
    elif menu == "🚨 Archivio & Multe":
        st.header("Modulo Polizia Municipale")
        res = supabase.table("contratti").select("*").eq("azienda_id", azienda['id']).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            sel = st.selectbox("Seleziona Cliente", df['cliente'] + " (" + df['targa'] + ")")
            st.button("📄 GENERA MODULO VIGILI")

    # --- NUOVA SEZIONE: FATTURAZIONE SDI ---
    elif menu == "🏦 Fatturazione SDI":
        st.header("🏦 Creazione Fattura Elettronica")
        res = supabase.table("contratti").select("*").eq("azienda_id", azienda['id']).execute()
        
        if res.data:
            df = pd.DataFrame(res.data)
            scelta_fatt = st.selectbox("Seleziona il noleggio da fatturare", df['cliente'] + " - " + df['targa'])
            dati_c = df[(df['cliente'] + " - " + df['targa']) == scelta_fatt].iloc[0]
            
            col_f1, col_f2 = st.columns(2)
            codice_sdi = col_f1.text_input("Codice Univoco / PEC", value="0000000")
            p_iva = col_f2.text_input("P.IVA / C.F. Cliente", value=dati_c.get('cf', ''))
            
            importo = float(dati_c.get('prezzo_tot', 0))
            iva = importo * 0.22
            totale_ivato = importo + iva
            
            st.write(f"*Riepilogo Importi:*")
            st.write(f"Imponibile: € {importo:.2f} | IVA (22%): € {iva:.2f} | *Totale: € {totale_ivato:.2f}*")
            
            if st.button("🚀 INVIA A SISTEMA DI INTERSCAMBIO (SDI)"):
                # Qui simuleremo l'invio o genereremo l'XML
                st.warning("⚠️ Collegamento API in corso. I dati sono pronti per l'invio ufficiale.")
                st.info(f"Fattura pronta per {dati_c['cliente']}. Destinatario: {codice_sdi}")
        else:
            st.info("Nessun contratto trovato per la fatturazione.")

