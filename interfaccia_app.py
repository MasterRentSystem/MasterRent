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

# --- GENERATORE PDF ---
def genera_documento(c, tipo="CONTRATTO"):
    pdf = fpdf.FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 10); pdf.set_fill_color(240, 240, 240)
    pdf.multi_cell(0, 5, txt=clean_t(INTESTAZIONE_DITTA), border=1, align='L', fill=True)
    pdf.ln(8)
    
    titoli = {"CONTRATTO": "CONTRATTO DI NOLEGGIO", "FATTURA": "RICEVUTA DI PAGAMENTO", "VIGILI": "ACCERTAMENTO VIOLAZIONE (VIGILI)"}
    pdf.set_font("Arial", 'B', 15); pdf.cell(0, 10, clean_t(titoli.get(tipo)), ln=1, align='C')
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 9); pdf.cell(0, 6, "DATI RIEPILOGATIVI", ln=1)
    pdf.set_font("Arial", size=9)
    pdf.cell(95, 7, clean_t(f"CLIENTE: {c.get('cliente')}"), border=1)
    pdf.cell(95, 7, clean_t(f"C.F.: {c.get('cf')}"), border=1, ln=1)
    pdf.cell(60, 7, clean_t(f"TARGA: {c.get('targa')}"), border=1)
    pdf.cell(65, 7, clean_t(f"INIZIO: {c.get('data_inizio')} ORE {c.get('ora_inizio')}"), border=1)
    pdf.cell(65, 7, clean_t(f"FINE: {c.get('data_fine')} ORE {c.get('ora_fine')}"), border=1, ln=1)
    
    if tipo == "CONTRATTO":
        pdf.ln(5); pdf.set_font("Arial", 'B', 7); pdf.cell(0, 5, "CONDIZIONI GENERALI (1-14) EX ART. 1341-1342 C.C.", ln=1)
        pdf.set_font("Arial", size=6)
        clausole = (
            "1) Locazione veicolo stato ottimo. 2) Responsabilita danni/furto totale. 3) Sanzioni + 25.83 Euro gestione.\n"
            "4) Foro Ischia. 5) Casco obbligatorio. 6) Privacy/GDPR/Foto patente. 7) Approvazione clausole vessatorie."
        )
        pdf.multi_cell(0, 3, txt=clean_t(clausole), border='T')
        pdf.ln(10); pdf.cell(0, 10, "Firma del Cliente: ______________________", align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- APP STREAMLIT ---
st.set_page_config(page_title="MasterRent Ischia", layout="centered")
menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Noleggio", "🗄️ Archivio", "🚨 Multe"])

if menu == "📝 Nuovo Noleggio":
    st.header("Nuovo Check-in")
    with st.form("form_master_final"):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Cognome e Nome")
        cf = c2.text_input("Codice Fiscale")
        nascita = c1.text_input("Luogo/Data Nascita")
        residenza = c2.text_input("Residenza")
        num_pat = c1.text_input("Num. Patente")
        targa = c2.text_input("TARGA").upper()
        
        st.subheader("Periodo Noleggio")
        d1, d2, d3, d4 = st.columns(4)
        data_i = d1.date_input("Data Inizio", datetime.date.today())
        ora_i = d2.text_input("Ora Inizio", "10:00")
        data_f = d3.date_input("Data Fine", datetime.date.today() + datetime.timedelta(days=1))
        ora_f = d4.text_input("Ora Fine", "10:00", key="ora_f_unique")
        
        prezzo = st.number_input("Prezzo Totale (€)", min_value=0.0)
        
        # --- INFORMATIVA CON OBBLIGO CLIC ---
        with st.expander("📄 LEGGI CONDIZIONI GENERALI (1-14) E PRIVACY"):
            st.write("1. Il cliente è responsabile del veicolo. 2. In caso di FURTO il cliente risponde dell'intero valore. 3. Le multe sono a carico del cliente + €25,83 spese. 4. Obbligo casco. 5. Foro competente Ischia. 6. Consenso foto patente per P.S.")
        
        accetto = st.checkbox("DICHIARO DI AVER LETTO E ACCETTO LE 14 CLAUSOLE (Art. 1341-1342 c.c.)")
        
        foto = st.camera_input("📸 Foto Patente")
        st.write("✍️ *Firma Cliente*")
        st_canvas(fill_color="white", stroke_width=2, height=150, key="sign_final")
        
        submit = st.form_submit_button("💾 SALVA NOLEGGIO")
        
        if submit:
            if not accetto:
                st.error("Devi spuntare la casella di accettazione delle clausole per procedere!")
            else:
                fn = f"{targa}_{int(time.time())}.jpg"
                if foto: supabase.storage.from_(BUCKET_NAME).upload(fn, foto.getvalue())
                dat = {"cliente": nome, "cf": cf, "luogo_nascita": nascita, "residenza": residenza, 
                       "num_doc": num_pat, "targa": targa, "prezzo": prezzo,
                       "data_inizio": str(data_i), "ora_inizio": ora_i, "data_fine": str(data_f), "ora_fine": ora_f, "foto_path": fn if foto else None}
                supabase.table("contratti").insert(dat).execute()
                st.success("Contratto Salvato!")

elif menu == "🗄️ Archivio":
    st.header("🗄️ Archivio")
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"📄 {c['cliente']} - {c['targa']}"):
            col1, col2, col3, col4 = st.columns([1,1,1,1.2])
            col1.download_button("📜 Contratto", genera_documento(c, "CONTRATTO"), f"C_{c['targa']}.pdf")
            col2.download_button("💰 Fattura", genera_documento(c, "FATTURA"), f"F_{c['id']}.pdf")
            if c.get("foto_path"):
                u = supabase.storage.from_(BUCKET_NAME).get_public_url(c["foto_path"])
                col3.link_button("📸 Foto", u)
            
            # --- TASTO WHATSAPP RIPRISTINATO ---
            testo_wa = f"Ciao {c['cliente']}, ecco il riepilogo MasterRent per la targa {c['targa']}. Valido fino al {c['data_fine']} ore {c['ora_fine']}."
            col4.link_button("💬 WhatsApp", f"https://wa.me/?text={urllib.parse.quote(testo_wa)}")

elif menu == "🚨 Multe":
    st.header("🚨 Modulo Vigili")
    t_m = st.text_input("Targa").upper()
    if t_m:
        res_m = supabase.table("contratti").select("*").eq("targa", t_m).execute()
        if res_m.data:
            st.download_button("📥 Scarica Accertamento Violazione", genera_documento(res_m.data[0], "VIGILI"), f"Vigili_{t_m}.pdf")
