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
PRIVACY_TESTO = "INFORMATIVA PRIVACY: I dati personali sono trattati ai sensi del Regolamento UE 2016/679 (GDPR)."
CLAUSOLE_TESTO = "APPROVAZIONE CLAUSOLE: Ai sensi degli artt. 1341 e 1342 c.c. il Cliente approva le clausole: Art. 3 (Multe), Art. 4 (Spese), Art. 5 (Danni)."

def genera_pdf_contratto(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 10); pdf.multi_cell(0, 5, txt=clean_t(INFO_MARIANNA))
    pdf.ln(8); pdf.set_font("Arial", 'B', 16); pdf.cell(0, 10, clean_t("CONTRATTO DI NOLEGGIO"), ln=1, align='C')
    pdf.ln(5); pdf.set_font("Arial", size=11)
    testo = (
        f"Cliente: {c['cliente']}\nCF: {c.get('cf','')}\nNato a: {c.get('luogo_nascita','')}\n"
        f"Residenza: {c.get('residenza','')}\nPatente: {c.get('num_doc','')}\n\n"
        f"TARGA: {c['targa']}\nDATA: {c.get('data_inizio','')}\nPREZZO: {c.get('prezzo', 0)} Euro"
    )
    pdf.multi_cell(0, 7, txt=clean_t(testo))
    pdf.ln(10); pdf.set_font("Arial", 'B', 9); pdf.cell(0, 5, clean_t("NOTE LEGALI E PRIVACY"), ln=1)
    pdf.set_font("Arial", size=8); pdf.multi_cell(0, 4, txt=clean_t(f"{PRIVACY_TESTO}\n\n{CLAUSOLE_TESTO}"))
    pdf.ln(20); pdf.cell(0, 10, clean_t("Firma del Cliente: ________________________"), ln=1)
    return pdf.output(dest='S').encode('latin-1')

def genera_pdf_multe(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10); pdf.multi_cell(0, 5, txt=clean_t(INFO_MARIANNA))
    pdf.ln(10); pdf.set_font("Arial", 'B', 12); pdf.cell(0, 7, clean_t("COMUNICAZIONE LOCAZIONE VEICOLO"), ln=1, align='C')
    pdf.ln(10); pdf.set_font("Arial", size=11)
    testo_m = f"Veicolo: {c['targa']}\nIn data {c.get('data_inizio','')} era in uso a:\n\nNOME: {c['cliente']}\nCF: {c.get('cf','')}\nNATO A: {c.get('luogo_nascita','')}\nPATENTE: {c.get('num_doc','')}"
    pdf.multi_cell(0, 7, txt=clean_t(testo_m))
    pdf.ln(20); pdf.cell(0, 10, "In fede, Marianna Battaglia", align='R')
    return pdf.output(dest='S').encode('latin-1')

st.sidebar.title("🚀 MasterRent Ischia")
menu = st.sidebar.radio("Menu", ["📝 Nuovo Noleggio", "🗄️ Archivio"])

if menu == "📝 Nuovo Noleggio":
    st.header("Registrazione")
    c1, c2 = st.columns(2)
    cliente = c1.text_input("Nome e Cognome")
    cf = c2.text_input("Codice Fiscale")
    nascita = c1.text_input("Luogo/Data Nascita")
    residenza = c2.text_input("Residenza")
    num_doc = c1.text_input("Num. Patente")
    tel = c2.text_input("Telefono")
    targa = c1.text_input("TARGA").upper()
    prezzo = c2.number_input("Prezzo (€)", min_value=0.0)
    
    st.camera_input("📸 Foto Patente")
    st_canvas(fill_color="white", stroke_width=2, height=150, key="sig_v_fix")

    if st.button("💾 SALVA"):
        if cliente and targa:
            try:
                # Salviamo solo le colonne sicure per evitare l'errore PGRST204
                dat = {
                    "cliente": cliente, "cf": cf, "luogo_nascita": nascita, 
                    "residenza": residenza, "num_doc": num_doc, 
                    "telefono": tel, "targa": targa, "prezzo": prezzo,
                    "data_inizio": str(datetime.date.today())
                }
                supabase.table("contratti").insert(dat).execute()
                st.success("✅ Salvato! Vai in Archivio.")
            except Exception as e:
                st.error(f"Errore: {e}")
        else:
            st.warning("Mancano dati!")

elif menu == "🗄️ Archivio":
    st.header("🔎 Ricerca per Targa")
    t_search = st.text_input("SCRIVI TARGA").upper()
    if t_search:
        res = supabase.table("contratti").select("*").eq("targa", t_search).execute()
        if res.data:
            for c in res.data:
                with st.expander(f"📂 {c['cliente']} ({c.get('data_inizio','')})"):
                    pdf_c = genera_pdf_contratto(c)
                    pdf_m = genera_pdf_multe(c)
                    col1, col2 = st.columns(2)
                    col1.download_button("📄 Contratto", pdf_c, f"Contratto_{c['targa']}.pdf", key=f"c_{c['id']}")
                    col2.download_button("🚨 Modulo Multe", pdf_m, f"Multe_{c['targa']}.pdf", key=f"m_{c['id']}")
                    st.link_button("📲 WhatsApp", f"https://wa.me/{c.get('telefono','')}?text=Contratto")
        else: st.warning("Nulla trovato.")
