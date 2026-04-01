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
    for k, v in r.items(): t = str(text).replace(k, v)
    return t.encode('latin-1', 'ignore').decode('latin-1')

st.set_page_config(page_title="MasterRent V30", layout="wide")
menu = st.sidebar.radio("Scegli", ["Nuovo", "Archivio", "Multe"])

if menu == "Nuovo":
    with st.form("f_v30"):
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
        accetto = st.checkbox("Accetto Condizioni e Privacy")
        st.camera_input("Foto Patente", key="cam_v30")
        st_canvas(height=100, key="sign_v30")
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
            
            # --- PDF 1: CONTRATTO (Scritto a mano qui) ---
            p1 = FPDF()
            p1.add_page()
            p1.set_text_color(200, 0, 0) # TITOLO ROSSO PER TEST
            p1.set_font("Arial", 'B', 16); p1.cell(0, 10, "CONTRATTO DI NOLEGGIO", ln=1, align='C')
            p1.set_text_color(0, 0, 0)
            p1.set_font("Arial", size=10); p1.ln(10)
            p1.multi_cell(0, 7, clean_t(f"Ditta: {DITTA}\nCliente: {c['cliente']}\nTarga: {c['targa']}\nCF: {c['cf']}\nNato a: {c['luogo_nascita']}\nResidente: {c['residenza']}\nPatente: {c['num_doc']}\nPeriodo: {c['data_inizio']} / {c['data_fine']}"))
            p1.ln(10); p1.set_font("Arial", 'B', 8); p1.multi_cell(0, 4, clean_t("CONDIZIONI: Responsabilita totale danni/furto. Multe a carico cliente. Privacy GDPR."))
            p1.ln(20); p1.cell(0, 10, "Firma: ______________", align='R')
            col1.download_button("📜 SCARICA CONTRATTO", p1.output(dest='S').encode('latin-1'), f"Contratto_{c['id']}.pdf", key=f"c_{c['id']}_v30")

            # --- PDF 2: RICEVUTA (Scritta a mano qui) ---
            p2 = FPDF()
            p2.add_page()
            p2.set_text_color(0, 0, 200) # TITOLO BLU PER TEST
            p2.set_font("Arial", 'B', 16); p2.cell(0, 10, "RICEVUTA PAGAMENTO", ln=1, align='C')
            p2.set_text_color(0, 0, 0)
            p2.set_font("Arial", size=12); p2.ln(20)
            p2.cell(0, 10, clean_t(f"Spett.le {c['cliente']}"), ln=1)
            p2.cell(0, 10, clean_t(f"Per noleggio scooter targa {c['targa']}"), ln=1)
            p2.ln(20); p1.set_font("Arial", 'B', 20)
            p2.cell(0, 20, clean_t(f"TOTALE EURO: {c['prezzo']}"), border=1, align='C')
            col2.download_button("💰 SCARICA RICEVUTA", p2.output(dest='S').encode('latin-1'), f"Ricevuta_{c['id']}.pdf", key=f"r_{c['id']}_v30")

elif menu == "Multe":
    tm = st.text_input("Targa").upper()
    if tm:
        rm = supabase.table("contratti").select("*").eq("targa", tm).execute()
        if rm.data:
            c = rm.data[0]
            pv = FPDF()
            pv.add_page()
            pv.set_font("Arial", 'B', 14); pv.cell(0, 10, "COMUNICAZIONE VIGILI", ln=1, align='C')
            pv.set_font("Arial", size=11); pv.ln(10)
            pv.multi_cell(0, 8, clean_t(f"Il veicolo {c['targa']} era condotto da {c['cliente']} (Nato a {c['luogo_nascita']}, CF {c['cf']})."))
            st.download_button("🚨 MODULO VIGILI", pv.output(dest='S').encode('latin-1'), f"Vigili_{tm}.pdf")
