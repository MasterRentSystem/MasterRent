import streamlit as st
import datetime
import fpdf
from fpdf import FPDF
from io import BytesIO
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
import time

# 1. CONNESSIONE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)
BUCKET_NAME = "DOCUMENTI_PATENTI"

# DATI AZIENDALI
DITTA = "BATTAGLIA MARIANNA"
DITTA_INFO = "Via Cognole, 5 - 80075 Forio (NA)\nP. IVA 10252601215 | C.F. BTTMNN87A53Z112S"

def clean_t(text):
    if not text or text == "None": return "---"
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in repls.items(): text = str(text).replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

def intestazione_standard(pdf, titolo):
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, DITTA, ln=True)
    pdf.set_font("Arial", size=9)
    pdf.multi_cell(0, 5, clean_t(DITTA_INFO))
    pdf.line(10, 32, 200, 32)
    pdf.ln(12)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, clean_t(titolo), ln=True, align='C')
    pdf.ln(5)

# --- FUNZIONE 1: CONTRATTO ---
def crea_contratto(c):
    pdf = FPDF()
    pdf.add_page()
    intestazione_standard(pdf, "CONTRATTO DI NOLEGGIO")
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 8, clean_t(f"CLIENTE: {c['cliente']}\nCF: {c['cf']}\nTARGA: {c['targa']}\nPERIODO: {c['data_inizio']} / {c['data_fine']}"), border=1)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 8); pdf.cell(0, 5, "CONDIZIONI GENERALI (1-14):", ln=True)
    pdf.set_font("Arial", size=7)
    pdf.multi_cell(0, 4, clean_t("Responsabilita totale danni e furto. Sanzioni C.d.S. a carico cliente + 25.83 euro. Foro Ischia. Casco obbligatorio. Privacy GDPR."), border='T')
    pdf.ln(20); pdf.cell(0, 10, "Firma Cliente: ______________________", align='R')
    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer

# --- FUNZIONE 2: RICEVUTA ---
def crea_ricevuta(c):
    pdf = FPDF()
    pdf.add_page()
    intestazione_standard(pdf, "RICEVUTA DI PAGAMENTO")
    pdf.set_font("Arial", size=12); pdf.ln(10)
    pdf.cell(0, 10, clean_t(f"Ricevuti da: {c['cliente']}"), ln=True)
    pdf.cell(0, 10, clean_t(f"Per noleggio targa: {c['targa']}"), ln=True)
    pdf.ln(20); pdf.set_font("Arial", 'B', 20)
    pdf.cell(0, 20, clean_t(f"TOTALE: Euro {c['prezzo']}"), border=1, ln=True, align='C')
    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer

# --- FUNZIONE 3: VIGILI ---
def crea_vigili(c):
    pdf = FPDF()
    pdf.add_page()
    intestazione_standard(pdf, "DICHIARAZIONE DATI CONDUCENTE")
    pdf.set_font("Arial", size=11)
    testo = (f"Il sottoscritto dichiara che il veicolo con targa {c['targa']} "
             f"era condotto dal cliente {c['cliente']} (C.F. {c['cf']}) "
             f"in data {c['data_inizio']}.\n\nSi richiede rinotifica ai sensi della L. 445/2000.")
    pdf.multi_cell(0, 8, clean_t(testo))
    pdf.ln(30); pdf.cell(0, 10, "Firma e Timbro: ______________________", align='R')
    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer

# --- INTERFACCIA ---
st.set_page_config(page_title="MasterRent V4", layout="wide")
scelta = st.sidebar.radio("Navigazione", ["Nuovo", "Archivio", "Multe"])

if scelta == "Nuovo":
    with st.form("f_v24"):
        c1, c2 = st.columns(2)
        n = c1.text_input("Nome Cliente")
        t = c2.text_input("Targa").upper()
        cf = c1.text_input("C.F.")
        p = c2.number_input("Prezzo (€)", min_value=0.0)
        di = st.date_input("Inizio")
        df = st.date_input("Fine")
        st.write("---")
        acc = st.checkbox("Accetto Privacy e Clausole 1-14")
        f = st.camera_input("Foto Patente")
        if st.form_submit_button("SALVA"):
            if acc:
                path = f"{t}_{int(time.time())}.jpg"
                if f: supabase.storage.from_(BUCKET_NAME).upload(path, f.getvalue())
                dat = {"cliente": n, "targa": t, "cf": cf, "prezzo": p, "data_inizio": str(di), "data_fine": str(df), "foto_path": path if f else None}
                supabase.table("contratti").insert(dat).execute()
                st.success("Dati archiviati!")

elif scelta == "Archivio":
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"{c['cliente']} - {c['targa']}"):
            col1, col2 = st.columns(2)
            # Qui usiamo il buffer BytesIO direttamente
            col1.download_button("📜 CONTRATTO", crea_contratto(c), f"Contratto_{c['id']}.pdf", key=f"c_{c['id']}")
            col2.download_button("💰 RICEVUTA", crea_ricevuta(c), f"Ricevuta_{c['id']}.pdf", key=f"r_{c['id']}")

elif scelta == "Multe":
    tm = st.text_input("Targa").upper()
    if tm:
        rm = supabase.table("contratti").select("*").eq("targa", tm).execute()
        if rm.data:
            st.download_button("🚨 MODULO VIGILI", crea_vigili(rm.data[0]), f"Vigili_{tm}.pdf")
