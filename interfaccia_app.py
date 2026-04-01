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

st.set_page_config(page_title="MasterRent V40", layout="wide")

menu = st.sidebar.radio("Menu", ["📝 Nuovo Noleggio", "🗄️ Archivio", "🚨 Multe"])

if menu == "📝 Nuovo Noleggio":
    st.subheader("Registrazione Nuovo Noleggio")
    with st.form("form_v40"):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Cognome e Nome")
        cf = c2.text_input("Codice Fiscale")
        nascita = c1.text_input("Luogo e Data di Nascita")
        residenza = c2.text_input("Indirizzo Residenza")
        patente = c1.text_input("Numero Patente")
        telefono = c2.text_input("Telefono")
        
        st.write("---")
        targa = c1.text_input("TARGA VEICOLO").upper()
        prezzo = c2.number_input("Prezzo Totale (€)", min_value=0.0)
        di = st.date_input("Data Inizio", datetime.date.today())
        df = st.date_input("Data Fine", datetime.date.today() + datetime.timedelta(days=1))
        
        st.write("---")
        # RIPRISTINO PRIVACY
        accetto = st.checkbox("Accetto le Condizioni di Noleggio (1-14) e la Privacy")
        
        # RIPRISTINO FOTOCAMERA
        foto = st.camera_input("📸 Scansiona Patente")
        
        if st.form_submit_button("💾 SALVA NOLEGGIO"):
            if accetto and nome and targa:
                fn = f"{targa}_{int(time.time())}.jpg"
                if foto:
                    supabase.storage.from_(BUCKET_NAME).upload(fn, foto.getvalue())
                
                dat = {
                    "cliente": nome, "cf": cf, "luogo_nascita": nascita, 
                    "residenza": residenza, "num_doc": patente, "telefono": telefono,
                    "targa": targa, "prezzo": prezzo, "data_inizio": str(di), 
                    "data_fine": str(df), "foto_path": fn if foto else None
                }
                supabase.table("contratti").insert(dat).execute()
                st.success(f"Noleggio di {nome} salvato!")
            else:
                st.warning("Devi accettare la privacy e inserire i dati obbligatori!")

elif menu == "🗄️ Archivio":
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"📄 {c['cliente']} - {c['targa']}"):
            col1, col2 = st.columns(2)
            
            # PDF CONTRATTO (Metodo stabile)
            pdf_c = FPDF()
            pdf_c.add_page()
            pdf_c.set_font("Helvetica", 'B', 16)
            pdf_c.cell(0, 10, "CONTRATTO DI NOLEGGIO", ln=1, align='C')
            pdf_c.set_font("Helvetica", size=10); pdf_c.ln(10)
            info = f"CLIENTE: {c['cliente']}\nNATO A: {c.get('luogo_nascita','---')}\nRESIDENTE: {c.get('residenza','---')}\nCF: {c['cf']}\nPATENTE: {c.get('num_doc','---')}\nTEL: {c.get('telefono','---')}\nVEICOLO: {c['targa']}\nDAL: {c['data_inizio']} AL: {c['data_fine']}"
            pdf_c.multi_cell(0, 7, clean_t(info), border=1)
            
            col1.download_button("📜 SCARICA CONTRATTO", pdf_c.output(), f"C_{c['id']}.pdf", "application/pdf", key=f"c_{c['id']}")

            # PDF RICEVUTA
            pdf_r = FPDF()
            pdf_r.add_page()
            pdf_r.set_font("Helvetica", 'B', 16); pdf_r.cell(0, 10, "RICEVUTA DI PAGAMENTO", ln=1, align='C')
            pdf_r.set_font("Helvetica", size=12); pdf_r.ln(20)
            pdf_r.cell(0, 10, clean_t(f"Ricevuto da: {c['cliente']}"), ln=1)
            pdf_r.ln(10); pdf_r.set_font("Helvetica", 'B', 20)
            pdf_r.cell(0, 20, clean_t(f"TOTALE: {c['prezzo']} Euro"), border=1, align='C')
            
            col2.download_button("💰 RICEVUTA", pdf_r.output(), f"R_{c['id']}.pdf", "application/pdf", key=f"r_{c['id']}")

elif menu == "🚨 Multe":
    t_m = st.text_input("Targa").upper()
    if t_m:
        rm = supabase.table("contratti").select("*").eq("targa", t_m).execute()
        if rm.data:
            c = rm.data[0]
            pdf_v = FPDF()
            pdf_v.add_page()
            pdf_v.set_font("Helvetica", 'B', 14); pdf_v.cell(0, 10, "MODULO VIGILI", ln=1, align='C')
            pdf_v.multi_cell(0, 8, clean_t(f"Veicolo {c['targa']} affidato a {c['cliente']}."))
            st.download_button("🚨 VIGILI", pdf_v.output(), f"V_{c['id']}.pdf", key=f"v_{c['id']}")
