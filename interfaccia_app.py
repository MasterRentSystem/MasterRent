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
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '°': 'o', '’': "'", '–': '-'}
    for k, v in repls.items(): text = text.replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

# TESTO LEGALE INTEGRALE (14 PUNTI)
TESTO_LEGALE = """1. Consegna veicolo in ottimo stato, riconsegna con pieno carburante. 2. Cliente responsabile infrazioni C.d.S. 3. Addebito Euro 25.83 per gestione amministrativa verbali. 4. Responsabilita danni, furto e incendio a carico del cliente. 5. Divieto trasporto persone eccedenti e guida in stato di ebbrezza o sotto effetto di stupefacenti. 6. Noleggio termina alla data/ora indicata. 7. In caso di sinistro, obbligo denuncia immediata e raccolta dati controparte. 8. Divieto sub-noleggio. 9. Il cliente dichiara di avere la patente valida. 10. Smarrimento chiavi: penale Euro 50. 11. Il veicolo non puo uscire dall'isola di Ischia. 12. Assistenza stradale a carico del cliente se causata da negligenza. 13. Foro competente: Napoli - Sezione distaccata Ischia. 14. Informativa Privacy: I dati sono trattati secondo il GDPR 679/2016 per finalita contrattuali."""

st.sidebar.title("🚀 MasterRent Ischia")
aziende_res = supabase.table("aziende").select("*").execute()
lista_aziende = {a['nome_azienda']: a for a in aziende_res.data} if aziende_res.data else {}

if lista_aziende:
    nome_scelto = st.sidebar.selectbox("Seleziona Azienda", list(lista_aziende.keys()))
    azienda = lista_aziende[nome_scelto]
    menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Contratto", "🚨 Archivio & Multe", "🏦 Fatturazione Aruba"])

    if menu == "📝 Nuovo Contratto":
        st.header(f"Contratto: {azienda['nome_azienda']}")
        
        with st.expander("👤 DATI CLIENTE", expanded=True):
            col1, col2 = st.columns(2)
            nome = col1.text_input("NOME E COGNOME")
            cf = col2.text_input("CODICE FISCALE / P.IVA")
            residenza = col1.text_input("RESIDENZA COMPLETA")
            doc_dati = col2.text_input("DOCUMENTO (Tipo e Numero)")
            tel = col1.text_input("TELEFONO")

        with st.expander("🛵 DATI NOLEGGIO", expanded=True):
            col3, col4 = st.columns(2)
            targa = col3.text_input("TARGA VEICOLO")
            prezzo = col4.number_input("CORRISPETTIVO (Euro)", min_value=0)
            inizio = col3.date_input("INIZIO", datetime.date.today())
            fine = col4.date_input("FINE", datetime.date.today() + datetime.timedelta(days=1))

        st.camera_input("📸 SCATTA FOTO PATENTE")
        
        st.subheader("📖 Condizioni Generali e Privacy")
        st.text_area("Termini (1-14)", value=TESTO_LEGALE, height=180)
        accetto = st.checkbox("Accetto i 14 punti e il trattamento dei dati (Privacy)")

        st.subheader("✍️ Firma Legale del Cliente")
        canvas_result = st_canvas(fill_color="white", stroke_width=2, stroke_color="black", background_color="white", height=150, key="sig_legale")

        if st.button("💾 GENERA CONTRATTO LEGALE"):
            if nome and targa and accetto and canvas_result.image_data is not None:
                # Salva su DB
                payload = {"cliente": nome, "cf": cf, "targa": targa, "data_inizio": str(inizio), "azienda_id": azienda['id'], "residenza": residenza, "documento": doc_dati, "prezzo_tot": str(prezzo)}
                supabase.table("contratti").insert(payload).execute()

                # Genera PDF
                pdf = fpdf.FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(0, 10, txt=clean_t("Noleggio BATTAGLIA MARIANNA"), ln=1)
                pdf.set_font("Arial", size=8)
                pdf.cell(0, 5, txt="Via Cognole, 5 - 80075 Forio (NA) - P.IVA 10252601215", ln=1)
                pdf.ln(8)

                # Riepilogo
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(0, 8, txt="ESTREMI DEL CONTRATTO", ln=1, border='B')
                pdf.set_font("Arial", size=9)
                pdf.multi_cell(0, 5, txt=clean_t(f"Cliente: {nome}\nCF/PIVA: {cf}\nResidenza: {residenza}\nDoc: {doc_dati}\nVeicolo: {targa}\nPeriodo: {inizio} al {fine}\nPrezzo: Euro {prezzo}"))
                
                # Testo Legale Piccolo
                pdf.ln(5)
                pdf.set_font("Arial", 'B', 8)
                pdf.cell(0, 5, txt="CONDIZIONI GENERALI DI CONTRATTO (ARTT. 1-14)", ln=1)
                pdf.set_font("Arial", size=7)
                pdf.multi_cell(0, 4, txt=clean_t(TESTO_LEGALE))
                
                # Firma nel PDF
                if canvas_result.image_data is not None:
                    img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                    img_byte_arr = io.BytesIO()
                    img.save(img_byte_arr, format='PNG')
                    with open("temp_firma.png", "wb") as f:
                        f.write(img_byte_arr.getvalue())
                    
                    pdf.ln(10)
                    pdf.set_font("Arial", 'I', 8)
                    pdf.cell(0, 5, txt="Firma per accettazione e clausole vessatorie (Art. 1341-1342 C.C.):", ln=1)
                    pdf.image("temp_firma.png", x=10, w=45)

                name = f"Contratto_{targa}.pdf"
                pdf.output(name)
                st.success("✅ Contratto Legale Generato!")
                with open(name, "rb") as f:
                    st.download_button("📥 Scarica PDF", f, file_name=name)
            else:
                st.error("Firma e accetta i termini per proseguire!")

    elif menu == "🚨 Archivio & Multe":
        st.header("Moduli Vigili")
        st.write("Seleziona un contratto per generare la comunicazione dati conducente.")

    elif menu == "🏦 Fatturazione Aruba":
        st.header("Aruba SDI")
        st.write("Pronto per l'invio fattura.")

