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
    replacements = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '°': 'o', '’': "'", '–': '-'}
    for k, v in replacements.items(): text = text.replace(k, v)
    return text

# Testo Condizioni Reali (Sintesi Bilingue)
CONDIZIONI_TESTO = """
1.⁠ ⁠Stato Veicolo: Ottimo stato, pieno carburante. / Vehicle: Excellent condition, full tank.
2.⁠ ⁠Responsabilita: Cliente responsabile per infrazioni CDS. / Liability: Customer responsible for traffic fines.
3.⁠ ⁠Penale Verbali: Euro 25.83 per spese gestione pratica. / Fine Fee: Euro 25.83 administrative fee.
4.⁠ ⁠Danni/Furto: Responsabilita totale del cliente. / Damage/Theft: Total customer liability.
5.⁠ ⁠Divieto: Guida sotto effetto alcool/droghe. / Prohibited: Driving under influence of alcohol/drugs.
"""

st.sidebar.title("🔑 Sistema Multi-Noleggio")
aziende_res = supabase.table("aziende").select("*").execute()
lista_aziende = {a['nome_azienda']: a for a in aziende_res.data} if aziende_res.data else {}

if lista_aziende:
    nome_scelto = st.sidebar.selectbox("Seleziona il tuo Noleggio", list(lista_aziende.keys()))
    scelta_azienda = lista_aziende[nome_scelto]
    menu = st.sidebar.radio("Menu Principale", ["Nuovo Contratto", "Archivio & Multe Comuni", "Fatturazione SDI"])

    # --- NUOVO CONTRATTO ---
    if menu == "Nuovo Contratto":
        st.header(f"📝 {scelta_azienda['nome_azienda'].upper()}")
        
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("NOME E COGNOME / FULL NAME")
            cf = st.text_input("CODICE FISCALE / TAX ID")
            telefono = st.text_input("CELLULARE / PHONE")
        with col2:
            targa = st.text_input("TARGA / PLATE")
            inizio = st.date_input("INIZIO / START", datetime.date.today())
            fine = st.date_input("FINE / END", datetime.date.today() + datetime.timedelta(days=1))
        
        foto_doc = st.camera_input("📸 SCATTA FOTO PATENTE / TAKE PHOTO ID")
        
        st.subheader("📖 Termini e Condizioni")
        st.text_area("Leggi qui / Read here", value=CONDIZIONI_TESTO, height=150)
        accetto = st.checkbox("Accetto i 14 punti e la Privacy / I accept terms and Privacy")

        st.subheader("✍️ Firma Cliente / Signature")
        canvas_result = st_canvas(fill_color="white", stroke_width=3, stroke_color="black", background_color="white", height=150, key="sig")

        if st.button("💾 SALVA E GENERA CONTRATTO"):
            if nome and targa and accetto and canvas_result.image_data is not None:
                # Salva su DB
                payload = {"cliente": nome, "cf": cf, "targa": targa, "data_inizio": str(inizio), "azienda_id": scelta_azienda['id'], "telefono": telefono}
                supabase.table("contratti").insert(payload).execute()

                # PDF Contratto
                pdf = fpdf.FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(0, 10, txt=clean_text(scelta_azienda['nome_azienda']), ln=1)
                pdf.set_font("Arial", size=10)
                pdf.cell(0, 5, txt=f"Contratto Noleggio Targa: {targa}", ln=1)
                pdf.ln(5)
                pdf.multi_cell(0, 5, txt=clean_text(CONDIZIONI_TESTO))
                
                # Firma nel PDF
                signature_img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                signature_img.save("firma.png")
                pdf.image("firma.png", x=10, y=pdf.get_y()+10, w=40)
                
                pdf_name = f"Contratto_{targa}.pdf"
                pdf.output(pdf_name)
                st.success("✅ Contratto registrato!")
                with open(pdf_name, "rb") as f:
                    st.download_button("📥 Scarica PDF Contratto", f, file_name=pdf_name)
            else:
                st.error("Mancano dati, foto o firma!")

    # --- ARCHIVIO & MULTE ---
    elif menu == "Archivio & Multe Comuni":
        st.header("🚨 Generazione Moduli per i Vigili")
        res = supabase.table("contratti").select("*").eq("azienda_id", scelta_azienda['id']).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            scelta = st.selectbox("Seleziona il Cliente della Multa", df['cliente'] + " - " + df['targa'])
            
            if st.button("📄 GENERA MODULO PER COMUNE"):
                dati = df[(df['cliente'] + " - " + df['targa']) == scelta].iloc[0]
                
                # Creazione Modulo Vigili
                pdf_m = fpdf.FPDF()
                pdf_m.add_page()
                pdf_m.set_font("Arial", 'B', 14)
                pdf_m.cell(0, 10, txt="COMUNICAZIONE DATI CONDUCENTE", ln=1, align='C')
                pdf_m.ln(10)
                pdf_m.set_font("Arial", size=11)
                testo_vigili = f"""
Al Comando Polizia Municipale,

La sottoscritta ditta {scelta_azienda['nome_azienda']}, proprietaria del veicolo targa {dati['targa']},
comunica che in data {dati['data_inizio']} il veicolo era affidato in noleggio al Sig./ra:

NOME: {dati['cliente']}
CODICE FISCALE: {dati['cf']}

Si allega copia del contratto e del documento d'identita.
                """
                pdf_m.multi_cell(0, 10, txt=clean_text(testo_vigili))
                pdf_m.ln(20)
                pdf_m.cell(0, 10, txt="Firma del Titolare (Battaglia Rent)", ln=1)
                
                nome_m = f"Modulo_Vigili_{dati['targa']}.pdf"
                pdf_m.output(nome_m)
                with open(nome_m, "rb") as f:
                    st.download_button("📥 SCARICA MODULO VIGILI", f, file_name=nome_m)
        else:
            st.info("Nessun noleggio trovato.")

    # --- FATTURAZIONE ---
    elif menu == "Fatturazione SDI":
        st.header("🏦 Fatturazione Elettronica")
        st.write(f"Gestione SDI per: {scelta_azienda['nome_azienda']}")
        st.button("Invia Fatture Selezionate a AdE")

