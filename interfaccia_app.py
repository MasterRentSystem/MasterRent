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

DITTA_NOME = "BATTAGLIA MARIANNA"
DITTA_INFO = "Via Cognole, 5 - 80075 Forio (NA)\nCod. Fisc. BTTMNN87A53Z112S - P. IVA 10252601215"

def clean_t(text):
    if not text or text == "None": return "---"
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in repls.items(): text = str(text).replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

def intestazione(pdf):
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 8, clean_t(DITTA_NOME), ln=1, align='L')
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 5, clean_t(DITTA_INFO), align='L')
    pdf.line(10, 32, 200, 32)
    pdf.ln(15)

# --- 1. FUNZIONE CONTRATTO ---
def genera_contratto(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    intestazione(pdf)
    pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, "CONTRATTO DI NOLEGGIO", ln=1, align='C'); pdf.ln(5)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 7, clean_t(f"CLIENTE: {c['cliente']}\nC.F.: {c['cf']}\nRESIDENZA: {c['residenza']}\nVEICOLO: {c['targa']}\nDAL: {c['data_inizio']} ore {c['ora_inizio']} AL: {c['data_fine']} ore {c['ora_fine']}"), border=1)
    pdf.ln(10); pdf.set_font("Arial", 'B', 9); pdf.cell(0, 5, "CONDIZIONI GENERALI (Sintesi 1-14)", ln=1)
    pdf.set_font("Arial", size=7.5)
    pdf.multi_cell(0, 4, clean_t("1. Veicolo in ottimo stato. 2. Responsabilita danni/usura. 3. Multe a carico cliente + 25.83 Euro gestione. 4. RESPONSABILITA TOTALE FURTO/INCENDIO. 5. Foro competente Ischia. 6. Obbligo casco. 7. Privacy GDPR."), border='T')
    pdf.ln(20); pdf.cell(0, 10, "Firma del Cliente: ______________________", align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- 2. FUNZIONE RICEVUTA ---
def genera_ricevuta(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    intestazione(pdf)
    pdf.set_font("Arial", 'B', 16); pdf.cell(0, 10, "RICEVUTA DI PAGAMENTO", ln=1, align='C'); pdf.ln(10)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, clean_t(f"Ricevuti da: {c['cliente']}"), ln=1)
    pdf.cell(0, 10, clean_t(f"Per noleggio veicolo targa: {c['targa']}"), ln=1)
    pdf.cell(0, 10, clean_t(f"Periodo: {c['data_inizio']} - {c['data_fine']}"), ln=1)
    pdf.ln(15); pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 15, clean_t(f"TOTALE PAGATO: Euro {c['prezzo']}"), border=1, ln=1, align='C')
    return pdf.output(dest='S').encode('latin-1')

# --- 3. FUNZIONE VIGILI (ACCERTAMENTO) ---
def genera_modulo_vigili(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    intestazione(pdf)
    pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, "OGGETTO: COMUNICAZIONE DATI LOCATARIO PER RINOTIFICA", ln=1, align='C'); pdf.ln(5)
    pdf.set_font("Arial", size=10)
    testo = (
        f"La sottoscritta BATTAGLIA MARIANNA, titolare della ditta MasterRent,\n\n"
        f"DICHIARA ai sensi della L. 445/2000 che il veicolo targa {c['targa']}\n"
        f"nel giorno {c['data_inizio']} era concesso in locazione al Sig.:\n\n"
        f"NOME: {c['cliente']}\nNATO A: {c.get('luogo_nascita', '---')}\n"
        f"RESIDENTE: {c['residenza']}\nC.F.: {c['cf']}\nPATENTE: {c['num_doc']}\n\n"
        f"Si richiede pertanto la rinotifica del verbale al soggetto sopra indicato.\n"
        f"In allegato copia del contratto firmato."
    )
    pdf.multi_cell(0, 7, clean_t(testo))
    pdf.ln(20); pdf.cell(0, 10, "In fede, Marianna Battaglia", align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- APP ---
st.set_page_config(page_title="MasterRent Pro", layout="wide")
menu = st.sidebar.radio("Menu", ["📝 Nuovo", "🗄️ Archivio", "🚨 Multe"])

if menu == "📝 Nuovo":
    with st.form("form_v18"):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome e Cognome")
        cf = c2.text_input("Codice Fiscale")
        nascita = c1.text_input("Luogo/Data Nascita")
        residenza = c2.text_input("Residenza")
        patente = c1.text_input("Num. Patente")
        targa = c1.text_input("TARGA").upper()
        tel = c2.text_input("Telefono")
        d1, d2, d3, d4 = st.columns(4)
        di = d1.date_input("Inizio", datetime.date.today())
        oi = d2.text_input("Ora Inizio", "10:00")
        df = d3.date_input("Fine", datetime.date.today() + datetime.timedelta(days=1))
        of = d4.text_input("Ora Fine", "10:00")
        prezzo = st.number_input("Prezzo (€)", min_value=0.0)
        accetto = st.checkbox("Accetto Condizioni 1-14")
        foto = st.camera_input("📸 Foto Patente")
        st_canvas(height=150, key="sign_v18")
        if st.form_submit_button("💾 SALVA"):
            if accetto:
                fn = f"{targa}_{int(time.time())}.jpg"
                if foto: supabase.storage.from_(BUCKET_NAME).upload(fn, foto.getvalue())
                dat = {"cliente": nome, "cf": cf, "luogo_nascita": nascita, "residenza": residenza, "num_doc": patente, "targa": targa, "prezzo": prezzo, "data_inizio": str(di), "ora_inizio": oi, "data_fine": str(df), "ora_fine": of, "telefono": tel, "foto_path": fn if foto else None}
                supabase.table("contratti").insert(dat).execute()
                st.success("Salvato correttamente!")
            else: st.error("Spunta la casella 'Accetto'!")

elif menu == "🗄️ Archivio":
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"📄 {c['cliente']} - {c['targa']}"):
            col1, col2, col3 = st.columns(3)
            col1.download_button("📜 Contratto", genera_contratto(c), f"Contratto_{c['targa']}.pdf")
            col2.download_button("💰 Ricevuta", genera_ricevuta(c), f"Ricevuta_{c['id']}.pdf")
            tel_c = str(c.get('telefono','')).replace(" ","")
            if tel_c: col3.link_button("💬 WhatsApp", f"https://wa.me/39{tel_c}")

elif menu == "🚨 Multe":
    t_m = st.text_input("Targa").upper()
    if t_m:
        res_m = supabase.table("contratti").select("*").eq("targa", t_m).execute()
        if res_m.data:
            st.download_button("📥 Scarica Modulo Vigili", genera_modulo_vigili(res_m.data[0]), f"Vigili_{t_m}.pdf")
