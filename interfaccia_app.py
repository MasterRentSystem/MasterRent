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

DITTA = "BATTAGLIA MARIANNA"
DITTA_INFO = "Via Cognole, 5 - 80075 Forio (NA)\nP. IVA 10252601215 | C.F. BTTMNN87A53Z112S"

def clean_t(text):
    if not text or text == "None": return "---"
    r = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in r.items(): text = str(text).replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

def genera_pdf(c, tipo):
    pdf = FPDF()
    pdf.add_page()
    
    # Intestazione comune
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, DITTA, ln=True)
    pdf.set_font("Arial", size=9)
    pdf.multi_cell(0, 5, clean_t(DITTA_INFO))
    pdf.line(10, 32, 200, 32)
    pdf.ln(12)

    if tipo == "CONTRATTO":
        pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, "CONTRATTO DI NOLEGGIO", ln=True, align='C'); pdf.ln(5)
        pdf.set_font("Arial", size=10)
        info = f"CLIENTE: {c.get('cliente')}\nNATO A: {c.get('luogo_nascita')}\nRESIDENTE: {c.get('residenza')}\nC.F.: {c.get('cf')}\nPATENTE: {c.get('num_doc')}\nTEL: {c.get('telefono')}\n\nVEICOLO: {c.get('targa')}\nDAL: {c.get('data_inizio')} AL: {c.get('data_fine')}"
        pdf.multi_cell(0, 7, clean_t(info), border=1)
        pdf.ln(5); pdf.set_font("Arial", 'B', 8); pdf.cell(0, 5, "CONDIZIONI (1-14):", ln=True)
        pdf.set_font("Arial", size=6); pdf.multi_cell(0, 3, clean_t("1. Mezzo in ottimo stato. 2. Responsabilita danni/furto cliente. 3. Multe a carico cliente + 25.83 Euro. 4. Casco obbligatorio. 5. Foro Ischia. 6. Privacy GDPR."), border='T')
        pdf.ln(20); pdf.cell(0, 10, "Firma del Cliente: ______________________", align='R')
    
    elif tipo == "RICEVUTA":
        pdf.set_font("Arial", 'B', 15); pdf.cell(0, 10, "RICEVUTA DI PAGAMENTO", ln=True, align='C'); pdf.ln(15)
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, clean_t(f"Ricevuto da: {c.get('cliente')}"), ln=True)
        pdf.cell(0, 10, clean_t(f"Per noleggio veicolo targa: {c.get('targa')}"), ln=True)
        pdf.ln(20); pdf.set_font("Arial", 'B', 22)
        pdf.cell(0, 25, clean_t(f"TOTALE: Euro {c.get('prezzo')}"), border=1, ln=True, align='C')

    elif tipo == "VIGILI":
        pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, "DICHIARAZIONE DATI CONDUCENTE", ln=True, align='C'); pdf.ln(10)
        pdf.set_font("Arial", size=11)
        t = (f"La sottoscritta BATTAGLIA MARIANNA dichiara che il veicolo targa {c.get('targa')} "
             f"in data {c.get('data_inizio')} era affidato al Sig. {c.get('cliente')}.\n"
             f"Nato a: {c.get('luogo_nascita')}\nResidente in: {c.get('residenza')}\nPatente: {c.get('num_doc')}\n\n"
             f"Si richiede rinotifica verbale ai sensi della L. 445/2000.")
        pdf.multi_cell(0, 8, clean_t(t))
        pdf.ln(30); pdf.cell(0, 10, "Timbro e Firma: ______________________", align='R')

    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACCIA ---
st.set_page_config(page_title="MasterRent Management", layout="wide")
menu = st.sidebar.radio("Scegli", ["📝 Nuovo", "🗄️ Archivio", "🚨 Multe"])

if menu == "📝 Nuovo":
    with st.form("form_v27"):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Cognome Nome")
        cf = c2.text_input("C.F.")
        nasc = c1.text_input("Luogo Nascita")
        res = c2.text_input("Residenza")
        pat = c1.text_input("Patente")
        tel = c2.text_input("Telefono")
        targa = c1.text_input("Targa").upper()
        prezzo = c2.number_input("Prezzo (€)", min_value=0.0)
        di = st.date_input("Inizio")
        df = st.date_input("Fine")
        st.write("---")
        accetto = st.checkbox("Accetto Condizioni e Privacy")
        foto = st.camera_input("Foto Patente")
        st.write("Firma Cliente:")
        st_canvas(height=100, stroke_width=2, key="firma_v27")
        if st.form_submit_button("SALVA NOLEGGIO"):
            if accetto:
                fn = f"{targa}_{int(time.time())}.jpg"
                if foto: supabase.storage.from_(BUCKET_NAME).upload(fn, foto.getvalue())
                dat = {"cliente": nome, "cf": cf, "luogo_nascita": nasc, "residenza": res, "num_doc": pat, "targa": targa, "prezzo": prezzo, "data_inizio": str(di), "data_fine": str(df), "telefono": tel, "foto_path": fn if foto else None}
                supabase.table("contratti").insert(dat).execute()
                st.success("Salvato in Archivio!")
            else: st.error("Spunta la casella di accettazione!")

elif menu == "🗄️ Archivio":
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"📄 {c['cliente']} - {c['targa']}"):
            col1, col2, col3 = st.columns(3)
            col1.download_button("📜 CONTRATTO", genera_pdf(c, "CONTRATTO"), f"Contr_{c['id']}.pdf", key=f"c_{c['id']}")
            col2.download_button("💰 RICEVUTA", genera_pdf(c, "RICEVUTA"), f"Ricev_{c['id']}.pdf", key=f"r_{c['id']}")
            if c.get("foto_path"):
                u = supabase.storage.from_(BUCKET_NAME).get_public_url(c["foto_path"])
                col3.link_button("📸 PATENTE", u)

elif menu == "🚨 Multe":
    t_m = st.text_input("Inserisci Targa").upper()
    if t_m:
        rm = supabase.table("contratti").select("*").eq("targa", t_m).execute()
        if rm.data:
            st.download_button("🚨 MODULO VIGILI", genera_pdf(rm.data[0], "VIGILI"), f"Vigili_{t_m}.pdf")
