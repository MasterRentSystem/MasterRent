import streamlit as st
import datetime
import fpdf
from supabase import create_client
from streamlit_drawable_canvas import st_canvas

# 1. CONNESSIONE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def clean_t(text):
    if not text: return "---"
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in repls.items(): text = str(text).replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

# DATI AZIENDA
INTESTAZIONE = "MASTERRENT DI MARIANNA BATTAGLIA\nVia Cognole n. 5 - 80075 Forio (NA)\nC.F.: BTTMNN87A53Z112S | P.IVA: 10252601215"

def genera_pdf_professionale(c, tipo="CONTRATTO"):
    pdf = fpdf.FPDF()
    pdf.add_page()
    
    # Intestazione con linea
    pdf.set_font("Arial", 'B', 12)
    pdf.multi_cell(0, 6, txt=clean_t(INTESTAZIONE), align='L')
    pdf.line(10, 32, 200, 32)
    pdf.ln(12)
    
    # Titolo Documento
    pdf.set_font("Arial", 'B', 18)
    titolo = "CONTRATTO DI NOLEGGIO" if tipo == "CONTRATTO" else "FATTURA / RICEVUTA"
    pdf.cell(0, 10, clean_t(titolo), ln=1, align='C')
    pdf.ln(5)
    
    # Sezione Dati Cliente (Riquadro)
    pdf.set_font("Arial", 'B', 10); pdf.cell(0, 8, "DATI DEL CONDUCENTE", ln=1)
    pdf.set_font("Arial", size=10)
    pdf.set_fill_color(240, 240, 240)
    dati_c = (f"Nome: {clean_t(c.get('cliente'))}  |  CF: {clean_t(c.get('cf'))}\n"
              f"Nato a: {clean_t(c.get('luogo_nascita'))}\n"
              f"Residenza: {clean_t(c.get('residenza'))}\n"
              f"Patente: {clean_t(c.get('num_doc'))}  |  Scadenza: {clean_t(c.get('scadenza_patente'))}")
    pdf.multi_cell(0, 7, txt=dati_c, border=1, fill=True)
    pdf.ln(5)
    
    # Sezione Veicolo e Periodo
    pdf.set_font("Arial", 'B', 10); pdf.cell(0, 8, "DETTAGLI NOLEGGIO", ln=1)
    pdf.set_font("Arial", size=10)
    dati_v = (f"TARGA VEICOLO: {clean_t(c.get('targa'))}\n"
              f"PERIODO: dal {c.get('data_inizio')} al {c.get('data_fine')}\n"
              f"PREZZO TOTALE: {c.get('prezzo', 0)} Euro")
    pdf.multi_cell(0, 7, txt=dati_v, border=1)
    
    if tipo == "CONTRATTO":
        # Clausole Legali
        pdf.ln(5); pdf.set_font("Arial", 'B', 9); pdf.cell(0, 5, clean_t("INFORMATIVA PRIVACY E CONDIZIONI"), ln=1)
        pdf.set_font("Arial", size=7.5)
        clausole = (
            "1. Il cliente dichiara di essere l'unico conducente e di aver verificato l'efficienza del mezzo.\n"
            "2. Responsabilita: Il cliente risponde di ogni sanzione amministrativa (multe) durante il noleggio.\n"
            "3. Privacy: Si autorizza il trattamento dati (GDPR) e la riproduzione fotografica del documento per fini di Pubblica Sicurezza.\n"
            "4. Ai sensi degli artt. 1341-1342 c.c. si accettano specificamente i punti 1, 2 e 3."
        )
        pdf.multi_cell(0, 4, txt=clean_t(clausole))
        
        # Area Firma
        pdf.ln(15)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 10, clean_t("Firma del Cliente per Accettazione"), ln=1, align='R')
        pdf.cell(0, 5, "__________________________________", ln=1, align='R')
        pdf.set_font("Arial", 'I', 7)
        pdf.cell(0, 5, clean_t("Acquisita digitalmente tramite piattaforma MasterRent"), ln=1, align='R')

    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACCIA APP ---

st.sidebar.title("🚀 MasterRent")
menu = st.sidebar.radio("Menu", ["📝 Nuovo Noleggio", "🗄️ Archivio"])

if menu == "📝 Nuovo Noleggio":
    st.header("Compilazione Contratto")
    with st.container():
        c1, c2 = st.columns(2)
        cliente = c1.text_input("Nome e Cognome")
        cf = c2.text_input("Codice Fiscale")
        nascita = c1.text_input("Luogo e Data Nascita")
        residenza = c2.text_input("Indirizzo Residenza")
        num_doc = c1.text_input("Num. Patente")
        scadenza = c2.date_input("Scadenza Patente")
        
        st.divider()
        targa = c1.text_input("TARGA").upper()
        prezzo = c2.number_input("Prezzo Totale (€)", min_value=0.0)
        d_ini = c1.date_input("Inizio", datetime.date.today())
        d_fin = c2.date_input("Fine", datetime.date.today() + datetime.timedelta(days=1))
        
        st.camera_input("📸 Foto Patente")
        st.write("✍️ *Firma qui sotto*")
        st_canvas(fill_color="white", stroke_width=2, height=150, key="firma_v3")

    if st.button("💾 GENERA E SALVA"):
        if cliente and targa:
            dat = {"cliente": cliente, "cf": cf, "luogo_nascita": nascita, "residenza": residenza, 
                   "num_doc": num_doc, "scadenza_patente": str(scadenza), "targa": targa, 
                   "prezzo": prezzo, "data_inizio": str(d_ini), "data_fine": str(d_fin)}
            supabase.table("contratti").insert(dat).execute()
            st.success("Contratto creato! Vai in Archivio per scaricarlo.")
        else: st.error("Mancano dati obbligatori!")

elif menu == "🗄️ Archivio":
    st.header("Ricerca Documenti")
    res = supabase.table("contratti").select("*").order("data_inizio", desc=True).execute()
    if res.data:
        for c in res.data:
            with st.expander(f"📂 {c['cliente']} ({c['targa']}) - {c['data_inizio']}"):
                col1, col2 = st.columns(2)
                col1.download_button("📄 SCARICA CONTRATTO", genera_pdf_professionale(c, "CONTRATTO"), f"Contratto_{c['targa']}.pdf")
                col2.download_button("💰 SCARICA FATTURA", genera_pdf_professionale(c, "FATTURA"), f"Fattura_{c['id']}.pdf")
