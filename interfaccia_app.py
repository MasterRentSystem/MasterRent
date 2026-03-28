import streamlit as st
import pandas as pd
import datetime
import fpdf
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io

# 1. CONNESSIONE SUPABASE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# 2. FUNZIONE PULIZIA TESTO
def clean_t(text):
    if not text: return ""
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '°': 'o', '’': "'"}
    for k, v in repls.items(): text = text.replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

# 3. TESTI LEGALI
CONDIZIONI_ITA = """1) Veicolo in ottimo stato. 2) Riconsegna con pieno. 3) Responsabilita danni/furto cliente. 4) Multe: resp. cliente + Euro 25.83 gestione. 5) No alcool/droghe. 6) Termine noleggio come da contratto. 7) Sinistri: denuncia immediata."""
CONDIZIONI_ENG = """1) Excellent condition. 2) Full tank return. 3) Damage/theft liability: customer. 4) Fines: customer + Euro 25.83 fee. 5) No alcohol/drugs. 6) Return by due date. 7) Accidents: immediate report."""

st.sidebar.title("🚀 MasterRent Ischia")
aziende_res = supabase.table("aziende").select("*").execute()
lista_aziende = {a['nome_azienda']: a for a in aziende_res.data} if aziende_res.data else {}

if lista_aziende:
    nome_scelto = st.sidebar.selectbox("Seleziona Azienda", list(lista_aziende.keys()))
    azienda = lista_aziende[nome_scelto]
    menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Contratto", "🚨 Archivio & Multe", "🏦 Fatturazione SDI"])

    if menu == "📝 Nuovo Contratto":
        st.header(f"Noleggio: {azienda['nome_azienda']}")
        with st.expander("👤 DATI CLIENTE", expanded=True):
            col1, col2 = st.columns(2)
            nome = col1.text_input("NOME E COGNOME")
            cf = col2.text_input("CODICE FISCALE")
            residenza = col1.text_input("RESIDENZA")
            doc_dati = col2.text_input("DOCUMENTO (Tipo/Num)")
        with st.expander("🛵 DATI NOLEGGIO", expanded=True):
            targa = st.text_input("TARGA")
            prezzo = st.number_input("CORRISPETTIVO (€)", min_value=0)
            inizio = st.date_input("INIZIO", datetime.date.today())
            fine = st.date_input("FINE", datetime.date.today() + datetime.timedelta(days=1))
        
        st.camera_input("📸 FOTO PATENTE")
        st.checkbox("Accetto i 14 punti e la Privacy")
        st.subheader("✍️ Firma")
        canvas = st_canvas(fill_color="white", stroke_width=3, stroke_color="black", background_color="white", height=150, key="sig")

        if st.button("💾 GENERA CONTRATTO"):
            if nome and targa:
                payload = {"cliente": nome, "cf": cf, "targa": targa, "data_inizio": str(inizio), "azienda_id": azienda['id'], "residenza": residenza, "documento": doc_dati}
                supabase.table("contratti").insert(payload).execute()
                st.success("Contratto Salvato!")

    elif menu == "🚨 Archivio & Multe":
        st.header("Modulo per Polizia Municipale")
        res = supabase.table("contratti").select("*").eq("azienda_id", azienda['id']).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            sel_nome = st.selectbox("Seleziona il Cliente", df['cliente'] + " (" + df['targa'] + ")")
            dati = df[(df['cliente'] + " (" + df['targa'] + ")") == sel_nome].iloc[0]
            
            if st.button("📄 SCARICA MODULO VIGILI"):
                pdf_v = fpdf.FPDF()
                pdf_v.add_page()
                pdf_v.set_font("Arial", 'B', 14)
                pdf_v.cell(0, 10, txt="COMUNICAZIONE DATI CONDUCENTE", ln=1, align='C')
                pdf_v.ln(10)
                pdf_v.set_font("Arial", size=11)
                testo = f"""Spett.le Comando Polizia Municipale,
La ditta {azienda['nome_azienda']}, con sede in Via Cognole 5, Forio, 
in riferimento al verbale ricevuto per il veicolo targa {dati['targa']}, 
comunica che in data {dati['data_inizio']} il mezzo era affidato a:

NOME: {dati['cliente']}
C.F.: {dati.get('cf', 'N/D')}
RESIDENZA: {dati.get('residenza', 'N/D')}
DOCUMENTO: {dati.get('documento', 'N/D')}

Si allega copia del contratto di noleggio firmato.
                """
                pdf_v.multi_cell(0, 10, txt=clean_t(testo))
                pdf_v.ln(20)
                pdf_v.cell(0, 10, txt="Firma del Titolare (Battaglia Marianna)", ln=1)
                
                v_name = f"Vigili_{dati['targa']}.pdf"
                pdf_v.output(v_name)
                with open(v_name, "rb") as f:
                    st.download_button("📥 Scarica Modulo per il Comune", f, file_name=v_name)

    elif menu == "🏦 Fatturazione SDI":
        st.header("Fatturazione Elettronica")
        st.write("Area predisposta per l'invio SDI.")

