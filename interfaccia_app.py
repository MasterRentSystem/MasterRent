import streamlit as st
import datetime
import fpdf
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
import time

# 1. CONNESSIONE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def clean_t(text):
    if not text or text == "None": return "---"
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in repls.items(): text = str(text).replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

INTESTAZIONE = "MASTERRENT DI MARIANNA BATTAGLIA\nVia Cognole n. 5 - 80075 Forio (NA)\nC.F.: BTTMNN87A53Z112S | P.IVA: 10252601215"

def genera_pdf_stiloso(c, tipo="CONTRATTO"):
    pdf = fpdf.FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 11)
    pdf.set_fill_color(230, 230, 230)
    pdf.multi_cell(0, 6, txt=clean_t(INTESTAZIONE), border=1, align='L', fill=True)
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 16)
    titolo = "CONTRATTO DI NOLEGGIO" if tipo == "CONTRATTO" else "RICEVUTA FISCALE"
    pdf.cell(0, 10, clean_t(titolo), ln=1, align='C')
    pdf.ln(5)
    
    # TABELLA DATI
    pdf.set_font("Arial", 'B', 10); pdf.cell(0, 7, "DATI CONDUCENTE", ln=1)
    pdf.set_font("Arial", size=10)
    pdf.cell(95, 8, clean_t(f"NOME: {c.get('cliente')}"), border=1)
    pdf.cell(95, 8, clean_t(f"C.F.: {c.get('cf')}"), border=1, ln=1)
    pdf.cell(190, 8, clean_t(f"NATO A: {c.get('luogo_nascita')}"), border=1, ln=1)
    pdf.cell(190, 8, clean_t(f"RESIDENZA: {c.get('residenza')}"), border=1, ln=1)
    pdf.cell(95, 8, clean_t(f"PATENTE: {c.get('num_doc')}"), border=1)
    pdf.cell(95, 8, clean_t(f"SCADENZA: {c.get('scadenza_patente')}"), border=1, ln=1)
    pdf.ln(5)
    pdf.cell(60, 8, clean_t(f"TARGA: {c.get('targa')}"), border=1)
    pdf.cell(65, 8, clean_t(f"DAL: {c.get('data_inizio')}"), border=1)
    pdf.cell(65, 8, clean_t(f"AL: {c.get('data_fine')}"), border=1, ln=1)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, clean_t(f"TOTALE: {c.get('prezzo', 0)} EURO"), border=1, ln=1, align='C', fill=True)
    
    if tipo == "CONTRATTO":
        pdf.ln(5); pdf.set_font("Arial", 'B', 8); pdf.cell(0, 5, "PRIVACY E CLAUSOLE", ln=1)
        pdf.set_font("Arial", size=7.5)
        pdf.multi_cell(0, 4, txt=clean_t("Autorizzo la foto del documento per Pubblica Sicurezza (GDPR). Accetto la responsabilita per multe e danni."), border='T')
        pdf.ln(10); pdf.set_font("Arial", 'B', 10); pdf.cell(0, 5, "Firma del Cliente (Digitale)", ln=1, align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- APP ---
st.sidebar.title("🚀 MasterRent")
menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Noleggio", "🗄️ Archivio"])

if menu == "📝 Nuovo Noleggio":
    st.header("Nuovo Noleggio")
    with st.form("form_v5", clear_on_submit=True):
        c1, c2 = st.columns(2)
        cliente = c1.text_input("Nome e Cognome")
        cf = c2.text_input("Codice Fiscale")
        nascita = c1.text_input("Luogo/Data Nascita")
        residenza = c2.text_input("Indirizzo Residenza")
        num_doc = c1.text_input("Numero Patente")
        scadenza = c2.date_input("Scadenza Patente")
        targa = c1.text_input("TARGA").upper()
        prezzo = c2.number_input("Prezzo (€)", min_value=0.0)
        d_ini = c1.date_input("Inizio", datetime.date.today())
        d_fin = c2.date_input("Fine", datetime.date.today() + datetime.timedelta(days=1))
        
        foto = st.camera_input("📸 Scatta Foto Patente")
        st.write("✍️ *Firma*")
        canvas = st_canvas(fill_color="white", stroke_width=2, height=120, key="firma_v5")
        
        invia = st.form_submit_button("💾 SALVA TUTTO")
        if invia and cliente and targa:
            file_path = None
            if foto:
                # Caricamento foto nello Storage
                file_name = f"patente_{targa}_{int(time.time())}.jpg"
                supabase.storage.from_("patenti").upload(file_name, foto.getvalue())
                file_path = file_name
            
            dat = {"cliente": cliente, "cf": cf, "luogo_nascita": nascita, "residenza": residenza, 
                   "num_doc": num_doc, "scadenza_patente": str(scadenza), "targa": targa, 
                   "prezzo": prezzo, "data_inizio": str(d_ini), "data_fine": str(d_fin), "foto_path": file_path}
            supabase.table("contratti").insert(dat).execute()
            st.success("ARCHIVIATO!")

elif menu == "🗄️ Archivio":
    st.header("Documenti")
    res = supabase.table("contratti").select("*").order("data_inizio", desc=True).execute()
    if res.data:
        col_h = st.columns([2, 1, 1, 1])
        col_h[0].write("*CLIENTE"); col_h[1].write("CONTRATTO"); col_h[2].write("RICEVUTA"); col_h[3].write("FOTO*")
        
        for c in res.data:
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            c1.write(f"*{c['cliente']}*\n{c['targa']}")
            ts = int(time.time())
            c2.download_button("📜 PDF", genera_pdf_stiloso(c, "CONTRATTO"), f"Contratto_{c['id']}{ts}.pdf", key=f"c{c['id']}")
            c3.download_button("💰 PDF", genera_pdf_stiloso(c, "FATTURA"), f"Fattura_{c['id']}.pdf", key=f"f_{c['id']}")
            
            if c.get("foto_path"):
                url_foto = supabase.storage.from_("patenti").get_public_url(c["foto_path"])
                c4.link_button("📸 VEDI", url_foto)
            else:
                c4.write("❌ No")
