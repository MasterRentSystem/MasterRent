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

# --- FUNZIONI GENERAZIONE PDF (MAPPATE SULLE TUE COLONNE) ---

def genera_contratto(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 10); pdf.multi_cell(0, 5, txt=clean_t(INFO_AZIENDA))
    pdf.ln(10); pdf.set_font("Arial", 'B', 16); pdf.cell(0, 10, clean_t("CONTRATTO DI NOLEGGIO"), ln=1, align='C')
    pdf.ln(5); pdf.set_font("Arial", size=11)
    
    testo = (f"CLIENTE: {clean_t(c.get('cliente'))}\n"
             f"C.F.: {clean_t(c.get('cf'))}\n"
             f"NATO A: {clean_t(c.get('luogo_nascita'))}\n"
             f"RESIDENZA: {clean_t(c.get('residenza'))}\n"
             f"PATENTE: {clean_t(c.get('num_doc'))}\n"
             f"SCADENZA PAT.: {clean_t(c.get('scadenza_patente'))}\n\n"
             f"VEICOLO TARGA: {clean_t(c.get('targa'))}\n"
             f"PERIODO: dal {clean_t(c.get('data_inizio'))} al {clean_t(c.get('data_fine'))}\n"
             f"PREZZO: {c.get('prezzo', 0)} Euro")
    pdf.multi_cell(0, 8, txt=testo)
    pdf.ln(10); pdf.set_font("Arial", 'B', 9); pdf.cell(0, 5, "NOTE LEGALI E PRIVACY", ln=1)
    pdf.set_font("Arial", size=8); pdf.multi_cell(0, 4, txt=clean_t("Il cliente dichiara di aver preso visione del veicolo e di approvare le clausole di responsabilita per multe e danni (Art 3, 5, 13). Acconsente al trattamento dati GDPR."))
    pdf.ln(20); pdf.cell(0, 10, clean_t("Firma per accettazione: ________________________"))
    return pdf.output(dest='S').encode('latin-1')

def genera_fattura(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 10); pdf.multi_cell(0, 5, txt=clean_t(INFO_AZIENDA))
    pdf.ln(15); pdf.set_font("Arial", 'B', 16); pdf.cell(0, 10, "RICEVUTA DI PAGAMENTO", ln=1, align='C')
    pdf.ln(10); pdf.set_font("Arial", size=12)
    testo = (f"Ricevuto da: {clean_t(c.get('cliente'))}\n"
             f"Codice Fiscale: {clean_t(c.get('cf'))}\n"
             f"Per noleggio veicolo targa: {clean_t(c.get('targa'))}\n"
             f"Periodo: {clean_t(c.get('data_inizio'))} / {clean_t(c.get('data_fine'))}\n\n"
             f"TOTALE PAGATO: {c.get('prezzo', 0)} Euro")
    pdf.multi_cell(0, 10, txt=testo)
    return pdf.output(dest='S').encode('latin-1')

