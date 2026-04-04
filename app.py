import streamlit as st
import datetime
from fpdf import FPDF
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io
import base64

# CONFIG
st.set_page_config(
    layout="wide",
    page_title="Battaglia Rent Pro",
    initial_sidebar_state="collapsed"
)

# DATI AZIENDA
DITTA = "BATTAGLIA MARIANNA"
INDIRIZZO_FISCALE = "Via Cognole, 5 - 80075 Forio (NA)"
DATI_IVA = "C.F. BTTMNN87A53Z112S - P. IVA 10252601215"

# DATABASE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# ------------------------------------------------
# UTILITY
# ------------------------------------------------

def safe_text(text):
    if text is None:
        return ""
    return str(text).encode("latin-1", "replace").decode("latin-1")

def prossimo_numero_fattura():
    try:
        res = (
            supabase
            .table("contratti")
            .select("numero_fattura")
            .order("numero_fattura", desc=True)
            .limit(1)
            .execute()
        )

        if res.data:
            return int(res.data[0]["numero_fattura"]) + 1

        return 1

    except:
        return 1

def upload_to_supabase(file, targa, prefix):
    try:

        file_name = (
            f"{prefix}{targa}"
            f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        )

        supabase.storage.from_("documenti").upload(
            file_name,
            file.getvalue()
        )

        url = (
            supabase
            .storage
            .from_("documenti")
            .get_public_url(file_name)
        )

        return url

    except:
        return None

# ------------------------------------------------
# PDF
# ------------------------------------------------

def genera_pdf_tipo(c, tipo):

    pdf = FPDF()
    pdf.add_page()

    oggi = datetime.date.today().strftime("%d/%m/%Y")

    # HEADER
    pdf.set_font("Arial", "B", 12)

    pdf.cell(
        0,
        6,
        safe_text(DITTA),
        ln=True
    )

    pdf.set_font("Arial", "", 9)

    pdf.cell(
        0,
        5,
        safe_text(INDIRIZZO_FISCALE),
        ln=True
    )

    pdf.cell(
        0,
        5,
        safe_text(DATI_IVA),
        ln=True
    )

    pdf.ln(8)

    # ------------------------------------------------
    # CONTRATTO
    # ------------------------------------------------

    if tipo == "CONTRATTO":

        pdf.set_font("Arial", "B", 15)

        pdf.cell(
            0,
            10,
            "CONTRATTO DI NOLEGGIO / RENTAL AGREEMENT",
            ln=True,
            align="C",
            border="B"
        )

        pdf.ln(8)

        pdf.set_font("Arial", "", 10)

        testo = f"""
Cliente: {c.get('nome')} {c.get('cognome')}

Nato a: {c.get('luogo_nascita')}
Data nascita: {c.get('data_nascita')}

Patente: {c.get('numero_patente')}

Targa: {c.get('targa')}

Periodo:
dal {c.get('inizio')}
al {c.get('fine')}

Prezzo: EUR {c.get('prezzo')}
Deposito: EUR {c.get('deposito')}
"""

        pdf.multi_cell(
            0,
            6,
            safe_text(testo)
        )

        pdf.ln(6)

        pdf.set_font("Arial", "B", 10)

        pdf.cell(
            0,
            6,
            "CONDIZIONI / TERMS",
            ln=True
        )

        pdf.set_font("Arial", "", 8)

        clausole = """

1.⁠ ⁠Il cliente è responsabile per danni, furto e multe.
2.⁠ ⁠Il veicolo deve essere restituito con lo stesso carburante.
3.⁠ ⁠Il deposito viene restituito alla riconsegna.
4.⁠ ⁠I dati sono trattati secondo normativa GDPR.

1.⁠ ⁠Customer is responsible for damages, theft and fines.
2.⁠ ⁠Vehicle must be returned with same fuel level.
3.⁠ ⁠Deposit refunded at return.
4.⁠ ⁠Data processed under GDPR.
"""

        pdf.multi_cell(
            0,
            4,
            safe_text(clausole)
        )

    # ------------------------------------------------
    # FATTURA
    # ------------------------------------------------

    if tipo == "FATTURA":

        pdf.set_font("Arial", "B", 15)

        pdf.cell(
            0,
            10,
            "RICEVUTA DI PAGAMENTO / RECEIPT",
            ln=True,
            align="C",
            border="B"
        )

        pdf.ln(10)

        pdf.set_font("Arial", "", 10)

        testo = f"""
Numero Ricevuta:
{c.get('numero_fattura')}

Data emissione:
{oggi}

Cliente:
{c.get('nome')} {c.get('cognome')}

Targa:
{c.get('targa')}

Periodo:
dal {c.get('inizio')}
al {c.get('fine')}
"""

        pdf.multi_cell(
            0,
            6,
            safe_text(testo)
        )

        pdf.ln(8)

        pdf.set_font("Arial", "B", 16)

        pdf.cell(
            0,
            15,
            f"TOTALE INCASSATO: EUR {c.get('prezzo')}",
            ln=True,
            border=1,
            align="C"
        )

    # ------------------------------------------------
    # MULTE
    # ------------------------------------------------

    if tipo == "MULTE":

        pdf.set_font("Arial", "B", 14)

        pdf.cell(
            0,
            10,
            "COMUNICAZIONE DATI CONDUCENTE",
            ln=True,
            align="C",
            border="B"
        )

        pdf.ln(8)

        pdf.set_font("Arial", "", 10)

        testo = f"""
Spett.le Polizia Locale

La sottoscritta:

{DITTA}

dichiara che il veicolo:

TARGA:
{c.get('targa')}

DATA:
{c.get('inizio')}

era condotto dal seguente soggetto:

NOME:
{c.get('nome')} {c.get('cognome')}

NATO A:
{c.get('luogo_nascita')}

DATA NASCITA:
{c.get('data_nascita')}

PATENTE:
{c.get('numero_patente')}

Data:
{oggi}
"""

        pdf.multi_cell(
            0,
            6,
            safe_text(testo)
        )

    # ------------------------------------------------
    # FIRMA
    # ------------------------------------------------

    if c.get("firma"):

        try:

            firma_bytes = base64.b64decode(c["firma"])

            y = pdf.get_y() + 10

            if y > 250:
                pdf.add_page()
                y = 20

            pdf.image(
                io.BytesIO(firma_bytes),
                x=130,
                y=y,
                w=50
            )

        except:
            pass

    pdf.ln(25)

    pdf.set_font("Arial", "B", 10)

   pdf.cell(
    0,
    10,
    "Firma Cliente",
    ln=True,
    align="R"
)

