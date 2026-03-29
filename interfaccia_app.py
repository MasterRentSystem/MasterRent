import streamlit as st
import pandas as pd
import datetime
import fpdf
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io
import urllib.parse

# 1. CONNESSIONE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def clean_t(text):
    if not text: return ""
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in repls.items(): text = text.replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

# DATI FISSI MARIANNA (Per Intestazione Contratto e Modulo Multe)
INFO_MARIANNA = "BATTAGLIA MARIANNA\nNata a Berlino (Germania) il 13/01/1987\nResidente in Forio alla Via Cognole n. 5\nC.F.: BTTMNN87A53Z112S | P.IVA: 10252601215"

# TESTI LEGALI COMPLETI
PRIVACY_TESTO = "INFORMATIVA PRIVACY: I dati personali forniti saranno trattati ai sensi del Regolamento UE 2016/679 (GDPR) esclusivamente per le finalita connesse alla gestione del presente contratto di noleggio e per gli adempimenti di legge. Il cliente dichiara di aver ricevuto l'informativa e presta il consenso al trattamento dei dati."
CLAUSOLE_TESTO = "APPROVAZIONE CLAUSOLE: Ai sensi degli artt. 1341 e 1342 c.c. il Cliente dichiara di aver letto e di approvare specificamente le seguenti clausole: Art. 3 (Responsabilita per infrazioni e multe), Art. 4 (Spese di gestione verbali), Art. 5 (Penali per danni o furto), Art. 13 (Foro competente)."

def genera_pdf_contratto(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    
    # Intestazione Azienda
    pdf.set_font("Arial", 'B', 10)
    pdf.multi_cell(0, 5, txt=clean_t(INFO_MARIANNA))
    pdf.ln(10)
    
    # Titolo
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, clean_t("CONTRATTO DI NOLEGGIO"), ln=1, align='C')
    pdf.ln(5)
    
    # Dati Noleggio
    pdf.set_font("Arial", size=11)
    testo_dati = (
        f"Conducente: {c['cliente']}\n"
        f"Codice Fiscale: {c.get('cf','')}\n"
        f"Nato a: {c.get('luogo_nascita','')}\n"
        f"Residenza: {c.get('residenza','')}\n"
        f"Patente: {c.get('num_doc','')}\n\n"
        f"VEICOLO TARGA: {c['targa']}\n"
        f"DATA INIZIO: {c['data_inizio']}\n"
        f"PREZZO: {c.get('prezzo', 0)} Euro"
    )
    pdf.multi_cell(0, 7, txt=clean_t(testo_dati))
    pdf.ln(10)
    
    # Privacy e Clausole
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(0, 5, clean_t("NOTE LEGALI E PRIVACY"), ln=1)
    pdf.set_font("Arial", size=8)
    pdf.multi_cell(0, 4, txt=clean_t(f"{PRIVACY_TESTO}\n\n{CLAUSOLE_TESTO}"))
    
    # Spazio Firma
    pdf.ln(15)
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 10, clean_t("Firma del Cliente per accettazione: ________________________"), ln=1)
    
    return pdf.output(dest='S').encode('latin-1')

def genera_pdf_multe(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 5, txt=clean_t(INFO_MARIANNA))
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 7, clean_t("COMUNICAZIONE LOCAZIONE VEICOLO"), ln=1, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", size=11)
    testo_multe = (
        f"In riferimento al verbale di accertamento infrazione al Codice della Strada,\n"
        f"la sottoscritta dichiara che il veicolo targato {c['targa']}\n"
        f"in data {c['data_inizio']} era concesso in locazione al signor:\n\n"
        f"COGNOME E NOME: {c['cliente']}\n"
        f"CF: {c['cf']}\n"
        f"NATO A: {c.get('luogo_nascita','')}\n"
        f"RESIDENZA: {c.get('residenza','')}\n"
        f"IDENTIFICATO A MEZZO DOC: {c.get('num_doc','')}"
    )
    pdf.multi_cell(0, 7, txt=clean_t(testo_multe))
    pdf.ln(15)
    pdf.cell(0, 10, clean_t("In fede, Marianna Battaglia"), align='R')
    return pdf.output(dest='S').encode('latin-1')

st.sidebar.title("🚀 MasterRent Ischia")
menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Noleggio", "🗄️ Archivio"])

if menu == "📝 Nuovo Noleggio":
    st.header("Nuovo Noleggio")
    c1, c2 = st.columns(2)
    cliente = c1.text_input("Nome e Cognome")
    cf_cliente = c2.text_input("Codice Fiscale")
    nascita = c1.text_input("Luogo/Data Nascita")
    residenza = c2.text_input("Indirizzo Residenza")
    num_doc = c1.text_input("Numero Patente")
    telefono = c2.text_input("Cellulare")
    targa = c1.text_input("TARGA").upper()
    prezzo = c2.number_input("Prezzo (€)", min_value=0)

    # BLOCCO FATTURA RIMOSSO DEFINITIVAMENTE

    st.camera_input("📸 Foto Patente")
    st.write("✍️ Firma per accettazione clausole e privacy")
    st_canvas(fill_color="white", stroke_width=2, height=150, key="sig_final_ok")

    if st.button("💾 SALVA E ARCHIVIA"):
        if cliente and targa:
            dat = {"cliente": cliente, "cf": cf_cliente, "targa": targa, "data_inizio": str(datetime.date.today()), "telefono": telefono, "luogo_nascita": nascita, "residenza": residenza, "num_doc": num_doc, "prezzo": prezzo}
            supabase.table("contratti").insert(dat).execute()
            st.success("Tutto salvato! Vai in Archivio per i documenti.")
        else:
            st.error("Mancano Nome o Targa!")

elif menu == "🗄️ Archivio":
    st.header("🔎 Archivio Contratti")
    t_search = st.text_input("Inserisci TARGA").upper()
    if t_search:
        res = supabase.table("contratti").select("*").eq("targa", t_search).execute()
        if res.data:
            for c in res.data:
                with st.expander(f"📂 {c['cliente']} ({c['data_inizio']})"):
                    pdf_c = genera_pdf_contratto(c)
                    pdf_m = genera_pdf_multe(c)
                    
                    col1, col2 = st.columns(2)
                    col1.download_button("📄 Scarica Contratto", pdf_c, f"Contratto_{c['targa']}.pdf", key=f"c_{c['id']}")
                    col2.download_button("🚨 Modulo Multe", pdf_m, f"Multe_{c['targa']}.pdf", key=f"m_{c['id']}")
                    
                    msg = urllib.parse.quote(f"Ciao {c['cliente']}, ecco il contratto MasterRent.")
                    st.link_button("📲 Invia WhatsApp", f"https://wa.me/{c['telefono']}?text={msg}")
        else:
            st.warning("Nessun noleggio per questa targa.")

