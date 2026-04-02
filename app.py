import streamlit as st
import datetime
import io
from fpdf import FPDF
from supabase import create_client
from streamlit_drawable_canvas import st_canvas

st.set_page_config(layout="wide", page_title="MasterRent Pro")
st.title("🛵 MasterRent - Gestione Completa")

# Connessione
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def clean(t):
    if not t: return ""
    return str(t).encode("latin-1", "ignore").decode("latin-1")

# --- FUNZIONE PDF CORRETTA (Senza AttributeError) ---
def genera_pdf_sicuro(c, tipo="CONTRATTO"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    
    titolo = f"{tipo} NOLEGGIO"
    pdf.cell(0, 10, titolo, ln=True, align="C")
    pdf.ln(10)
    
    pdf.set_font("Arial", size=11)
    # Anagrafica Completa
    linee = [
        f"CLIENTE: {c.get('nome','')} {c.get('cognome','')}",
        f"CODICE FISCALE: {c.get('codice_fiscale', 'N/A')}",
        f"PATENTE N.: {c.get('numero_patente', 'N/A')}",
        f"TELEFONO: {c.get('telefono', 'N/A')}",
        f"EMAIL: {c.get('email', 'N/A')}",
        f"TARGA VEICOLO: {c.get('targa', 'N/A')}",
        f"DATA: {c.get('data_contratto', str(datetime.date.today()))[:10]}",
        f"PREZZO: Euro {c.get('prezzo', 0)}"
    ]
    
    for linea in linee:
        pdf.cell(0, 8, clean(linea), ln=True)
    
    if tipo == "CONTRATTO":
        pdf.ln(5)
        pdf.set_font("Arial", "I", 9)
        clausole = "Il locatario dichiara di ricevere il veicolo in ottimo stato. Responsabile di multe e danni."
        pdf.multi_cell(0, 5, clean(clausole))
    
    # Ritorna i byte in modo corretto per Streamlit
    return bytes(pdf.output())

# --- FORM ANAGRAFICA COMPLETA ---
with st.expander("📝 NUOVO NOLEGGIO (Anagrafica Completa)", expanded=True):
    with st.form("main_form"):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Nome")
        cognome = col1.text_input("Cognome")
        cf = col1.text_input("Codice Fiscale")
        tel = col1.text_input("Telefono")
        
        email = col2.text_input("Email")
        patente = col2.text_input("N. Patente")
        targa = col2.text_input("Targa").upper()
        prezzo = col2.number_input("Prezzo totale (€)", min_value=0.0)
        
        st.write("📸 *FOTO DOCUMENTO*")
        foto = st.camera_input("Inquadra la patente")
        
        st.write("✍️ *FIRMA DIGITALE*")
        canvas_result = st_canvas(stroke_width=3, height=150, width=400, key="canvas")
        
        if st.form_submit_button("💾 SALVA TUTTO"):
            if nome and targa:
                dati = {
                    "nome": nome, "cognome": cognome, "codice_fiscale": cf,
                    "telefono": tel, "email": email, "numero_patente": patente,
                    "targa": targa, "prezzo": prezzo
                }
                supabase.table("contratti").insert(dati).execute()
                st.success("Dati salvati! Vai in archivio per scaricare i PDF.")
            else:
                st.error("Mancano Nome o Targa!")

# --- ARCHIVIO ---
st.divider()
st.header("🗄️ Archivio Contratti")
res = supabase.table("contratti").select("*").order("id", desc=True).execute()

for c in res.data:
    label = f"📄 {c.get('nome','')} {c.get('cognome','')} - {c.get('targa','')}"
    with st.expander(label):
        c1, c2 = st.columns(2)
        # Qui usiamo la nuova funzione genera_pdf_sicuro
        c1.download_button("📜 SCARICA CONTRATTO", genera_pdf_sicuro(c, "CONTRATTO"), f"C_{c['id']}.pdf", "application/pdf", key=f"btn_c_{c['id']}")
        c2.download_button("💰 SCARICA RICEVUTA", genera_pdf_sicuro(c, "RICEVUTA"), f"R_{c['id']}.pdf", "application/pdf", key=f"btn_r_{c['id']}")
