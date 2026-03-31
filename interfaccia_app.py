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

# DATI AZIENDALI ESTRATTI DALLE FOTO
DITTA = "BATTAGLIA MARIANNA"
INDIRIZZO = "Via Cognole, 5 - 80075 Forio (NA)"
PIVA = "10252601215"
CF_DITTA = "BTTMNN87A53Z112S"
INFO_TITOLARE = f"{DITTA} nata a Berlino (Germania) il 13/01/1987 e residente in Forio alla Via Cognole n. 5\nin qualita di titolare dell'omonima ditta individuale, C.F.: {CF_DITTA} e P. IVA: {PIVA}"

def clean_t(text):
    if not text or text == "None": return "---"
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in repls.items(): text = str(text).replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

# --- GENERATORE DOCUMENTI ---
def genera_pdf_ufficiale(c, tipo="CONTRATTO"):
    pdf = fpdf.FPDF()
    pdf.add_page()
    
    if tipo == "VIGILI":
        # MODULO ACCERTAMENTO VIOLAZIONE (Foto 1)
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 5, "Spett. le", ln=1, align='R')
        pdf.cell(0, 5, "Polizia Locale di ______________________", ln=1, align='R')
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 10)
        pdf.multi_cell(0, 5, txt=clean_t("OGGETTO: RIFERIMENTO VS. ACCERTAMENTO VIOLAZIONE N. __________ PROT.\n- COMUNICAZIONE LOCAZIONE VEICOLO"))
        pdf.ln(5)
        pdf.set_font("Arial", size=10)
        testo_iniziale = f"In riferimento al Verbale di accertamento di infrazione al Codice della strada di cui all'oggetto, con la presente, la sottoscritta {INFO_TITOLARE}"
        pdf.multi_cell(0, 5, txt=clean_t(testo_iniziale))
        pdf.ln(5); pdf.set_font("Arial", 'B', 11); pdf.cell(0, 10, "DICHIARA", ln=1, align='C')
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 6, txt=clean_t(f"Ai sensi della L. 445/2000 che il veicolo targa {c.get('targa')} il giorno {c.get('data_inizio')} era concesso in locazione senza conducente al signor:"))
        pdf.ln(2)
        pdf.multi_cell(0, 8, txt=clean_t(f"COGNOME E NOME: {c.get('cliente')}\nLUOGO E DATA DI NASCITA: {c.get('luogo_nascita')}\nRESIDENZA: {c.get('residenza')}\nIDENTIFICATO A MEZZO: Patente n. {c.get('num_doc')}"), border=1)
        pdf.ln(5)
        pdf.multi_cell(0, 5, txt=clean_t("La presente al fine di procedere alla rinotifica nei confronti del locatario sopra indicato.\nSi allega: Copia del contratto di locazione con documento del trasgressore."))
        pdf.ln(10)
        pdf.cell(0, 5, "In fede", ln=1, align='R')
        pdf.cell(0, 5, clean_t(DITTA), ln=1, align='R')
        
    else:
        # CONTRATTO E RICEVUTA (Foto 2, 3, 4)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 6, clean_t(DITTA), ln=1)
        pdf.set_font("Arial", size=9)
        pdf.cell(0, 5, clean_t(f"{INDIRIZZO} - P. IVA {PIVA}"), ln=1)
        pdf.ln(5)
        
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, clean_t("CONTRATTO DI NOLEGGIO"), ln=1, align='C', border='B')
        pdf.ln(5)
        
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 6, txt=clean_t(f"Sottoscritto: {c.get('cliente')} | Tel: {c.get('telefono')}\nNato il: {c.get('luogo_nascita')} | Email: {c.get('email')}\nResidente a: {c.get('residenza')}\nPatente: {c.get('num_doc')}"))
        
        pdf.ln(2); pdf.set_font("Arial", 'B', 10)
        pdf.multi_cell(0, 7, txt=clean_t(f"VEICOLO TARGA: {c.get('targa')} | Prezzo: {c.get('prezzo')} Euro\nDALLE ORE {c.get('ora_inizio')} DEL {c.get('data_inizio')} ALLE ORE {c.get('ora_fine')} DEL {c.get('data_fine')}"), border=1)
        
        # Clausole Legali (Foto 4)
        pdf.ln(5); pdf.set_font("Arial", 'B', 8); pdf.cell(0, 5, "CONDIZIONI GENERALI", ln=1)
        pdf.set_font("Arial", size=6.5)
        pdf.multi_cell(0, 3.5, txt=clean_t("1) Veicolo in ottimo stato. 2) Segnalare anomalie subito. 3) Responsabilita danni/usura. 4) Responsabilita FURTO TOTALE/PARZIALE. 5) Sanzioni e Multe a carico cliente + 25.83 Euro gestione. 6) Comunicare verbali entro 2gg. 7) Copertura R.C.A. 8) Nessuna resp. per oggetti smarriti. 9) No resp. per guasti meccanici. 10) Foro competente ISCHIA. 11) Addebito su carta. 12) Obbligo CASCO. 13) Resp. chiavi. 14) Obbligo denuncia immediata sinistro."))
        pdf.ln(4)
        pdf.set_font("Arial", 'B', 7)
        pdf.multi_cell(0, 4, txt=clean_t("Ai sensi degli artt. 1341-1342 c.c. si approvano specificamente i punti: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14."))
        pdf.ln(10)
        pdf.cell(0, 5, "Firma del Cliente: ______________________", align='R')

    return pdf.output(dest='S').encode('latin-1')

