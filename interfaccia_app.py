import streamlit as st
import datetime
from fpdf import FPDF
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
import time

# 1. CONNESSIONE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)
BUCKET_NAME = "DOCUMENTI_PATENTI"

def clean_t(t):
    if not t or t == "None": return "---"
    r = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in r.items(): t = str(t).replace(k, v)
    return t.encode('latin-1', 'ignore').decode('latin-1')

st.set_page_config(page_title="MasterRent Ischia", layout="wide")

menu = st.sidebar.radio("Menu", ["📝 Nuovo Noleggio", "🗄️ Archivio", "🚨 Multe"])

if menu == "📝 Nuovo Noleggio":
    st.subheader("Registrazione Nuovo Noleggio")
    with st.form("form_completo"):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Cognome e Nome")
        cf = c2.text_input("Codice Fiscale")
        nascita = c1.text_input("Luogo e Data di Nascita")
        residenza = c2.text_input("Indirizzo Residenza")
        patente = c1.text_input("Numero Patente")
        telefono = c2.text_input("Telefono")
        
        st.write("---")
        targa = c1.text_input("TARGA VEICOLO").upper()
        prezzo = c2.number_input("Prezzo Totale (€)", min_value=0.0)
        
        di = st.date_input("Data Inizio", datetime.date.today())
        df = st.date_input("Data Fine", datetime.date.today() + datetime.timedelta(days=1))
        
        st.write("---")
        accetto = st.checkbox("Accetto le Condizioni di Noleggio (1-14) e la Privacy")
        foto = st.camera_input("📸 Scansiona Patente")
        
        st.write("Firma del Cliente:")
        canvas_result = st_canvas(fill_color="white", stroke_width=2, stroke_color="black", background_color="white", height=150, key="firma_nuova")
        
        if st.form_submit_button("💾 SALVA NOLEGGIO"):
            if accetto and nome and targa:
                # Caricamento foto se presente
                fn = f"{targa}_{int(time.time())}.jpg"
                if foto:
                    supabase.storage.from_(BUCKET_NAME).upload(fn, foto.getvalue())
                
                # Inserimento dati
                dat = {
                    "cliente": nome, "cf": cf, "luogo_nascita": nascita, 
                    "residenza": residenza, "num_doc": patente, "telefono": telefono,
                    "targa": targa, "prezzo": prezzo, "data_inizio": str(di), 
                    "data_fine": str(df), "foto_path": fn if foto else None
                }
                supabase.table("contratti").insert(dat).execute()
                st.success(f"Noleggio di {nome} salvato con successo!")
            else:
                st.error("Assicurati di aver inserito Nome, Targa e accettato le condizioni.")

elif menu == "🗄️ Archivio":
    st.subheader("Storico Contratti")
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"📄 {c['cliente']} - {c['targa']} (del {c['data_inizio']})"):
            col1, col2, col3 = st.columns(3)
            
            # PDF CONTRATTO
            pdf_c = FPDF()
            pdf_c.add_page()
            pdf_c.set_font("Arial", 'B', 16); pdf_c.cell(0, 10, "CONTRATTO DI NOLEGGIO", ln=1, align='C')
            pdf_c.set_font("Arial", size=10); pdf_c.ln(10)
            info = f"CLIENTE: {c['cliente']}\nNATO A: {c.get('luogo_nascita', '---')}\nRESIDENTE: {c.get('residenza', '---')}\nC.F.: {c.get('cf', '---')}\nPATENTE: {c.get('num_doc', '---')}\nTEL: {c.get('telefono', '---')}\n\nVEICOLO: {c['targa']}\nPERIODO: {c['data_inizio']} / {c['data_fine']}"
            pdf_c.multi_cell(0, 7, clean_t(info), border=1)
            pdf_c.ln(10); pdf_c.set_font("Arial", 'B', 8); pdf_c.cell(0, 5, "CONDIZIONI (1-14):", ln=1)
            pdf_c.set_font("Arial", size=6); pdf_c.multi_cell(0, 3, clean_t("Responsabilita danni/furto a carico del cliente. Multe + 25.83 Euro gestione. Obbligo casco. Foro Ischia."))
            
            col1.download_button("📜 CONTRATTO", pdf_c.output(), f"Contratto_{c['id']}.pdf", key=f"c_{c['id']}")

            # PDF RICEVUTA
            pdf_r = FPDF()
            pdf_r.add_page()
            pdf_r.set_font("Arial", 'B', 16); pdf_r.cell(0, 10, "RICEVUTA DI PAGAMENTO", ln=1, align='C')
            pdf_r.set_font("Arial", size=12); pdf_r.ln(20)
            pdf_r.cell(0, 10, clean_t(f"Ricevuto da: {c['cliente']}"), ln=1)
            pdf_r.cell(0, 10, clean_t(f"Per noleggio targa: {c['targa']}"), ln=1)
            pdf_r.ln(20); pdf_r.set_font("Arial", 'B', 22)
            pdf_r.cell(0, 25, clean_t(f"TOTALE: Euro {c['prezzo']}"), border=1, align='C', ln=1)
            
            col2.download_button("💰 RICEVUTA", pdf_r.output(), f"Ricevuta_{c['id']}.pdf", key=f"r_{c['id']}")

            if c.get("foto_path"):
                url_foto = supabase.storage.from_(BUCKET_NAME).get_public_url(c["foto_path"])
                col3.link_button("📸 VEDI PATENTE", url_foto)

elif menu == "🚨 Multe":
    st.subheader("Comunicazione Dati Conducente")
    t_m = st.text_input("Inserisci Targa per cercare il contratto").upper()
    if t_m:
        rm = supabase.table("contratti").select("*").eq("targa", t_m).execute()
        if rm.data:
            c = rm.data[0]
            st.info(f"Contratto trovato per {c['cliente']} in data {c['data_inizio']}")
            pdf_v = FPDF()
            pdf_v.add_page()
            pdf_v.set_font("Arial", 'B', 14); pdf_v.cell(0, 10, "MODULO RINOTIFICA VIGILI", ln=1, align='C'); pdf_v.ln(10)
            pdf_v.set_font("Arial", size=11)
            testo_v = f"La sottoscritta BATTAGLIA MARIANNA dichiara che il veicolo targa {c['targa']} in data {c['data_inizio']} era affidato a {c['cliente']}, nato a {c.get('luogo_nascita', '---')} e residente in {c.get('residenza', '---')}.\nPatente: {c.get('num_doc', '---')}.\n\nSi richiede rinotifica verbale ai sensi della L. 445/2000."
            pdf_v.multi_cell(0, 8, clean_t(testo_v))
            st.download_button("🚨 SCARICA MODULO VIGILI", pdf_v.output(), f"Vigili_{c['targa']}.pdf")
