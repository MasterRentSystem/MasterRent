import streamlit as st
import datetime
from fpdf import FPDF
from supabase import create_client
import time

# CONNESSIONE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def clean_t(t):
    if not t or t == "None": return "---"
    r = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'"}
    for k, v in r.items(): t = str(t).replace(k, v)
    return t.encode('latin-1', 'ignore').decode('latin-1')

st.set_page_config(page_title="MasterRent V42", layout="wide")

menu = st.sidebar.radio("Menu", ["📝 Nuovo Noleggio", "🗄️ Archivio"])

if menu == "📝 Nuovo Noleggio":
    st.subheader("Registrazione Nuovo Noleggio")
    with st.form("f_v42"):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome Cliente")
        cf = c2.text_input("Codice Fiscale")
        nascita = c1.text_input("Luogo/Data Nascita")
        residenza = c2.text_input("Residenza")
        patente = c1.text_input("Num. Patente")
        telefono = c2.text_input("Telefono")
        targa = c1.text_input("Targa").upper()
        prezzo = c2.number_input("Prezzo (€)", min_value=0.0)
        accetto = st.checkbox("Accetto Condizioni e Privacy")
        foto = st.camera_input("Scansiona Patente")
        
        if st.form_submit_button("💾 SALVA"):
            if accetto and nome and targa:
                dat = {"cliente": nome, "cf": cf, "luogo_nascita": nascita, "residenza": residenza, "num_doc": patente, "telefono": telefono, "targa": targa, "prezzo": prezzo, "data_inizio": str(datetime.date.today())}
                supabase.table("contratti").insert(dat).execute()
                st.success("Salvato!")

elif menu == "🗄️ Archivio":
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"📄 {c['cliente']} - {c['targa']}"):
            col1, col2 = st.columns(2)
            
            # PDF CONTRATTO
            pdf_c = FPDF()
            pdf_c.add_page()
            pdf_c.set_font("Helvetica", 'B', 16)
            pdf_c.cell(0, 10, "CONTRATTO DI NOLEGGIO", ln=1, align='C')
            pdf_c.set_font("Helvetica", size=10); pdf_c.ln(10)
            info = f"CLIENTE: {c['cliente']}\nCF: {c['cf']}\nTARGA: {c['targa']}\nNATO A: {c.get('luogo_nascita','---')}"
            pdf_c.multi_cell(0, 7, clean_t(info), border=1)
            # IL SEGRETO: Usiamo output(dest='S') codificato per evitare scambi
            col1.download_button("📜 CONTRATTO", pdf_c.output(dest='S').encode('latin-1'), f"C_{c['id']}.pdf", "application/pdf", key=f"c_{c['id']}")

            # PDF RICEVUTA
            pdf_r = FPDF()
            pdf_r.add_page()
            pdf_r.set_font("Helvetica", 'B', 16)
            pdf_r.cell(0, 10, "RICEVUTA DI PAGAMENTO", ln=1, align='C')
            pdf_r.set_font("Helvetica", size=12); pdf_r.ln(20)
            pdf_r.cell(0, 10, clean_t(f"Ricevuto da: {c['cliente']}"), ln=1)
            pdf_r.cell(0, 20, clean_t(f"TOTALE: {c['prezzo']} Euro"), border=1, align='C')
            col2.download_button("💰 RICEVUTA", pdf_r.output(dest='S').encode('latin-1'), f"R_{c['id']}.pdf", "application/pdf", key=f"r_{c['id']}")
