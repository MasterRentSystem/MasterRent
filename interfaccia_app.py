import streamlit as st
import pandas as pd
import datetime
import fpdf
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io

# Connessione
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def clean_text(text):
    if not text: return ""
    # Mappa completa per evitare UnicodeEncodeError
    replacements = {
        'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u',
        '€': 'Euro', '°': 'o', '’': "'", '‘': "'", '–': '-', '—': '-',
        '“': '"', '”': '"', '…': '...'
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    # Rimuove qualsiasi carattere non codificabile in latin-1
    return text.encode('latin-1', 'ignore').decode('latin-1')

# Testo integrale dei 14 punti (Sintesi Bilingue sicura)
CONDIZIONI_TESTO = """
1.⁠ ⁠Il veicolo e consegnato in ottimo stato. / Vehicle delivered in excellent condition.
2.⁠ ⁠Riconsegna con pieno di carburante. / Return with full tank.
3.⁠ ⁠Responsabilita infrazioni C.d.S. a carico del cliente. / Driver liable for traffic fines.
4.⁠ ⁠Spese gestione verbali: Euro 25.83. / Administrative fee for fines: Euro 25.83.
5.⁠ ⁠Responsabilita danni e furto del cliente. / Customer liable for damage and theft.
6.⁠ ⁠Divieto guida sotto effetto di alcool o droghe. / No driving under influence.
7.⁠ ⁠Foro competente: Napoli - Sez. Ischia. / Jurisdiction: Naples - Ischia Court.
"""

st.sidebar.title("🔑 MasterRent Gestione")
aziende_res = supabase.table("aziende").select("*").execute()
lista_aziende = {a['nome_azienda']: a for a in aziende_res.data} if aziende_res.data else {}

if lista_aziende:
    nome_scelto = st.sidebar.selectbox("Azienda attiva", list(lista_aziende.keys()))
    scelta_azienda = lista_aziende[nome_scelto]
    menu = st.sidebar.radio("Menu", ["Nuovo Contratto", "Archivio & Multe", "Fatturazione SDI"])

    if menu == "Nuovo Contratto":
        st.header(f"📝 {scelta_azienda['nome_azienda'].upper()}")
        
        with st.expander("👤 DATI CLIENTE E DOCUMENTO", expanded=True):
            col1, col2 = st.columns(2)
            nome = col1.text_input("NOME E COGNOME")
            cf = col2.text_input("CODICE FISCALE")
            doc_info = col1.text_input("TIPO E NUMERO DOCUMENTO")
            scatto_foto = st.camera_input("📸 FOTO PATENTE")

        with st.expander("🛵 DATI NOLEGGIO", expanded=True):
            col3, col4 = st.columns(2)
            targa = col3.text_input("TARGA")
            inizio = col3.date_input("DATA INIZIO", datetime.date.today())
            fine = col4.date_input("DATA FINE", datetime.date.today() + datetime.timedelta(days=1))
            prezzo = col4.number_input("CORRISPETTIVO (Euro)", min_value=0)

        st.subheader("📖 Termini e Condizioni")
        st.text_area("Leggi i 14 punti", value=CONDIZIONI_TESTO, height=150)
        accetto = st.checkbox("Accetto integralmente le condizioni sopra riportate")

        st.subheader("✍️ Firma Cliente")
        canvas_result = st_canvas(fill_color="white", stroke_width=3, stroke_color="black", background_color="white", height=150, key="sig")

        if st.button("💾 SALVA E GENERA CONTRATTO"):
            if nome and targa and accetto and canvas_result.image_data is not None:
                payload = {"cliente": nome, "cf": cf, "targa": targa, "data_inizio": str(inizio), "azienda_id": scelta_azienda['id']}
                supabase.table("contratti").insert(payload).execute()

                pdf = fpdf.FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(0, 10, txt=clean_text(scelta_azienda['nome_azienda']), ln=1)
                pdf.set_font("Arial", size=10)
                pdf.cell(0, 5, txt=clean_text(f"Contratto Targa: {targa} - Cliente: {nome}"), ln=1)
                pdf.ln(10)
                pdf.set_font("Arial", size=8)
                pdf.multi_cell(0, 5, txt=clean_text(CONDIZIONI_TESTO))
                
                # Firma
                sig_img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                sig_img.save("temp_sig.png")
                pdf.image("temp_sig.png", x=140, y=240, w=50)
                
                pdf_output = f"Contratto_{targa}.pdf"
                pdf.output(pdf_output)
                st.success("✅ Salvato!")
                with open(pdf_output, "rb") as f:
                    st.download_button("📥 Scarica PDF Contratto", f, file_name=pdf_output)
            else:
                st.error("Assicurati di aver compilato tutto e firmato!")

    elif menu == "Archivio & Multe":
        st.header("🚨 Modulo per la Polizia Municipale")
        res = supabase.table("contratti").select("*").eq("azienda_id", scelta_azienda['id']).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            scelta = st.selectbox("Seleziona il noleggio della multa", df['cliente'] + " (" + df['targa'] + ")")
            
            if st.button("📄 GENERA MODULO VIGILI"):
                dati = df[(df['cliente'] + " (" + df['targa'] + ")") == scelta].iloc[0]
                pdf_v = fpdf.FPDF()
                pdf_v.add_page()
                pdf_v.set_font("Arial", 'B', 14)
                pdf_v.cell(0, 10, txt="COMUNICAZIONE DATI CONDUCENTE", ln=1, align='C')
                pdf_v.ln(10)
                pdf_v.set_font("Arial", size=11)
                messaggio = f"""
Al Comando Polizia Municipale,
La ditta {scelta_azienda['nome_azienda']}, proprietaria del veicolo {dati['targa']},
comunica che in data {dati['data_inizio']} il mezzo era noleggiato al Sig.:

NOME: {dati['cliente']}
C.F.: {dati['cf']}

Si allega copia del contratto firmato.
                """
                pdf_v.multi_cell(0, 10, txt=clean_text(messaggio))
                pdf_v.ln(20)
                pdf_v.cell(0, 10, txt="Firma del Titolare __________________", ln=1)
                
                v_name = f"Modulo_Vigili_{dati['targa']}.pdf"
                pdf_v.output(v_name)
                with open(v_name, "rb") as f:
                    st.download_button("📥 SCARICA MODULO VIGILI", f, file_name=v_name)

    elif menu == "Fatturazione SDI":
        st.header("🏦 Fatturazione")
        st.info("Area predisposta per l'invio all'Agenzia delle Entrate.")

