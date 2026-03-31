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

# DATI FISSI INTESTAZIONE
INTESTAZIONE = "MASTERRENT DI MARIANNA BATTAGLIA\nVia Cognole n. 5, 80075 Forio (NA)\nC.F.: BTTMNN87A53Z112S | P.IVA: 10252601215\nTel: +39 333 1234567"

# --- FUNZIONI PDF ---

def genera_pdf_contratto(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 10); pdf.multi_cell(0, 5, txt=clean_t(INTESTAZIONE))
    pdf.ln(10); pdf.set_font("Arial", 'B', 16); pdf.cell(0, 10, clean_t("CONTRATTO DI NOLEGGIO"), ln=1, align='C')
    pdf.ln(5); pdf.set_font("Arial", size=10)
    
    testo = (f"CLIENTE: {clean_t(c.get('cliente'))}\nC.F.: {clean_t(c.get('cf'))}\n"
             f"NATO A: {clean_t(c.get('luogo_nascita'))}\nRESIDENZA: {clean_t(c.get('residenza'))}\n"
             f"PATENTE: {clean_t(c.get('num_doc'))} | SCADENZA: {clean_t(c.get('scadenza_patente'))}\n\n"
             f"VEICOLO: {clean_t(c.get('targa'))}\nPERIODO: dal {c.get('data_inizio')} al {c.get('data_fine')}\n"
             f"PREZZO: {c.get('prezzo', 0)} Euro")
    pdf.multi_cell(0, 7, txt=testo, border=1)
    
    pdf.ln(5); pdf.set_font("Arial", 'B', 8); pdf.cell(0, 5, clean_t("CLAUSOLE E PRIVACY (ACCETTATE AL MOMENTO DELLA FIRMA)"), ln=1)
    pdf.set_font("Arial", size=7.5)
    clausole = ("Il cliente dichiara di aver preso visione del mezzo. E responsabile per multe e danni. "
                "AUTORIZZAZIONE FOTO: Il cliente autorizza la copia fotografica del documento per fini di Pubblica Sicurezza (GDPR). "
                "Ai sensi degli artt. 1341-1342 c.c. si approvano specificamente le clausole su Multe e Danni.")
    pdf.multi_cell(0, 4, txt=clean_t(clausole))
    pdf.ln(15); pdf.cell(0, 10, clean_t("Firma del Cliente (Acquisita Digitalmente): ________________________"))
    return pdf.output(dest='S').encode('latin-1')

def genera_pdf_fattura(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 10); pdf.multi_cell(0, 5, txt=clean_t(INTESTAZIONE))
    pdf.ln(15); pdf.set_font("Arial", 'B', 16); pdf.cell(0, 10, "FATTURA / RICEVUTA", ln=1, align='C')
    pdf.ln(10); pdf.set_font("Arial", size=12)
    testo = f"Spett.le: {clean_t(c.get('cliente'))}\nC.F.: {clean_t(c.get('cf'))}\n\nDescrizione: Noleggio {c.get('targa')}\nPeriodo: {c.get('data_inizio')} - {c.get('data_fine')}\n\nTOTALE: {c.get('prezzo', 0)} Euro"
    pdf.multi_cell(0, 10, txt=testo)
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACCIA ---

st.sidebar.title("🚀 MasterRent")
menu = st.sidebar.radio("Menu", ["📝 Nuovo Noleggio", "🗄️ Archivio Documenti"])

if menu == "📝 Nuovo Noleggio":
    st.header("Nuovo Noleggio")
    c1, c2 = st.columns(2)
    cliente = c1.text_input("Nome e Cognome")
    cf = c2.text_input("Codice Fiscale")
    nascita = c1.text_input("Luogo/Data Nascita")
    residenza = c2.text_input("Residenza")
    num_doc = c1.text_input("Num. Patente")
    scadenza = c2.date_input("Scadenza Patente")
    targa = c1.text_input("TARGA").upper()
    prezzo = c2.number_input("Prezzo (€)", min_value=0.0)
    d_ini = c1.date_input("Inizio", datetime.date.today())
    d_fin = c2.date_input("Fine", datetime.date.today() + datetime.timedelta(days=1))
    
    img_patente = st.camera_input("📸 Foto Patente (Obbligatoria per Legge)")
    
    st.write("---")
    st.warning("⚠️ *INFORMATIVA*: Firmando qui sotto accetti le clausole su Multe, Danni e autorizzi la foto del documento per Pubblica Sicurezza.")
    canvas_result = st_canvas(fill_color="white", stroke_width=2, height=150, key="firma_new")

    if st.button("💾 SALVA E ARCHIVIA"):
        if cliente and targa:
            dat = {"cliente": cliente, "cf": cf, "luogo_nascita": nascita, "residenza": residenza, 
                   "num_doc": num_doc, "scadenza_patente": str(scadenza), "targa": targa, 
                   "prezzo": prezzo, "data_inizio": str(d_ini), "data_fine": str(d_fin)}
            supabase.table("contratti").insert(dat).execute()
            st.success("Contratto Salvato!")
        else: st.error("Mancano dati obbligatori!")

elif menu == "🗄️ Archivio Documenti":
    st.header("🗄️ Archivio")
    res = supabase.table("contratti").select("*").order("data_inizio", desc=True).execute()
    if res.data:
        h1, h2, h3, h4 = st.columns([2, 1, 1, 1])
        h1.write("*CLIENTE"); h2.write("CONTRATTO"); h3.write("FATTURA"); h4.write("FOTO*")
        
        for c in res.data:
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            c1.write(f"{c['cliente']}\n{c['targa']}")
            c2.download_button("📜 PDF", genera_pdf_contratto(c), f"Contratto_{c['targa']}.pdf", key=f"c_{c['id']}")
            c3.download_button("💰 PDF", genera_pdf_fattura(c), f"Fattura_{c['id']}.pdf", key=f"f_{c['id']}")
            if c4.button("👁️ Vedi", key=f"p_{c['id']}"):
                st.info("Funzione visualizzazione foto in attivazione...")