# --- APP STREAMLIT ---
st.set_page_config(page_title="MasterRent Ischia", layout="centered")

menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Noleggio", "🗄️ Archivio", "🚨 Gestione Multe"])

if menu == "📝 Nuovo Noleggio":
    st.header("Nuovo Noleggio")
    with st.form("form_v16"):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Cognome e Nome")
        cf = col2.text_input("Codice Fiscale")
        nascita = col1.text_input("Luogo e Data Nascita")
        residenza = col2.text_input("Residenza")
        tel = col1.text_input("Telefono")
        email = col2.text_input("Email")
        num_pat = col1.text_input("Num. Patente")
        targa = col2.text_input("TARGA").upper()
        
        d1, d2, d3, d4 = st.columns(4)
        data_i = d1.date_input("Inizio", datetime.date.today())
        ora_i = d2.text_input("Ore", "10:00")
        data_f = d3.date_input("Fine", datetime.date.today() + datetime.timedelta(days=1))
        ora_f = d4.text_input("Ore", "10:00")
        
        prezzo = st.number_input("Prezzo Totale Euro", min_value=0.0)
        foto = st.camera_input("📸 Foto Patente")
        st.write("✍️ Firma per accettazione condizioni (1-14)")
        st_canvas(fill_color="white", stroke_width=2, height=150, key="canvas_v16")
        
        if st.form_submit_button("💾 SALVA CONTRATTO"):
            fn = f"{targa}_{int(time.time())}.jpg"
            if foto: supabase.storage.from_(BUCKET_NAME).upload(fn, foto.getvalue())
            dat = {"cliente": nome, "cf": cf, "luogo_nascita": nascita, "residenza": residenza, 
                   "telefono": tel, "email": email, "num_doc": num_pat, "targa": targa, "prezzo": prezzo,
                   "data_inizio": str(data_i), "ora_inizio": ora_i, "data_fine": str(data_f), "ora_fine": ora_f, "foto_path": fn if foto else None}
            supabase.table("contratti").insert(dat).execute()
            st.success("Noleggio Registrato!")

elif menu == "🗄️ Archivio":
    st.header("Archivio")
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"📄 {c['cliente']} - {c['targa']}"):
            col1, col2, col3 = st.columns(3)
            col1.download_button("📜 Contratto", genera_pdf_ufficiale(c, "CONTRATTO"), f"C_{c['targa']}.pdf")
            col2.download_button("💰 Ricevuta", genera_pdf_ufficiale(c, "FATTURA"), f"R_{c['id']}.pdf")
            if c.get("foto_path"):
                u = supabase.storage.from_(BUCKET_NAME).get_public_url(c["foto_path"])
                col3.link_button("📸 Foto Patente", u)

elif menu == "🚨 Gestione Multe":
    st.header("Modulo Polizia Locale")
    t_m = st.text_input("Targa del verbale").upper()
    if t_m:
        res_m = supabase.table("contratti").select("*").eq("targa", t_m).execute()
        if res_m.data:
            st.success(f"Noleggiatore trovato: {res_m.data[0]['cliente']}")
            st.download_button("📥 Scarica Accertamento Violazione", genera_pdf_ufficiale(res_m.data[0], "VIGILI"), f"Vigili_{t_m}.pdf")
