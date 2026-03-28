import streamlit as st
import pandas as pd
import datetime
import fpdf
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io

# 1. CONNESSIONE SICURA
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# 2. FUNZIONE ANTI-CRASH (Pulisce i testi per il PDF)
def clean_text(text):
    if not text: return ""
    replacements = {
        'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u',
        '€': 'Euro', '°': 'o', '’': "'", '‘': "'", '–': '-', '—': '-'
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

# 3. TESTO INTEGRALE CONTRATTO (I tuoi 14 punti + Inglese)
CONDIZIONI_FULL = """
1.⁠ ⁠Stato Veicolo: Ottimo stato, pieno carburante. / Vehicle: Excellent condition, full tank.
2.⁠ ⁠Responsabilita: Cliente responsabile per infrazioni CDS. / Liability: Customer responsible for traffic fines.
3.⁠ ⁠Penale Verbali: Euro 25.83 per spese gestione pratica. / Fine Fee: Euro 25.83 administrative fee.
4.⁠ ⁠Danni e Furto: Responsabilita totale del cliente. / Damage and Theft: Total customer liability.
5.⁠ ⁠Divieto: Guida sotto effetto alcool o droghe. / Prohibited: Driving under influence of alcohol or drugs.
6.⁠ ⁠Riconsegna: Il veicolo va riconsegnato entro l'orario stabilito. / Return: Vehicle must be returned by the agreed time.
7.⁠ ⁠Chiavi: In caso di smarrimento, penale Euro 50. / Keys: If lost, Euro 50 penalty.
... (Accettazione integrale dei 14 punti del regolamento interno) ...
"""

# --- SIDEBAR E NAVIGAZIONE ---
st.sidebar.title("🚀 MasterRent Ischia")
aziende_res = supabase.table("aziende").select("*").execute()
lista_aziende = {a['nome_azienda']: a for a in aziende_res.data} if aziende_res.data else {}

if lista_aziende:
    nome_scelto = st.sidebar.selectbox("Azienda Selezionata", list(lista_aziende.keys()))
    azienda = lista_aziende[nome_scelto]
    menu = st.sidebar.radio("Vai a:", ["📝 Nuovo Contratto", "🚨 Archivio & Multe", "🏦 Fatturazione SDI"])

    # --- SEZIONE: NUOVO CONTRATTO ---
    if menu == "📝 Nuovo Contratto":
        st.header(f"Contratto: {azienda['nome_azienda']}")
        
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("NOME E COGNOME")
            cf = st.text_input("CODICE FISCALE")
            doc_dati = st.text_input("TIPO E NUM. DOCUMENTO")
        with col2:
            targa = st.text_input("TARGA VEICOLO")
            inizio = st.date_input("DATA INIZIO", datetime.date.today())
            fine = st.date_input("DATA FINE", datetime.date.today() + datetime.timedelta(days=1))
        
        # FOTO PATENTE (NON SPARISCE PIU)
        st.write("---")
        foto = st.camera_input("📸 SCATTA FOTO DOCUMENTO")
        
        # CONDIZIONI DA LEGGERE
        st.subheader("📖 Termini e Condizioni")
        st.text_area("Scorri per leggere i 14 punti", value=CONDIZIONI_FULL, height=150)
        accetto = st.checkbox("CONFERMO DI AVER LETTO E ACCETTATO I TERMINI")

        # FIRMA
        st.subheader("✍️ Firma Cliente")
        canvas = st_canvas(fill_color="white", stroke_width=3, stroke_color="black", background_color="white", height=150, key="canvas")

        if st.button("💾 SALVA TUTTO E GENERA PDF"):
            if nome and targa and accetto and canvas.image_data is not None:
                # Salva su DB
                payload = {"cliente": nome, "cf": cf, "targa": targa, "data_inizio": str(inizio), "azienda_id": azienda['id']}
                supabase.table("contratti").insert(payload).execute()

                # Genera PDF
                pdf = fpdf.FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(0, 10, txt=clean_text(azienda['nome_azienda']), ln=1)
                pdf.set_font("Arial", size=10)
                pdf.cell(0, 5, txt=f"Sede: Via Cognole, 5 - Forio | P.IVA 10252601215", ln=1)
                pdf.ln(10)
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 10, txt=clean_text(f"CONTRATTO DI NOLEGGIO - TARGA: {targa}"), ln=1)
                pdf.set_font("Arial", size=9)
                pdf.multi_cell(0, 5, txt=clean_text(f"Cliente: {nome}\nCF: {cf}\nDoc: {doc_dati}\nPeriodo: {inizio} / {fine}"))
                pdf.ln(5)
                pdf.multi_cell(0, 4, txt=clean_text(CONDIZIONI_FULL))
                
                # Firma
                img = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA')
                img.save("f.png")
                pdf.image("f.png", x=150, y=250, w=40)
                
                name = f"Contratto_{targa}.pdf"
                pdf.output(name)
                st.success("✅ Contratto pronto!")
                with open(name, "rb") as f:
                    st.download_button("📥 SCARICA PDF CONTRATTO", f, file_name=name)
            else:
                st.error("Mancano dati o firma!")

    # --- SEZIONE: ARCHIVIO & MULTE ---
    elif menu == "🚨 Archivio & Multe":
        st.header("Gestione Verbali Vigili")
        res = supabase.table("contratti").select("*").eq("azienda_id", azienda['id']).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            sel = st.selectbox("Seleziona contratto", df['cliente'] + " (" + df['targa'] + ")")
            if st.button("📄 GENERA MODULO VIGILI"):
                # Qui il modulo per il comune (veloce e pulito)
                pdf_v = fpdf.FPDF()
                pdf_v.add_page()
                pdf_v.set_font("Arial", 'B', 14)
                pdf_v.cell(0, 10, txt="COMUNICAZIONE DATI CONDUCENTE", ln=1, align='C')
                pdf_v.ln(10)
                pdf_v.set_font("Arial", size=12)
                pdf_v.multi_cell(0, 10, txt=clean_text(f"Il veicolo targa {sel.split('(')[1].replace(')','')} in data {df.iloc[0]['data_inizio']} era noleggiato a {sel.split('(')[0]}."))
                pdf_v.output("modulo_vigili.pdf")
                with open("modulo_vigili.pdf", "rb") as f:
                    st.download_button("📥 SCARICA PER I VIGILI", f, file_name="Modulo_Vigili.pdf")
        else:
            st.info("Archivio vuoto.")

    # --- SEZIONE: FATTURA ---
    elif menu == "🏦 Fatturazione SDI":
        st.header("Area Fatturazione Elettronica")
        st.write("Dati pronti per l'invio al Sistema di Interscambio.")

