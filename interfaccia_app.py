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
DITTA_INFO = "Via Cognole, 5 - 80075 Forio (NA)\nP. IVA 10252601215 | C.F. BTTMNN87A53Z112S"

def clean_t(text):
    if not text or text == "None": return "---"
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in repls.items(): text = str(text).replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

def add_header_custom(pdf, titolo):
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(0, 10, clean_t(DITTA_NOME), ln=1, align='L')
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 5, clean_t(DITTA_INFO), align='L')
    pdf.line(10, 35, 200, 35)
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 15)
    pdf.cell(0, 10, clean_t(titolo), ln=1, align='C')
    pdf.ln(5)

# --- 📜 FUNZIONE CONTRATTO ---
def crea_pdf_contratto_v21(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    add_header_custom(pdf, "CONTRATTO DI NOLEGGIO")
    pdf.set_font("Arial", size=10)
    testo_box = f"CLIENTE: {c['cliente']}\nC.F.: {c['cf']}\nMEZZO: {c['targa']}\nPERIODO: dal {c['data_inizio']} al {c['data_fine']}"
    pdf.multi_cell(0, 7, clean_t(testo_box), border=1)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 8); pdf.cell(0, 5, "CONDIZIONI (1-14):", ln=1)
    pdf.set_font("Arial", size=7)
    pdf.multi_cell(0, 4, clean_t("Responsabilita totale danni e furto a carico del cliente. Multe + 25.83 euro. Foro Ischia. Casco obbligatorio. Privacy GDPR."), border='T')
    pdf.ln(20); pdf.cell(0, 10, "Firma: ______________________", align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- 💰 FUNZIONE RICEVUTA ---
def crea_pdf_ricevuta_v21(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    add_header_custom(pdf, "RICEVUTA DI PAGAMENTO")
    pdf.set_font("Arial", size=12)
    pdf.ln(10)
    pdf.cell(0, 10, clean_t(f"Ricevuti da: {c['cliente']}"), ln=1)
    pdf.cell(0, 10, clean_t(f"Per noleggio veicolo targa: {c['targa']}"), ln=1)
    pdf.ln(15)
    pdf.set_font("Arial", 'B', 20)
    pdf.cell(0, 20, clean_t(f"TOTALE: Euro {c['prezzo']}"), border=1, ln=1, align='C')
    return pdf.output(dest='S').encode('latin-1')

# --- 🚨 FUNZIONE VIGILI ---
def crea_pdf_vigili_v21(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    add_header_custom(pdf, "DICHIARAZIONE DATI CONDUCENTE")
    pdf.set_font("Arial", size=11)
    testo = (
        f"La sottoscritta BATTAGLIA MARIANNA dichiara che il veicolo targa {c['targa']}\n"
        f"in data {c['data_inizio']} era affidato al Sig.:\n\n"
        f"NOME: {c['cliente']}\nC.F.: {c['cf']}\nRESIDENTE: {c['residenza']}\nPATENTE: {c['num_doc']}\n\n"
        f"Si richiede la rinotifica al conducente sopra indicato ai sensi della L. 445/2000."
    )
    pdf.multi_cell(0, 8, clean_t(testo))
    pdf.ln(20); pdf.cell(0, 10, "Firma e Timbro: ______________________", align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACCIA ---
st.set_page_config(page_title="MasterRent Ischia", layout="wide")
scelta = st.sidebar.radio("Scegli", ["Nuovo", "Archivio", "Multe"])

if scelta == "Nuovo":
    with st.form("main_v21"):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome Cliente")
        targa = c2.text_input("Targa").upper()
        cf = c1.text_input("C.F.")
        res = c2.text_input("Residenza")
        pat = c1.text_input("Patente")
        tel = c2.text_input("Telefono")
        prezzo = c1.number_input("Prezzo (€)", min_value=0.0)
        
        d1, d2 = st.columns(2)
        di = d1.date_input("Inizio", datetime.date.today())
        df = d2.date_input("Fine", datetime.date.today() + datetime.timedelta(days=1))
        
        accetto = st.checkbox("Accetto Privacy e Clausole 1-14")
        foto = st.camera_input("Foto Patente")
        st_canvas(height=100, key="sign_v21")
        
        if st.form_submit_button("SALVA"):
            if accetto:
                fn = f"{targa}_{int(time.time())}.jpg"
                if foto: supabase.storage.from_(BUCKET_NAME).upload(fn, foto.getvalue())
                dat = {"cliente": nome, "targa": targa, "cf": cf, "residenza": res, "num_doc": pat, "telefono": tel, "prezzo": prezzo, "data_inizio": str(di), "data_fine": str(df), "foto_path": fn if foto else None}
                supabase.table("contratti").insert(dat).execute()
                st.success("Salvato correttamente!")
            else: st.error("Accetta i termini!")

elif scelta == "Archivio":
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"📄 {c['cliente']} - {c['targa']}"):
            col1, col2, col3, col4 = st.columns(4)
            col1.download_button("📜 CONTRATTO", crea_pdf_contratto_v21(c), f"Contr_{c['id']}.pdf")
            col2.download_button("💰 RICEVUTA", crea_pdf_ricevuta_v21(c), f"Ricev_{c['id']}.pdf")
            if c.get("foto_path"):
                url = supabase.storage.from_(BUCKET_NAME).get_public_url(c["foto_path"])
                col3.link_button("📸 PATENTE", url)
            if c.get("telefono"):
                col4.link_button("💬 WA", f"https://wa.me/39{c['telefono']}")

elif scelta == "Multe":
    t_m = st.text_input("Inserisci Targa").upper()
    if t_m:
        res_m = supabase.table("contratti").select("*").eq("targa", t_m).execute()
        if res_m.data:
            st.download_button("🚨 MODULO VIGILI", crea_pdf_vigili_v21(res_m.data[0]), f"Vigili_{t_m}.pdf")
