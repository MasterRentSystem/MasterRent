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

def clean_t(text):
    if not text or text == "None": return "---"
    r = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in r.items(): text = str(text).replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

# --- FUNZIONE UNICA CON LOGICA SEPARATA ---
def crea_documento_fpdf(c, tipo):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    
    if tipo == "CONTRATTO":
        pdf.cell(0, 10, "CONTRATTO DI NOLEGGIO - MASTERRENT", ln=1, align='C')
        pdf.set_font("Arial", size=10); pdf.ln(10)
        testo = f"CLIENTE: {c['cliente']}\nCF: {c['cf']}\nNATO A: {c['luogo_nascita']}\nRESIDENTE: {c['residenza']}\nPATENTE: {c['num_doc']}\nTEL: {c['telefono']}\n\nTARGA: {c['targa']}\nDAL: {c['data_inizio']} AL: {c['data_fine']}"
        pdf.multi_cell(0, 7, clean_t(testo), border=1)
        pdf.ln(10); pdf.set_font("Arial", 'B', 8); pdf.multi_cell(0, 4, clean_t("CONDIZIONI 1-14: Danni/Furto cliente. Multe + spese. Foro Ischia."))
        pdf.ln(20); pdf.cell(0, 10, "Firma Cliente: ______________________", align='R')
    
    else: # RICEVUTA
        pdf.cell(0, 10, "RICEVUTA DI PAGAMENTO - MASTERRENT", ln=1, align='C')
        pdf.set_font("Arial", size=12); pdf.ln(20)
        pdf.cell(0, 10, clean_t(f"Ricevuto da: {c['cliente']}"), ln=1)
        pdf.cell(0, 10, clean_t(f"Per noleggio scooter targa {c['targa']}"), ln=1)
        pdf.ln(20); pdf.set_font("Arial", 'B', 22)
        pdf.cell(0, 25, clean_t(f"TOTALE EURO: {c['prezzo']}"), border=1, ln=1, align='C')
    
    return pdf.output(dest='S').encode('latin-1')

# --- APP ---
st.set_page_config(page_title="MasterRent V32", layout="wide")
menu = st.sidebar.radio("Menu", ["Nuovo", "Archivio", "Multe"])

if menu == "Nuovo":
    with st.form("f_v32"):
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
        acc = st.checkbox("Accetto tutto")
        st.camera_input("Foto", key="cam")
        st_canvas(height=100, key="sign")
        if st.form_submit_button("SALVA"):
            if acc:
                dat = {"cliente": nome, "cf": cf, "luogo_nascita": nasc, "residenza": res, "num_doc": pat, "targa": targa, "prezzo": prezzo, "data_inizio": str(di), "data_fine": str(df), "telefono": tel}
                supabase.table("contratti").insert(dat).execute()
                st.success("Salvato!")

elif menu == "Archivio":
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"📄 {c['cliente']} - {c['targa']}"):
            col1, col2 = st.columns(2)
            
            # Generazione IMMEDIATA dentro il pulsante
            col1.download_button(
                label="📜 SCARICA CONTRATTO",
                data=crea_documento_fpdf(c, "CONTRATTO"),
                file_name=f"Contratto_{c['id']}.pdf",
                mime="application/pdf",
                key=f"btn_c_{c['id']}_{time.time()}"
            )
            
            col2.download_button(
                label="💰 SCARICA RICEVUTA",
                data=crea_documento_fpdf(c, "RICEVUTA"),
                file_name=f"Ricevuta_{c['id']}.pdf",
                mime="application/pdf",
                key=f"btn_r_{c['id']}_{time.time()}"
            )

elif menu == "Multe":
    tm = st.text_input("Targa").upper()
    if tm:
        rm = supabase.table("contratti").select("*").eq("targa", tm).execute()
        if rm.data:
            c = rm.data[0]
            st.download_button("🚨 VIGILI", crea_documento_fpdf(c, "CONTRATTO"), f"V_{c['id']}.pdf")
