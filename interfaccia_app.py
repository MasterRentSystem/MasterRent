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

INFO_MARIANNA = "BATTAGLIA MARIANNA\nNata a Berlino (Germania) il 13/01/1987\nResidente in Forio alla Via Cognole n. 5\nC.F.: BTTMNN87A53Z112S | P.IVA: 10252601215"
PRIVACY_TESTO = "INFORMATIVA PRIVACY: I dati personali sono trattati ai sensi del Regolamento UE 2016/679 (GDPR) per la gestione del contratto e obblighi di legge."
CLAUSOLE_TESTO = "APPROVAZIONE CLAUSOLE: Ai sensi degli artt. 1341 e 1342 c.c. il Cliente approva le clausole: Art. 3 (Multe), Art. 4 (Spese), Art. 5 (Danni), Art. 13 (Foro)."

def genera_pdf_contratto(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 10); pdf.multi_cell(0, 5, txt=clean_t(INFO_MARIANNA))
    pdf.ln(8); pdf.set_font("Arial", 'B', 16); pdf.cell(0, 10, clean_t("CONTRATTO DI NOLEGGIO"), ln=1, align='C')
    pdf.ln(5); pdf.set_font("Arial", size=11)
    
    testo = (
        f"Conducente: {c['cliente']}\nCF: {c.get('cf','')}\n"
        f"Nato a: {c.get('luogo_nascita','')}\nResidenza: {c.get('residenza','')}\n"
        f"Documento: {c.get('num_doc','')}\n\n"
        f"VEICOLO TARGA: {c['targa']}\n"
        f"DATA INIZIO: {c.get('data_inizio','')}\n"
        f"DATA FINE: {c.get('data_fine','')}\n"
        f"PREZZO: {c.get('prezzo', 0)} Euro"
    )
    pdf.multi_cell(0, 7, txt=clean_t(testo))
    pdf.ln(10); pdf.set_font("Arial", 'B', 9); pdf.cell(0, 5, clean_t("NOTE LEGALI E PRIVACY"), ln=1)
    pdf.set_font("Arial", size=8); pdf.multi_cell(0, 4, txt=clean_t(f"{PRIVACY_TESTO}\n\n{CLAUSOLE_TESTO}"))
    pdf.ln(20); pdf.cell(0, 10, clean_t("Firma del Cliente: ________________________"), ln=1)
    return pdf.output(dest='S').encode('latin-1')

st.sidebar.title("🚀 MasterRent Ischia")
menu = st.sidebar.radio("Menu", ["📝 Nuovo Noleggio", "🗄️ Archivio"])

if menu == "📝 Nuovo Noleggio":
    st.header("Nuovo Noleggio")
    col1, col2 = st.columns(2)
    cliente = col1.text_input("Nome e Cognome")
    cf = col2.text_input("Codice Fiscale")
    nascita = col1.text_input("Luogo/Data Nascita")
    residenza = col2.text_input("Indirizzo Residenza")
    num_doc = col1.text_input("Numero Patente")
    tel = col2.text_input("Telefono")
    
    st.divider()
    targa = col1.text_input("TARGA").upper()
    prezzo = col2.number_input("Prezzo (€)", min_value=0.0)
    
    # AGGIUNTI CAMPI DATA
    d_inizio = col1.date_input("Data Inizio", datetime.date.today())
    d_fine = col2.date_input("Data Fine", datetime.date.today() + datetime.timedelta(days=1))

    st.camera_input("📸 Foto Patente")
    st_canvas(fill_color="white", stroke_width=2, height=150, key="sig_v_final_dates")

    if st.button("💾 SALVA NOLEGGIO"):
        if cliente and targa:
            try:
                dat = {
                    "cliente": cliente, "cf": cf, "luogo_nascita": nascita, 
                    "residenza": residenza, "num_doc": num_doc, "telefono": tel, 
                    "targa": targa, "prezzo": prezzo,
                    "data_inizio": str(d_inizio), "data_fine": str(d_fine)
                }
                supabase.table("contratti").insert(dat).execute()
                st.success(f"Noleggio salvato! Dal {d_inizio} al {d_fine}")
            except Exception as e:
                st.error(f"Errore: {e}. Controlla se le colonne data_inizio e data_fine esistono su Supabase.")
        else:
            st.warning("Nome e Targa obbligatori!")

elif menu == "🗄️ Archivio":
    st.header("🔎 Archivio")
    t_search = st.text_input("CERCA TARGA").upper()
    if t_search:
        res = supabase.table("contratti").select("*").eq("targa", t_search).execute()
        if res.data:
            for c in res.data:
                with st.expander(f"📂 {c['cliente']} (Dal {c.get('data_inizio','?')})"):
                    pdf_c = genera_pdf_contratto(c)
                    st.download_button("📄 Scarica Contratto Completo", pdf_c, f"Contratto_{c['targa']}.pdf", key=f"dl_{c['id']}")
                    st.link_button("📲 WhatsApp", f"https://wa.me/{c.get('telefono','')}?text=Contratto")
        else:
            st.warning("Nessun noleggio trovato.")
