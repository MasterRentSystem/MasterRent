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

def clean_t(t):
    if not t or t == "None": return "---"
    r = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in r.items(): t = str(t).replace(k, v)
    return t.encode('latin-1', 'ignore').decode('latin-1')

st.set_page_config(page_title="MasterRent V38", layout="wide")

menu = st.sidebar.radio("Menu", ["📝 Nuovo Noleggio", "🗄️ Archivio", "🚨 Multe"])

if menu == "📝 Nuovo Noleggio":
    with st.form("form_v38"):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Cognome e Nome")
        cf = c2.text_input("C.F.")
        nascita = c1.text_input("Luogo/Data Nascita")
        residenza = c2.text_input("Residenza")
        patente = c1.text_input("Num. Patente")
        telefono = c2.text_input("Telefono")
        targa = c1.text_input("TARGA").upper()
        prezzo = c2.number_input("Prezzo (€)", min_value=0.0)
        di = st.date_input("Inizio", datetime.date.today())
        df = st.date_input("Fine", datetime.date.today() + datetime.timedelta(days=1))
        accetto = st.checkbox("Accetto Condizioni e Privacy")
        if st.form_submit_button("💾 SALVA"):
            if nome and targa and accetto:
                dat = {"cliente": nome, "cf": cf, "luogo_nascita": nascita, "residenza": residenza, "num_doc": patente, "telefono": telefono, "targa": targa, "prezzo": prezzo, "data_inizio": str(di), "data_fine": str(df)}
                supabase.table("contratti").insert(dat).execute()
                st.success("Noleggio Salvato!")

elif menu == "🗄️ Archivio":
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"📄 {c['cliente']} - {c['targa']}"):
            col1, col2 = st.columns(2)
            
            # --- CONTRATTO ---
            pdf_c = FPDF()
            pdf_c.add_page()
            pdf_c.set_font("Helvetica", 'B', 16)
            pdf_c.cell(0, 10, "CONTRATTO DI NOLEGGIO", center=True, new_x="LMARGIN", new_y="NEXT")
            pdf_c.set_font("Helvetica", size=10); pdf_c.ln(10)
            info_c = f"CLIENTE: {c['cliente']}\nNATO A: {c.get('luogo_nascita','---')}\nRESIDENTE: {c.get('residenza','---')}\nCF: {c['cf']}\nPATENTE: {c.get('num_doc','---')}\nTEL: {c.get('telefono','---')}\n\nVEICOLO: {c['targa']}\nDAL: {c['data_inizio']} AL: {c['data_fine']}"
            pdf_c.multi_cell(0, 7, clean_t(info_c), border=1)
            pdf_c.ln(10); pdf_c.set_font("Helvetica", 'B', 8)
            pdf_c.multi_cell(0, 4, clean_t("CONDIZIONI: Il cliente e responsabile di danni e furto. Multe a carico cliente + spese gestione. Foro Ischia."))
            pdf_c.ln(20); pdf_c.cell(0, 10, "Firma Cliente: ______________________", align='R')
            
            col1.download_button(
                label="📜 SCARICA CONTRATTO",
                data=bytes(pdf_c.output()), # Forza la conversione in bytes
                file_name=f"Contratto_{c['id']}.pdf",
                mime="application/pdf",
                key=f"c_{c['id']}"
            )

            # --- RICEVUTA ---
            pdf_r = FPDF()
            pdf_r.add_page()
            pdf_r.set_font("Helvetica", 'B', 16)
            pdf_r.cell(0, 10, "RICEVUTA DI PAGAMENTO", center=True, new_x="LMARGIN", new_y="NEXT")
            pdf_r.set_font("Helvetica", size=12); pdf_r.ln(20)
            pdf_r.cell(0, 10, clean_t(f"Ricevuto da: {c['cliente']}"), new_x="LMARGIN", new_y="NEXT")
            pdf_r.cell(0, 10, clean_t(f"Per targa: {c['targa']}"), new_x="LMARGIN", new_y="NEXT")
            pdf_r.ln(20); pdf_r.set_font("Helvetica", 'B', 20)
            pdf_r.cell(0, 20, clean_t(f"TOTALE: {c['prezzo']} Euro"), border=1, align='C', new_x="LMARGIN", new_y="NEXT")
            
            col2.download_button(
                label="💰 SCARICA RICEVUTA",
                data=bytes(pdf_r.output()), 
                file_name=f"Ricevuta_{c['id']}.pdf",
                mime="application/pdf",
                key=f"r_{c['id']}"
            )

elif menu == "🚨 Multe":
    t_m = st.text_input("Targa").upper()
    if t_m:
        rm = supabase.table("contratti").select("*").eq("targa", t_m).execute()
        if rm.data:
            c = rm.data[0]
            pdf_v = FPDF()
            pdf_v.add_page()
            pdf_v.set_font("Helvetica", 'B', 14); pdf_v.cell(0, 10, "MODULO VIGILI", center=True, new_x="LMARGIN", new_y="NEXT")
            pdf_v.set_font("Helvetica", size=11); pdf_v.ln(10)
            pdf_v.multi_cell(0, 8, clean_t(f"Il veicolo {c['targa']} era condotto da {c['cliente']} in data {c['data_inizio']}."))
            st.download_button("🚨 SCARICA VIGILI", bytes(pdf_v.output()), f"Vigili_{c['targa']}.pdf", key=f"v_{c['id']}")
