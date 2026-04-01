import streamlit as st
import datetime
from fpdf import FPDF  # fpdf2 usa lo stesso import ma è più potente
from supabase import create_client
import time

# CONNESSIONE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def clean_t(t):
    if not t or t == "None": return "---"
    r = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro'}
    for k, v in r.items(): t = str(t).replace(k, v)
    return t.encode('latin-1', 'ignore').decode('latin-1')

st.set_page_config(page_title="MasterRent V35", layout="wide")

menu = st.sidebar.radio("Menu", ["Nuovo", "Archivio", "Multe"])

if menu == "Nuovo":
    with st.form("f_v35"):
        n = st.text_input("Nome Cliente")
        t = st.text_input("Targa").upper()
        p = st.number_input("Prezzo", min_value=0.0)
        cf = st.text_input("C.F.")
        if st.form_submit_button("SALVA"):
            d = {"cliente": n, "targa": t, "prezzo": p, "cf": cf, "data_inizio": str(datetime.date.today())}
            supabase.table("contratti").insert(d).execute()
            st.success("Salvato!")

elif menu == "Archivio":
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"{c['cliente']} - {c['targa']}"):
            col1, col2 = st.columns(2)
            
            # --- 1. Genera bytes CONTRATTO ---
            pdf_c = FPDF()
            pdf_c.add_page()
            pdf_c.set_font("Arial", 'B', 16)
            pdf_c.cell(0, 10, "CONTRATTO DI NOLEGGIO", ln=True, align='C')
            pdf_c.set_font("Arial", size=11); pdf_c.ln(10)
            pdf_c.multi_cell(0, 8, clean_t(f"CLIENTE: {c['cliente']}\nTARGA: {c['targa']}\nCF: {c['cf']}"))
            bytes_contratto = pdf_c.output() # Con fpdf2 output() restituisce già i bytes
            
            col1.download_button(
                label="📜 SCARICA CONTRATTO",
                data=bytes_contratto,
                file_name=f"Contr_{c['id']}.pdf",
                mime="application/pdf",
                key=f"btn_c_{c['id']}" # Key stabile
            )

            # --- 2. Genera bytes RICEVUTA ---
            pdf_r = FPDF()
            pdf_r.add_page()
            pdf_r.set_font("Arial", 'B', 16)
            pdf_r.cell(0, 10, "RICEVUTA DI PAGAMENTO", ln=True, align='C')
            pdf_r.set_font("Arial", size=14); pdf_r.ln(15)
            pdf_r.cell(0, 10, clean_t(f"Ricevuto da: {c['cliente']}"), ln=True)
            pdf_r.set_font("Arial", 'B', 20); pdf_r.ln(10)
            pdf_r.cell(0, 20, clean_t(f"TOTALE: {c['prezzo']} Euro"), border=1, align='C')
            bytes_ricevuta = pdf_r.output()
            
            col2.download_button(
                label="💰 SCARICA RICEVUTA",
                data=bytes_ricevuta,
                file_name=f"Ricev_{c['id']}.pdf",
                mime="application/pdf",
                key=f"btn_r_{c['id']}" # Key stabile
            )

elif menu == "Multe":
    t_m = st.text_input("Targa").upper()
    if t_m:
        rm = supabase.table("contratti").select("*").eq("targa", t_m).execute()
        if rm.data:
            c = rm.data[0]
            pdf_v = FPDF()
            pdf_v.add_page()
            pdf_v.set_font("Arial", 'B', 14); pdf_v.cell(0, 10, "MODULO VIGILI", ln=True, align='C')
            pdf_v.set_font("Arial", size=11); pdf_v.ln(10)
            pdf_v.multi_cell(0, 8, clean_t(f"Il veicolo {c['targa']} era condotto da {c['cliente']}."))
            st.download_button("🚨 SCARICA VIGILI", pdf_v.output(), f"V_{c['id']}.pdf", key=f"v_{c['id']}")
