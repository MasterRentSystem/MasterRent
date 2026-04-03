import streamlit as st
import datetime
from fpdf import FPDF
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io
import base64

st.set_page_config(layout="wide", page_title="Battaglia Rent Pro")

# -------------------------
# DATI AZIENDA
# -------------------------

DITTA = "BATTAGLIA MARIANNA"
INDIRIZZO_FISCALE = "Via Cognole, 5 - 80075 Forio (NA)"
DATI_IVA = "C.F. BTTMNN87A53Z112S - P. IVA 10252601215"

# -------------------------
# DATABASE
# -------------------------

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# -------------------------
# PROTEZIONE CARATTERI
# -------------------------

def safe_text(text):
    if text is None:
        return ""
    return str(text).encode("latin-1", "replace").decode("latin-1")

# -------------------------
# NUMERO FATTURA PROGRESSIVO
# -------------------------

def prossimo_numero_fattura():

    try:

        res = (
            supabase.table("contratti")
            .select("numero_fattura")
            .order("numero_fattura", desc=True)
            .limit(1)
            .execute()
        )

        if res.data:
            ultimo = res.data[0]["numero_fattura"]

            if ultimo:
                return int(ultimo) + 1

        return 1

    except:
        return 1

# -------------------------
# GENERATORE PDF DEFINITIVO
# -------------------------

