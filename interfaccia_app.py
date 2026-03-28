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

# Funzione per pulire i testi dagli accenti (per evitare errori PDF)
def clean_text(text):
    if not text: return ""
    replacements = {
        'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u',
        '€': 'Euro'
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text

st.sidebar.title("🔑 Accesso Gestore")
aziende_res = supabase.table("aziende").select("*").execute()
lista_aziende = {a['nome_azienda']: a for a in aziende_res.data} if aziende_res.data else {}

if lista_aziende:
    nome_scelto = st.sidebar.selectbox("Seleziona il tuo Noleggio", list(lista_aziende.keys()))
    scelta_azienda = lista_aziende[nome_scelto]
    
    menu = st.sidebar.radio("Navigazione", ["Nuovo Contratto", "Archivio & Multe"])

    if menu == "Nuovo Contratto":
        st.header(f"📝 {scelta_azienda['nome_azienda'].upper()}")
        
        with st.expander("👤 Anagrafica Cliente", expanded=True):
            col1, col2 = st.columns(2)
            nome = col1.text_input("NOME E COGNOME")
            cf = col2.text_input("CODICE FISCALE")
            data_nascita = col1.date_input("DATA DI NASCITA", datetime.date(1990, 1, 1))
            luogo_nascita = col2.text_input("LUOGO DI NASCITA")
            residenza = col1.text_input("RESIDENZA")
            telefono = col2.text_input("TELEFONO")
            tipo_doc = col1.selectbox("TIPO DOCUMENTO", ["Patente", "C.I.", "Passaporto"])
            num_doc = col2.text_input("NUMERO DOC")

        with st.expander("🛵 Dati Noleggio", expanded=True):
            col3, col4 = st.columns(2)
            targa = col3.text_input("TARGA VEICOLO")
            data_inizio = col3.date_input("DATA INIZIO", datetime.date.today())
            data_fine = col4.date_input("DATA FINE", datetime.date.today() + datetime.timedelta(days=1))
            prezzo_tot = col4.number_input("TOTALE (Euro)", min_value=0)

        st.subheader("✍️ Firma del Cliente")
        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 255, 1)", stroke_width=3,
            stroke_color="#000000", background_color="#FFFFFF",
            height=150, key="signature",
        )

        if st.button("💾 GENERA CONTRATTO E SALVA"):
            if nome and cf and targa and canvas_result.image_data is not None:
                # 1. Salva su DB
                payload = {
                    "cliente": nome, "cf": cf, "targa": targa, "prezzo_tot": str(prezzo_tot),
                    "data_inizio": str(data_inizio), "azienda_id": scelta_azienda['id'],
                    "telefono": telefono, "residenza": residenza
                }
                supabase.table("contratti").insert(payload).execute()

                # 2. Crea PDF
                pdf = fpdf.FPDF()
                pdf.add_page()
                
                # Intestazione
                pdf.set_font("Arial", 'B', 20)
                pdf.cell(0, 15, txt=clean_text(scelta_azienda['nome_azienda'].upper()), ln=1, align='C')
                
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 10, txt="CONTRATTO DI NOLEGGIO / RENTAL AGREEMENT", ln=1, align='C')
                pdf.ln(5)

                # Dati Cliente (Puliti da accenti)
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(0, 8, txt="DATI CLIENTE / CUSTOMER INFO", ln=1)
                pdf.set_font("Arial", size=10)
                
                pdf.cell(95, 8, txt=clean_text(f"Nome/Name: {nome}"), border=1)
                pdf.cell(95, 8, txt=clean_text(f"C.F./Tax ID: {cf}"), border=1, ln=1)
                pdf.cell(95, 8, txt=clean_text(f"Nato a: {luogo_nascita} il {data_nascita}"), border=1)
                pdf.cell(95, 8, txt=clean_text(f"Residente/Address: {residenza}"), border=1, ln=1)
                pdf.cell(95, 8, txt=clean_text(f"Tel: {telefono}"), border=1)
                pdf.cell(95, 8, txt=clean_text(f"Doc: {tipo_doc} n. {num_doc}"), border=1, ln=1)
                
                pdf.ln(5)

                # Dati Noleggio
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(0, 8, txt="DATI NOLEGGIO / RENTAL INFO", ln=1)
                pdf.set_font("Arial", size=10)
                
                pdf.cell(95, 8, txt=clean_text(f"Veicolo/Vehicle Targa: {targa}"), border=1)
                pdf.cell(95, 8, txt=clean_text(f"Prezzo/Price: Euro {prezzo_tot}"), border=1, ln=1)
                pdf.cell(95, 8, txt=clean_text(f"Inizio/Start: {data_inizio}"), border=1)
                pdf.cell(95, 8, txt=clean_text(f"Fine/End: {data_fine}"), border=1, ln=1)

                # Termini Legali
                pdf.ln(5)
                pdf.set_font("Arial", 'B', 9)
                pdf.cell(0, 5, txt="TERMINI E CONDIZIONI / TERMS AND CONDITIONS", ln=1)
                pdf.set_font("Arial", size=7)
                testo = "Il cliente riceve il veicolo in ottimo stato ed e responsabile per multe (con Euro 20 spese gestione) e danni. / Customer receives vehicle in excellent condition and is liable for fines (Euro 20 fee) and damages."
                pdf.multi_cell(0, 4, txt=testo)
                
                # Firma
                signature_img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                signature_img.save("firma.png")
                pdf.ln(5)
                pdf.cell(0, 5, txt="FIRMA DEL CLIENTE / CUSTOMER SIGNATURE:", ln=1)
                pdf.image("firma.png", x=10, w=50)
                
                pdf_name = f"Contratto_{targa}.pdf"
                pdf.output(pdf_name)
                
                st.success("✅ Contratto salvato e PDF generato!")
                with open(pdf_name, "rb") as f:
                    st.download_button("📥 SCARICA PDF", f, file_name=pdf_name)
            else:
                st.error("Dati mancanti o firma non rilevata!")

    elif menu == "Archivio & Multe":
        st.header("🚨 Archivio Storico")
        res = supabase.table("contratti").select("*").eq("azienda_id", scelta_azienda['id']).execute()
        if res.data:
            st.dataframe(pd.DataFrame(res.data))

