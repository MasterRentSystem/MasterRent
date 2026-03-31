import streamlit as st
import datetime
from fpdf import FPDF
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
import time

# 1. CONNESSIONE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)
BUCKET_NAME = "DOCUMENTI_PATENTI"

INFO_MARIANNA = "BATTAGLIA MARIANNA\nVia Cognole, 5 - 80075 Forio (NA)\nP. IVA 10252601215 | C.F. BTTMNN87A53Z112S"

def pulisci(t):
    if not t or t == "None": return "---"
    r = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in r.items(): t = str(t).replace(k, v)
    return t.encode('latin-1', 'ignore').decode('latin-1')

# --- 📜 FUNZIONE 1: GENERATORE CONTRATTO ---
def build_CONTRATTO_pdf(c):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "BATTAGLIA MARIANNA - CONTRATTO", ln=1)
    pdf.set_font("Arial", size=9); pdf.multi_cell(0, 5, pulisci(INFO_MARIANNA))
    pdf.line(10, 35, 200, 35); pdf.ln(10)
    pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, "DATI DEL NOLEGGIO", ln=1, align='C')
    pdf.set_font("Arial", size=10)
    testo = f"CLIENTE: {c['cliente']}\nCF: {c['cf']}\nTARGA: {c['targa']}\nDAL: {c['data_inizio']} AL: {c['data_fine']}"
    pdf.multi_cell(0, 8, pulisci(testo), border=1); pdf.ln(5)
    pdf.set_font("Arial", 'B', 8); pdf.cell(0, 5, "CLAUSOLE (1-14):", ln=1)
    pdf.set_font("Arial", size=7); pdf.multi_cell(0, 4, pulisci("Responsabilita totale danni/furto a carico cliente. Sanzioni + 25.83 Euro. Foro Ischia. Casco obbligatorio. Privacy GDPR."), border='T')
    pdf.ln(20); pdf.cell(0, 10, "Firma: ______________________", align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- 💰 FUNZIONE 2: GENERATORE RICEVUTA ---
def build_RICEVUTA_pdf(c):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "BATTAGLIA MARIANNA - RICEVUTA", ln=1)
    pdf.set_font("Arial", size=9); pdf.multi_cell(0, 5, pulisci(INFO_MARIANNA))
    pdf.line(10, 35, 200, 35); pdf.ln(20)
    pdf.set_font("Arial", 'B', 25)
    pdf.cell(0, 25, pulisci(f"TOTALE: Euro {c['prezzo']}"), border=1, ln=1, align='C')
    pdf.ln(15); pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, pulisci(f"Ricevuti da: {c['cliente']}"), ln=1)
    pdf.cell(0, 10, pulisci(f"Per targa: {c['targa']}"), ln=1)
    return pdf.output(dest='S').encode('latin-1')

