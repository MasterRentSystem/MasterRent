import streamlit as st
import datetime
from fpdf import FPDF
from supabase import create_client
import time

# 1. CONNESSIONE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def clean_t(t):
    if not t or t == "None": return "---"
    r = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in r.items(): t = str(t).replace(k, v)
    return t.encode('latin-1', 'ignore').decode('latin-1')

st.set_page_config(page_title="MasterRent V39", layout="wide")

menu = st.sidebar.radio("Menu", ["Nuovo", "Archivio", "Multe"])

if menu == "Nuovo":
    with st.form("f_v39"):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome Cliente")
        cf = c2.text_input("Codice Fiscale")
        nascita = c1.text_input("Luogo/Data Nascita")
        residenza = c2.text_input("Residenza")
        patente = c1.text_input("Num. Patente")
        telefono = c2.text_input("Telefono")
        targa = c1.text_input("Targa").upper()
        prezzo = c2.number_input("Prezzo (€)", min_value=0.0)
        di = st.date_input("Inizio", datetime.date.today())
        df = st.date_input("Fine", datetime.date.today() + datetime.timedelta(days=1))
        if st.form_submit_button("SALVA"):
            dat = {"cliente": nome, "cf": cf, "luogo_nascita": nascita, "residenza": residenza, "num_doc": patente, "telefono": telefono, "targa": targa, "prezzo": prezzo, "data_inizio": str(di), "data_fine": str(df)}
            supabase.table("contratti").insert(dat).execute()
            st.success("Salvato!")

elif menu == "Archivio":
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"{c['cliente']} - {c['targa']}"):
            col1, col2 = st.columns(2)
            
            # --- PDF CONTRATTO ---
            p_c = FPDF()
            p_c.add_page()
            p_c.set_font("Helvetica", 'B', 16)
            p_c.cell(0, 10, "CONTRATTO DI NOLEGGIO", ln=1, align='C')
            p_c.set_font("Helvetica", size=10); p_c.ln(10)
            info = f"CLIENTE: {c['cliente']}\nNATO A: {c.get('luogo_nascita','---')}\nRESIDENTE: {c.get('residenza','---')}\nCF: {c['cf']}\nPATENTE: {c.get('num_doc','---')}\nTEL: {c.get('telefono','---')}\nVEICOLO: {c['targa']}\nDAL: {c['data_inizio']} AL: {c['data_fine']}"
            p_c.multi_cell(0, 7, clean_t(info), border=1)
            
            # Conversione ultra-stabile
            data_c = p_c.output(dest='S').encode('latin-1')
            col1.download_button("📜 CONTRATTO", data_c, f"C_{c['id']}.pdf", "application/pdf", key=f"c_{c['id']}")

            # --- PDF RICEVUTA ---
            p_r = FPDF()
            p_r.add_page()
            p_r.set_font("Helvetica", 'B', 16)
            p_r.cell(0, 10, "RICEVUTA DI PAGAMENTO", ln=1, align='C')
            p_r.set_font("Helvetica", size=12); p_r.ln(20)
            p_r.cell(0, 10, clean_t(f"Ricevuto da: {c['cliente']}"), ln=1)
            p_r.ln(10); p_r.set_font("Helvetica", 'B', 20)
            p_r.cell(0, 20, clean_t(f"TOTALE: {c['prezzo']} Euro"), border=1, align='C')
            
            data_r = p_r.output(dest='S').encode('latin-1')
            col2.download_button("💰 RICEVUTA", data_r, f"R_{c['id']}.pdf", "application/pdf", key=f"r_{c['id']}")

elif menu == "Multe":
    tm = st.text_input("Targa").upper()
    if tm:
        rm = supabase.table("contratti").select("*").eq("targa", tm).execute()
        if rm.data:
            c = rm.data[0]
            p_v = FPDF()
            p_v.add_page()
            p_v.set_font("Helvetica", 'B', 14); p_v.cell(0, 10, "MODULO VIGILI", ln=1, align='C')
            p_v.set_font("Helvetica", size=11); p_v.ln(10)
            p_v.multi_cell(0, 8, clean_t(f"Veicolo {c['targa']} affidato a {c['cliente']}."))
            st.download_button("🚨 VIGILI", p_v.output(dest='S').encode('latin-1'), f"V_{c['id']}.pdf", key=f"v_{c['id']}")
