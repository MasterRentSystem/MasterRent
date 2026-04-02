import streamlit as st
import datetime
from fpdf import FPDF
from supabase import create_client
from streamlit_drawable_canvas import st_canvas

st.set_page_config(layout="wide", page_title="MasterRent Ischia Pro")
st.title("🛵 MasterRent - Gestione Legale & Contratti")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def clean(t):
    if not t: return ""
    repl = {"à":"a","è":"e","é":"e","ì":"i","ò":"o","ù":"u","€":"Euro"}
    for k,v in repl.items(): t = str(t).replace(k,v)
    return t.encode("latin-1", "ignore").decode("latin-1")

# --- GENERATORE PDF PROFESSIONALE ---
def genera_documento(c, tipo="CONTRATTO"):
    pdf = FPDF()
    pdf.add_page()
    
    # Intestazione Aziendale
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "MASTERRENT - ISCHIA", ln=True, align="C")
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 7, clean(f"{tipo} DI NOLEGGIO"), ln=True, align="C")
    pdf.ln(5)

    # Dati Anagrafici
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 8, "DATI DEL CONDUCENTE / CUSTOMER DETAILS", ln=True, fill=False)
    pdf.set_font("Arial", size=10)
    anagrafica = (
        f"Nome/Cognome: {c.get('nome','')} {c.get('cognome','')}\n"
        f"Codice Fiscale: {c.get('codice_fiscale','')}\n"
        f"Patente: {c.get('numero_patente','')} | Tel: {c.get('telefono','')}\n"
        f"Veicolo: {c.get('targa','')} | Prezzo: {c.get('prezzo',0)} Euro"
    )
    pdf.multi_cell(0, 6, clean(anagrafica), border=1)
    
    if tipo == "CONTRATTO":
        pdf.ln(5)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 8, "CONDIZIONI GENERALI DI NOLEGGIO", ln=True)
        pdf.set_font("Arial", size=8)
        clausole = (
            "1. STATO VEICOLO: Il locatario riceve il veicolo in ottimo stato e con il pieno.\n"
            "2. RESPONSABILITA: Il cliente e responsabile di ogni danno, furto o incendio.\n"
            "3. MULTE: Ogni sanzione amministrativa nel periodo di noleggio e a carico del cliente.\n"
            "4. RICONSEGNA: Il veicolo va riconsegnato entro l'orario stabilito o sara addebitata una penale.\n"
            "5. PRIVACY (GDPR): I dati sono trattati solo per fini contrattuali (Reg. UE 2016/679)."
        )
        pdf.multi_cell(0, 5, clean(clausole))
        pdf.ln(10)
        pdf.cell(0, 10, "FIRMA DEL CLIENTE: ______________________________", ln=True)

    return bytes(pdf.output())

# --- INTERFACCIA ---
with st.form("form_noleggio"):
    st.subheader("📝 Nuova Pratica")
    c1, c2 = st.columns(2)
    nome = c1.text_input("Nome")
    cognome = c1.text_input("Cognome")
    cf = c1.text_input("Codice Fiscale")
    tel = c1.text_input("Telefono")
    
    targa = c2.text_input("Targa").upper()
    patente = c2.text_input("Numero Patente")
    prezzo = c2.number_input("Prezzo Totale (€)", min_value=0.0)
    
    st.write("📸 *FOTO PATENTE*")
    foto = st.camera_input("Scatta")
    
    st.write("✍️ *FIRMA DIGITALE*")
    canvas = st_canvas(stroke_width=2, height=100, width=350, key="firma_pro")
    
    st.warning("⚠️ *CLAUSOLE LEGALI & PRIVACY*")
    privacy = st.checkbox("Dichiaro di aver letto le condizioni e acconsento al trattamento dei dati (GDPR)")

    if st.form_submit_button("💾 SALVA E GENERA"):
        if nome and targa and privacy:
            dati = {
                "nome": nome, "cognome": cognome, "codice_fiscale": cf,
                "telefono": tel, "numero_patente": patente, "targa": targa,
                "prezzo": prezzo, "privacy_accettata": True
            }
            supabase.table("contratti").insert(dati).execute()
            st.success("✅ Contratto registrato con successo!")
        else:
            st.error("❌ Errore: Assicurati di aver inserito Nome, Targa e accettato la Privacy!")

# --- ARCHIVIO ---
st.divider()
st.header("🗄️ Archivio Contratti")
res = supabase.table("contratti").select("*").order("id", desc=True).execute()

for c in res.data:
    with st.expander(f"📄 {c.get('nome','')} - {c.get('targa','')}"):
        col_c, col_r = st.columns(2)
        col_c.download_button("📜 CONTRATTO LEGALE", genera_documento(c, "CONTRATTO"), f"Contratto_{c['id']}.pdf", "application/pdf", key=f"c_{c['id']}")
        col_r.download_button("💰 RICEVUTA PAGAMENTO", genera_documento(c, "RICEVUTA"), f"Ricevuta_{c['id']}.pdf", "application/pdf", key=f"r_{c['id']}")
