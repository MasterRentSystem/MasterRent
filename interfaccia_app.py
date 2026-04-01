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

# --- INTERFACCIA ---
st.set_page_config(page_title="MasterRent V29", layout="wide")
menu = st.sidebar.radio("Scegli", ["Nuovo", "Archivio", "Multe"])

if menu == "Nuovo":
    with st.form("f_v29"):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome Cliente")
        cf = c2.text_input("Codice Fiscale")
        nasc = c1.text_input("Luogo/Data Nascita")
        res = c2.text_input("Residenza")
        pat = c1.text_input("Patente")
        tel = c2.text_input("Telefono")
        targa = c1.text_input("Targa").upper()
        prezzo = c2.number_input("Prezzo (€)", min_value=0.0)
        di = st.date_input("Inizio")
        df = st.date_input("Fine")
        st.write("---")
        accetto = st.checkbox("Accetto Condizioni (1-14) e Privacy")
        foto = st.camera_input("Foto Patente")
        st_canvas(height=100, key="firma_v29")
        if st.form_submit_button("SALVA"):
            if accetto:
                fn = f"{targa}_{int(time.time())}.jpg"
                if foto: supabase.storage.from_(BUCKET_NAME).upload(fn, foto.getvalue())
                dat = {"cliente": nome, "cf": cf, "luogo_nascita": nasc, "residenza": res, "num_doc": pat, "targa": targa, "prezzo": prezzo, "data_inizio": str(di), "data_fine": str(df), "telefono": tel, "foto_path": fn if foto else None}
                supabase.table("contratti").insert(dat).execute()
                st.success("Salvato!")

elif menu == "Archivio":
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"{c['cliente']} - {c['targa']}"):
            col1, col2 = st.columns(2)
            
            # --- GENERAZIONE CONTRATTO DIRETTA ---
            pdf_c = FPDF()
            pdf_c.add_page()
            pdf_c.set_font("Arial", 'B', 16); pdf_c.cell(0, 10, DITTA, ln=1)
            pdf_c.set_font("Arial", size=9); pdf_c.multi_cell(0, 5, clean_t(DITTA_INFO))
            pdf_c.line(10, 32, 200, 32); pdf_c.ln(10)
            pdf_c.set_font("Arial", 'B', 14); pdf_c.cell(0, 10, "CONTRATTO DI NOLEGGIO", ln=1, align='C'); pdf_c.ln(5)
            pdf_c.set_font("Arial", size=10)
            pdf_c.multi_cell(0, 7, clean_t(f"CLIENTE: {c['cliente']}\nNATO A: {c['luogo_nascita']}\nRESIDENTE: {c['residenza']}\nCF: {c['cf']}\nPATENTE: {c['num_doc']}\nTEL: {c['telefono']}\nVEICOLO: {c['targa']}\nDAL: {c['data_inizio']} AL: {c['data_fine']}"), border=1)
            pdf_c.ln(5); pdf_c.set_font("Arial", 'B', 8); pdf_c.cell(0, 5, "CONDIZIONI GENERALI:", ln=1)
            pdf_c.set_font("Arial", size=6); pdf_c.multi_cell(0, 3, clean_t("Responsabilita totale danni/furto. Multe + 25.83 euro. Obbligo casco. Foro Ischia. Privacy."), border='T')
            pdf_c.ln(15); pdf_c.cell(0, 10, "Firma Cliente: ______________________", align='R')
            
            col1.download_button("📜 CONTRATTO", pdf_c.output(dest='S').encode('latin-1'), f"Contr_{c['id']}.pdf", key=f"btn_c_{c['id']}_{time.time()}")

            # --- GENERAZIONE RICEVUTA DIRETTA ---
            pdf_r = FPDF()
            pdf_r.add_page()
            pdf_r.set_font("Arial", 'B', 16); pdf_r.cell(0, 10, DITTA, ln=1)
            pdf_r.set_font("Arial", size=9); pdf_r.multi_cell(0, 5, clean_t(DITTA_INFO))
            pdf_r.line(10, 32, 200, 32); pdf_r.ln(10)
            pdf_r.set_font("Arial", 'B', 14); pdf_r.cell(0, 10, "RICEVUTA DI PAGAMENTO", ln=1, align='C'); pdf_r.ln(15)
            pdf_r.set_font("Arial", size=12)
            pdf_r.cell(0, 10, clean_t(f"Ricevuto da: {c['cliente']}"), ln=1)
            pdf_r.cell(0, 10, clean_t(f"Per targa: {c['targa']}"), ln=1)
            pdf_r.ln(15); pdf_r.set_font("Arial", 'B', 20)
            pdf_r.cell(0, 20, clean_t(f"TOTALE: Euro {c['prezzo']}"), border=1, ln=1, align='C')
            
            col2.download_button("💰 RICEVUTA", pdf_r.output(dest='S').encode('latin-1'), f"Ricev_{c['id']}.pdf", key=f"btn_r_{c['id']}_{time.time()}")

elif menu == "Multe":
    tm = st.text_input("Targa").upper()
    if tm:
        rm = supabase.table("contratti").select("*").eq("targa", tm).execute()
        if rm.data:
            c = rm.data[0]
            pdf_v = FPDF()
            pdf_v.add_page()
            pdf_v.set_font("Arial", 'B', 16); pdf_v.cell(0, 10, DITTA, ln=1)
            pdf_v.line(10, 32, 200, 32); pdf_v.ln(15)
            pdf_v.set_font("Arial", 'B', 12); pdf_v.cell(0, 10, "MODULO RINOTIFICA VIGILI", ln=1, align='C'); pdf_v.ln(10)
            pdf_v.set_font("Arial", size=11)
            pdf_v.multi_cell(0, 8, clean_t(f"Il veicolo targa {c['targa']} in data {c['data_inizio']} era affidato a {c['cliente']}, nato a {c['luogo_nascita']} e residente in {c['residenza']}.\n\nSi richiede rinotifica ai sensi della L. 445/2000."))
            st.download_button("🚨 MODULO VIGILI", pdf_v.output(dest='S').encode('latin-1'), f"Vigili_{tm}.pdf")
