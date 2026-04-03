import streamlit as st
import datetime
from fpdf import FPDF
from supabase import create_client

st.set_page_config(layout="wide", page_title="Battaglia Rent Pro")

# --- DATABASE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- FUNZIONE PDF ---
def genera_pdf_tipo(c, tipo="CONTRATTO"):
    pdf = FPDF()
    pdf.add_page()
    try:
        pdf.image("logo.png", 10, 8, 33)
    except:
        pdf.set_font("Arial", "B", 20)
        pdf.cell(0, 10, "BATTAGLIA RENT", ln=True, align="C")
    
    pdf.ln(15)
    titoli = {"CONTRATTO": "CONTRATTO DI NOLEGGIO", "FATTURA": "RICEVUTA DI PAGAMENTO", "MULTE": "COMUNICAZIONE DATI CONDUCENTE"}
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, titoli.get(tipo, "DOCUMENTO"), ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Arial", "", 10)
    dati = f"Cliente: {c.get('nome')} {c.get('cognome')}\nNato a: {c.get('luogo_nascita')} il {c.get('data_nascita')}\nPatente: {c.get('numero_patente')}\nVeicolo: {c.get('targa')}"
    pdf.multi_cell(0, 6, dati)
    
    if tipo == "CONTRATTO":
        pdf.ln(5)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 10, "CLAUSOLE:", ln=True)
        pdf.set_font("Arial", "", 8)
        pdf.multi_cell(0, 5, "1. Responsabilita danni e multe a carico del cliente.\n2. Riconsegna con stesso carburante.\n3. Privacy: Dati trattati secondo GDPR.")
    
    pdf.ln(20)
    pdf.cell(100, 10, "Firma Titolare", 0, 0)
    pdf.cell(0, 10, "Firma Cliente", 0, 1, "R")
    return bytes(pdf.output())

# --- LOGIN ---
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False

if not st.session_state.autenticato:
    password = st.text_input("Inserisci Password", type="password")
    if st.button("Accedi"):
        if password == "ischia2024": # Puoi cambiare la password qui
            st.session_state.autenticato = True
            st.rerun()
        else:
            st.error("Password errata")
else:
    # --- 1. MODULO INSERIMENTO ---
    st.header("📝 Nuovo Contratto - Battaglia Rent")
    col1, col2 = st.columns(2)
    with col1:
        nome = st.text_input("Nome")
        cognome = st.text_input("Cognome")
        data_n = st.date_input("Data di Nascita", value=None)
        luogo_n = st.text_input("Luogo di Nascita")
        indirizzo = st.text_input("Indirizzo")
    with col2:
        tel = st.text_input("Telefono")
        cf = st.text_input("Codice Fiscale")
        pat = st.text_input("Numero Patente")
        targa = st.text_input("Targa Veicolo")
        prezzo = st.number_input("Prezzo (€)", min_value=0.0)
        deposito = st.number_input("Deposito (€)", min_value=0.0)

    st.subheader("⚖️ Privacy e Foto")
    f_fronte = st.file_uploader("Fronte Documento", type=['jpg','png'])
    accetto = st.checkbox("Accetto Clausole e Privacy GDPR")

    if st.button("💾 SALVA CONTRATTO"):
        if accetto and nome and targa:
            try:
                dati_db = {
                    "nome": nome, "cognome": cognome, "telefono": tel,
                    "numero_patente": pat, "targa": targa, "prezzo": prezzo,
                    "deposito": deposito, "indirizzo": indirizzo,
                    "luogo_nascita": luogo_n, "data_nascita": str(data_n),
                    "privacy_accettata": True
                }
                supabase.table("contratti").insert(dati_db).execute()
                st.success("✅ Salvato!")
                st.rerun()
            except Exception as e:
                st.error(f"Errore: {e}")
        else:
            st.warning("⚠️ Accetta la privacy e compila i campi!")

    # --- 2. ARCHIVIO ---
    st.divider()
    st.header("📋 Archivio Contratti")
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        id_c = c.get('id')
        with st.expander(f"ID: {id_c} - {c.get('nome')} {c.get('cognome')} ({c.get('targa')})"):
            c1, c2, c3 = st.columns(3)
            c1.download_button("📜 Contratto", genera_pdf_tipo(c, "CONTRATTO"), f"C_{id_c}.pdf")
            c2.download_button("💰 Ricevuta", genera_pdf_tipo(c, "FATTURA"), f"R_{id_c}.pdf")
            c3.download_button("🚨 Modulo Multe", genera_pdf_tipo(c, "MULTE"), f"M_{id_c}.pdf")
