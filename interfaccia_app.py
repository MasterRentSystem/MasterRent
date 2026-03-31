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

DITTA_NOME = "BATTAGLIA MARIANNA"
DITTA_INFO = "Via Cognole, 5 - 80075 Forio (NA)\nP. IVA 10252601215 | C.F. BTTMNN87A53Z112S"

def clean_t(text):
    if not text or text == "None": return "---"
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in repls.items(): text = str(text).replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

def add_header_v22(pdf, titolo_doc):
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(0, 10, clean_t(DITTA_NOME), ln=1, align='L')
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 5, clean_t(DITTA_INFO), align='L')
    pdf.line(10, 35, 200, 35)
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 15)
    pdf.cell(0, 10, clean_t(titolo_doc), ln=1, align='C')
    pdf.ln(5)

# --- PDF CONTRATTO (CON CLAUSOLE) ---
def genera_pdf_contratto(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    add_header_v22(pdf, "CONTRATTO DI NOLEGGIO")
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 7, clean_t(f"CLIENTE: {c['cliente']}\nC.F.: {c['cf']}\nTARGA: {c['targa']}\nPERIODO: {c['data_inizio']} - {c['data_fine']}"), border=1)
    pdf.ln(5); pdf.set_font("Arial", 'B', 8); pdf.cell(0, 5, "CONDIZIONI GENERALI (1-14):", ln=1)
    pdf.set_font("Arial", size=7)
    pdf.multi_cell(0, 4, clean_t("Responsabilita totale danni/furto. Sanzioni + 25.83 euro. Foro Ischia. Casco obbligatorio. Privacy GDPR."), border='T')
    pdf.ln(20); pdf.cell(0, 10, "Firma Cliente: ______________________", align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- PDF RICEVUTA (PULITA) ---
def genera_pdf_ricevuta(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    add_header_v22(pdf, "RICEVUTA DI PAGAMENTO")
    pdf.set_font("Arial", size=12); pdf.ln(10)
    pdf.cell(0, 10, clean_t(f"Ricevuti da: {c['cliente']}"), ln=1)
    pdf.cell(0, 10, clean_t(f"Per noleggio targa: {c['targa']}"), ln=1)
    pdf.ln(15); pdf.set_font("Arial", 'B', 20)
    pdf.cell(0, 20, clean_t(f"TOTALE: Euro {c['prezzo']}"), border=1, ln=1, align='C')
    return pdf.output(dest='S').encode('latin-1')

# --- PDF VIGILI (DICHIARAZIONE LEGALE) ---
def genera_pdf_vigili(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    add_header_v22(pdf, "DICHIARAZIONE DATI CONDUCENTE")
    pdf.set_font("Arial", size=11)
    testo = (
        f"La sottoscritta BATTAGLIA MARIANNA dichiara che il veicolo targa {c['targa']}\n"
        f"era affidato al Sig. {c['cliente']} (C.F. {c['cf']}) residente in {c['residenza']}.\n\n"
        f"Si richiede la rinotifica ai sensi della L. 445/2000."
    )
    pdf.multi_cell(0, 8, clean_t(testo))
    pdf.ln(20); pdf.cell(0, 10, "Firma: ______________________", align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACCIA ---
st.set_page_config(page_title="MasterRent Ischia", layout="wide")
menu = st.sidebar.radio("Scegli", ["Nuovo", "Archivio", "Multe"])

if menu == "Nuovo":
    with st.form("form_v22"):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Cognome Nome")
        cf = c2.text_input("Codice Fiscale")
        nascita = c1.text_input("Nascita")
        res = c2.text_input("Residenza")
        pat = c1.text_input("Patente")
        targa = c2.text_input("Targa").upper()
        tel = c1.text_input("Telefono")
        prezzo = c2.number_input("Prezzo (€)", min_value=0.0)
        di = st.date_input("Inizio")
        df = st.date_input("Fine")
        
        st.write("---")
        accetto = st.checkbox("ACCETTO PRIVACY E CLAUSOLE 1-14 (OBBLIGATORIO)")
        foto = st.camera_input("FOTO PATENTE")
        st_canvas(height=150, key="sign_v22")
        
        if st.form_submit_button("SALVA"):
            if accetto:
                fn = f"{targa}_{int(time.time())}.jpg"
                if foto: supabase.storage.from_(BUCKET_NAME).upload(fn, foto.getvalue())
                dat = {"cliente": nome, "cf": cf, "luogo_nascita": nascita, "residenza": res, "num_doc": pat, "targa": targa, "prezzo": prezzo, "data_inizio": str(di), "data_fine": str(df), "telefono": tel, "foto_path": fn if foto else None}
                supabase.table("contratti").insert(dat).execute()
                st.success("Salvato!")
            else: st.error("Devi accettare le condizioni!")

elif menu == "Archivio":
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"{c['cliente']} - {c['targa']}"):
            col1, col2, col3, col4 = st.columns(4)
            col1.download_button("📜 CONTRATTO", genera_pdf_contratto(c), f"C_{c['id']}.pdf", key=f"c_{c['id']}")
            col2.download_button("💰 RICEVUTA", genera_pdf_ricevuta(c), f"R_{c['id']}.pdf", key=f"r_{c['id']}")
            if c.get("foto_path"):
                u = supabase.storage.from_(BUCKET_NAME).get_public_url(c["foto_path"])
                col3.link_button("📸 PATENTE", u)
            if c.get("telefono"):
                col4.link_button("💬 WA", f"https://wa.me/39{c['telefono']}")

elif menu == "Multe":
    t_m = st.text_input("Targa").upper()
    if t_m:
        res_m = supabase.table("contratti").select("*").eq("targa", t_m).execute()
        if res_m.data:
            st.download_button("🚨 MODULO VIGILI", genera_pdf_vigili(res_m.data[0]), f"V_{t_m}.pdf")
