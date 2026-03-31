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

INTESTAZIONE_TXT = "MASTERRENT DI MARIANNA BATTAGLIA\nVia Cognole 5, 80075 Forio (NA)\nC.F.: BTTMNN87A53Z112S | P.IVA: 10252601215"

def clean_t(text):
    if not text or text == "None": return "---"
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in repls.items(): text = str(text).replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

# --- GENERATORE PDF ---
def genera_pdf_completo(c, tipo="CONTRATTO"):
    pdf = fpdf.FPDF()
    pdf.add_page()
    
    # Intestazione Professionale
    pdf.set_font("Arial", 'B', 10); pdf.set_fill_color(240, 240, 240)
    pdf.multi_cell(0, 5, txt=clean_t(INTESTAZIONE_TXT), border=1, align='L', fill=True)
    pdf.ln(8)
    
    titoli = {"CONTRATTO": "CONTRATTO DI NOLEGGIO", "FATTURA": "RICEVUTA DI PAGAMENTO", "VIGILI": "COMUNICAZIONE DATI CONDUCENTE"}
    pdf.set_font("Arial", 'B', 15); pdf.cell(0, 10, clean_t(titoli.get(tipo)), ln=1, align='C')
    pdf.ln(5)
    
    # Dati Cliente e Veicolo
    pdf.set_font("Arial", 'B', 9); pdf.cell(0, 6, "DATI CONDUCENTE E VEICOLO", ln=1)
    pdf.set_font("Arial", size=9)
    pdf.cell(95, 7, clean_t(f"CLIENTE: {c.get('cliente')}"), border=1)
    pdf.cell(95, 7, clean_t(f"C.F.: {c.get('cf')}"), border=1, ln=1)
    pdf.cell(95, 7, clean_t(f"PATENTE: {c.get('num_doc')}"), border=1)
    pdf.cell(95, 7, clean_t(f"SCADENZA: {c.get('scadenza_patente')}"), border=1, ln=1)
    pdf.cell(60, 7, clean_t(f"TARGA: {c.get('targa')}"), border=1)
    pdf.cell(65, 7, clean_t(f"DAL: {c.get('data_inizio')}"), border=1)
    pdf.cell(65, 7, clean_t(f"AL: {c.get('data_fine', '---')}"), border=1, ln=1)
    
    if tipo == "CONTRATTO":
        pdf.ln(5); pdf.set_font("Arial", 'B', 8); pdf.cell(0, 5, "CONDIZIONI GENERALI DI NOLEGGIO (ARTT. 1341-1342 C.C.)", ln=1)
        pdf.set_font("Arial", size=7)
        clausole = (
            "1. Il cliente dichiara di aver ricevuto il veicolo in ottimo stato.\n"
            "2. RESPONSABILITA: Il conducente e responsabile per danni, furto e contravvenzioni.\n"
            "3. DIVIETI: Vietata la guida a terzi non autorizzati.\n"
            "4. PRIVACY: Si autorizza il trattamento dati e la foto della patente ai sensi del GDPR.\n"
            "5. Clausola vessatoria: Il cliente accetta specificamente gli artt. 1341 e 1342 c.c."
        )
        pdf.multi_cell(0, 4, txt=clean_t(clausole), border='T')
        pdf.ln(10); pdf.set_font("Arial", 'B', 10); pdf.cell(0, 10, "Firma del Cliente: ______________________", align='R')
    
    elif tipo == "VIGILI":
        pdf.ln(10); pdf.set_font("Arial", size=11)
        testo_v = "Si dichiara che nella data indicata il veicolo era affidato al soggetto sopra identificato."
        pdf.multi_cell(0, 7, txt=clean_t(testo_v))

    return pdf.output(dest='S').encode('latin-1')

# --- APP STREAMLIT ---
st.set_page_config(page_title="MasterRent - Gestione", layout="centered")
st.title("🛵 MasterRent Ischia")
st.caption(INTESTAZIONE_TXT.split("\n")[0])

menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Noleggio", "🗄️ Archivio", "🚨 Gestione Multe"])

if menu == "📝 Nuovo Noleggio":
    with st.form("checkin_form"):
        st.subheader("Registrazione Cliente")
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome e Cognome")
        cf = c2.text_input("Codice Fiscale")
        nascita = c1.text_input("Luogo e Data Nascita")
        residenza = c2.text_input("Residenza")
        num_doc = c1.text_input("Numero Patente")
        scadenza = c2.date_input("Scadenza Patente")
        targa = c1.text_input("TARGA").upper()
        prezzo = c2.number_input("Prezzo Totale (€)", min_value=0.0)
        telefono = st.text_input("Cellulare Cliente (per WhatsApp)", help="Es: 393331234567")
        
        # Area Informativa Privacy
        st.info("*INFORMATIVA PRIVACY & CONDIZIONI LEGALI*\n\nIl cliente noleggiatore dichiara di essere maggiorenne e responsabile del veicolo. Ai sensi degli artt. 1341-1342 c.c. accetta la responsabilità per danni, furto e sanzioni amministrative. Autorizza la conservazione della foto patente per obblighi di legge.")
        
        foto = st.camera_input("📸 Foto Patente")
        st.write("✍️ *Firma Digitale*")
        st_canvas(fill_color="white", stroke_width=2, height=150, key="canvas_v11")
        
        if st.form_submit_button("💾 SALVA E GENERA"):
            fn = f"{targa}_{int(time.time())}.jpg"
            if foto: supabase.storage.from_(BUCKET_NAME).upload(fn, foto.getvalue())
            
            dat = {"cliente": nome, "cf": cf, "luogo_nascita": nascita, "residenza": residenza, 
                   "num_doc": num_doc, "scadenza_patente": str(scadenza), "targa": targa, 
                   "prezzo": prezzo, "data_inizio": str(datetime.date.today()), "foto_path": fn if foto else None}
            supabase.table("contratti").insert(dat).execute()
            st.success("Noleggio Archiviato!")

elif menu == "🗄️ Archivio":
    st.header("🗄️ Archivio Contratti")
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"📄 {c['cliente']} - {c['targa']}"):
            col1, col2, col3, col4 = st.columns([1,1,1,1.5])
            col1.download_button("📜 Contratto", genera_pdf_completo(c, "CONTRATTO"), f"Contratto_{c['targa']}.pdf")
            col2.download_button("💰 Fattura", genera_pdf_completo(c, "FATTURA"), f"Fattura_{c['id']}.pdf")
            
            if c.get("foto_path"):
                u = supabase.storage.from_(BUCKET_NAME).get_public_url(c["foto_path"])
                col3.link_button("📸 Foto", u)
            
            # Tasto WhatsApp
            msg = f"Ciao {c['cliente']}, ecco il riepilogo del tuo noleggio MasterRent.\nTarga: {c['targa']}\nPrezzo: {c['prezzo']}€\nBuon viaggio a Ischia!"
            msg_enc = urllib.parse.quote(msg)
            col4.link_button("💬 Invia WhatsApp", f"https://wa.me/?text={msg_enc}")

elif menu == "🚨 Gestione Multe":
    st.header("🚨 Modulo per i Vigili")
    t_m = st.text_input("Inserisci Targa da ricercare").upper()
    if t_m:
        res_m = supabase.table("contratti").select("*").eq("targa", t_m).execute()
        if res_m.data:
            st.success(f"Trovato noleggio per: {res_m.data[0]['cliente']}")
            st.download_button("📥 Scarica Modulo Vigili", genera_pdf_completo(res_m.data[0], "VIGILI"), f"Modulo_Vigili_{t_m}.pdf")
        else: st.error("Nessun noleggio trovato per questa targa.")
