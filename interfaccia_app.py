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

INFO_DITTA = "BATTAGLIA MARIANNA\nVia Cognole, 5 - 80075 Forio (NA)\nP. IVA 10252601215 | C.F. BTTMNN87A53Z112S"

def pulisci(t):
    if not t or t == "None": return "---"
    r = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in r.items(): t = str(t).replace(k, v)
    return t.encode('latin-1', 'ignore').decode('latin-1')

def intestazione_fissa(pdf, tit):
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(0, 10, "BATTAGLIA MARIANNA", ln=1)
    pdf.set_font("Arial", size=9)
    pdf.multi_cell(0, 5, pulisci(INFO_DITTA))
    pdf.line(10, 32, 200, 32)
    pdf.ln(12)
    pdf.set_font("Arial", 'B', 15)
    pdf.cell(0, 10, pulisci(tit), ln=1, align='C')
    pdf.ln(5)

# --- FUNZIONI TOTALMENTE SEPARATE ---
def stampa_CONTRATTO_nuovo(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    intestazione_fissa(pdf, "CONTRATTO DI NOLEGGIO")
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 8, pulisci(f"CLIENTE: {c['cliente']}\nCF: {c['cf']}\nTARGA: {c['targa']}\nPERIODO: {c['data_inizio']} / {c['data_fine']}"), border=1)
    pdf.ln(5); pdf.set_font("Arial", 'B', 8); pdf.cell(0, 5, "CONDIZIONI GENERALI:", ln=1)
    pdf.set_font("Arial", size=7); pdf.multi_cell(0, 4, pulisci("1. Danni/Furto a carico cliente. 2. Multe + 25.83 euro. 3. Foro Ischia. 4. Privacy GDPR."), border='T')
    pdf.ln(20); pdf.cell(0, 10, "Firma Cliente: ______________________", align='R')
    return pdf.output(dest='S').encode('latin-1')

def stampa_RICEVUTA_nuova(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    intestazione_fissa(pdf, "RICEVUTA DI PAGAMENTO")
    pdf.set_font("Arial", size=12); pdf.ln(10)
    pdf.cell(0, 10, pulisci(f"Ricevuto da: {c['cliente']}"), ln=1)
    pdf.cell(0, 10, pulisci(f"Per noleggio targa: {c['targa']}"), ln=1)
    pdf.ln(20); pdf.set_font("Arial", 'B', 22)
    pdf.cell(0, 20, pulisci(f"TOTALE: Euro {c['prezzo']}"), border=1, ln=1, align='C')
    return pdf.output(dest='S').encode('latin-1')

def stampa_VIGILI_nuovo(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    intestazione_fissa(pdf, "MODULO RINOTIFICA VIGILI")
    pdf.set_font("Arial", size=11)
    t = (f"La ditta MasterRent comunica che il veicolo targa {c['targa']} "
         f"in data {c['data_inizio']} era affidato al Sig. {c['cliente']}.\n\n"
         f"Si richiede rinotifica verbale come da L. 445/2000.")
    pdf.multi_cell(0, 8, pulisci(t))
    pdf.ln(30); pdf.cell(0, 10, "Firma: ______________________", align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- APP ---
st.set_page_config(page_title="MasterRent V3", layout="wide")
scelta = st.sidebar.radio("Vai a:", ["Check-in", "Archivio", "Multe"])

if scelta == "Check-in":
    with st.form("form_definitivo"):
        c1, c2 = st.columns(2)
        n = c1.text_input("Nome")
        t = c2.text_input("Targa").upper()
        cf = c1.text_input("CF")
        tel = c2.text_input("Tel")
        p = c1.number_input("Prezzo", min_value=0.0)
        di = st.date_input("Inizio")
        df = st.date_input("Fine")
        acc = st.checkbox("Accetto Privacy e Clausole")
        f = st.camera_input("Foto Patente")
        st_canvas(height=100, key="firma_def")
        if st.form_submit_button("SALVA"):
            if acc:
                path = f"{t}_{int(time.time())}.jpg"
                if f: supabase.storage.from_(BUCKET_NAME).upload(path, f.getvalue())
                dat = {"cliente": n, "targa": t, "cf": cf, "prezzo": p, "data_inizio": str(di), "data_fine": str(df), "telefono": tel, "foto_path": path if f else None}
                supabase.table("contratti").insert(dat).execute()
                st.success("Salvato!")

elif scelta == "Archivio":
    re = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in re.data:
        with st.expander(f"{c['cliente']} - {c['targa']}"):
            col1, col2, col3 = st.columns(3)
            col1.download_button("📜 CONTRATTO", stampa_CONTRATTO_nuovo(c), f"C_{c['id']}.pdf", key=f"C_{c['id']}_X")
            col2.download_button("💰 RICEVUTA", stampa_RICEVUTA_nuova(c), f"R_{c['id']}.pdf", key=f"R_{c['id']}_X")
            if c.get("foto_path"):
                col3.link_button("📸 FOTO", supabase.storage.from_(BUCKET_NAME).get_public_url(c["foto_path"]))

elif scelta == "Multe":
    tm = st.text_input("Targa").upper()
    if tm:
        rm = supabase.table("contratti").select("*").eq("targa", tm).execute()
        if rm.data:
            st.download_button("🚨 SCARICA VIGILI", stampa_VIGILI_nuovo(rm.data[0]), f"V_{tm}.pdf")
