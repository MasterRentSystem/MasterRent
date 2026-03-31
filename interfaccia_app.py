import streamlit as st
import datetime
import fpdf
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
import time

# 1. CONNESSIONE E CONFIGURAZIONE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)
BUCKET_NAME = "DOCUMENTI_PATENTI"

def clean_t(text):
    if not text or text == "None": return "---"
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in repls.items(): text = str(text).replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

INTESTAZIONE = "MASTERRENT DI MARIANNA BATTAGLIA\nVia Cognole n. 5 - 80075 Forio (NA)\nC.F.: BTTMNN87A53Z112S | P.IVA: 10252601215"

# --- FUNZIONI GENERAZIONE PDF (PROFESSIONALI) ---

def genera_pdf_stiloso(c, tipo="CONTRATTO", data_multa=None):
    pdf = fpdf.FPDF()
    pdf.add_page()
    
    # Intestazione
    pdf.set_font("Arial", 'B', 11); pdf.set_fill_color(230, 230, 230)
    pdf.multi_cell(0, 6, txt=clean_t(INTESTAZIONE), border=1, align='L', fill=True)
    pdf.ln(8)
    
    # Titolo Dinamico
    pdf.set_font("Arial", 'B', 16)
    if tipo == "CONTRATTO": titolo = "CONTRATTO DI NOLEGGIO"
    elif tipo == "VIGILI": titolo = "COMUNICAZIONE DATI CONDUCENTE"
    else: titolo = "RICEVUTA DI PAGAMENTO"
    pdf.cell(0, 10, clean_t(titolo), ln=1, align='C')
    pdf.ln(5)
    
    # Tabella Dati Cliente
    pdf.set_font("Arial", 'B', 10); pdf.cell(0, 7, "DATI DEL CONDUCENTE", ln=1)
    pdf.set_font("Arial", size=10)
    pdf.cell(95, 8, clean_t(f"NOME: {c.get('cliente')}"), border=1)
    pdf.cell(95, 8, clean_t(f"C.F.: {c.get('cf')}"), border=1, ln=1)
    pdf.cell(190, 8, clean_t(f"NATO A: {c.get('luogo_nascita')}"), border=1, ln=1)
    pdf.cell(190, 8, clean_t(f"RESIDENZA: {c.get('residenza')}"), border=1, ln=1)
    pdf.cell(95, 8, clean_t(f"PATENTE: {c.get('num_doc')}"), border=1)
    pdf.cell(95, 8, clean_t(f"SCADENZA: {c.get('scadenza_patente')}"), border=1, ln=1)
    pdf.ln(4)
    
    # Tabella Veicolo
    pdf.set_font("Arial", 'B', 10); pdf.cell(0, 7, "DETTAGLI NOLEGGIO", ln=1)
    pdf.set_font("Arial", size=10)
    pdf.cell(60, 8, clean_t(f"TARGA: {c.get('targa')}"), border=1)
    pdf.cell(65, 8, clean_t(f"DAL: {c.get('data_inizio')}"), border=1)
    pdf.cell(65, 8, clean_t(f"AL: {c.get('data_fine')}"), border=1, ln=1)
    
    if tipo == "VIGILI" and data_multa:
        pdf.ln(5); pdf.set_font("Arial", 'I', 11)
        pdf.multi_cell(0, 8, txt=clean_t(f"Si conferma che in data {data_multa} il veicolo sopra indicato era affidato al conducente identificato nei dati di cui sopra."))

    if tipo == "CONTRATTO":
        pdf.ln(5); pdf.set_font("Arial", 'B', 8); pdf.cell(0, 5, "PRIVACY E RESPONSABILITA", ln=1)
        pdf.set_font("Arial", size=7.5)
        pdf.multi_cell(0, 4, txt=clean_t("Il cliente autorizza la copia del documento (GDPR). Si assume responsabilita per multe e danni. Accetta artt. 1341-1342 c.c."), border='T')
        pdf.ln(10); pdf.set_font("Arial", 'B', 10); pdf.cell(0, 10, "Firma del Cliente (Digitale): ______________________", ln=1, align='R')

    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACCIA APP ---

