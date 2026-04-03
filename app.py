import streamlit as st
import datetime
from fpdf import FPDF
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io
import base64

st.set_page_config(layout="wide", page_title="Battaglia Rent Pro")

# --- DATI AZIENDA ---
DITTA = "BATTAGLIA MARIANNA"
INDIRIZZO_FISCALE = "Via Cognole, 5 - 80075 Forio (NA)"
DATI_IVA = "C.F. BTTMNN87A53Z112S - P. IVA 10252601215"

# --- DATABASE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def safe_text(text):
    if text is None: return ""
    return str(text).encode("latin-1", "replace").decode("latin-1")

def prossimo_numero_fattura():
    try:
        res = supabase.table("contratti").select("numero_fattura").order("numero_fattura", desc=True).limit(1).execute()
        if res.data and res.data[0]["numero_fattura"]:
            return int(res.data[0]["numero_fattura"]) + 1
        return 1
    except: return 1

# --- GENERATORE PDF CON CLAUSOLE LEGALI ---
def genera_pdf_tipo(c, tipo="CONTRATTO"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 6, safe_text(DITTA), ln=True)
    pdf.set_font("Arial", "", 9)
    pdf.cell(0, 5, safe_text(INDIRIZZO_FISCALE), ln=True)
    pdf.cell(0, 5, safe_text(DATI_IVA), ln=True)
    pdf.ln(8)

    titoli = {"CONTRATTO": "CONTRATTO DI NOLEGGIO / RENTAL AGREEMENT", "FATTURA": "RICEVUTA DI PAGAMENTO / RECEIPT", "MULTE": "MODULO DATI CONDUCENTE"}
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, safe_text(titoli.get(tipo, "DOCUMENTO")), ln=True, align="C")
    pdf.ln(5)

    # Dati Cliente
    pdf.set_font("Arial", "", 10)
    testo_dati = (f"Cliente: {safe_text(c.get('nome'))} {safe_text(c.get('cognome'))}\n"
                  f"C.F.: {safe_text(c.get('codice_fiscale'))} - Patente: {safe_text(c.get('numero_patente'))}\n"
                  f"Residenza: {safe_text(c.get('indirizzo'))}\n"
                  f"Veicolo Targa: {safe_text(c.get('targa'))}\n"
                  f"Periodo: dal {safe_text(c.get('inizio'))} al {safe_text(c.get('fine'))}")
    pdf.multi_cell(0, 6, testo_dati)

    if tipo == "CONTRATTO":
        pdf.ln(5)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 7, "CONDIZIONI GENERALI DI NOLEGGIO:", ln=True)
        pdf.set_font("Arial", "", 8)
        clausole = (
            "1. STATO VEICOLO: Il locatario riceve il veicolo in ottimo stato e con il pieno/livello carburante indicato.\n"
            "2. RESPONSABILITA: Il cliente e responsabile per danni al veicolo, furto, incendio e danni a terzi.\n"
            "3. INFRAZIONI: Ogni sanzione amministrativa (multe, ZTL) occorsa durante il noleggio e a carico del locatario.\n"
            "4. MANUTENZIONE: E vietato l'uso del veicolo su strade non asfaltate o per scopi impropri.\n"
            "5. RICONSEGNA: Il veicolo deve essere riconsegnato entro l'orario stabilito, pena l'addebito di una giornata extra.\n"
            "6. PRIVACY (GDPR): Il cliente autorizza il trattamento dei dati personali ai sensi del Reg. UE 2016/679 per finalita contrattuali e amministrative."
        )
        pdf.multi_cell(0, 4, safe_text(clausole))

    if tipo == "FATTURA":
        pdf.ln(10)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, f"TOTALE PAGATO: EUR {safe_text(c.get('prezzo'))}", ln=True)

    # Firma
    if c.get("firma"):
        try:
            firma_bytes = base64.b64decode(c["firma"])
            img = Image.open(io.BytesIO(firma_bytes))
            temp = io.BytesIO(); img.save(temp, format="PNG"); temp.seek(0)
            y_pos = pdf.get_y() + 10
            if y_pos > 250: pdf.add_page(); y_pos = 20
            pdf.image(temp, x=130, y=y_pos, w=50)
        except: pass

    pdf.ln(25)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 10, "Firma del Cliente per Accettazione", ln=True, align="R")
    return bytes(pdf.output())