def genera_pdf_tipo(c, tipo="CONTRATTO"):

    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 6, safe_text(DITTA), ln=True)

    pdf.set_font("Arial", "", 9)
    pdf.cell(0, 5, safe_text(INDIRIZZO_FISCALE), ln=True)
    pdf.cell(0, 5, safe_text(DATI_IVA), ln=True)

    pdf.ln(8)

    titoli = {
        "CONTRATTO": "CONTRATTO DI NOLEGGIO / RENTAL AGREEMENT",
        "FATTURA": "RICEVUTA DI PAGAMENTO / RECEIPT",
        "MULTE": "MODULO DATI CONDUCENTE / DRIVER DATA"
    }

    pdf.set_font("Arial", "B", 15)

    pdf.cell(
        0,
        10,
        safe_text(titoli.get(tipo, "DOCUMENTO")),
        ln=True,
        align="C"
    )

    pdf.ln(6)

    pdf.set_font("Arial", "", 10)

    testo = (
        f"Cliente / Customer: {safe_text(c.get('nome'))} "
        f"{safe_text(c.get('cognome'))}\n"
        f"Codice Fiscale: {safe_text(c.get('codice_fiscale'))}\n"
        f"Patente n.: {safe_text(c.get('numero_patente'))}\n"
        f"Targa / Plate: {safe_text(c.get('targa'))}\n"
        f"Periodo: dal {safe_text(c.get('inizio'))} "
        f"al {safe_text(c.get('fine'))}\n"
        f"Prezzo Totale: EUR {safe_text(c.get('prezzo'))}\n"
        f"Deposito Cauzione: EUR {safe_text(c.get('deposito'))}"
    )

    pdf.multi_cell(0, 6, testo)

    # FATTURA

    if tipo == "FATTURA":

        pdf.ln(6)

        pdf.set_font("Arial", "B", 12)

        pdf.cell(
            0,
            8,
            f"Numero Ricevuta: {safe_text(c.get('numero_fattura'))}",
            ln=True
        )

    # CLAUSOLE

    if tipo == "CONTRATTO":

        pdf.ln(6)

        pdf.set_font("Arial", "B", 10)

        pdf.cell(
            0,
            8,
            "CONDIZIONI / TERMS",
            ln=True
        )

        pdf.set_font("Arial", "", 8)

        clausole = (
            "1. Il cliente è responsabile di danni, furti e multe.\n"
            "2. Riconsegna con stesso livello carburante.\n"
            "3. Deposito restituito alla riconsegna.\n"
            "4. Dati trattati secondo GDPR.\n\n"
            "1. Customer responsible for damages, theft and fines.\n"
            "2. Return with same fuel level.\n"
            "3. Deposit refunded at return.\n"
            "4. Data processed under GDPR."
        )

        pdf.multi_cell(0, 4, clausole)

    # MODULO MULTE

    if tipo == "MULTE":

        pdf.ln(6)

        pdf.multi_cell(
            0,
            6,
            "Il conducente sopra indicato era alla guida del veicolo ed è responsabile per eventuali violazioni del Codice della Strada."
        )

    # FIRMA DINAMICA

    if c.get("firma"):

        try:

            firma_bytes = base64.b64decode(c["firma"])

            img = Image.open(io.BytesIO(firma_bytes))

            temp = io.BytesIO()

            img.save(temp, format="PNG")

            temp.seek(0)

            y = pdf.get_y() + 10

            if y > 250:
                pdf.add_page()
                y = 20

            pdf.image(
                temp,
                x=130,
                y=y,
                w=50
            )

        except:
            pass

    pdf.ln(30)

    pdf.set_font("Arial", "B", 10)

    pdf.cell(
  pdf.cell(
        0,
        10,
        "Firma Cliente / Customer Signature: ___________________",
        ln=True,
        align="R"
    )

    return bytes(pdf.output())

# -------------------------
# LOGIN
# -------------------------
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False

if not st.session_state.autenticato:

    st.title("Accesso Battaglia Rent")

    pwd = st.text_input("Password", type="password")

    if st.button("Entra"):

        if pwd == st.secrets["APP_PASSWORD"]:

            st.session_state.autenticato = True
            st.rerun()

        else:

            st.error("Password errata")

else:

    st.header(f"Gestione {DITTA}")

    col1, col2 = st.columns(2)

    with col1:

        nome = st.text_input("Nome")
        cognome = st.text_input("Cognome")
        cf = st.text_input("Codice Fiscale")
        indirizzo = st.text_input("Residenza")
        data_n = st.date_input("Data nascita")
        luogo_n = st.text_input("Luogo nascita")

    with col2:

        pat = st.text_input("Numero patente")
        targa = st.text_input("Targa").upper().strip()

        inizio = st.date_input(
            "Inizio noleggio",
            value=datetime.date.today()
        )

        fine = st.date_input(
            "Fine noleggio",
            value=datetime.date.today() + datetime.timedelta(days=1)
        )

        prezzo = st.number_input(
            "Prezzo",
            min_value=0.0
        )

        deposito = st.number_input(
            "Deposito",
            min_value=0.0
        )

    if fine <= inizio:

        st.error("Data fine non valida")

        st.stop()

    st.subheader("Firma cliente")

    canvas = st_canvas(
        stroke_width=3,
        stroke_color="#000",
        background_color="#eee",
        height=150,
        width=400
    )

    accetto = st.checkbox(
        "Accetto condizioni e privacy"
    )

    if st.button("SALVA CONTRATTO"):

        if not nome or not cognome or not targa:

            st.error(
                "Inserisci Nome, Cognome e Targa"
            )

            st.stop()

        if not accetto:

            st.error(
                "Accetta condizioni"
            )

            st.stop()

        numero = prossimo_numero_fattura()

        firma_base64 = None

        if canvas.image_data is not None:

            img = Image.fromarray(
                canvas.image_data.astype("uint8")
            )

            buffer = io.BytesIO()

            img.save(buffer, format="PNG")

            firma_base64 = base64.b64encode(
                buffer.getvalue()
            ).decode()

        dati = {

            "nome": nome,
            "cognome": cognome,
            "codice_fiscale": cf,
            "indirizzo": indirizzo,
            "numero_patente": pat,
            "targa": targa,
            "prezzo": prezzo,
            "deposito": deposito,
            "luogo_nascita": luogo_n,
            "data_nascita": str(data_n),
            "inizio": str(inizio),
            "fine": str(fine),
            "firma": firma_base64,
            "numero_fattura": numero

        }

        supabase.table("contratti").insert(dati).execute()

        st.success("Contratto salvato")

        st.rerun()

    st.divider()

    st.header("Archivio")

    res = (
        supabase.table("contratti")
        .select("*")
        .order("id", desc=True)
        .execute()
    )

    for c in res.data:

        with st.expander(
            f"{c['nome']} {c['cognome']} - {c['targa']}"
        ):

            col1, col2, col3 = st.columns(3)

            col1.download_button(
                "Contratto",
                data=genera_pdf_tipo(c, "CONTRATTO"),
                file_name=f"Contratto_{c['id']}.pdf"
            )

            col2.download_button(
                "Ricevuta",
                data=genera_pdf_tipo(c, "FATTURA"),
                file_name=f"Ricevuta_{c['numero_fattura']}.pdf"
            )

            col3.download_button(
                "Modulo Multe",
                data=genera_pdf_tipo(c, "MULTE"),
                file_name=f"Multe_{c['id']}.pdf"
            )