# FIX DEFINITIVO STREAMLIT / FPDF
pdf_bytes = pdf.output(dest="S")

if isinstance(pdf_bytes, str):
    pdf_bytes = pdf_bytes.encode("latin-1")

return pdf_bytes
# ------------------------------------------------
# LOGIN
# ------------------------------------------------

if "autenticato" not in st.session_state:
    st.session_state.autenticato = False

if not st.session_state.autenticato:

    st.title("Login")

    pwd = st.text_input(
        "Password",
        type="password"
    )

    if st.button("Entra"):

        if pwd == st.secrets["APP_PASSWORD"]:

            st.session_state.autenticato = True
            st.rerun()

else:

    st.title("Nuovo Noleggio Scooter")

    with st.form(
        "nuovo_noleggio",
        clear_on_submit=True
    ):

        col1, col2 = st.columns(2)

        nome = col1.text_input("Nome")

        cognome = col1.text_input("Cognome")

        targa = col2.text_input("Targa").upper()

        prezzo = col2.number_input(
            "Prezzo (€)",
            min_value=0.0
        )

        luogo_nascita = col1.text_input(
            "Luogo nascita"
        )

        data_nascita = col1.text_input(
            "Data nascita"
        )

        patente = col2.text_input(
            "Numero patente"
        )

        deposito = col2.number_input(
            "Deposito (€)",
            min_value=0.0
        )

        data_inizio = col1.date_input(
            "Inizio"
        )

        data_fine = col2.date_input(
            "Fine"
        )

        st.subheader("Foto patente")

        fronte = st.file_uploader(
            "Fronte",
            type=["jpg", "png"]
        )

        retro = st.file_uploader(
            "Retro",
            type=["jpg", "png"]
        )

        st.subheader("Firma cliente")

        canvas = st_canvas(
            stroke_width=3,
            stroke_color="#000",
            background_color="#eee",
            height=150,
            width=400,
            key="firma"
        )

        if st.form_submit_button("SALVA"):

            firma_b64 = ""

            if canvas.image_data is not None:

                img = Image.fromarray(
                    canvas.image_data.astype("uint8")
                )

                buffer = io.BytesIO()

                img.save(
                    buffer,
                    format="PNG"
                )

                firma_b64 = base64.b64encode(
                    buffer.getvalue()
                ).decode()

            url_fronte = upload_to_supabase(
                fronte,
                targa,
                "fronte"
            )

            url_retro = upload_to_supabase(
                retro,
                targa,
                "retro"
            )

            numero = prossimo_numero_fattura()

            dati = dict(

                nome=nome,
                cognome=cognome,
                targa=targa,

                prezzo=prezzo,
                deposito=deposito,

                inizio=str(data_inizio),
                fine=str(data_fine),

                firma=firma_b64,

                numero_fattura=numero,

                luogo_nascita=luogo_nascita,
                data_nascita=data_nascita,

                numero_patente=patente,

                url_fronte=url_fronte,
                url_retro=url_retro

            )

            supabase.table(
                "contratti"
            ).insert(
                dati
            ).execute()

            st.success(
                "Contratto salvato correttamente"
            )

            st.rerun()

    st.divider()

    st.subheader("Archivio")

    res = (
        supabase
        .table("contratti")
        .select("*")
        .order("id", desc=True)
        .execute()
    )

    for c in res.data:

        with st.expander(
            f"{c['numero_fattura']} - {c['nome']} {c['cognome']} ({c['targa']})"
        ):

            col1, col2, col3 = st.columns(3)

            col1.download_button(
                "Contratto",
                genera_pdf_tipo(c, "CONTRATTO"),
                f"Contratto_{c['id']}.pdf",
                mime="application/pdf"
            )

            col2.download_button(
                "Ricevuta",
                genera_pdf_tipo(c, "FATTURA"),
                f"Ricevuta_{c['id']}.pdf",
                mime="application/pdf"
            )

            col3.download_button(
                "Multe",
                genera_pdf_tipo(c, "MULTE"),
                f"Multe_{c['id']}.pdf",
                mime="application/pdf"
            )

            if c.get("url_fronte"):
                st.link_button(
                    "Vedi patente fronte",
                    c["url_fronte"]
                )

            if c.get("url_retro"):
                st.link_button(
                    "Vedi patente retro",
                    c["url_retro"]
                )
