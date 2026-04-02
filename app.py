import streamlit as st
import datetime
from fpdf import FPDF
from supabase import create_client
from streamlit_drawable_canvas import st_canvas

st.set_page_config(layout="wide", page_title="MasterRent - Battaglia Marianna")

# Connessione
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def clean(t):
    if not t: return ""
    repl = {"à":"a","è":"e","é":"e","ì":"i","ò":"o","ù":"u","€":"Euro"}
    for k,v in repl.items(): t = str(t).replace(k,v)
    return t.encode("latin-1", "ignore").decode("latin-1")

def genera_pdf_professionale(c, tipo="CONTRATTO"):
    pdf = FPDF()
    pdf.add_page()
    
    # --- INTESTAZIONE MARIANNA BATTAGLIA ---
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 7, "BATTAGLIA MARIANNA", ln=True, align="L")
    pdf.set_font("Arial", size=9)
    pdf.cell(0, 5, "Via Cognole, 5 - 80075 Forio (NA)", ln=True, align="L")
    pdf.cell(0, 5, "Cod. Fisc. BTTMNN87A53Z112S - P. IVA 10252601215", ln=True, align="L")
    pdf.ln(10)
    
    # Titolo Documento
    pdf.set_font("Arial", "B", 12)
    titolo = "DICHIARAZIONE DATI CONDUCENTE" if tipo == "MULTE" else f"{tipo} DI PAGAMENTO / NOLEGGIO"
    pdf.cell(0, 10, clean(titolo), ln=True, align="C", border="B")
    pdf.ln(5)

    # --- CORPO DEL DOCUMENTO ---
    pdf.set_font("Arial", size=10)
    
    if tipo == "MULTE":
        testo_multe = (
            f"La sottoscritta BATTAGLIA MARIANNA, titolare della ditta MasterRent,\n"
            f"in riferimento all'accertamento di violazione sul veicolo TARGA: {c.get('targa','')}\n"
            f"comunica che in data {c.get('data_contratto',' ')[:10]} il mezzo era affidato a:\n\n"
            f"CONDUCENTE: {c.get('nome','')} {c.get('cognome','')}\n"
            f"NATO A: {c.get('luogo_nascita','_____')}\n"
            f"RESIDENTE: {c.get('indirizzo','_____')}\n"
            f"C.F.: {c.get('codice_fiscale','')}\n"
            f"PATENTE N: {c.get('numero_patente','')}\n\n"
            f"Si rilascia la presente per gli usi consentiti dalla legge."
        )
        pdf.multi_cell(0, 8, clean(testo_multe))
    else:
        dati_client = (
            f"CLIENTE: {c.get('nome','')} {c.get('cognome','')}\n"
            f"NATO A: {c.get('luogo_nascita','')}\n"
            f"RESIDENTE: {c.get('indirizzo','')}\n"
            f"C.F.: {c.get('codice_fiscale','')}\n"
            f"TARGA: {c.get('targa','')} | PATENTE: {c.get('numero_patente','')}\n"
            f"PREZZO: {c.get('prezzo',0)} Euro"
        )
        pdf.multi_cell(0, 8, clean(dati_client), border=1)
        
        if tipo == "CONTRATTO":
            pdf.ln(5)
            pdf.set_font("Arial", "B", 9)
            pdf.cell(0, 7, "CONDIZIONI E PRIVACY (GDPR)", ln=True)
            pdf.set_font("Arial", size=8)
            pdf.multi_cell(0, 4, clean("Il cliente e responsabile per multe e danni. Il veicolo viene consegnato integro.\nI dati sono trattati per fini contrattuali (Reg. UE 2016/679)."))
            pdf.ln(15)
            pdf.cell(0, 10, "FIRMA DEL CLIENTE: ______________________________", ln=True)

    return bytes(pdf.output())

# --- INTERFACCIA APP ---
st.title("🛵 MasterRent Ischia - Gestione")

with st.form("form_noleggio"):
    c1, c2 = st.columns(2)
    n = c1.text_input("Nome")
    cog = c1.text_input("Cognome")
    luogo = c1.text_input("Luogo di Nascita")
    ind = c1.text_input("Indirizzo Residenza")
    
    cf = c2.text_input("Codice Fiscale")
    pat = c2.text_input("N. Patente")
    tar = c2.text_input("Targa").upper()
    pre = c2.number_input("Prezzo (€)", min_value=0.0)
    
    st.write("✍️ *FIRMA E PRIVACY*")
    canvas = st_canvas(stroke_width=2, height=100, width=300, key="firma_v210")
    priv = st.checkbox("Accetto Condizioni e Privacy GDPR")

    if st.form_submit_button("💾 SALVA E GENERA"):
        if n and tar and priv:
            dati = {"nome": n, "cognome": cog, "luogo_nascita": luogo, "indirizzo": ind, 
                    "codice_fiscale": cf, "numero_patente": pat, "targa": tar, 
                    "prezzo": pre, "privacy_accettata": True}
            supabase.table("contratti").insert(dati).execute()
            st.success("✅ Contratto registrato!")
        else:
            st.error("Mancano dati o Privacy non accettata!")

# ARCHIVIO
st.divider()
res = supabase.table("contratti").select("*").order("id", desc=True).execute()
for c in res.data:
    with st.expander(f"📄 {c.get('nome','')} - {c.get('targa','')}"):
        col1, col2, col3 = st.columns(3)
        col1.download_button("📜 CONTRATTO", genera_pdf_professionale(c, "CONTRATTO"), f"C_{c['id']}.pdf")
        col2.download_button("💰 RICEVUTA", genera_pdf_professionale(c, "RICEVUTA"), f"R_{c['id']}.pdf")
        col3.download_button("🚨 MODULO MULTE", genera_pdf_professionale(c, "MULTE"), f"Multe_{c['targa']}.pdf")
