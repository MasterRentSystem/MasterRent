import streamlit as st
import datetime
import fpdf
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
import urllib.parse

# 1. CONNESSIONE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def clean_t(text):
    if not text: return "---"
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in repls.items(): text = str(text).replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

INFO_AZIENDA = "BATTAGLIA MARIANNA\nVia Cognole n. 5, Forio (NA)\nC.F.: BTTMNN87A53Z112S | P.IVA: 10252601215"

# --- GENERAZIONE PDF ---

def genera_pdf_contratto(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 10); pdf.multi_cell(0, 5, txt=clean_t(INFO_AZIENDA))
    pdf.ln(8); pdf.set_font("Arial", 'B', 16); pdf.cell(0, 10, clean_t("CONTRATTO DI NOLEGGIO"), ln=1, align='C')
    pdf.ln(5); pdf.set_font("Arial", size=10)
    
    testo = (f"CLIENTE: {clean_t(c.get('cliente'))}\nC.F.: {clean_t(c.get('cf'))}\n"
             f"NATO A: {clean_t(c.get('luogo_nascita'))}\nRESIDENZA: {clean_t(c.get('residenza'))}\n"
             f"PATENTE: {clean_t(c.get('num_doc'))} | SCADENZA: {clean_t(c.get('scadenza_patente'))}\n\n"
             f"VEICOLO: {clean_t(c.get('targa'))}\nPERIODO: dal {c.get('data_inizio')} al {c.get('data_fine')}\n"
             f"PREZZO: {c.get('prezzo', 0)} Euro")
    pdf.multi_cell(0, 7, txt=testo, border=1)
    
    pdf.ln(5); pdf.set_font("Arial", 'B', 8); pdf.cell(0, 5, "NOTE LEGALI E PRIVACY (GDPR)", ln=1)
    pdf.set_font("Arial", size=7)
    legale = ("Il cliente dichiara di aver ricevuto il veicolo in ottimo stato. Si assume ogni responsabilita civile e penale per infrazioni al CdS. "
              "AUTORIZZAZIONE DOCUMENTI: Il cliente autorizza espressamente la copia fotografica del documento di identita/patente "
              "ai sensi del Reg. UE 2016/679 esclusivamente per fini di Pubblica Sicurezza e gestione contrattuale.")
    pdf.multi_cell(0, 4, txt=clean_t(legale))
    pdf.ln(15); pdf.cell(0, 10, clean_t("Firma del Cliente (acquisita digitalmente): ________________________"))
    return pdf.output(dest='S').encode('latin-1')

def genera_pdf_fattura(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 10); pdf.multi_cell(0, 5, txt=clean_t(INFO_AZIENDA))
    pdf.ln(10); pdf.set_font("Arial", 'B', 16); pdf.cell(0, 10, "FATTURA / RICEVUTA", ln=1, align='C')
    pdf.ln(10); pdf.set_font("Arial", size=12)
    testo = f"Spett.le: {clean_t(c.get('cliente'))}\nC.F.: {clean_t(c.get('cf'))}\n\nNoleggio Veicolo: {c.get('targa')}\nPeriodo: {c.get('data_inizio')} / {c.get('data_fine')}\n\nTOTALE PAGATO: {c.get('prezzo', 0)} Euro"
    pdf.multi_cell(0, 10, txt=testo)
    return pdf.output(dest='S').encode('latin-1')

def genera_pdf_vigili(c, data_m):
    pdf = fpdf.FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 10); pdf.multi_cell(0, 5, txt=clean_t(INFO_AZIENDA))
    pdf.ln(10); pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, clean_t("COMUNICAZIONE DATI CONDUCENTE"), ln=1, align='C')
    pdf.ln(10); pdf.set_font("Arial", size=11)
    testo = (f"In merito all'infrazione del {data_m}, si dichiara che il veicolo {c['targa']}\nera locato al sig.:\n\n"
             f"NOME: {clean_t(c['cliente'])}\nC.F.: {clean_t(c['cf'])}\nNATO A: {clean_t(c['luogo_nascita'])}\n"
             f"RESIDENZA: {clean_t(c['residenza'])}\nPATENTE: {clean_t(c['num_doc'])}")
    pdf.multi_cell(0, 8, txt=testo)
    pdf.ln(20); pdf.cell(0, 10, "In fede, Marianna Battaglia", align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACCIA ---

st.sidebar.title("🚀 MasterRent Ischia")
menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Noleggio", "🗄️ Archivio Documenti"])

if menu == "📝 Nuovo Noleggio":
    st.header("Nuovo Noleggio")
    c1, c2 = st.columns(2)
    cliente = c1.text_input("Nome e Cognome")
    cf = c2.text_input("Codice Fiscale")
    nascita = c1.text_input("Luogo e Data Nascita")
    residenza = c2.text_input("Residenza")
    num_doc = c1.text_input("Numero Patente")
    scadenza = c2.date_input("Scadenza Patente")
    targa = c1.text_input("TARGA").upper()
    prezzo = c2.number_input("Prezzo (€)", min_value=0.0)
    d_ini = c1.date_input("Inizio", datetime.date.today())
    d_fin = c2.date_input("Fine", datetime.date.today() + datetime.timedelta(days=1))
    tel = c1.text_input("Telefono")

    st.camera_input("📸 Foto Patente")
    st_canvas(fill_color="white", stroke_width=2, height=150, key="sig_final")

    if st.button("💾 SALVA ED ARCHIVIA"):
        if cliente and targa:
            dat = {"cliente": cliente, "cf": cf, "luogo_nascita": nascita, "residenza": residenza, 
                   "num_doc": num_doc, "scadenza_patente": str(scadenza), "targa": targa, 
                   "prezzo": prezzo, "data_inizio": str(d_ini), "data_fine": str(d_fin), "telefono": tel}
            supabase.table("contratti").insert(dat).execute()
            st.success("Tutto salvato! Vai in Archivio.")
        else: st.warning("Compila i campi obbligatori.")

elif menu == "🗄️ Archivio Documenti":
    st.header("🗄️ Archivio Contratti e Fatture")
    
    with st.expander("🚨 Genera Modulo per i Vigili (Ricerca Infrazione)"):
        r1, r2 = st.columns(2)
        t_m = r1.text_input("Targa Multa").upper()
        d_m = r2.date_input("Data Multa")
        if t_m:
            res_m = supabase.table("contratti").select("*").eq("targa", t_m).lte("data_inizio", str(d_m)).gte("data_fine", str(d_m)).execute()
            if res_m.data:
                pdf_m = genera_pdf_vigili(res_m.data[0], d_m)
                st.download_button(f"📥 Scarica Modulo per {res_m.data[0]['cliente']}", pdf_m, f"Multe_{t_m}.pdf")
            else: st.info("Nessun cliente trovato per questa data.")

    st.divider()
    res = supabase.table("contratti").select("*").order("data_inizio", desc=True).execute()
    if res.data:
        h1, h2, h3, h4 = st.columns([2, 1, 1, 1])
        h1.write("*CLIENTE / TARGA"); h2.write("CONTRATTO"); h3.write("FATTURA"); h4.write("FOTO*")
        
        for c in res.data:
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            c1.write(f"*{c['cliente']}*\n{c['targa']}")
            c2.download_button("📜 PDF", genera_pdf_contratto(c), f"Contratto_{c['targa']}.pdf", key=f"c_{c['id']}")
            c3.download_button("💰 PDF", genera_pdf_fattura(c), f"Fattura_{c['id']}.pdf", key=f"f_{c['id']}")
            c4.button("📸 Vedi", key=f"p_{c['id']}")