# --- INTERFACCIA APP ---
if "autenticato" not in st.session_state: st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.title("Accesso Battaglia Rent")
    pwd = st.text_input("Password", type="password")
    if st.button("Entra"):
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state.autenticato = True
            st.rerun()
else:
    st.header(f"Nuovo Contratto - {DITTA}")
    
    with st.form("modulo_noleggio"):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome")
            cognome = st.text_input("Cognome")
            cf = st.text_input("Codice Fiscale")
            indirizzo = st.text_input("Residenza (Via, Città)")
        with col2:
            patente = st.text_input("Numero Patente")
            targa = st.text_input("Targa Veicolo").upper()
            prezzo = st.number_input("Prezzo Totale (€)", min_value=0.0)
            deposito = st.number_input("Cauzione (solo per memoria)", min_value=0.0)
        
        c3, c4 = st.columns(2)
        with c3: inizio = st.date_input("Inizio Noleggio")
        with c4: fine = st.date_input("Fine Noleggio")

        st.divider()
        st.subheader("📸 Documenti")
        f_fronte = st.file_uploader("Carica Foto FRONTE Documento", type=["jpg", "png", "jpeg"])
        f_retro = st.file_uploader("Carica Foto RETRO Documento", type=["jpg", "png", "jpeg"])

        st.divider()
        st.subheader("⚖️ Termini Legali e Privacy")
        st.warning("""
        *CONDIZIONI DI NOLEGGIO:* Il cliente dichiara di essere responsabile per multe, danni e furto. 
        *PRIVACY:* I dati saranno trattati secondo il Regolamento UE 2016/679 (GDPR).
        """)
        accetto_clausole = st.checkbox("DICHIARO DI AVER LETTO E ACCETTO LE CONDIZIONI E L'INFORMATIVA PRIVACY")

        st.write("Firma qui sotto:")
        canvas = st_canvas(stroke_width=3, stroke_color="#000", background_color="#eee", height=150, width=400, key="firma")

        salva = st.form_submit_button("💾 SALVA E GENERA CONTRATTO")

        if salva:
            if not accetto_clausole:
                st.error("⚠️ Devi spuntare la casella di accettazione clausole per continuare!")
            elif not nome or not targa:
                st.error("⚠️ Nome e Targa sono obbligatori!")
            else:
                # Conversione Firma
                firma_b64 = ""
                if canvas.image_data is not None:
                    img = Image.fromarray(canvas.image_data.astype("uint8"))
                    buf = io.BytesIO(); img.save(buf, format="PNG")
                    firma_b64 = base64.b64encode(buf.getvalue()).decode()
                
                num_fatt = prossimo_numero_fattura()
                dati = {
                    "nome": nome, "cognome": cognome, "codice_fiscale": cf, "indirizzo": indirizzo,
                    "numero_patente": patente, "targa": targa, "prezzo": prezzo, "deposito": deposito,
                    "inizio": str(inizio), "fine": str(fine), "firma": firma_b64, "numero_fattura": num_fatt
                }
                supabase.table("contratti").insert(dati).execute()
                st.success(f"✅ Contratto n. {num_fatt} salvato con successo!")
                st.rerun()

    # ARCHIVIO
    st.divider()
    st.header("📋 Archivio Contratti")
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"{c['nome']} {c['cognome']} - {c['targa']}"):
            col_a, col_b, col_c = st.columns(3)
            col_a.download_button("📜 Scarica Contratto", genera_pdf_tipo(c, "CONTRATTO"), f"Contratto_{c['id']}.pdf")
            col_b.download_button("💰 Scarica Ricevuta", genera_pdf_tipo(c, "FATTURA"), f"Ricevuta_{c['id']}.pdf")
            col_c.download_button("🚨 Modulo Multe", genera_pdf_tipo(c, "MULTE"), f"Multe_{c['id']}.pdf")
