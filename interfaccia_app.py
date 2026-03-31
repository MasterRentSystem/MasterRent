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

# INTESTAZIONE AZIENDALE COMPLETA
INTESTAZIONE_DITTA = "MASTERRENT DI MARIANNA BATTAGLIA\nVia Cognole 5 - 80075 Forio (NA)\nC.F.: BTTMNN87A53Z112S | P.IVA: 10252601215\nTel: +39 081 XXX XXXX | Email: info@masterrentischia.it"

def clean_t(text):
    if not text or text == "None": return "---"
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in repls.items(): text = str(text).replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

# --- GENERATORE PDF PROFESSIONALE ---
def genera_pdf_pro(c, tipo="CONTRATTO"):
    pdf = fpdf.FPDF()
    pdf.add_page()
    
    # Intestazione con bordo
    pdf.set_font("Arial", 'B', 10); pdf.set_fill_color(245, 245, 245)
    pdf.multi_cell(0, 5, txt=clean_t(INTESTAZIONE_DITTA), border=1, align='L', fill=True)
    pdf.ln(10)
    
    # Titolo
    pdf.set_font("Arial", 'B', 16)
    titolo = "CONTRATTO DI NOLEGGIO" if tipo == "CONTRATTO" else "RICEVUTA DI PAGAMENTO"
    if tipo == "VIGILI": titolo = "DICHIARAZIONE DATI CONDUCENTE"
    pdf.cell(0, 10, clean_t(titolo), ln=1, align='C')
    pdf.ln(5)
    
    # Tabella Dati Cliente
    pdf.set_font("Arial", 'B', 9); pdf.cell(0, 7, "DATI DEL CONDUCENTE", ln=1)
    pdf.set_font("Arial", size=9)
    pdf.cell(95, 8, clean_t(f"CLIENTE: {c.get('cliente')}"), border=1)
    pdf.cell(95, 8, clean_t(f"C.F.: {c.get('cf')}"), border=1, ln=1)
    pdf.cell(190, 8, clean_t(f"RESIDENZA: {c.get('residenza')}"), border=1, ln=1)
    pdf.cell(95, 8, clean_t(f"PATENTE N.: {c.get('num_doc')}"), border=1)
    pdf.cell(95, 8, clean_t(f"SCADENZA: {c.get('scadenza_patente')}"), border=1, ln=1)
    pdf.ln(3)

    # Tabella Dati Noleggio
    pdf.set_font("Arial", 'B', 9); pdf.cell(0, 7, "DETTAGLI NOLEGGIO", ln=1)
    pdf.set_font("Arial", size=9)
    pdf.cell(60, 8, clean_t(f"TARGA: {c.get('targa')}"), border=1)
    pdf.cell(65, 8, clean_t(f"INIZIO: {c.get('data_inizio')}"), border=1)
    pdf.cell(65, 8, clean_t(f"FINE: {c.get('data_fine')}"), border=1, ln=1)
    pdf.cell(190, 8, clean_t(f"CORRISPETTIVO TOTALE: {c.get('prezzo', 0)} EURO"), border=1, ln=1, fill=True)
    
    if tipo == "CONTRATTO":
        pdf.ln(5); pdf.set_font("Arial", 'B', 8); pdf.cell(0, 5, "CONDIZIONI GENERALI E PRIVACY (Art. 1341-1342 c.c.)", ln=1)
        pdf.set_font("Arial", size=7)
        clausole = (
            "Il locatario dichiara di aver visionato il veicolo e di trovarlo in ottimo stato. Si impegna a restituirlo nelle medesime condizioni.\n"
            "- RESPONSABILITA: Il cliente e responsabile per danni meccanici, carrozzeria, furto totale o parziale e incendio.\n"
            "- SANZIONI: Ogni multa o infrazione al C.d.S. occorsa durante il periodo di noleggio e a carico del cliente.\n"
            "- PRIVACY: Il cliente autorizza MasterRent alla conservazione dei dati e della foto della patente per obblighi di legge (GDPR).\n"
            "- FIRMA: Con la firma il cliente accetta specificamente le clausole limitative della responsabilita e le penali previste."
        )
        pdf.multi_cell(0, 4, txt=clean_t(clausole), border='T')
        pdf.ln(15); pdf.set_font("Arial", 'B', 10); pdf.cell(0, 10, "Firma del Cliente (Digitale): ______________________", align='R')
    
    return pdf.output(dest='S').encode('latin-1')

