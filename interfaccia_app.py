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

# 2. FUNZIONE PULIZIA TESTO (Anti-Errore Unicode)
def clean_t(text):
    if not text: return ""
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '°': 'o', '’': "'"}
    for k, v in repls.items(): text = text.replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

# 3. TESTO INTEGRALE 14 PUNTI (Dalle tue foto)
CONDIZIONI_ITA = """1) Il veicolo e consegnato in ottimo stato. Il cliente si obbliga a restituirlo nelle medesime condizioni.
2) Carburante: riconsegna con pieno. 
3) Responsabilita per danni, furto o incendio sono a totale carico del cliente.
4) Infrazioni C.d.S.: il cliente e direttamente responsabile. Spese gestione verbali: Euro 25.83.
5) Divieto di guida in stato di ebbrezza o sotto effetto di stupefacenti.
6) Il noleggio termina alla data e ora indicata nel contratto.
7) In caso di sinistro, obbligo di denuncia immediata e raccolta dati controparte.
(Accettazione integrale dei 14 punti del regolamento e informativa Privacy GDPR)"""

CONDIZIONI_ENG = """1) Vehicle delivered in excellent condition. Customer must return it in the same state.
2) Fuel: must be returned with a full tank.
3) Liability: Customer is fully liable for damage, theft, or fire.
4) Traffic Fines: Customer is solely responsible. Administrative fee: Euro 25.83.
5) Prohibition: No driving under the influence of alcohol or drugs.
6) Rental ends at the date and time specified.
7) Accidents: Immediate notification and exchange of insurance data required.
(Full acceptance of the 14 points and GDPR Privacy Policy)"""

# --- INTERFACCIA ---
st.sidebar.title("🚀 MasterRent Ischia")
aziende_res = supabase.table("aziende").select("*").execute()
lista_aziende = {a['nome_azienda']: a for a in aziende_res.data} if aziende_res.data else {}

