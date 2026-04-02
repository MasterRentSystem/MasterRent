import streamlit as st
import datetime
from fpdf import FPDF
from supabase import create_client

st.set_page_config(page_title="MasterRent Ischia", layout="wide")
st.title("🛵 MasterRent - Gestione Noleggi")

# --- CONNESSIONE SUPABASE ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except:
    st.error("Errore connessione Supabase nei Secrets")
    st.stop()

# --- FUNZIONE PULIZIA TESTO ---
def clean_text(text):
    if not text: return ""
    replacements = {"à": "a", "è": "e", "é": "e", "ì": "i", "ò": "o", "ù": "u", "€": "Euro"}
    for k, v in replacements.items():
        text = str(text).replace(k, v)
    return text.encode("latin-1", "ignore").decode("latin-1")

# --- GENERAZIONE PDF (Logica Universale) ---
def crea_pdf_final(titolo, corpo):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, clean_text(titolo), ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 8, clean_text(corpo))
    # Il segreto è usare bytes(pdf.output()) senza parametri extra
    return bytes(pdf.output())

# --- INTERFACCIA TABS ---
tab1, tab2, tab3 = st.tabs(["📝 Nuovo Noleggio", "🗄️ Archivio", "🚨 Multe"])

with tab1:
    with st.form("form_noleggio"):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Nome Cliente")
        targa = col1.text_input("Targa").upper()
        prezzo = col2.number_input("Prezzo (€)", min_value=0.0)
        cf = col2.text_input("Codice Fiscale")
        if st.form_submit_button("💾 SALVA NOLEGGIO"):
            if nome and targa:
                dati = {"cliente": nome, "targa": targa, "prezzo": prezzo, "cf": cf, "data_inizio": str(datetime.date.today())}
                supabase.table("contratti").insert(dati).execute()
                st.success("Noleggio salvato!")

with tab2:
    st.subheader("Storico Noleggi")
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"📄 {c['cliente']} - {c['targa']}"):
            col_c, col_r = st.columns(2)
            
            # Contratto
            txt_c = f"CONTRATTO DI NOLEGGIO\n\nCliente: {c['cliente']}\nTarga: {c['targa']}\nCF: {c.get('cf','')}\nData: {c['data_inizio']}\n\nFirma: ______________"
            col_c.download_button("📜 CONTRATTO", crea_pdf_final("CONTRATTO", txt_c), f"C_{c['id']}.pdf", "application/pdf", key=f"c_{c['id']}")
            
            # Ricevuta
            txt_r = f"RICEVUTA DI PAGAMENTO\n\nRicevuto da: {c['cliente']}\nPer veicolo: {c['targa']}\n\nTOTALE: {c['prezzo']} Euro"
            col_r.download_button("💰 RICEVUTA", crea_pdf_final("RICEVUTA", txt_r), f"R_{c['id']}.pdf", "application/pdf", key=f"r_{c['id']}")

with tab3:
    st.subheader("Gestione Multe")
    t_multa = st.text_input("Targa per ricerca veloce").upper()
    if t_multa:
        r_m = supabase.table("contratti").select("*").eq("targa", t_multa).execute()
        if r_m.data:
            m = r_m.data[0]
            txt_m = f"COMUNICAZIONE DATI\n\nVeicolo: {m['targa']}\nConducente: {m['cliente']}\nCF: {m.get('cf','')}"
            st.download_button("🚨 MODULO VIGILI", crea_pdf_final("MODULO VIGILI", txt_m), f"Vigili_{t_multa}.pdf", "application/pdf")