def genera_modulo_vigili(c, d_infrazione):
    pdf = fpdf.FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 10); pdf.multi_cell(0, 5, txt=clean_t(INFO_AZIENDA))
    pdf.ln(10); pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, clean_t("DICHIARAZIONE DATI CONDUCENTE PER INFRAZIONE"), ln=1, align='C')
    pdf.ln(10); pdf.set_font("Arial", size=11)
    testo = (f"In merito all'infrazione rilevata in data {d_infrazione},\n"
             f"si comunica che il veicolo {clean_t(c.get('targa'))} era locato a:\n\n"
             f"NOME: {clean_t(c.get('cliente'))}\n"
             f"C.F.: {clean_t(c.get('cf'))}\n"
             f"NATO A: {clean_t(c.get('luogo_nascita'))}\n"
             f"RESIDENZA: {clean_t(c.get('residenza'))}\n"
             f"PATENTE: {clean_t(c.get('num_doc'))}")
    pdf.multi_cell(0, 8, txt=testo)
    pdf.ln(20); pdf.cell(0, 10, "In fede, Marianna Battaglia", align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACCIA APP ---

st.sidebar.title("🚀 MasterRent Ischia")
menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Noleggio", "🗄️ Archivio Documenti"])

if menu == "📝 Nuovo Noleggio":
    st.header("Nuovo Noleggio")
    c1, c2 = st.columns(2)
    cliente = c1.text_input("Nome e Cognome")
    cf = c2.text_input("Codice Fiscale")
    nascita = c1.text_input("Luogo e Data Nascita")
    residenza = c2.text_input("Residenza Completa")
    num_doc = c1.text_input("Num. Patente")
    scadenza = c2.date_input("Scadenza Patente")
    tel = c1.text_input("Telefono")
    targa = c2.text_input("TARGA").upper()
    prezzo = c1.number_input("Prezzo Totale (€)", min_value=0.0)
    d_ini = c1.date_input("Data Inizio", datetime.date.today())
    d_fin = c2.date_input("Data Fine", datetime.date.today() + datetime.timedelta(days=1))
    
    st.camera_input("📸 Foto Patente")
    st_canvas(fill_color="white", stroke_width=2, height=150, key="sig_v_def")

    if st.button("💾 SALVA TUTTO"):
        if cliente and targa:
            dat = {
                "cliente": cliente, "cf": cf, "luogo_nascita": nascita, "residenza": residenza,
                "num_doc": num_doc, "scadenza_patente": str(scadenza), "telefono": tel,
                "targa": targa, "prezzo": prezzo, "data_inizio": str(d_ini), "data_fine": str(d_fin)
            }
            supabase.table("contratti").insert(dat).execute()
            st.success("Archiviato! Controlla in Archivio.")
        else:
            st.warning("Inserisci Nome e Targa!")

elif menu == "🗄️ Archivio Documenti":
    st.header("🗄️ Gestione Documentale")
    
    # Sezione Modulo Vigili
    with st.expander("🚨 Genera Modulo per i Vigili (Ricerca Rapida)"):
        r1, r2 = st.columns(2)
        t_v = r1.text_input("Targa Multa").upper()
        d_v = r2.date_input("Data della Multa")
        if st.button("Trova Cliente e Genera PDF"):
            res_v = supabase.table("contratti").select("*").eq("targa", t_v).lte("data_inizio", str(d_v)).gte("data_fine", str(d_v)).execute()
            if res_v.data:
                pdf_v = genera_modulo_vigili(res_v.data[0], d_v)
                st.download_button(f"📥 Scarica Modulo per {res_v.data[0]['cliente']}", pdf_v, f"Multe_{t_v}.pdf")
            else: st.error("Nessun noleggio trovato per questa data.")

    st.divider()

    # Tabella a Colonne
    res = supabase.table("contratti").select("*").order("data_inizio", desc=True).execute()
    if res.data:
        # Intestazione
        col_h = st.columns([2, 1, 1, 1])
        col_h[0].write("*CLIENTE / TARGA*")
        col_h[1].write("*CONTRATTO*")
        col_h[2].write("*FATTURA*")
        col_h[3].write("*FOTO*")
        
        for c in res.data:
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            c1.write(f"*{c['cliente']}*\n{c['targa']}")
            
            # Scarica Contratto
            pdf_c = genera_contratto(c)
            c2.download_button("📜 PDF", pdf_c, f"Contratto_{c['targa']}.pdf", key=f"c_{c['id']}")
            
            # Scarica Fattura
            pdf_f = genera_fattura(c)
            c3.download_button("💰 PDF", pdf_f, f"Fattura_{c['id']}.pdf", key=f"f_{c['id']}")
            
            # Foto (Anteprima o tasto)
            c4.button("📸 Vedi", key=f"p_{c['id']}")
    else:
        st.info("L'archivio è ancora vuoto.")

