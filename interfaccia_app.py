import streamlit as st
import datetime
from fpdf import FPDF
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
import time
import uuid

# 1. CONNESSIONE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)
BUCKET_NAME = "DOCUMENTI_PATENTI"

def clean_t(text):
    if not text or text == "None": return "---"
    r = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in r.items(): text = str(text).replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

# --- FUNZIONI PURE (UNA PER TIPO) ---

def genera_bytes_CONTRATTO(c):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16); pdf.cell(0, 10, "BATTAGLIA MARIANNA - CONTRATTO", ln=1, align='C')
    pdf.set_font("Arial", size=10); pdf.ln(10)
    # Codice univoco per debug (se cambia, i PDF sono diversi)
    pdf.set_font("Arial", 'I', 7); pdf.cell(0, 5, f"ID Sessione: {uuid.uuid4()}", ln=1); pdf.ln(5)
    pdf.set_font("Arial", size=11)
    testo = f"CLIENTE: {c['cliente']}\nCF: {c['cf']}\nNATO A: {c['luogo_nascita']}\nRESIDENTE: {c['residenza']}\nPATENTE: {c['num_doc']}\nTEL: {c['telefono']}\n\nVEICOLO: {c['targa']}\nDAL: {c['data_inizio']} AL: {c['data_fine']}"
    pdf.multi_cell(0, 7, clean_t(testo), border=1)
    pdf.ln(10); pdf.set_font("Arial", 'B', 8); pdf.multi_cell(0, 4, clean_t("CONDIZIONI 1-14: Responsabilita danni/furto. Multe a carico cliente. Foro Ischia."))
    pdf.ln(20); pdf.cell(0, 10, "Firma: ______________________", align='R')
    return pdf.output(dest='S').encode('latin-1')

def genera_bytes_RICEVUTA(c):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16); pdf.cell(0, 10, "BATTAGLIA MARIANNA - RICEVUTA", ln=1, align='C')
    pdf.set_font("Arial", size=10); pdf.ln(10)
    pdf.set_font("Arial", 'I', 7); pdf.cell(0, 5, f"ID Sessione: {uuid.uuid4()}", ln=1); pdf.ln(5)
    pdf.set_font("Arial", size=14); pdf.ln(10)
    pdf.cell(0, 10, clean_t(f"Ricevuto da: {c['cliente']}"), ln=1)
    pdf.cell(0, 10, clean_t(f"Per targa: {c['targa']}"), ln=1)
    pdf.ln(20); pdf.set_font("Arial", 'B', 22)
    pdf.cell(0, 25, clean_t(f"TOTALE EURO: {c['prezzo']}"), border=1, ln=1, align='C')
    return pdf.output(dest='S').encode('latin-1')

def genera_bytes_VIGILI(c):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, "MODULO VIGILI URBANI", ln=1, align='C'); pdf.ln(10)
    pdf.set_font("Arial", size=11)
    pdf.multi_cell(0, 8, clean_t(f"Si dichiara che il veicolo targa {c['targa']} era condotto da {c['cliente']} (Nato a {c['luogo_nascita']}, CF {c['cf']}).\nRichiesta rinotifica ai sensi della L. 445/2000."))
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACCIA ---
st.set_page_config(page_title="MasterRent Fix", layout="wide")
menu = st.sidebar.radio("Scegli", ["Nuovo", "Archivio", "Multe"])

if menu == "Nuovo":
    with st.form("form_master"):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Cognome Nome")
        cf = c2.text_input("C.F.")
        nasc = c1.text_input("Luogo/Data Nascita")
        res = c2.text_input("Residenza")
        pat = c1.text_input("Patente")
        tel = c2.text_input("Telefono")
        targa = c1.text_input("Targa").upper()
        prezzo = c2.number_input("Prezzo (€)", min_value=0.0)
        di = st.date_input("Inizio")
        df = st.date_input("Fine")
        st.write("---")
        accetto = st.checkbox("Accetto Condizioni e Privacy")
        st.camera_input("Foto Patente", key="cam")
        st_canvas(height=100, key="sign")
        if st.form_submit_button("SALVA"):
            if accetto:
                dat = {"cliente": nome, "cf": cf, "luogo_nascita": nasc, "residenza": res, "num_doc": pat, "targa": targa, "prezzo": prezzo, "data_inizio": str(di), "data_fine": str(df), "telefono": tel}
                supabase.table("contratti").insert(dat).execute()
                st.success("Salvato!")

elif menu == "Archivio":
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"{c['cliente']} - {c['targa']}"):
            col1, col2 = st.columns(2)
            
            # CHIAMATA ALLA FUNZIONE DENTRO IL PULSANTE
            col1.download_button(
                label="📜 SCARICA CONTRATTO",
                data=genera_bytes_CONTRATTO(c),
                file_name=f"Contr_{c['id']}.pdf",
                mime="application/pdf",
                key=f"btn_c_{c['id']}_{uuid.uuid4()}"
            )
            
            col2.download_button(
                label="💰 SCARICA RICEVUTA",
                data=genera_bytes_RICEVUTA(c),
                file_name=f"Ricev_{c['id']}.pdf",
                mime="application/pdf",
                key=f"btn_r_{c['id']}_{uuid.uuid4()}"
            )

elif menu == "Multe":
    tm = st.text_input("Targa").upper()
    if tm:
        rm = supabase.table("contratti").select("*").eq("targa", tm).execute()
        if rm.data:
            c = rm.data[0]
            st.download_button("🚨 SCARICA VIGILI", genera_bytes_VIGILI(c), f"Vigili_{tm}.pdf", key=f"v_{c['id']}")
