import streamlit as st
import datetime
import fpdf
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
import time
import urllib.parse

# 1. CONNESSIONE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)
BUCKET_NAME = "DOCUMENTI_PATENTI"

# INTESTAZIONE GIGANTE
DITTA_NOME = "BATTAGLIA MARIANNA"
DITTA_INFO = "Via Cognole, 5 - 80075 Forio (NA)\nCod. Fisc. BTTMNN87A53Z112S - P. IVA 10252601215"

def clean_t(text):
    if not text or text == "None": return "---"
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in repls.items(): text = str(text).replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

def applica_intestazione(pdf):
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(0, 10, clean_t(DITTA_NOME), ln=1, align='L')
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 5, clean_t(DITTA_INFO), align='L')
    pdf.line(10, 35, 200, 35)
    pdf.ln(15)

# --- FUNZIONE 1: SOLO CONTRATTO ---
def doc_contratto(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    applica_intestazione(pdf)
    pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, "CONTRATTO DI NOLEGGIO", ln=1, align='C'); pdf.ln(5)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 7, clean_t(f"CLIENTE: {c['cliente']}\nC.F.: {c['cf']}\nRESIDENZA: {c['residenza']}\nVEICOLO: {c['targa']}\nPERIODO: dal {c['data_inizio']} ore {c['ora_inizio']} al {c['data_fine']} ore {c['ora_fine']}"), border=1)
    pdf.ln(10); pdf.set_font("Arial", 'B', 9); pdf.cell(0, 5, "CONDIZIONI GENERALI (Art. 1341-1342 c.c.)", ln=1)
    pdf.set_font("Arial", size=7)
    pdf.multi_cell(0, 4, clean_t("1. Mezzo in ottimo stato. 2. Responsabile danni/furto. 3. Multe + 25.83 Euro spese. 4. FURTO A CARICO CLIENTE. 5. Foro Ischia. 6. Casco obbligatorio. 7. Privacy."), border='T')
    pdf.ln(20); pdf.cell(0, 10, "Firma Cliente: ______________________", align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- FUNZIONE 2: SOLO RICEVUTA ---
def doc_ricevuta(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    applica_intestazione(pdf)
    pdf.set_font("Arial", 'B', 16); pdf.cell(0, 10, "RICEVUTA DI PAGAMENTO", ln=1, align='C'); pdf.ln(15)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, clean_t(f"Ricevuti da: {c['cliente']}"), ln=1)
    pdf.cell(0, 10, clean_t(f"Per il noleggio della targa: {c['targa']}"), ln=1)
    pdf.cell(0, 10, clean_t(f"Dal: {c['data_inizio']} al {c['data_fine']}"), ln=1)
    pdf.ln(20); pdf.set_font("Arial", 'B', 20)
    pdf.cell(0, 20, clean_t(f"TOTALE PAGATO: Euro {c['prezzo']}"), border=1, ln=1, align='C')
    return pdf.output(dest='S').encode('latin-1')

# --- FUNZIONE 3: SOLO MODULO VIGILI ---
def doc_vigili(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    applica_intestazione(pdf)
    pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, "DICHIARAZIONE DATI CONDUCENTE (L. 445/2000)", ln=1, align='C'); pdf.ln(10)
    pdf.set_font("Arial", size=11)
    testo = (
        f"La sottoscritta BATTAGLIA MARIANNA, titolare di MasterRent,\n\n"
        f"DICHIARA che il veicolo targa {c['targa']} in data {c['data_inizio']}\n"
        f"era concesso in locazione al Sig.:\n\n"
        f"NOME: {c['cliente']}\nNATO A: {c.get('luogo_nascita', '---')}\n"
        f"RESIDENTE: {c['residenza']}\nC.F.: {c['cf']}\nPATENTE: {c['num_doc']}\n\n"
        f"Si richiede la rinotifica del verbale al soggetto sopra indicato."
    )
    pdf.multi_cell(0, 8, clean_t(testo))
    pdf.ln(25); pdf.cell(0, 10, "Timbro e Firma: ______________________", align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACCIA ---
st.set_page_config(page_title="MasterRent", layout="wide")
menu = st.sidebar.radio("Scegli", ["Nuovo", "Archivio", "Multe"])

if menu == "Nuovo":
    with st.form("form_v19"):
        st.subheader("Dati Cliente")
        col1, col2 = st.columns(2)
        nome = col1.text_input("Cognome Nome")
        cf = col2.text_input("C.F.")
        nascita = col1.text_input("Nascita")
        res = col2.text_input("Residenza")
        pat = col1.text_input("Patente")
        targa = col2.text_input("Targa").upper()
        tel = col1.text_input("Telefono")
        prezzo = col2.number_input("Prezzo", min_value=0.0)
        
        d1, d2, d3, d4 = st.columns(4)
        di = d1.date_input("Data Inizio")
        oi = d2.text_input("Ora Inizio", "10:00")
        df = d3.date_input("Data Fine")
        of = d4.text_input("Ora Fine", "10:00")
        
        accetto = st.checkbox("Accetto clausole 1-14")
        if st.form_submit_button("SALVA"):
            if accetto:
                dat = {"cliente": nome, "cf": cf, "luogo_nascita": nascita, "residenza": res, "num_doc": pat, "targa": targa, "prezzo": prezzo, "data_inizio": str(di), "ora_inizio": oi, "data_fine": str(df), "ora_fine": of, "telefono": tel}
                supabase.table("contratti").insert(dat).execute()
                st.success("Salvato!")
            else: st.error("Spunta Accetto!")

elif menu == "Archivio":
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"{c['cliente']} - {c['targa']}"):
            col1, col2, col3 = st.columns(3)
            col1.download_button("📜 CONTRATTO", doc_contratto(c), f"Contratto_{c['id']}.pdf")
            col2.download_button("💰 RICEVUTA", doc_ricevuta(c), f"Ricevuta_{c['id']}.pdf")
            t_wa = str(c.get('telefono','')).replace(" ","")
            if t_wa: col3.link_button("💬 WhatsApp", f"https://wa.me/39{t_wa}")

elif menu == "Multe":
    t_m = st.text_input("Targa").upper()
    if t_m:
        res_m = supabase.table("contratti").select("*").eq("targa", t_m).execute()
        if res_m.data:
            st.download_button("🚨 SCARICA MODULO VIGILI", doc_vigili(res_m.data[0]), f"Vigili_{t_m}.pdf")