# --- APP INTERFACCIA ---
st.set_page_config(page_title="MasterRent Ischia", layout="centered")
st.sidebar.title("🚀 MasterRent")
menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Noleggio", "🗄️ Archivio", "🚨 Multe"])

if menu == "📝 Nuovo Noleggio":
    st.header("Registrazione Noleggio")
    with st.form("form_v13", clear_on_submit=True):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome e Cognome Cliente")
        cf = c2.text_input("Codice Fiscale")
        residenza = st.text_input("Indirizzo Residenza")
        
        c3, c4 = st.columns(2)
        num_pat = c3.text_input("Numero Patente")
        scadenza_p = c4.date_input("Scadenza Patente", datetime.date.today())
        
        c5, c6 = st.columns(2)
        targa = c5.text_input("TARGA VEICOLO").upper()
        prezzo = c6.number_input("Prezzo Totale (€)", min_value=0.0)
        
        # DATE NOLEGGIO
        st.subheader("Periodo di Noleggio")
        d1, d2 = st.columns(2)
        data_ini = d1.date_input("Data Inizio", datetime.date.today())
        data_fin = d2.date_input("Data Fine", datetime.date.today() + datetime.timedelta(days=1))
        
        st.warning("*INFORMATIVA:* Il cliente si assume ogni responsabilità per danni, furto e multe. Accetta il trattamento dei dati e la ripresa fotografica della patente ai sensi del GDPR e degli artt. 1341-1342 c.c.")
        
        foto = st.camera_input("📸 Scatta Foto Patente")
        st.write("✍️ *Firma per Accettazione*")
        st_canvas(fill_color="white", stroke_width=2, height=150, key="canvas_v13")
        
        if st.form_submit_button("💾 SALVA ED EMETTI CONTRATTO"):
            fn = f"{targa}_{int(time.time())}.jpg"
            if foto: supabase.storage.from_(BUCKET_NAME).upload(fn, foto.getvalue())
            
            dat = {
                "cliente": nome, "cf": cf, "residenza": residenza, "num_doc": num_pat,
                "scadenza_patente": str(scadenza_p), "targa": targa, "prezzo": prezzo,
                "data_inizio": str(data_ini), "data_fine": str(data_fin), "foto_path": fn if foto else None
            }
            supabase.table("contratti").insert(dat).execute()
            st.success(f"Contratto creato per {nome} (Targa: {targa})")

elif menu == "🗄️ Archivio":
    st.header("🗄️ Archivio Contratti")
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"📄 {c['cliente']} | {c['targa']} | {c['data_inizio']}"):
            col1, col2, col3, col4 = st.columns([1,1,1,1.5])
            col1.download_button("📜 Contratto", genera_pdf_pro(c, "CONTRATTO"), f"C_{c['targa']}.pdf")
            col2.download_button("💰 Ricevuta", genera_pdf_pro(c, "FATTURA"), f"R_{c['id']}.pdf")
            if c.get("foto_path"):
                u = supabase.storage.from_(BUCKET_NAME).get_public_url(c["foto_path"])
                col3.link_button("📸 Foto", u)
            
            msg = urllib.parse.quote(f"Ciao {c['cliente']}, MasterRent ti invia il riepilogo noleggio Targa {c['targa']}. Dal {c['data_inizio']} al {c['data_fine']}. Grazie!")
            col4.link_button("💬 WhatsApp", f"https://wa.me/?text={msg}")

elif menu == "🚨 Multe":
    st.header("🚨 Gestione Multe")
    t_m = st.text_input("Inserisci Targa").upper()
    if t_m:
        res_m = supabase.table("contratti").select("*").eq("targa", t_m).execute()
        if res_m.data:
            st.success(f"Noleggiatore trovato: {res_m.data[0]['cliente']}")
            st.download_button("📥 Genera PDF per Vigili", genera_pdf_pro(res_m.data[0], "VIGILI"), f"Multe_{t_m}.pdf")
