import streamlit as st
import datetime
from fpdf import FPDF
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
import time
import io

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

st.set_page_config(page_title="MasterRent V37", layout="wide")

menu = st.sidebar.radio("Menu", ["📝 Nuovo Noleggio", "🗄️ Archivio", "🚨 Multe"])

if menu == "📝 Nuovo Noleggio":
    with st.form("form_v37"):
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
        st.form_submit_button("💾 SALVA")
        if nome and targa and accetto:
            dat = {"cliente": nome, "cf": cf, "luogo_nascita": nascita, "residenza": residenza, "num_doc": patente, "telefono": telefono, "targa": targa, "prezzo": prezzo, "data_inizio": str(di), "data_fine": str(df)}
            supabase.table("contratti").insert(dat).execute()
            st.success("Salvato!")

elif menu == "🗄️ Archivio":
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"📄 {c['cliente']} - {c['targa']}"):
            col1, col2 = st.columns(2)
            
            # --- GENERAZIONE CONTRATTO (Buffer isolato) ---
            pdf_c = FPDF()
            pdf_c.add_page()
            pdf_c.set_font("Arial", 'B', 16)
            pdf_c.cell(0, 10, "CONTRATTO DI NOLEGGIO", ln=1, align='C')
            pdf_c.set_font("Arial", size=10); pdf_c.ln(10)
            info_c = f"CLIENTE: {c['cliente']}\nTARGA: {c['targa']}\nCF: {c['cf']}\nPATENTE: {c.get('num_doc','---')}"
            pdf_c.multi_cell(0, 7, clean_t(info_c), border=1)
            pdf_c.ln(10); pdf_c.set_font("Arial", 'B', 8)
            pdf_c.cell(0, 5, "CONDIZIONI: Responsabilita danni cliente. Multe + spese.", ln=1)
            
            # Trasformiamo in bytes in modo sicuro per fpdf2
            buffer_c = io.BytesIO()
            pdf_str_c = pdf_c.output()
            buffer_c.write(pdf_str_c)
            buffer_c.seek(0)
            
            col1.download_button("📜 SCARICA CONTRATTO", data=buffer_c, file_name=f"Contratto_{c['id']}.pdf", mime="application/pdf", key=f"c_{c['id']}_v37")

            # --- GENERAZIONE RICEVUTA (Buffer isolato) ---
            pdf_r = FPDF()
            pdf_r.add_page()
            pdf_r.set_font("Arial", 'B', 16)
            pdf_r.cell(0, 10, "RICEVUTA DI PAGAMENTO", ln=1, align='C')
            pdf_r.set_font("Arial", size=12); pdf_r.ln(20)
            pdf_r.cell(0, 10, clean_t(f"Ricevuto da: {c['cliente']}"), ln=1)
            pdf_r.ln(10); pdf_r.set_font("Arial", 'B', 20)
            pdf_r.cell(0, 20, clean_t(f"TOTALE: {c['prezzo']} Euro"), border=1, align='C')
            
            buffer_r = io.BytesIO()
            pdf_str_r = pdf_r.output()
            buffer_r.write(pdf_str_r)
            buffer_r.seek(0)
            
            col2.download_button("💰 SCARICA RICEVUTA", data=buffer_r, file_name=f"Ricevuta_{c['id']}.pdf", mime="application/pdf", key=f"r_{c['id']}_v37")

elif menu == "🚨 Multe":
    t_m = st.text_input("Targa").upper()
    if t_m:
        rm = supabase.table("contratti").select("*").eq("targa", t_m).execute()
        if rm.data:
            c = rm.data[0]
            pdf_v = FPDF()
            pdf_v.add_page()
            pdf_v.set_font("Arial", 'B', 14); pdf_v.cell(0, 10, "MODULO VIGILI", ln=1, align='C')
            pdf_v.set_font("Arial", size=11); pdf_v.ln(10)
            pdf_v.multi_cell(0, 8, clean_t(f"Il veicolo {c['targa']} era condotto da {c['cliente']}."))
            
            buffer_v = io.BytesIO()
            buffer_v.write(pdf_v.output())
            buffer_v.seek(0)
            st.download_button("🚨 SCARICA VIGILI", data=buffer_v, file_name=f"Vigili_{c['targa']}.pdf", key=f"v_{c['id']}")
