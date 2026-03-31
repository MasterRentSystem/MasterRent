import streamlit as st
import datetime
import fpdf
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
import time
import urllib.parse

# 1. CONNESSIONE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)
BUCKET_NAME = "DOCUMENTI_PATENTI"

# INTESTAZIONE PROFESSIONALE
DITTA_NOME = "BATTAGLIA MARIANNA"
DITTA_INFO = "Via Cognole, 5 - 80075 Forio (NA)\nP. IVA 10252601215 | C.F. BTTMNN87A53Z112S"

def clean_t(text):
    if not text or text == "None": return "---"
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in repls.items(): text = str(text).replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

def add_header(pdf):
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, clean_t(DITTA_NOME), ln=1, align='L')
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 5, clean_t(DITTA_INFO), align='L')
    pdf.line(10, 35, 200, 35)
    pdf.ln(12)

# --- FUNZIONE CONTRATTO (Con Clausole) ---
def crea_pdf_contratto(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    add_header(pdf)
    pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, "CONTRATTO DI NOLEGGIO", ln=1, align='C'); pdf.ln(5)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 7, clean_t(f"CLIENTE: {c['cliente']}\nC.F.: {c['cf']}\nRESIDENZA: {c['residenza']}\nVEICOLO: {c['targa']}\nPERIODO: {c['data_inizio']} ({c['ora_inizio']}) - {c['data_fine']} ({c['ora_fine']})"), border=1)
    pdf.ln(5); pdf.set_font("Arial", 'B', 8); pdf.cell(0, 5, "CONDIZIONI GENERALI (ART. 1-14)", ln=1)
    pdf.set_font("Arial", size=7)
    pdf.multi_cell(0, 4, clean_t("1. Veicolo in ottimo stato. 2. Responsabilita danni/furto totale. 3. Sanzioni C.d.S. a carico cliente + 25.83 Euro gestione. 4. Obbligo casco e fermo amm.vo. 5. Foro competente Ischia. 6. Privacy GDPR."), border='T')
    pdf.ln(20); pdf.cell(0, 10, "Firma Cliente: ______________________", align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- FUNZIONE RICEVUTA (Solo Pagamento) ---
def crea_pdf_ricevuta(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    add_header(pdf)
    pdf.set_font("Arial", 'B', 16); pdf.cell(0, 10, "RICEVUTA DI PAGAMENTO", ln=1, align='C'); pdf.ln(15)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, clean_t(f"Ricevuti da: {c['cliente']}"), ln=1)
    pdf.cell(0, 10, clean_t(f"Targa veicolo: {c['targa']}"), ln=1)
    pdf.ln(20); pdf.set_font("Arial", 'B', 20)
    pdf.cell(0, 20, clean_t(f"TOTALE CORRISPOSTO: Euro {c['prezzo']}"), border=1, ln=1, align='C', center=True)
    return pdf.output(dest='S').encode('latin-1')

# --- FUNZIONE VIGILI (Dichiarazione Legale) ---
def crea_pdf_vigili(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    add_header(pdf)
    pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, "DICHIARAZIONE SOSTITUTIVA (L. 445/2000)", ln=1, align='C'); pdf.ln(10)
    pdf.set_font("Arial", size=11)
    testo = (
        f"La sottoscritta BATTAGLIA MARIANNA, titolare di MasterRent, dichiara che il veicolo targa {c['targa']}\n"
        f"in data {c['data_inizio']} era affidato per noleggio al Sig.:\n\n"
        f"NOME: {c['cliente']}\nNATO A: {c.get('luogo_nascita', '---')}\n"
        f"RESIDENTE: {c['residenza']}\nC.F.: {c['cf']}\nPATENTE: {c['num_doc']}\n\n"
        f"Si richiede la rinotifica dei verbali al suddetto locatario."
    )
    pdf.multi_cell(0, 8, clean_t(testo))
    pdf.ln(20); pdf.cell(0, 10, "Timbro e Firma: ______________________", align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACCIA APP ---
st.set_page_config(page_title="MasterRent Ischia", layout="wide")
menu = st.sidebar.radio("Scegli Operazione", ["📝 Nuovo Noleggio", "🗄️ Archivio", "🚨 Modulo Vigili"])

if menu == "📝 Nuovo Noleggio":
    with st.form("form_v20"):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Cognome Nome")
        cf = col2.text_input("C.F.")
        nascita = col1.text_input("Luogo/Data Nascita")
        residenza = col2.text_input("Indirizzo Residenza")
        patente = col1.text_input("Numero Patente")
        targa = col2.text_input("TARGA").upper()
        tel = col1.text_input("Telefono")
        prezzo = col2.number_input("Prezzo Totale (€)", min_value=0.0)
        
        d1, d2, d3, d4 = st.columns(4)
        di = d1.date_input("Data Inizio")
        oi = d2.text_input("Ora Inizio", "10:00")
        df = d3.date_input("Data Fine")
        of = d4.text_input("Ora Fine", "10:00")
        
        st.info("Informativa: Il cliente accetta la responsabilita per danni, furto e sanzioni (Art. 1341-1342 c.c.)")
        accetto = st.checkbox("ACCETTO LE CONDIZIONI E LA PRIVACY")
        
        foto = st.camera_input("📸 SCATTA FOTO PATENTE")
        st_canvas(height=150, key="sign_v20")
        
        if st.form_submit_button("💾 SALVA NOLEGGIO"):
            if accetto:
                fn = f"{targa}_{int(time.time())}.jpg"
                if foto: supabase.storage.from_(BUCKET_NAME).upload(fn, foto.getvalue())
                dat = {"cliente": nome, "cf": cf, "luogo_nascita": nascita, "residenza": residenza, "num_doc": patente, "targa": targa, "prezzo": prezzo, "data_inizio": str(di), "ora_inizio": oi, "data_fine": str(df), "ora_fine": of, "telefono": tel, "foto_path": fn if foto else None}
                supabase.table("contratti").insert(dat).execute()
                st.success("Dati salvati in Archivio!")
            else: st.error("Devi spuntare la casella di accettazione!")

elif menu == "🗄️ Archivio":
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"📄 {c['cliente']} - {c['targa']}"):
            col1, col2, col3, col4 = st.columns(4)
            col1.download_button("📜 CONTRATTO", crea_pdf_contratto(c), f"Contratto_{c['id']}.pdf")
            col2.download_button("💰 RICEVUTA", crea_pdf_ricevuta(c), f"Ricevuta_{c['id']}.pdf")
            if c.get("foto_path"):
                url_f = supabase.storage.from_(BUCKET_NAME).get_public_url(c["foto_path"])
                col3.link_button("📸 VEDI PATENTE", url_f)
            t_wa = str(c.get('telefono','')).replace(" ","")
            if t_wa: col4.link_button("💬 WHATSAPP", f"https://wa.me/39{t_wa}")

elif menu == "🚨 Modulo Vigili":
    t_m = st.text_input("Inserisci Targa").upper()
    if t_m:
        res_m = supabase.table("contratti").select("*").eq("targa", t_m).execute()
        if res_m.data:
            st.download_button("🚨 SCARICA DICHIARAZIONE VIGILI", crea_pdf_vigili(res_m.data[0]), f"Vigili_{t_m}.pdf")