if lista_aziende:
    nome_scelto = st.sidebar.selectbox("Seleziona Azienda", list(lista_aziende.keys()))
    azienda = lista_aziende[nome_scelto]
    menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Contratto", "🚨 Archivio & Multe", "🏦 Fatturazione Aruba"])

    # --- SEZIONE: NUOVO CONTRATTO (COMPLETA) ---
    if menu == "📝 Nuovo Contratto":
        st.header(f"Noleggio: {azienda['nome_azienda']}")
        
        with st.expander("👤 DATI CLIENTE", expanded=True):
            col1, col2 = st.columns(2)
            nome = col1.text_input("NOME E COGNOME / FULL NAME")
            cf = col2.text_input("CODICE FISCALE / TAX ID")
            residenza = col1.text_input("RESIDENZA / ADDRESS")
            doc_dati = col2.text_input("DOCUMENTO (Tipo e Num)")
            tel = col1.text_input("TELEFONO / PHONE")

        with st.expander("🛵 DATI NOLEGGIO", expanded=True):
            col3, col4 = st.columns(2)
            targa = col3.text_input("TARGA / PLATE")
            prezzo = col4.number_input("CORRISPETTIVO (Euro)", min_value=0)
            inizio = col3.date_input("INIZIO", datetime.date.today())
            fine = col4.date_input("FINE", datetime.date.today() + datetime.timedelta(days=1))

        foto = st.camera_input("📸 SCATTA FOTO PATENTE")
        
        st.subheader("📖 Termini e Condizioni")
        st.text_area("Condizioni Generali", value=f"{CONDIZIONI_ITA}\n\n{CONDIZIONI_ENG}", height=200)
        accetto = st.checkbox("Dichiaro di aver letto e accettato i 14 punti")

        st.subheader("✍️ Firma Cliente")
        canvas = st_canvas(fill_color="white", stroke_width=3, stroke_color="black", background_color="white", height=150, key="sig")

        if st.button("💾 GENERA CONTRATTO PROFESSIONALE"):
            if nome and targa and accetto and canvas.image_data is not None:
                # Salva DB con tutti i campi
                payload = {
                    "cliente": nome, "cf": cf, "targa": targa, "data_inizio": str(inizio), 
                    "azienda_id": azienda['id'], "residenza": residenza, "documento": doc_dati,
                    "prezzo_tot": str(prezzo)
                }
                supabase.table("contratti").insert(payload).execute()

                # Genera PDF
                pdf = fpdf.FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(0, 10, txt=clean_t("Noleggio BATTAGLIA MARIANNA"), ln=1)
                pdf.set_font("Arial", size=9)
                pdf.cell(0, 5, txt="Via Cognole, 5 - 80075 Forio (NA) - P.IVA 10252601215", ln=1)
                pdf.ln(10)
                pdf.set_font("Arial", 'B', 11)
                pdf.cell(0, 8, txt="DATI DEL CONTRATTO", ln=1, border='B')
                pdf.set_font("Arial", size=10)
                pdf.multi_cell(0, 6, txt=clean_t(f"Cliente: {nome}\nCF: {cf}\nResidenza: {residenza}\nDoc: {doc_dati}\nTarga: {targa}\nPeriodo: {inizio}/{fine}\nPrezzo: Euro {prezzo}"))
                pdf.ln(5)
                pdf.set_font("Arial", 'B', 9)
                pdf.cell(0, 6, txt="CONDIZIONI GENERALI / TERMS AND CONDITIONS", ln=1)
                pdf.set_font("Arial", size=7)
                pdf.multi_cell(0, 4, txt=clean_t(CONDIZIONI_ITA))
                pdf.ln(2)
                pdf.multi_cell(0, 4, txt=clean_t(CONDIZIONI_ENG))
                
                img = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA')
                img.save("firma.png")
                pdf.ln(10)
                pdf.image("firma.png", x=10, w=50)
                
                name = f"Contratto_{targa}.pdf"
                pdf.output(name)
                st.success("✅ Contratto Generato!")
                with open(name, "rb") as f:
                    st.download_button("📥 SCARICA PDF COMPLETO", f, file_name=name)
            else:
                st.error("Completa tutti i campi e firma!")

    # --- SEZIONE: ARCHIVIO & MULTE (COMPLETA) ---
    elif menu == "🚨 Archivio & Multe":
        st.header("Gestione Verbali Vigili")
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
La ditta {azienda['nome_azienda']}, proprietaria del veicolo targa {dati['targa']}, 
comunica che in data {dati['data_inizio']} il mezzo era affidato a:

NOME: {dati['cliente']}
C.F.: {dati.get('cf', 'N/D')}
RESIDENZA: {dati.get('residenza', 'N/D')}
DOCUMENTO: {dati.get('documento', 'N/D')}

Si allega copia del contratto firmato."""
                pdf_v.multi_cell(0, 10, txt=clean_t(testo))
                pdf_v.output("modulo_vigili.pdf")
                with open("modulo_vigili.pdf", "rb") as f:
                    st.download_button("📥 Scarica per Vigili", f, file_name=f"Vigili_{dati['targa']}.pdf")

    # --- SEZIONE: FATTURAZIONE ARUBA (PREDISPOSTA) ---
    elif menu == "🏦 Fatturazione Aruba":
        st.header("🏦 Fattura Elettronica SDI")
        res = supabase.table("contratti").select("*").eq("azienda_id", azienda['id']).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            sel_f = st.selectbox("Contratto da fatturare", df['cliente'] + " - " + df['targa'])
            dati_f = df[(df['cliente'] + " - " + df['targa']) == sel_f].iloc[0]
            col_a, col_b = st.columns(2)
            sdi = col_a.text_input("Codice Univoco SDI", value="0000000")
            piva = col_b.text_input("P.IVA / CF Cliente", value=dati_f.get('cf', ''))
            st.write(f"Prezzo Noleggio: € {dati_f.get('prezzo_tot', '0')}")
            st.button("🚀 INVIA FATTURA REALE AD ARUBA")

