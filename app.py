import streamlit as st
import datetime
import base64
from fpdf import FPDF
from supabase import create_client
from streamlit_drawable_canvas import st_canvas

st.set_page_config(layout="wide", page_title="MasterRent Pro")
st.title("🛵 MasterRent - Sistema Professionale")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def clean(t):
    return str(t).encode("latin-1", "ignore").decode("latin-1") if t else ""

# --- PDF GENERATOR ---
def genera_pdf(c, tipo="CONTRATTO"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    titolo = f"{tipo} N. {c.get('numero_fattura', 'N/A')}"
    pdf.cell(0, 10, titolo, ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    info = f"Cliente: {c.get('nome','')} {c.get('cognome','')}\nTarga: {c.get('targa','')}\nData: {c.get('data_contratto','')[:10]}"
    if tipo == "CONTRATTO":
        info += f"\nPatente: {c.get('numero_patente','')}\n\nClausole Legali:\nIl locatario accetta le condizioni di noleggio..."
    else:
        info += f"\n\nTOTALE PAGATO: Euro {c.get('prezzo', 0)}"
    pdf.multi_cell(0, 10, clean(info))
    return pdf.output(dest="S").encode("latin-1")

# --- FORM DI INSERIMENTO ---
with st.expander("📝 CREA NUOVO NOLEGGIO", expanded=True):
    with st.form("noleggio_form"):
        col1, col2 = st.columns(2)
        n = col1.text_input("Nome")
        cog = col1.text_input("Cognome")
        pat = col2.text_input("N. Patente")
        tar = col2.text_input("Targa").upper()
        pre = col2.number_input("Prezzo Euro", min_value=0.0)
        
        st.write("📸 *DOCUMENTI*")
        foto = st.camera_input("Scatta foto Patente")
        
        st.write("✍️ *FIRMA*")
        canvas = st_canvas(stroke_width=3, height=150, width=400, key="firma_new")
        
        if st.form_submit_button("SALVA E GENERA"):
            # Logica salvataggio (semplificata per evitare errori)
            dati = {"nome": n, "cognome": cog, "targa": tar, "numero_patente": pat, "prezzo": pre}
            supabase.table("contratti").insert(dati).execute()
            st.success("Salvato! Ricarica la pagina per vedere l'archivio.")

# --- ARCHIVIO ---
st.header("🗄️ Archivio")
res = supabase.table("contratti").select("*").order("id", desc=True).execute()
for c in res.data:
    # Usiamo .get() per evitare il crash KeyError
    label = f"📄 {c.get('nome','')} {c.get('cognome','')} - {c.get('targa','')}"
    with st.expander(label):
        c1, c2 = st.columns(2)
        c1.download_button("📜 CONTRATTO", genera_pdf(c, "CONTRATTO"), f"C_{c['id']}.pdf", key=f"c_{c['id']}")
        c2.download_button("💰 RICEVUTA", genera_pdf(c, "RICEVUTA"), f"R_{c['id']}.pdf", key=f"r_{c['id']}")
