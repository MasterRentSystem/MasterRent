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
    
    pdf.ln(5)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 8, "CONDIZIONI E PRIVACY:", ln=True)
    pdf.set_font("Arial", "", 8)
    clausole_pdf = ("1. Il cliente e responsabile di danni, furti e multe.\n"
                    "2. Riconsegna con stesso livello di carburante.\n"
                    "3. I dati sono trattati secondo il GDPR (UE 2016/679).")
    pdf.multi_cell(0, 4, clausole_pdf)

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

    # --- FOTO DOCUMENTI ---
    st.subheader("📸 Foto Documento d'Identità")
    c1, c2 = st.columns(2)
    with c1:
        f_fronte = st.file_uploader("Fronte Documento", type=['png', 'jpg', 'jpeg'])
    with c2:
        f_retro = st.file_uploader("Retro Documento", type=['png', 'jpg', 'jpeg'])

    # --- CLAUSOLE DA LEGGERE PRIMA DI FIRMARE ---
    st.divider()
    st.subheader("⚖️ Termini, Condizioni e Privacy")
    st.info("""
    *CONTRATTO DI NOLEGGIO - BATTAGLIA RENT*
    
    1. *Responsabilità:* Il cliente dichiara di ricevere il veicolo in ottimo stato. È responsabile di ogni danno causato al veicolo, a sé stesso o a terzi durante il periodo di noleggio.
    2. *Multe e Infrazioni:* Ogni contravvenzione al Codice della Strada è a totale carico del locatario.
    3. *Carburante:* Il veicolo deve essere riconsegnato con lo stesso livello di carburante presente alla consegna.
    4. *Furto:* In caso di furto, il cliente è tenuto a sporgere denuncia immediata e a risarcire il valore del veicolo se non diversamente concordato.
    
    *INFORMATIVA PRIVACY (GDPR):*
    Ai sensi del Reg. UE 2016/679, i dati personali qui raccolti verranno utilizzati esclusivamente per la gestione del contratto di noleggio e per adempimenti di legge. Non verranno ceduti a terzi per scopi pubblicitari.
    """)
    
    accetto = st.checkbox("CONFERMO DI AVER LETTO E ACCETTO TUTTE LE CLAUSOLE SOPRA RIPORTATE")

    # --- FIRMA DIGITALE ---
    st.subheader("✍️ Firma del Cliente")
    canvas = st_canvas(stroke_width=3, stroke_color="#000", background_color="#eee", height=150, width=400, drawing_mode="freedraw", key="canvas")

    if st.button("💾 SALVA CONTRATTO"):
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
                st.success("✅ Contratto salvato con successo!")
                st.rerun()
            except Exception as e:
                st.error(f"Errore: {e}")
        else:
            st.error("⚠️ Attenzione! Devi accettare le clausole (spunta la casella) e inserire i dati prima di salvare.")

    # ARCHIVIO
    st.divider()
    st.header("📋 Archivio Contratti")
    try:
        res = supabase.table("contratti").select("*").order("id", desc=True).execute()
        for c in res.data:
            with st.expander(f"ID: {c['id']} - {c['nome']} {c['cognome']} ({c['targa']})"):
                col1, col2, col3 = st.columns(3)
                col1.download_button("📜 Contratto", genera_pdf_tipo(c, "CONTRATTO"), f"C_{c['id']}.pdf")
                col2.download_button("💰 Ricevuta", genera_pdf_tipo(c, "FATTURA"), f"R_{c['id']}.pdf")
                col3.download_button("🚨 Multe", genera_pdf_tipo(c, "MULTE"), f"M_{c['id']}.pdf")
    except:
        st.info("Archivio vuoto.")
