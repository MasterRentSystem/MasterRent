import streamlit as st
import datetime
from fpdf import FPDF
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
import time
import random

# 1. CONNESSIONE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)
BUCKET_NAME = "DOCUMENTI_PATENTI"

DITTA = "BATTAGLIA MARIANNA"
DITTA_INFO = "Via Cognole, 5 - 80075 Forio (NA)\nP. IVA 10252601215 | C.F. BTTMNN87A53Z112S"

def clean_t(text):
    if not text or text == "None": return "---"
    r = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in r.items(): text = str(text).replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

def header_master(pdf, tit):
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, DITTA, ln=True)
    pdf.set_font("Arial", size=9)
    pdf.multi_cell(0, 5, clean_t(DITTA_INFO))
    pdf.line(10, 32, 200, 32)
    pdf.ln(12)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, clean_t(tit), ln=True, align='C')
    pdf.ln(5)

# --- FUNZIONI PDF TOTALMENTE INDIPENDENTI ---
def crea_pdf_CONTRATTO(c):
    pdf = FPDF()
    pdf.add_page()
    header_master(pdf, "CONTRATTO DI NOLEGGIO")
    pdf.set_font("Arial", size=10)
    info = (f"CLIENTE: {c.get('cliente')}\nNATO A: {c.get('luogo_nascita')}\n"
            f"RESIDENTE: {c.get('residenza')}\nC.F.: {c.get('cf')}\n"
            f"PATENTE: {c.get('num_doc')}\nTEL: {c.get('telefono')}\n\n"
            f"VEICOLO: {c.get('targa')}\nDAL: {c.get('data_inizio')} AL: {c.get('data_fine')}")
    pdf.multi_cell(0, 7, clean_t(info), border=1)
    pdf.ln(5); pdf.set_font("Arial", 'B', 8); pdf.cell(0, 5, "CONDIZIONI GENERALI:", ln=True)
    pdf.set_font("Arial", size=6); pdf.multi_cell(0, 3, clean_t("Responsabilita totale danni/furto. Multe a carico cliente + 25.83 euro gestione. Obbligo casco. Foro Ischia. Privacy GDPR."), border='T')
    pdf.ln(20); pdf.cell(0, 10, "Firma Cliente: ______________________", align='R')
    return pdf.output(dest='S').encode('latin-1')

def crea_pdf_RICEVUTA(c):
    pdf = FPDF()
    pdf.add_page()
    header_master(pdf, "RICEVUTA DI PAGAMENTO")
    pdf.set_font("Arial", size=12); pdf.ln(10)
    pdf.cell(0, 10, clean_t(f"Ricevuto da: {c.get('cliente')}"), ln=True)
    pdf.cell(0, 10, clean_t(f"Per noleggio veicolo targa: {c.get('targa')}"), ln=True)
    pdf.ln(20); pdf.set_font("Arial", 'B', 22)
    pdf.cell(0, 25, clean_t(f"TOTALE: Euro {c.get('prezzo')}"), border=1, ln=True, align='C')
    return pdf.output(dest='S').encode('latin-1')

def crea_pdf_VIGILI(c):
    pdf = FPDF()
    pdf.add_page()
    header_master(pdf, "MODULO RINOTIFICA VIGILI")
    pdf.set_font("Arial", size=11); pdf.ln(5)
    t = (f"La sottoscritta BATTAGLIA MARIANNA dichiara che il veicolo targa {c.get('targa')} "
         f"in data {c.get('data_inizio')} era affidato al Sig. {c.get('cliente')}.\n"
         f"Nato a: {c.get('luogo_nascita')}\nResidente in: {c.get('residenza')}\n"
         f"Patente: {c.get('num_doc')}\n\nSi richiede rinotifica ai sensi della L. 445/2000.")
    pdf.multi_cell(0, 8, clean_t(t))
    pdf.ln(30); pdf.cell(0, 10, "Firma: ______________________", align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACCIA ---
st.set_page_config(page_title="MasterRent V28", layout="wide")
menu = st.sidebar.radio("Scegli", ["Nuovo", "Archivio", "Multe"])

if menu == "Nuovo":
    with st.form("f_v28"):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome Cliente")
        cf = c2.text_input("Codice Fiscale")
        nasc = c1.text_input("Luogo Nascita")
        res = c2.text_input("Residenza")
        pat = c1.text_input("Patente")
        tel = c2.text_input("Telefono")
        targa = c1.text_input("Targa").upper()
        prezzo = c2.number_input("Prezzo (€)", min_value=0.0)
        di = st.date_input("Inizio")
        df = st.date_input("Fine")
        st.write("---")
        accetto = st.checkbox("Accetto Condizioni e Privacy")
        st.camera_input("Foto Patente", key="foto_v28")
        st_canvas(height=100, key="firma_v28")
        if st.form_submit_button("SALVA"):
            if accetto:
                dat = {"cliente": nome, "cf": cf, "luogo_nascita": nasc, "residenza": res, "num_doc": pat, "targa": targa, "prezzo": prezzo, "data_inizio": str(di), "data_fine": str(df), "telefono": tel}
                supabase.table("contratti").insert(dat).execute()
                st.success("Noleggio Salvato!")

elif menu == "Archivio":
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"{c['cliente']} - {c['targa']}"):
            col1, col2 = st.columns(2)
            # Nomi file dinamici per fregare la cache del browser
            ts = int(time.time())
            col1.download_button("📜 CONTRATTO", crea_pdf_CONTRATTO(c), f"Contr_{c['id']}{ts}.pdf", key=f"c{c['id']}_{ts}")
            col2.download_button("💰 RICEVUTA", crea_pdf_RICEVUTA(c), f"Ricev_{c['id']}{ts}.pdf", key=f"r{c['id']}_{ts}")

elif menu == "Multe":
    t_m = st.text_input("Cerca Targa").upper()
    if t_m:
        rm = supabase.table("contratti").select("*").eq("targa", t_m).execute()
        if rm.data:
            ts = int(time.time())
            st.download_button("🚨 MODULO VIGILI", crea_pdf_VIGILI(rm.data[0]), f"Vigili_{t_m}{ts}.pdf", key=f"v{t_m}")
