import streamlit as st
import datetime
from fpdf import FPDF
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io

st.set_page_config(layout="wide", page_title="Battaglia Rent Pro")

# --- DATI FISCALI ---
DITTA = "BATTAGLIA MARIANNA"
INDIRIZZO_FISCALA = "Via Cognole, 5 - 80075 Forio (NA)"
DATI_IVA = "C.F. BTTMNN87A53Z112S - P. IVA 10252601215"

# --- DATABASE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- GENERATORE PDF ---
def genera_pdf_tipo(c, tipo="CONTRATTO", firma_data=None):
    pdf = FPDF()
    pdf.add_page()
    
    # Intestazione Fiscale
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 6, DITTA, ln=True)
    pdf.set_font("Arial", "", 9)
    pdf.cell(0, 5, INDIRIZZO_FISCALA, ln=True)
    pdf.cell(0, 5, DATI_IVA, ln=True)
    pdf.ln(10)
    
    # Titolo
    titoli = {"CONTRATTO": "CONTRATTO DI NOLEGGIO", "FATTURA": "RICEVUTA DI PAGAMENTO", "MULTE": "MODULO DATI CONDUCENTE"}
    pdf.set_font("Arial", "B", 15)
    pdf.cell(0, 10, titoli.get(tipo, "DOCUMENTO"), ln=True, align="C")
    pdf.ln(5)
    
    # Dati Completi
    pdf.set_font("Arial", "", 10)
    testo = (f"Cliente: {c.get('nome')} {c.get('cognome')}\n"
             f"Codice Fiscale: {c.get('codice_fiscale')}\n"
             f"Nato a: {c.get('luogo_nascita')} il {c.get('data_nascita')}\n"
             f"Residente in: {c.get('indirizzo')}\n"
             f"Patente n.: {c.get('numero_patente')} - Targa: {c.get('targa')}\n"
             f"Periodo: dal {c.get('inizio')} al {c.get('fine')}\n"
             f"Prezzo: {c.get('prezzo')} Euro - Deposito: {c.get('deposito')} Euro")
    pdf.multi_cell(0, 6, testo)
    
    if tipo == "CONTRATTO":
        pdf.ln(5)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 8, "CONDIZIONI E PRIVACY:", ln=True)
        pdf.set_font("Arial", "", 8)
        pdf.multi_cell(0, 4, "Il cliente accetta la piena responsabilita per danni, furti e multe. I dati sono trattati secondo il GDPR (UE 2016/679).")

    # Firma nel PDF
    if firma_data is not None:
        pdf.ln(10)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 10, "Firma del Cliente:", ln=True)
        img = Image.fromarray(firma_data.astype('uint8'), 'RGBA')
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        pdf.image(buf, x=10, y=pdf.get_y(), w=50)

    return bytes(pdf.output())

# --- ACCESSO ---
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.title("🔑 Accesso Battaglia Rent")
    pwd = st.text_input("Password", type="password")
    if st.button("Entra"):
        if pwd == "ischia2024":
            st.session_state.autenticato = True
            st.rerun()
else:
    st.header(f"📝 {DITTA}")
    
    # --- MODULO DATI ---
    col1, col2 = st.columns(2)
    with col1:
        nome = st.text_input("Nome")
        cognome = st.text_input("Cognome")
        cf = st.text_input("Codice Fiscale")
        indirizzo = st.text_input("Residenza (Via/Città)")
        data_n = st.date_input("Data di Nascita", value=None)
        luogo_n = st.text_input("Luogo di Nascita")
    with col2:
        pat = st.text_input("Patente n.")
        targa = st.text_input("Targa")
        inizio = st.date_input("Inizio Noleggio", value=datetime.date.today())
        fine = st.date_input("Fine Noleggio", value=datetime.date.today() + datetime.timedelta(days=1))
        prezzo = st.number_input("Prezzo (€)", min_value=0.0)
        deposito = st.number_input("Deposito (€)", min_value=0.0)

    # FIRMA
    st.subheader("✍️ Firma del Cliente")
    canvas = st_canvas(stroke_width=3, stroke_color="#000", background_color="#eee", height=150, width=400, drawing_mode="freedraw", key="canvas")

    accetto = st.checkbox("Il cliente accetta i Termini e la Privacy GDPR")

    if st.button("💾 SALVA E GENERA"):
        if accetto and nome and targa:
            try:
                dati = {
                    "nome": nome, "cognome": cognome, "codice_fiscale": cf,
                    "indirizzo": indirizzo, "targa": targa, "numero_patente": pat,
                    "prezzo": prezzo, "deposito": deposito, "luogo_nascita": luogo_n,
                    "data_nascita": str(data_n), "inizio": str(inizio), "fine": str(fine),
                    "privacy_accettata": True
                }
                supabase.table("contratti").insert(dati).execute()
                st.success("✅ Contratto salvato!")
                st.rerun()
            except Exception as e:
                st.error(f"Errore: {e}")
        else:
            st.warning("⚠️ Compila i dati obbligatori e fai firmare!")

    # ARCHIVIO
    st.divider()
    st.header("📋 Archivio")
    try:
        res = supabase.table("contratti").select("*").order("id", desc=True).execute()
        for c in res.data:
            with st.expander(f"Contratto {c['id']} - {c['nome']} {c['cognome']} ({c['targa']})"):
                col1, col2, col3 = st.columns(3)
                col1.download_button("📜 Contratto", genera_pdf_tipo(c, "CONTRATTO"), f"C_{c['id']}.pdf")
                col2.download_button("💰 Ricevuta", genera_pdf_tipo(c, "FATTURA"), f"R_{c['id']}.pdf")
                col3.download_button("🚨 Multe", genera_pdf_tipo(c, "MULTE"), f"M_{c['id']}.pdf")
    except:
        st.info("Archivio vuoto.")
