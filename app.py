import streamlit as st
import datetime
from fpdf import FPDF
from supabase import create_client
from streamlit_drawable_canvas import st_canvas

st.set_page_config(layout="wide", page_title="MasterRent Pro")
st.title("🛵 MasterRent - Gestione Contratti & Multe")

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
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "MASTERRENT ISCHIA", ln=True, align="C")
    
    if tipo == "MULTE":
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "DICHIARAZIONE DATI CONDUCENTE (ACCERTAMENTO VIOLAZIONE)", ln=True, align="C")
        pdf.ln(5)
        pdf.set_font("Arial", size=11)
        testo = (f"Il sottoscritto titolare della ditta MasterRent, in relazione al verbale di contestazione,\n"
                 f"comunica che in data odierna il veicolo targa {c.get('targa','')} era locato a:\n\n"
                 f"CONDUCENTE: {c.get('nome','')} {c.get('cognome','')}\n"
                 f"NATO IL: {c.get('data_nascita','N/A')}\n"
                 f"RESIDENTE IN: {c.get('indirizzo','N/A')}\n"
                 f"CODICE FISCALE: {c.get('codice_fiscale','N/A')}\n"
                 f"PATENTE N: {c.get('numero_patente','N/A')}\n\n"
                 f"Si allega copia del contratto di noleggio e del documento d'identita.")
        pdf.multi_cell(0, 8, clean(testo))
    else:
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, clean(f"{tipo} DI NOLEGGIO"), ln=True, align="C")
        pdf.ln(5)
        pdf.set_font("Arial", size=10)
        dati = (f"CLIENTE: {c.get('nome','')} {c.get('cognome','')}\n"
                f"INDIRIZZO: {c.get('indirizzo','')}\n"
                f"CF: {c.get('codice_fiscale','')} | Patente: {c.get('numero_patente','')}\n"
                f"Tel: {c.get('telefono','')} | Targa: {c.get('targa','')} | Prezzo: {c.get('prezzo',0)}€")
        pdf.multi_cell(0, 7, clean(dati), border=1)

    if tipo == "CONTRATTO":
        pdf.ln(5)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(0, 7, "CONDIZIONI LEGALI E PRIVACY", ln=True)
        pdf.set_font("Arial", size=8)
        pdf.multi_cell(0, 5, clean("1. Il cliente risponde di danni e multe.\n2. Consegna e reso con pieno.\n3. Privacy GDPR Reg. UE 2016/679."))
        pdf.ln(10)
        pdf.cell(0, 10, "Firma: ______________________________", ln=True)
        
    return bytes(pdf.output())

# FORM
with st.form("noleggio_form"):
    st.subheader("📝 Nuova Anagrafica Cliente")
    c1, c2 = st.columns(2)
    n = c1.text_input("Nome")
    cog = c1.text_input("Cognome")
    ind = c1.text_input("Indirizzo di Residenza")
    cf = c1.text_input("Codice Fiscale")
    
    tel = c2.text_input("Telefono")
    pat = c2.text_input("N. Patente")
    tar = c2.text_input("Targa").upper()
    pre = c2.number_input("Prezzo (€)", min_value=0.0)
    
    st.write("✍️ *FIRMA E PRIVACY*")
    canvas = st_canvas(stroke_width=2, height=100, width=300, key="firma_v200")
    priv = st.checkbox("Accetto Condizioni e Privacy GDPR")

    if st.form_submit_button("💾 SALVA TUTTO"):
        if n and tar and priv:
            dati = {"nome": n, "cognome": cog, "indirizzo": ind, "codice_fiscale": cf, 
                    "telefono": tel, "numero_patente": pat, "targa": tar, 
                    "prezzo": pre, "privacy_accettata": True}
            supabase.table("contratti").insert(dati).execute()
            st.success("✅ Salvato!")
        else:
            st.error("Mancano dati obbligatori!")

# ARCHIVIO
st.divider()
res = supabase.table("contratti").select("*").order("id", desc=True).execute()
for c in res.data:
    with st.expander(f"📄 {c.get('nome','')} - {c.get('targa','')}"):
        col_a, col_b, col_c = st.columns(3)
        col_a.download_button("📜 CONTRATTO", genera_pdf(c, "CONTRATTO"), f"C_{c['id']}.pdf", key=f"c_{c['id']}")
        col_b.download_button("💰 RICEVUTA", genera_pdf(c, "RICEVUTA"), f"R_{c['id']}.pdf", key=f"r_{c['id']}")
        col_c.download_button("🚨 MODULO VIGILI", genera_pdf(c, "MULTE"), f"Vigili_{c['targa']}.pdf", key=f"m_{c['id']}")
