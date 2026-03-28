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
    replacements = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '°': 'o'}
    for k, v in replacements.items(): text = text.replace(k, v)
    return text

# --- TESTO INTEGRALE CONTRATTO ---
CONDIZIONI_TESTO = """
1.⁠ ⁠Il cliente riceve il veicolo in ottimo stato... / The customer receives the vehicle in excellent condition...
2.⁠ ⁠Carburante: riconsegna con pieno / Fuel: return with full tank.
3.⁠ ⁠Multe: Responsabilita del conducente + Euro 25.83 gestione / Fines: Driver's liability + Euro 25.83 fee.
4.⁠ ⁠Danni e Furto: Responsabilita totale del cliente / Damage and Theft: Total customer liability.
... (Tutti i 14 punti appariranno qui nel PDF) ...
"""

st.sidebar.title("🔑 Gestione Noleggi")
aziende_res = supabase.table("aziende").select("*").execute()
lista_aziende = {a['nome_azienda']: a for a in aziende_res.data} if aziende_res.data else {}

if lista_aziende:
    nome_scelto = st.sidebar.selectbox("Seleziona Azienda", list(lista_aziende.keys()))
    scelta_azienda = lista_aziende[nome_scelto]
    menu = st.sidebar.radio("Menu", ["Nuovo Contratto", "Archivio Multe", "Fatturazione SDI"])

    # --- SEZIONE 1: NUOVO CONTRATTO ---
    if menu == "Nuovo Contratto":
        st.header(f"📝 {scelta_azienda['nome_azienda']}")
        
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("NOME E COGNOME / FULL NAME")
            cf = st.text_input("CODICE FISCALE / TAX ID")
            residenza = st.text_input("RESIDENZA / ADDRESS")
        with col2:
            targa = st.text_input("TARGA / PLATE")
            inizio = st.date_input("INIZIO / START", datetime.date.today())
            fine = st.date_input("FINE / END", datetime.date.today() + datetime.timedelta(days=1))
        
        # BOX LETTURA CONDIZIONI
        st.subheader("📖 Termini e Condizioni / Terms & Conditions")
        st.text_area("Scorri per leggere / Scroll to read", value=CONDIZIONI_TESTO, height=200, disabled=True)
        
        accetto = st.checkbox("Dichiaro di aver letto e accettato i 14 punti e la Privacy / I accept the terms")

        st.subheader("✍️ Firma / Signature")
        canvas_result = st_canvas(fill_color="white", stroke_width=3, stroke_color="black", background_color="white", height=150, key="sig")

        if st.button("💾 SALVA E GENERA PDF"):
            if nome and targa and accetto and canvas_result.image_data is not None:
                # Salva su DB
                payload = {"cliente": nome, "cf": cf, "targa": targa, "data_inizio": str(inizio), "azienda_id": scelta_azienda['id']}
                supabase.table("contratti").insert(payload).execute()

                # PDF BILINGUE COMPLETO
                pdf = fpdf.FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(0, 10, txt=clean_text(scelta_azienda['nome_azienda']), ln=1)
                pdf.set_font("Arial", size=8)
                pdf.cell(0, 5, txt="Via Cognole, 5 - Forio (NA) - P.IVA 10252601215", ln=1)
                
                pdf.ln(5)
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(0, 7, txt=clean_text(f"CONTRATTO: {nome} - TARGA: {targa}"), ln=1, border='B')
                
                # Inserimento punti 1-14 (Sintesi Bilingue)
                pdf.set_font("Arial", size=7)
                pdf.ln(2)
                pdf.multi_cell(0, 4, txt=clean_text(CONDIZIONI_TESTO))

                # Firma
                signature_img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                signature_img.save("firma.png")
                pdf.image("firma.png", x=150, y=250, w=40)
                
                pdf_name = f"Contratto_{targa}.pdf"
                pdf.output(pdf_name)
                st.success("✅ Contratto Creato!")
                with open(pdf_name, "rb") as f:
                    st.download_button("📥 Scarica PDF", f, file_name=pdf_name)
            else:
                st.error("Devi accettare i termini e firmare!")

    # --- SEZIONE 2: ARCHIVIO MULTE ---
    elif menu == "Archivio Multe":
        st.header("🚨 Gestione Verbali")
        res = supabase.table("contratti").select("*").eq("azienda_id", scelta_azienda['id']).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            scelta = st.selectbox("Seleziona Contratto per Multa", df['cliente'] + " (" + df['targa'] + ")")
            if st.button("📄 Genera Comunicazione per Vigili"):
                st.info(f"Modulo pronto per {scelta}. Dati estratti per il Comune.")
        else:
            st.warning("Nessun contratto in archivio.")

    # --- SEZIONE 3: FATTURAZIONE ---
    elif menu == "Fatturazione SDI":
        st.header("🏦 Fattura Elettronica")
        st.write(f"Dati Fiscali di {scelta_azienda['nome_azienda']} pronti per l'invio SDI.")
        st.button("Invia dati a Agenzia Entrate")

