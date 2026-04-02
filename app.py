import streamlit as st
import datetime
from fpdf import FPDF
from supabase import create_client
from streamlit_drawable_canvas import st_canvas

st.set_page_config(layout="wide", page_title="MasterRent Pro - V220")

# Connessione
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def clean(t):
    if not t: return ""
    repl = {"à":"a","è":"e","é":"e","ì":"i","ò":"o","ù":"u","€":"Euro"}
    for k,v in repl.items(): t = str(t).replace(k,v)
    return t.encode("latin-1", "ignore").decode("latin-1")

def genera_pdf_master(c, tipo="CONTRATTO"):
    pdf = FPDF()
    pdf.add_page()
    
    # INTESTAZIONE FISSA MARIANNA BATTAGLIA
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 7, "BATTAGLIA MARIANNA", ln=True)
    pdf.set_font("Arial", size=9)
    pdf.cell(0, 5, "Via Cognole, 5 - 80075 Forio (NA)", ln=True)
    pdf.cell(0, 5, "C.F. BTTMNN87A53Z112S - P. IVA 10252601215", ln=True)
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 12)
    titolo_doc = "COMUNICAZIONE DATI CONDUCENTE (PER MULTE)" if tipo == "MULTE" else f"{tipo} DI NOLEGGIO"
    pdf.cell(0, 10, clean(titolo_doc), ln=True, align="C", border="B")
    pdf.ln(5)

    pdf.set_font("Arial", size=10)
    if tipo == "MULTE":
        testo = (f"La sottoscritta BATTAGLIA MARIANNA comunica che il veicolo TARGA {c.get('targa','')}\n"
                 f"in data {c.get('data_contratto',' ')[:10]} era affidato a:\n\n"
                 f"CONDUCENTE: {c.get('nome','')} {c.get('cognome','')}\n"
                 f"NATO A: {c.get('luogo_nascita','_____')}\n"
                 f"RESIDENTE: {c.get('indirizzo','_____')}\n"
                 f"C.F.: {c.get('codice_fiscale','')}\n"
                 f"PATENTE: {c.get('numero_patente','')}\n\n"
                 f"Si rilascia per accertamento violazione del Codice della Strada.")
        pdf.multi_cell(0, 8, clean(testo))
    else:
        info = (f"CLIENTE: {c.get('nome','')} {c.get('cognome','')}\n"
                f"INDIRIZZO: {c.get('indirizzo','N/A')}\n"
                f"C.F.: {c.get('codice_fiscale','')} | NATO A: {c.get('luogo_nascita','')}\n"
                f"TARGA: {c.get('targa','')} | PATENTE: {c.get('numero_patente','')}\n"
                f"PREZZO: {c.get('prezzo',0)} Euro")
        pdf.multi_cell(0, 8, clean(info), border=1)
        
        if tipo == "CONTRATTO":
            pdf.ln(5)
            pdf.set_font("Arial", "B", 9)
            pdf.cell(0, 7, "TERMINI LEGALI E PRIVACY GDPR", ln=True)
            pdf.set_font("Arial", size=8)
            pdf.multi_cell(0, 4, clean("Il cliente e responsabile per danni, furto e multe. Veicolo consegnato integro.\nI dati sono trattati secondo Reg. UE 2016/679. Firma per accettazione stato mezzo e clausole."))
            pdf.ln(15)
            pdf.cell(0, 10, "FIRMA DEL CLIENTE: ______________________________", ln=True)

    return bytes(pdf.output())

# INTERFACCIA
st.header("🛵 MasterRent V220 - Marianna Battaglia")
with st.form("main_form"):
    col1, col2 = st.columns(2)
    nome = col1.text_input("Nome")
    cognome = col1.text_input("Cognome")
    luogo = col1.text_input("Luogo di Nascita")
    indirizzo = col1.text_input("Indirizzo Residenza Completo")
    
    cf = col2.text_input("Codice Fiscale")
    patente = col2.text_input("N. Patente")
    targa = col2.text_input("Targa").upper()
    prezzo = col2.number_input("Prezzo (€)", min_value=0.0)
    
    st_canvas(stroke_width=2, height=100, width=300, key="firma_v220")
    privacy = st.checkbox("Accetto Condizioni Legali e Privacy GDPR")

    if st.form_submit_button("💾 SALVA TUTTO"):
        if nome and targa and privacy:
            dati = {"nome": nome, "cognome": cognome, "luogo_nascita": luogo, "indirizzo": indirizzo, 
                    "codice_fiscale": cf, "numero_patente": patente, "targa": targa, "prezzo": prezzo}
            supabase.table("contratti").insert(dati).execute()
            st.success("✅ Salvato!")
        else: st.error("Mancano dati o Privacy!")

# ARCHIVIO CON 3 TASTI
st.divider()
res = supabase.table("contratti").select("*").order("id", desc=True).execute()
for c in res.data:
    with st.expander(f"📄 {c.get('nome','')} - {c.get('targa','')}"):
        btn1, btn2, btn3 = st.columns(3)
        btn1.download_button("📜 CONTRATTO", genera_pdf_master(c, "CONTRATTO"), f"C_{c['id']}.pdf", key=f"c_{c['id']}")
        btn2.download_button("💰 RICEVUTA", genera_pdf_master(c, "RICEVUTA"), f"R_{c['id']}.pdf", key=f"r_{c['id']}")
        btn3.download_button("🚨 MODULO MULTE", genera_pdf_master(c, "MULTE"), f"M_{c['id']}.pdf", key=f"m_{c['id']}")
