import streamlit as st
import datetime
from fpdf import FPDF
from supabase import create_client
from streamlit_drawable_canvas import st_canvas

st.set_page_config(layout="wide", page_title="MasterRent V230")

# Connessione
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def clean(t):
    if not t: return ""
    repl = {"à":"a","è":"e","é":"e","ì":"i","ò":"o","ù":"u","€":"Euro"}
    for k,v in repl.items(): t = str(t).replace(k,v)
    return t.encode("latin-1", "ignore").decode("latin-1")

def genera_pdf(c, tipo="CONTRATTO"):
    pdf = FPDF()
    pdf.add_page()
    
    # INTESTAZIONE MARIANNA BATTAGLIA
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 7, "BATTAGLIA MARIANNA", ln=True)
    pdf.set_font("Arial", size=9)
    pdf.cell(0, 5, "Via Cognole, 5 - 80075 Forio (NA)", ln=True)
    pdf.cell(0, 5, "C.F. BTTMNN87A53Z112S - P. IVA 10252601215", ln=True)
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 12)
    titolo = "DICHIARAZIONE DATI CONDUCENTE (MULTE)" if tipo == "MULTE" else f"{tipo} DI NOLEGGIO"
    pdf.cell(0, 10, clean(titolo), ln=True, align="C", border="B")
    pdf.ln(5)

    pdf.set_font("Arial", size=10)
    if tipo == "MULTE":
        testo = (f"La sottoscritta BATTAGLIA MARIANNA comunica che il veicolo TARGA {c.get('targa','')}\n"
                 f"era affidato in data {c.get('data_contratto',' ')[:10]} al conducente:\n\n"
                 f"NOME/COGNOME: {c.get('nome','')} {c.get('cognome','')}\n"
                 f"NATO A: {c.get('luogo_nascita','_____')}\n"
                 f"RESIDENTE: {c.get('indirizzo','_____')}\n"
                 f"C.F.: {c.get('codice_fiscale','')}\n"
                 f"PATENTE: {c.get('numero_patente','')}\n\n"
                 f"Si rilascia per gli accertamenti di violazione al Codice della Strada.")
        pdf.multi_cell(0, 8, clean(testo))
    else:
        info = (f"CLIENTE: {c.get('nome','')} {c.get('cognome','')}\n"
                f"RESIDENTE: {c.get('indirizzo','N/A')}\n"
                f"C.F.: {c.get('codice_fiscale','')} | NATO A: {c.get('luogo_nascita','')}\n"
                f"TARGA: {c.get('targa','')} | PATENTE: {c.get('numero_patente','')}\n"
                f"PREZZO: {c.get('prezzo',0)} Euro")
        pdf.multi_cell(0, 8, clean(info), border=1)
        
        if tipo == "CONTRATTO":
            pdf.ln(5)
            pdf.set_font("Arial", "B", 9)
            pdf.cell(0, 7, "CONTRATTO LEGALE E PRIVACY (GDPR)", ln=True)
            pdf.set_font("Arial", size=8)
            pdf.multi_cell(0, 4, clean("1. Il cliente e pienamente responsabile per danni, furto e multe.\n2. Veicolo consegnato in perfetto stato.\n3. Privacy: Dati trattati secondo Reg. UE 2016/679.\n4. Foro competente: Napoli."))
            pdf.ln(15)
            pdf.cell(0, 10, "FIRMA DEL CLIENTE: ______________________________", ln=True)

    return bytes(pdf.output())

# INTERFACCIA
st.header("🛵 MasterRent Professionale V230")
with st.form("form_master"):
    col1, col2 = st.columns(2)
    nome = col1.text_input("Nome")
    cognome = col1.text_input("Cognome")
    luogo = col1.text_input("Luogo di Nascita")
    indirizzo = col1.text_input("Indirizzo Residenza Completo")
    
    cf = col2.text_input("Codice Fiscale")
    patente = col2.text_input("N. Patente")
    targa = col2.text_input("Targa").upper()
    prezzo = col2.number_input("Prezzo (€)", min_value=0.0)
    
    st_canvas(stroke_width=2, height=100, width=300, key="firma_v230")
    privacy = st.checkbox("ACCETTO CONDIZIONI LEGALI E PRIVACY GDPR")

    if st.form_submit_button("💾 SALVA NOLEGGIO"):
        if nome and targa and privacy:
            dati = {"nome": nome, "cognome": cognome, "luogo_nascita": luogo, "indirizzo": indirizzo, 
                    "codice_fiscale": cf, "numero_patente": patente, "targa": targa, "prezzo": prezzo}
            supabase.table("contratti").insert(dati).execute()
            st.success("✅ SALVATO! SCARICA I PDF SOTTO.")
        else: st.error("Dati obbligatori mancanti!")

# ARCHIVIO 3 TASTI
st.divider()
try:
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"📄 {c.get('nome','')} {c.get('cognome','')} - {c.get('targa','')}"):
            b1, b2, b3 = st.columns(3)
            b1.download_button("📜 CONTRATTO", genera_pdf(c, "CONTRATTO"), f"Contratto_{c['id']}.pdf", key=f"c_{c['id']}")
            b2.download_button("💰 RICEVUTA", genera_pdf(c, "RICEVUTA"), f"Ricevuta_{c['id']}.pdf", key=f"r_{c['id']}")
            b3.download_button("🚨 MODULO MULTE", genera_pdf(c, "MULTE"), f"Multe_{c['id']}.pdf", key=f"m_{c['id']}")
except: st.info("Carica il primo contratto!")
