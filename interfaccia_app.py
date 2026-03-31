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

INTESTAZIONE_DITTA = "BATTAGLIA MARIANNA\nVia Cognole, 5 - 80075 Forio (NA)\nP. IVA 10252601215"

def clean_t(text):
    if not text or text == "None": return "---"
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in repls.items(): text = str(text).replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

# --- GENERATORE PDF MULTIFUNZIONE (CONTRATTO, FATTURA, VIGILI) ---
def genera_documento(c, tipo="CONTRATTO"):
    pdf = fpdf.FPDF()
    pdf.add_page()
    
    # Intestazione Professionale
    pdf.set_font("Arial", 'B', 10); pdf.set_fill_color(240, 240, 240)
    pdf.multi_cell(0, 5, txt=clean_t(INTESTAZIONE_DITTA), border=1, align='L', fill=True)
    pdf.ln(8)
    
    titoli = {"CONTRATTO": "CONTRATTO DI NOLEGGIO", "FATTURA": "RICEVUTA DI PAGAMENTO", "VIGILI": "COMUNICAZIONE DATI CONDUCENTE (ACCERTAMENTO VIOLAZIONE)"}
    pdf.set_font("Arial", 'B', 15); pdf.cell(0, 10, clean_t(titoli.get(tipo)), ln=1, align='C')
    pdf.ln(5)
    
    # Dati Cliente e Veicolo
    pdf.set_font("Arial", 'B', 9); pdf.cell(0, 6, "DATI RIEPILOGATIVI", ln=1)
    pdf.set_font("Arial", size=9)
    pdf.cell(95, 7, clean_t(f"CLIENTE: {c.get('cliente')}"), border=1)
    pdf.cell(95, 7, clean_t(f"C.F.: {c.get('cf')}"), border=1, ln=1)
    pdf.cell(60, 7, clean_t(f"TARGA: {c.get('targa')}"), border=1)
    pdf.cell(65, 7, clean_t(f"INIZIO: {c.get('data_inizio')} ORE {c.get('ora_inizio')}"), border=1)
    pdf.cell(65, 7, clean_t(f"FINE: {c.get('data_fine')} ORE {c.get('ora_fine')}"), border=1, ln=1)
    
    if tipo == "CONTRATTO":
        pdf.ln(5); pdf.set_font("Arial", 'B', 8); pdf.cell(0, 5, "CONDIZIONI GENERALI (ARTT. 1341-1342 C.C.)", ln=1)
        pdf.set_font("Arial", size=6.5)
        clausole = (
            "1) Veicolo in ottimo stato. 2) Responsabilita totale danni/furto. 3) Sanzioni a carico del cliente + 25.83 Euro spese.\n"
            "4) Foro competente: Ischia. 5) Obbligo casco e fermo amm.vo 90gg per violazioni.\n"
            "6) Privacy: Autorizzazione foto patente e dati GDPR. 7) Approvazione specifica clausole 1-14."
        )
        pdf.multi_cell(0, 4, txt=clean_t(clausole), border='T')
        pdf.ln(10); pdf.cell(0, 10, "Firma del Cliente: ______________________", align='R')
    
    elif tipo == "VIGILI":
        pdf.ln(10); pdf.set_font("Arial", size=11)
        testo_v = f"Il sottoscritto dichiara che in data {c.get('data_inizio')} il veicolo targa {c.get('targa')} era affidato a {c.get('cliente')}."
        pdf.multi_cell(0, 7, txt=clean_t(testo_v))
        pdf.ln(10); pdf.cell(0, 10, "Timbro e Firma: ______________________", align='R')

    return pdf.output(dest='S').encode('latin-1')

# --- APP STREAMLIT ---
st.set_page_config(page_title="MasterRent - Sistema Completo", layout="centered")
menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Noleggio", "🗄️ Archivio", "🚨 Gestione Multe"])

if menu == "📝 Nuovo Noleggio":
    with st.form("form_full_v15"):
        st.subheader("Dati Contratto")
        c1, c2 = st.columns(2)
        nome = c1.text_input("Cognome e Nome")
        cf = c2.text_input("Codice Fiscale")
        nascita = c1.text_input("Luogo e Data Nascita")
        residenza = c2.text_input("Residenza")
        num_pat = c1.text_input("Num. Patente")
        targa = c2.text_input("TARGA").upper()
        
        d1, d2, d3, d4 = st.columns(4)
        data_i = d1.date_input("Data Inizio", datetime.date.today())
        ora_i = d2.text_input("Ora Inizio", "10:00")
        data_f = d3.date_input("Data Fine", datetime.date.today() + datetime.timedelta(days=1))
        ora_f = d4.text_input("Ora Fine", "10:00")
        
        prezzo = st.number_input("Prezzo Totale (€)", min_value=0.0)
        st.info("*CONDIZIONI:* Accettazione clausole 1-14 (Furto, Danni, Multe) e Privacy GDPR.")
        
        foto = st.camera_input("📸 Foto Patente")
        st_canvas(fill_color="white", stroke_width=2, height=150, key="sign_full")
        
        if st.form_submit_button("💾 SALVA TUTTO"):
            fn = f"{targa}_{int(time.time())}.jpg"
            if foto: supabase.storage.from_(BUCKET_NAME).upload(fn, foto.getvalue())
            dat = {"cliente": nome, "cf": cf, "luogo_nascita": nascita, "residenza": residenza, 
                   "num_doc": num_pat, "targa": targa, "prezzo": prezzo,
                   "data_inizio": str(data_i), "ora_inizio": ora_i, "data_fine": str(data_f), "ora_fine": ora_f, "foto_path": fn if foto else None}
            supabase.table("contratti").insert(dat).execute()
            st.success("Archiviato con successo!")

elif menu == "🗄️ Archivio":
    st.header("🗄️ Archivio Documenti")
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"📄 {c['cliente']} - {c['targa']}"):
            col1, col2, col3, col4 = st.columns([1,1,1,1.2])
            col1.download_button("📜 Contratto", genera_documento(c, "CONTRATTO"), f"C_{c['targa']}.pdf")
            col2.download_button("💰 Fattura", genera_documento(c, "FATTURA"), f"F_{c['id']}.pdf")
            if c.get("foto_path"):
                u = supabase.storage.from_(BUCKET_NAME).get_public_url(c["foto_path"])
                col3.link_button("📸 Foto", u)
            msg = urllib.parse.quote(f"Ciao {c['cliente']}, MasterRent conferma noleggio {c['targa']} fino al {c['data_fine']}.")
            col4.link_button("💬 WhatsApp", f"https://wa.me/?text={msg}")

elif menu == "🚨 Gestione Multe":
    st.header("🚨 Accertamento Violazione Vigili")
    t_m = st.text_input("Inserisci Targa").upper()
    if t_m:
        res_m = supabase.table("contratti").select("*").eq("targa", t_m).execute()
        if res_m.data:
            st.success(f"Trovato: {res_m.data[0]['cliente']}")
            st.download_button("📥 Scarica Modulo Vigili", genera_documento(res_m.data[0], "VIGILI"), f"Vigili_{t_m}.pdf")