st.sidebar.title("🚀 MasterRent Ischia")
menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Noleggio", "🗄️ Archivio Documenti"])

if menu == "📝 Nuovo Noleggio":
    st.header("Registrazione Contratto")
    with st.form("form_completo", clear_on_submit=False):
        c1, c2 = st.columns(2)
        cliente = c1.text_input("Nome e Cognome")
        cf = c2.text_input("Codice Fiscale")
        nascita = c1.text_input("Luogo e Data Nascita")
        residenza = c2.text_input("Indirizzo Residenza")
        num_doc = c1.text_input("Numero Patente")
        scadenza = c2.date_input("Scadenza Patente")
        targa = c1.text_input("TARGA").upper()
        prezzo = c2.number_input("Prezzo (€)", min_value=0.0)
        d_ini = c1.date_input("Data Inizio", datetime.date.today())
        d_fin = c2.date_input("Data Fine", datetime.date.today() + datetime.timedelta(days=1))
        
        foto = st.camera_input("📸 Foto Patente")
        st.write("✍️ *Firma Cliente*")
        st_canvas(fill_color="white", stroke_width=2, height=120, key="firma_v8")
        
        if st.form_submit_button("💾 SALVA ED ARCHIVIA"):
            path_foto = None
            if foto:
                try:
                    fname = f"{targa}_{int(time.time())}.jpg"
                    supabase.storage.from_(BUCKET_NAME).upload(fname, foto.getvalue())
                    path_foto = fname
                except: pass
            
            dat = {"cliente": cliente, "cf": cf, "luogo_nascita": nascita, "residenza": residenza, 
                   "num_doc": num_doc, "scadenza_patente": str(scadenza), "targa": targa, 
                   "prezzo": prezzo, "data_inizio": str(d_ini), "data_fine": str(d_fin), "foto_path": path_foto}
            supabase.table("contratti").insert(dat).execute()
            st.success("Contratto archiviato con successo!")

elif menu == "🗄️ Archivio Documenti":
    st.header("🗄️ Gestione Archivio")
    
    # 🚨 Sezione Ricerca Vigili
    with st.expander("🚨 Genera Modulo per i Vigili"):
        r1, r2 = st.columns(2)
        t_v = r1.text_input("Targa Infrazione").upper()
        d_v = r2.date_input("Data della Multa")
        if t_v:
            res_v = supabase.table("contratti").select("*").eq("targa", t_v).lte("data_inizio", str(d_v)).gte("data_fine", str(d_v)).execute()
            if res_v.data:
                st.download_button(f"📥 Scarica Modulo Vigili per {res_v.data[0]['cliente']}", genera_pdf_stiloso(res_v.data[0], "VIGILI", d_v), f"Vigili_{t_v}.pdf")
            else: st.warning("Nessun cliente trovato per questa data.")

    st.divider()

    # 📋 Tabella Archivio a Colonne (Contratti, Fatture, Foto)
    res = supabase.table("contratti").select("*").order("data_inizio", desc=True).execute()
    if res.data:
        h1, h2, h3, h4 = st.columns([2, 1, 1, 1])
        h1.write("*CLIENTE / TARGA"); h2.write("CONTRATTO"); h3.write("FATTURA"); h4.write("FOTO*")
        st.write("---")
        
        for c in res.data:
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            c1.write(f"*{c['cliente']}*\n{c['targa']}")
            
            # Contratti e Ricevute
            c2.download_button("📜 PDF", genera_pdf_stiloso(c, "CONTRATTO"), f"Contratto_{c['targa']}.pdf", key=f"c_{c['id']}")
            c3.download_button("💰 PDF", genera_pdf_stiloso(c, "FATTURA"), f"Fattura_{c['id']}.pdf", key=f"f_{c['id']}")
            
            # Foto Patente
            if c.get("foto_path"):
                url_foto = supabase.storage.from_(BUCKET_NAME).get_public_url(c["foto_path"])
                c4.link_button("📸 VEDI", url_foto)
            else: c4.write("❌")
