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
    replacements = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro'}
    for k, v in replacements.items(): text = text.replace(k, v)
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
        
        with st.expander("👤 DATI CLIENTE", expanded=True):
            col1, col2 = st.columns(2)
            nome = col1.text_input("NOME E COGNOME")
            cf = col2.text_input("CODICE FISCALE")
            residenza = col1.text_input("RESIDENZA COMPLETA")
            telefono = col2.text_input("TELEFONO")
            doc = col1.text_input("TIPO E NUM. DOCUMENTO")

        with st.expander("🛵 DATI NOLEGGIO", expanded=True):
            col3, col4 = st.columns(2)
            targa = col3.text_input("TARGA VEICOLO")
            prezzo = col4.number_input("CORRISPETTIVO (€)", min_value=0)
            inizio = col3.date_input("DATA INIZIO", datetime.date.today())
            fine = col4.date_input("DATA FINE", datetime.date.today() + datetime.timedelta(days=1))

        st.subheader("✍️ Firma per Accettazione Condizioni (Punti 1-14)")
        canvas_result = st_canvas(fill_color="white", stroke_width=3, stroke_color="black", background_color="white", height=150, key="sig")

        if st.button("💾 GENERA CONTRATTO UFFICIALE"):
            if nome and targa and canvas_result.image_data is not None:
                # Salva su DB
                payload = {"cliente": nome, "cf": cf, "targa": targa, "prezzo_tot": str(prezzo), "data_inizio": str(inizio), "azienda_id": scelta_azienda['id']}
                supabase.table("contratti").insert(payload).execute()

                # Genera PDF
                pdf = fpdf.FPDF()
                pdf.add_page()
                
                # INTESTAZIONE DALLE TUE FOTO
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(0, 10, txt="Noleggio BATTAGLIA MARIANNA", ln=1, align='L')
                pdf.set_font("Arial", size=9)
                pdf.cell(0, 5, txt="Via Cognole, 5 - 80075 Forio (NA) - P.IVA 10252601215", ln=1, align='L')
                pdf.ln(5)

                # BOX DATI
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(0, 8, txt="DETTAGLI NOLEGGIO", ln=1, border='B')
                pdf.set_font("Arial", size=10)
                pdf.multi_cell(0, 8, txt=clean_text(f"Cliente: {nome}\nC.F.: {cf}\nResidenza: {residenza}\nDocumento: {doc}\nVeicolo: {targa}\nPeriodo: dal {inizio} al {fine}\nCorrispettivo: Euro {prezzo}"))
                
                # CONDIZIONI GENERALI (Sintesi dei tuoi 14 punti)
                pdf.ln(5)
                pdf.set_font("Arial", 'B', 8)
                pdf.cell(0, 5, txt="CONDIZIONI GENERALI DI CONTRATTO", ln=1)
                pdf.set_font("Arial", size=6)
                condizioni = (
                    "1. Veicolo consegnato in ottimo stato, riconsegna con pieno. 2. Cliente responsabile infrazioni C.d.S. "
                    "3. Addebito Euro 25.83 per gestione amministrativa verbali. 4. Responsabilita danni e furto a carico del cliente. "
                    "5. Divieto trasporto persone eccedenti e guida in stato di ebbrezza. 6. Foro competente: Napoli/Ischia. "
                    "Il cliente dichiara di aver letto e accettato i 14 punti delle condizioni generali e l'informativa Privacy GDPR."
                )
                pdf.multi_cell(0, 4, txt=clean_text(condizioni))

                # FIRMA
                signature_img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                signature_img.save("firma.png")
                pdf.ln(5)
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(0, 5, txt="Firma del Cliente:", ln=1)
                pdf.image("firma.png", x=10, w=40)

                pdf_name = f"Contratto_{targa}.pdf"
                pdf.output(pdf_name)
                st.success("✅ Contratto Ufficiale Generato!")
                with open(pdf_name, "rb") as f:
                    st.download_button("📥 Scarica Contratto PDF", f, file_name=pdf_name)
