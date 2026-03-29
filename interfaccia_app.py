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
    if not text: return ""
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in repls.items(): text = text.replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

INFO_AZIENDA = "BATTAGLIA MARIANNA\nVia Cognole n. 5, Forio (NA)\nC.F.: BTTMNN87A53Z112S | P.IVA: 10252601215"

# --- GENERAZIONE PDF ---

def genera_contratto(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 10); pdf.multi_cell(0, 5, txt=clean_t(INFO_AZIENDA))
    pdf.ln(10); pdf.set_font("Arial", 'B', 16); pdf.cell(0, 10, clean_t("CONTRATTO DI NOLEGGIO"), ln=1, align='C')
    pdf.set_font("Arial", size=11)
    testo = (f"CLIENTE: {c['cliente']}\nC.F.: {c.get('cf','')}\nNATO A: {c.get('luogo_nascita','')}\n"
             f"RESIDENZA: {c.get('residenza','')}\nPATENTE: {c.get('num_doc','')}\n\n"
             f"VEICOLO: {c['targa']}\nDAL: {c.get('data_inizio','')} AL: {c.get('data_fine','')}\n"
             f"PREZZO: {c.get('prezzo', 0)} Euro")
    pdf.multi_cell(0, 8, txt=clean_t(testo))
    pdf.ln(10); pdf.set_font("Arial", 'B', 9); pdf.cell(0, 5, "NOTE LEGALI E PRIVACY", ln=1)
    pdf.set_font("Arial", size=8); pdf.multi_cell(0, 4, txt=clean_t("Il cliente approva le clausole (Art 3, 5, 13) e presta il consenso al trattamento dati (GDPR)."))
    return pdf.output(dest='S').encode('latin-1')

def genera_fattura(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 10); pdf.multi_cell(0, 5, txt=clean_t(INFO_AZIENDA))
    pdf.ln(10); pdf.set_font("Arial", 'B', 16); pdf.cell(0, 10, "FATTURA / RICEVUTA", ln=1, align='C')
    pdf.set_font("Arial", size=11)
    testo = f"CLIENTE: {c['cliente']}\nCF/PIVA: {c.get('cf','')}\nIMPORTO: {c.get('prezzo', 0)} Euro\nVEICOLO: {c['targa']}"
    pdf.multi_cell(0, 8, txt=clean_t(testo))
    return pdf.output(dest='S').encode('latin-1')

def genera_modulo_vigili(c, data_multa):
    pdf = fpdf.FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 10); pdf.multi_cell(0, 5, txt=clean_t(INFO_AZIENDA))
    pdf.ln(10); pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, clean_t("COMUNICAZIONE DATI CONDUCENTE (VIGILI)"), ln=1, align='C')
    pdf.set_font("Arial", size=11)
    testo = (f"In relazione all'infrazione del {data_multa}, si comunica che il veicolo {c['targa']}\n"
             f"era in uso a:\n\nCONDUCENTE: {c['cliente']}\nC.F.: {c.get('cf','')}\n"
             f"NATO A: {c.get('luogo_nascita','')}\nRESIDENZA: {c.get('residenza','')}\n"
             f"PATENTE: {c.get('num_doc','')}")
    pdf.multi_cell(0, 8, txt=clean_t(testo))
    pdf.ln(20); pdf.cell(0, 10, "In fede, Marianna Battaglia", align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- APP STREAMLIT ---

st.sidebar.title("🚀 MasterRent Ischia")
menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Noleggio", "🗄️ Archivio Documenti"])

if menu == "📝 Nuovo Noleggio":
    st.header("Registrazione Contratto")
    col1, col2 = st.columns(2)
    cliente = col1.text_input("Nome e Cognome")
    cf = col2.text_input("Codice Fiscale")
    nascita = col1.text_input("Luogo/Data Nascita")
    residenza = col2.text_input("Indirizzo Residenza")
    num_doc = col1.text_input("Numero Patente")
    tel = col2.text_input("Cellulare")
    targa = col1.text_input("TARGA").upper()
    prezzo = col2.number_input("Prezzo (€)", min_value=0.0)
    d_ini = col1.date_input("Inizio", datetime.date.today())
    d_fin = col2.date_input("Fine", datetime.date.today() + datetime.timedelta(days=1))
    
    st.camera_input("📸 Foto Patente")
    st_canvas(fill_color="white", stroke_width=2, height=150, key="sig_v_new")

    if st.button("💾 SALVA"):
        dat = {"cliente": cliente, "cf": cf, "luogo_nascita": nascita, "residenza": residenza, 
               "num_doc": num_doc, "telefono": tel, "targa": targa, "prezzo": prezzo, 
               "data_inizio": str(d_ini), "data_fine": str(d_fin)}
        supabase.table("contratti").insert(dat).execute()
        st.success("Archiviato!")

elif menu == "🗄️ Archivio Documenti":
    st.header("🗄️ Archivio Contratti e Fatture")
    
    # --- SEZIONE RICERCA VIGILI ---
    st.subheader("🚨 Modulo per i Vigili")
    r1, r2 = st.columns(2)
    t_vigili = r1.text_input("Targa Infrazione").upper()
    d_vigili = r2.date_input("Data Infrazione")
    
    if t_vigili:
        # Cerchiamo il noleggio che copre quella data per quella targa
        res_v = supabase.table("contratti").select("*").eq("targa", t_vigili).lte("data_inizio", str(d_vigili)).gte("data_fine", str(d_vigili)).execute()
        if res_v.data:
            c_v = res_v.data[0]
            pdf_v = genera_modulo_vigili(c_v, d_vigili)
            st.download_button(f"🚨 SCARICA MODULO VIGILI ({c_v['cliente']})", pdf_v, f"Modulo_Vigili_{t_vigili}.pdf")
        else:
            st.info("Nessun noleggio attivo trovato per questa targa in quella data.")

    st.divider()

    # --- TABELLA ARCHIVIO GENERALE ---
    res = supabase.table("contratti").select("*").order("data_inizio", desc=True).execute()
    if res.data:
        # Intestazione Colonne
        h1, h2, h3, h4 = st.columns([2, 1, 1, 1])
        h1.write("*Cliente*")
        h2.write("*Contratto*")
        h3.write("*Fattura*")
        h4.write("*Foto*")
        
        for c in res.data:
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            c1.write(f"{c['cliente']}\n({c['targa']})")
            
            # Tasto Contratto
            pdf_c = genera_contratto(c)
            c2.download_button("📜 PDF", pdf_c, f"Contratto_{c['targa']}.pdf", key=f"c_{c['id']}")
            
            # Tasto Fattura
            pdf_f = genera_fattura(c)
            c3.download_button("💰 PDF", pdf_f, f"Fattura_{c['id']}.pdf", key=f"f_{c['id']}")
            
            # Tasto Foto (Simulato link o visualizzazione)
            c4.button("📸 Vedi", key=f"p_{c['id']}")
    else:
        st.write("L'archivio è vuoto.")

