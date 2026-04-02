import streamlit as st
import datetime
from fpdf import FPDF
from supabase import create_client
from streamlit_drawable_canvas import st_canvas

st.set_page_config(layout="wide", page_title="MasterRent Pro")
st.title("🛵 MasterRent - Contratto Legale V180")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def clean(t):
    if not t: return ""
    repl = {"à":"a","è":"e","é":"e","ì":"i","ò":"o","ù":"u","€":"Euro"}
    for k,v in repl.items(): t = str(t).replace(k,v)
    return t.encode("latin-1", "ignore").decode("latin-1")

# --- GENERATORE PDF PROFESSIONALE ---
def genera_pdf_pro(c, tipo="CONTRATTO"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "MASTERRENT ISCHIA - NOLEGGIO SCOOTER", ln=True, align="C")
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, clean(f"{tipo} DI NOLEGGIO"), ln=True, align="C")
    pdf.ln(5)

    # Box Dati Cliente
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 8, "DATI DEL LOCATARIO", ln=True)
    pdf.set_font("Arial", size=10)
    info = (f"Cliente: {c.get('nome','')} {c.get('cognome','')}\n"
            f"CF: {c.get('codice_fiscale','')} | Patente: {c.get('numero_patente','')}\n"
            f"Tel: {c.get('telefono','')} | Veicolo: {c.get('targa','')} | Prezzo: {c.get('prezzo',0)} Euro")
    pdf.multi_cell(0, 7, clean(info), border=1)
    
    if tipo == "CONTRATTO":
        pdf.ln(5)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(0, 7, "CONDIZIONI GENERALI E PRIVACY (GDPR)", ln=True)
        pdf.set_font("Arial", size=8)
        legale = (
            "1. Il cliente e responsabile dei danni al veicolo, furto e incendio.\n"
            "2. Tutte le sanzioni amministrative (multe) sono a carico del locatario.\n"
            "3. Il veicolo viene consegnato con il pieno e va reso con il pieno.\n"
            "4. PRIVACY: I dati sono trattati secondo il Reg. UE 2016/679 (GDPR).\n"
            "5. Foro competente: Per ogni controversia e competente il foro di Napoli."
        )
        pdf.multi_cell(0, 5, clean(legale))
        pdf.ln(10)
        pdf.cell(0, 10, "Firma del Cliente: ______________________________", ln=True)

    return bytes(pdf.output())

# --- INTERFACCIA ---
with st.form("noleggio_form"):
    c1, c2 = st.columns(2)
    nome = c1.text_input("Nome")
    cognome = c1.text_input("Cognome")
    cf = c1.text_input("Codice Fiscale")
    tel = c1.text_input("Telefono")
    
    targa = c2.text_input("Targa").upper()
    patente = c2.text_input("Numero Patente")
    prezzo = c2.number_input("Prezzo (€)", min_value=0.0)
    
    st.write("✍️ *FIRMA E PRIVACY*")
    canvas = st_canvas(stroke_width=2, height=100, width=300, key="firma_v180")
    privacy = st.checkbox("Accetto Condizioni di Noleggio e Privacy GDPR")

    if st.form_submit_button("💾 SALVA CONTRATTO"):
        if nome and targa and privacy:
            dati = {
                "nome": nome, "cognome": cognome, "codice_fiscale": cf,
                "telefono": tel, "numero_patente": patente, "targa": targa,
                "prezzo": prezzo, "privacy_accettata": True
            }
            try:
                supabase.table("contratti").insert(dati).execute()
                st.success("✅ Salvato con successo!")
            except Exception as e:
                st.error(f"Errore Database: {e}")
        else:
            st.error("Mancano dati obbligatori o non hai spuntato la Privacy!")

# --- ARCHIVIO ---
st.divider()
res = supabase.table("contratti").select("*").order("id", desc=True).execute()
for c in res.data:
    with st.expander(f"📄 {c.get('nome','')} - {c.get('targa','')}"):
        col_c, col_r = st.columns(2)
        col_c.download_button("📜 CONTRATTO", genera_pdf_pro(c, "CONTRATTO"), f"C_{c['id']}.pdf", key=f"c_{c['id']}")
        col_r.download_button("💰 RICEVUTA", genera_pdf_pro(c, "RICEVUTA"), f"R_{c['id']}.pdf", key=f"r_{c['id']}")
