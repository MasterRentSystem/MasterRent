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
    if not text or text == "None": return "DATO MANCANTE"
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in repls.items(): text = str(text).replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

INTESTAZIONE = "MASTERRENT DI MARIANNA BATTAGLIA\nVia Cognole n. 5 - 80075 Forio (NA)\nC.F.: BTTMNN87A53Z112S | P.IVA: 10252601215"

def genera_pdf_stiloso(c, tipo="CONTRATTO"):
    pdf = fpdf.FPDF()
    pdf.add_page()
    
    # BOX INTESTAZIONE
    pdf.set_font("Arial", 'B', 11)
    pdf.set_fill_color(230, 230, 230)
    pdf.multi_cell(0, 6, txt=clean_t(INTESTAZIONE), border=1, align='L', fill=True)
    pdf.ln(10)
    
    # TITOLO
    pdf.set_font("Arial", 'B', 18)
    titolo = "CONTRATTO DI NOLEGGIO" if tipo == "CONTRATTO" else "RICEVUTA FISCALE"
    pdf.cell(0, 10, clean_t(titolo), ln=1, align='C')
    pdf.ln(5)
    
    # TABELLA DATI CLIENTE
    pdf.set_font("Arial", 'B', 10); pdf.cell(0, 7, "DATI CONDUCENTE", ln=1)
    pdf.set_font("Arial", size=10)
    pdf.cell(95, 8, clean_t(f"NOME: {c.get('cliente')}"), border=1)
    pdf.cell(95, 8, clean_t(f"C.F.: {c.get('cf')}"), border=1, ln=1)
    pdf.cell(190, 8, clean_t(f"NATO A: {c.get('luogo_nascita')}"), border=1, ln=1)
    pdf.cell(190, 8, clean_t(f"RESIDENZA: {c.get('residenza')}"), border=1, ln=1)
    pdf.cell(95, 8, clean_t(f"PATENTE: {c.get('num_doc')}"), border=1)
    pdf.cell(95, 8, clean_t(f"SCADENZA: {c.get('scadenza_patente')}"), border=1, ln=1)
    pdf.ln(5)
    
    # TABELLA VEICOLO
    pdf.set_font("Arial", 'B', 10); pdf.cell(0, 7, "DETTAGLI VEICOLO", ln=1)
    pdf.set_font("Arial", size=10)
    pdf.cell(60, 8, clean_t(f"TARGA: {c.get('targa')}"), border=1)
    pdf.cell(65, 8, clean_t(f"DAL: {c.get('data_inizio')}"), border=1)
    pdf.cell(65, 8, clean_t(f"AL: {c.get('data_fine')}"), border=1, ln=1)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, clean_t(f"TOTALE PAGATO: {c.get('prezzo', 0)} EURO"), border=1, ln=1, align='C', fill=True)
    
    if tipo == "CONTRATTO":
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 8); pdf.cell(0, 5, "INFORMATIVA LEGALE E PRIVACY", ln=1)
        pdf.set_font("Arial", size=7)
        privacy = ("Il cliente autorizza la copia fotografica del documento per fini di Pubblica Sicurezza (Reg. UE 2016/679). "
                   "Si assume responsabilita per multe, danni e furto. Accetta gli artt. 1341-1342 c.c.")
        pdf.multi_cell(0, 4, txt=clean_t(privacy), border='T')
        
        pdf.ln(15)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 5, "Firma del Cliente per accettazione", ln=1, align='R')
        pdf.ln(10)
        pdf.cell(0, 0, "______________________________", ln=1, align='R')
        pdf.set_font("Arial", 'I', 7)
        pdf.cell(0, 10, "Firma acquisita digitalmente", ln=1, align='R')

    return pdf.output(dest='S').encode('latin-1')

# --- APP ---
st.sidebar.title("🚀 MasterRent")
menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Noleggio", "🗄️ Archivio"])

if menu == "📝 Nuovo Noleggio":
    st.header("Compilazione Nuovo Contratto")
    with st.form("form_noleggio"):
        col1, col2 = st.columns(2)
        cliente = col1.text_input("Nome e Cognome")
        cf = col2.text_input("Codice Fiscale")
        nascita = col1.text_input("Luogo e Data Nascita")
        residenza = col2.text_input("Indirizzo Residenza")
        num_doc = col1.text_input("Numero Patente")
        scadenza = col2.date_input("Scadenza Patente")
        targa = col1.text_input("TARGA").upper()
        prezzo = col2.number_input("Prezzo (€)", min_value=0.0)
        d_ini = col1.date_input("Inizio", datetime.date.today())
        d_fin = col2.date_input("Fine", datetime.date.today() + datetime.timedelta(days=1))
        
        st.write("✍️ *Firma Cliente*")
        canvas = st_canvas(fill_color="white", stroke_width=2, height=120, key="firma_v4")
        
        invia = st.form_submit_button("💾 SALVA E ARCHIVIA")
        if invia and cliente and targa:
            dat = {"cliente": cliente, "cf": cf, "luogo_nascita": nascita, "residenza": residenza, 
                   "num_doc": num_doc, "scadenza_patente": str(scadenza), "targa": targa, 
                   "prezzo": prezzo, "data_inizio": str(d_ini), "data_fine": str(d_fin)}
            supabase.table("contratti").insert(dat).execute()
            st.success("REGISTRATO! Vai in Archivio.")

elif menu == "🗄️ Archivio":
    st.header("Documenti Archiviati")
    res = supabase.table("contratti").select("*").order("data_inizio", desc=True).execute()
    if res.data:
        for c in res.data:
            with st.expander(f"📂 {c['cliente']} - {c['targa']} ({c['data_inizio']})"):
                c1, c2 = st.columns(2)
                # Timestamp per evitare cache
                ts = int(time.time())
                c1.download_button("📜 SCARICA CONTRATTO", genera_pdf_stiloso(c, "CONTRATTO"), f"Contratto_{c['targa']}{ts}.pdf", key=f"c{c['id']}_{ts}")
                c2.download_button("💰 SCARICA RICEVUTA", genera_pdf_stiloso(c, "FATTURA"), f"Ricevuta_{c['id']}{ts}.pdf", key=f"f{c['id']}_{ts}")