# --- 🚨 FUNZIONE 3: GENERATORE VIGILI ---
def build_VIGILI_pdf(c):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "DICHIARAZIONE PER RINOTIFICA", ln=1)
    pdf.ln(10); pdf.set_font("Arial", size=11)
    testo = (f"La sottoscritta BATTAGLIA MARIANNA dichiara che il veicolo targa {c['targa']} "
             f"era affidato al Sig. {c['cliente']} (CF: {c['cf']}) residente in {c['residenza']}.\n\n"
             f"Si richiede rinotifica verbale ai sensi della L. 445/2000.")
    pdf.multi_cell(0, 8, pulisci(testo))
    pdf.ln(30); pdf.cell(0, 10,

cat << 'EOF' > interfaccia_app.py
import streamlit as st
import datetime
from fpdf import FPDF
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
import time

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

# --- FUNZIONE GENERICA PDF ---
def genera_documento(c, tipo):
    pdf = FPDF()
    pdf.add_page()
    
    # Intestazione
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, DITTA, ln=True)
    pdf.set_font("Arial", size=9)
    pdf.multi_cell(0, 5, clean_t(DITTA_INFO))
    pdf.line(10, 32, 200, 32)
    pdf.ln(10)

    if tipo == "CONTRATTO":
        pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, "CONTRATTO DI NOLEGGIO", ln=True, align='C'); pdf.ln(5)
        pdf.set_font("Arial", size=10)
        info = f"CLIENTE: {c.get('cliente')}\nNATO A: {c.get('luogo_nascita')}\nRESIDENTE: {c.get('residenza')}\nC.F.: {c.get('cf')}\nPATENTE: {c.get('num_doc')}\nTEL: {c.get('telefono')}\n\nVEICOLO: {c.get('targa')}\nDAL: {c.get('data_inizio')} AL: {c.get('data_fine')}"
        pdf.multi_cell(0, 7, clean_t(info), border=1)
        pdf.ln(5); pdf.set_font("Arial", 'B', 8); pdf.cell(0, 5, "CONDIZIONI (1-14):", ln=True)
        pdf.set_font("Arial", size=6); pdf.multi_cell(0, 3, clean_t("Responsabilita totale danni/furto. Multe a carico cliente + 25.83 euro gestione. Obbligo casco. Foro Ischia. Privacy GDPR."), border='T')
        pdf.ln(15); pdf.cell(0, 10, "Firma del Cliente: ______________________", align='R')
    
    elif tipo == "RICEVUTA":
        pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, "RICEVUTA DI PAGAMENTO", ln=True, align='C'); pdf.ln(15)
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, clean_t(f"Ricevuti da: {c.get('cliente')}"), ln=True)
        pdf.cell(0, 10, clean_t(f"Per noleggio veicolo targa: {c.get('targa')}"), ln=True)
        pdf.ln(15); pdf.set_font("Arial", 'B', 20)
        pdf.cell(0, 20, clean_t(f"TOTALE PAGATO: Euro {c.get('prezzo')}"), border=1, ln=True, align='C')

    elif tipo == "VIGILI":
        pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, "COMUNICAZIONE DATI PER RINOTIFICA", ln=True, align='C'); pdf.ln(10)
        pdf.set_font("Arial", size=11)
        t = (f"La sottoscritta BATTAGLIA MARIANNA dichiara che il veicolo targa {c.get('targa')} "
             f"in data {c.get('data_inizio')} era affidato al Sig. {c.get('cliente')}.\n"
             f"Residente in: {c.get('residenza')}\nPatente: {c.get('num_doc')}\n\n"
             f"Si richiede rinotifica verbale ai sensi della L. 445/2000.")
        pdf.multi_cell(0, 8, clean_t(t))
        pdf.ln(25); pdf.cell(0, 10, "Timbro e Firma: ______________________", align='R')

    return pdf.output(dest='S').encode('latin-1')

# --- APP ---
st.set_page_config(page_title="MasterRent V26", layout="wide")
m = st.sidebar.radio("Menu", ["Nuovo", "Archivio", "Multe"])

if m == "Nuovo":
    with st.form("f_v26"):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Cognome Nome")
        cf = c2.text_input("C.F.")
        nasc = c1.text_input("Luogo Nascita")
        res = c2.text_input("Residenza")
        pat = c1.text_input("Patente")
        tel = c2.text_input("Telefono")
        targa = c1.text_input("Targa").upper()
        prezzo = c2.number_input("Prezzo", min_value=0.0)
        di = st.date_input("Inizio")
        df = st.date_input("Fine")
        acc = st.checkbox("Accetto tutto (1-14 + Privacy)")
        st.camera_input("Foto Patente", key="cam")
        st_canvas(height=100, key="sign")
        if st.form_submit_button("SALVA"):
            if acc:
                dat = {"cliente": nome, "cf": cf, "luogo_nascita": nasc, "residenza": res, "num_doc": pat, "targa": targa, "prezzo": prezzo, "data_inizio": str(di), "data_fine": str(df), "telefono": tel}
                supabase.table("contratti").insert(dat).execute()
                st.success("Salvato!")

elif m == "Archivio":
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"{c['cliente']} - {c['targa']}"):
            col1, col2 = st.columns(2)
            # GENERIAMO IL PDF DIVERSO PER OGNI TASTO
            col1.download_button("📜 CONTRATTO", genera_documento(c, "CONTRATTO"), f"C_{c['id']}.pdf", key=f"c_{c['id']}")
            col2.download_button("💰 RICEVUTA", genera_documento(c, "RICEVUTA"), f"R_{c['id']}.pdf", key=f"r_{c['id']}")

elif m == "Multe":
    t_m = st.text_input("Targa").upper()
    if t_m:
        rm = supabase.table("contratti").select("*").eq("targa", t_m).execute()
        if rm.data:
            st.download_button("🚨 VIGILI", genera_documento(rm.data[0], "VIGILI"), f"V_{t_m}.pdf")
