import streamlit as st
import datetime
from supabase import create_client, Client
from fpdf import FPDF
import base64
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io

st.set_page_config(page_title="Rent Scooter", layout="centered")

# -------------------------
# SUPABASE
# -------------------------

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(url, key)

# -------------------------
# LOGIN
# -------------------------

def check_password():

    if "auth" not in st.session_state:
        st.session_state.auth = False

    if not st.session_state.auth:

        st.title("Accesso")

        pwd = st.text_input(
            "Password",
            type="password"
        )

        if pwd == st.secrets["APP_PASSWORD"]:

            st.session_state.auth = True
            st.rerun()

        elif pwd != "":

            st.error("Password errata")

        return False

    return True


if not check_password():
    st.stop()

# -------------------------
# NUMERO FATTURA
# -------------------------

def get_next_fattura():

    year = datetime.date.today().year

    try:

        res = supabase.table("contratti") \
            .select("numero_fattura") \
            .order("numero_fattura", desc=True) \
            .limit(1) \
            .execute()

        if not res.data:

            return f"{year}-001"

        last = int(
            res.data[0]["numero_fattura"]
            .split("-")[1]
        )

        return f"{year}-{str(last + 1).zfill(3)}"

    except:

        return f"{year}-001"

# -------------------------
# UPLOAD FILE
# -------------------------

def upload_file(file, targa, tipo):

    if file is None:
        return None

    try:

        ext = file.name.split(".")[-1]

        nome = (
            f"{tipo}{targa}"
            f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            f".{ext}"
        )

        supabase.storage \
            .from_("documenti") \
            .upload(
                nome,
                file.getvalue()
            )

        url = supabase.storage \
            .from_("documenti") \
            .get_public_url(nome)

        return url

    except:

        st.error("Errore upload file")

        return None

# -------------------------
# PDF
# -------------------------

def genera_pdf(d, tipo):

    pdf = FPDF()
    pdf.add_page()

    def clean(t):

        if t is None:
            return ""

        return str(t) \
            .encode(
                "latin-1",
                "replace"
            ) \
            .decode(
                "latin-1"
            )

    pdf.set_font("Arial", size=11)

    if tipo == "CONTRATTO":

        testo = f"""
CONTRATTO DI NOLEGGIO

Cliente:
{d.get('nome')} {d.get('cognome')}

Nazionalità:
{d.get('nazionalita')}

Codice Fiscale:
{d.get('codice_fiscale')}

Patente:
{d.get('numero_patente')}

Telefono:
{d.get('telefono')}

Veicolo:
{d.get('targa')}

Periodo:
{d.get('inizio')} - {d.get('fine')}

Prezzo:
Euro {d.get('prezzo')}

Il cliente è responsabile per:

•⁠  ⁠danni
•⁠  ⁠multe
•⁠  ⁠uso improprio del veicolo
•⁠  ⁠restituzione in buone condizioni

Il cliente autorizza il trattamento dei dati personali
ai sensi del GDPR.
"""

        pdf.multi_cell(0, 8, clean(testo))

    if tipo == "FATTURA":

        pdf.multi_cell(
            0,
            8,
            clean(
                f"Ricevuta {d.get('numero_fattura')}\n"
                f"Cliente: {d.get('nome')} {d.get('cognome')}\n"
                f"Importo: Euro {d.get('prezzo')}"
            )
        )

    if tipo == "MULTE":

        pdf.multi_cell(
            0,
            8,
            clean(
                f"""
DICHIARAZIONE DATI CONDUCENTE

Veicolo:
{d.get('targa')}

Cliente:
{d.get('nome')} {d.get('cognome')}

Nazionalità:
{d.get('nazionalita')}

Patente:
{d.get('numero_patente')}

Telefono:
{d.get('telefono')}
"""
            )
        )

    pdf_bytes = pdf.output(dest="S")

    if isinstance(pdf_bytes, str):

        pdf_bytes = pdf_bytes.encode("latin-1")

    return pdf_bytes

# -------------------------
# MENU
# -------------------------

menu = st.sidebar.radio(

    "Menu",

    [
        "Nuovo Noleggio",
        "Archivio"
    ]

)

# -------------------------
# NUOVO NOLEGGIO
# -------------------------

if menu == "Nuovo Noleggio":

    st.header("Nuovo Noleggio")

    with st.form(
        "form",
        clear_on_submit=True
    ):

        nome = st.text_input("Nome")
        cognome = st.text_input("Cognome")
        nazionalita = st.text_input("Nazionalità")
        codice_fiscale = st.text_input("Codice Fiscale")
        numero_patente = st.text_input("Numero Patente")
        telefono = st.text_input("Telefono")
        targa = st.text_input("Targa")

        inizio = st.date_input("Inizio")
        fine = st.date_input("Fine")

        prezzo = st.number_input(
            "Prezzo",
            min_value=0.0
        )

        patente_fronte = st.file_uploader(
            "Foto patente fronte"
        )

        patente_retro = st.file_uploader(
            "Foto patente retro"
        )

        privacy_file = st.file_uploader(
            "Foto informativa privacy firmata"
        )

        # -------------------------
        # PRIVACY E CLAUSOLE
        # -------------------------

        st.subheader("Informativa Privacy e Clausole")

        privacy_text = """
INFORMATIVA PRIVACY

Il cliente autorizza il trattamento dei dati personali
per finalità amministrative e di sicurezza.

CLAUSOLE

Il cliente dichiara:

•⁠  ⁠di avere patente valida
•⁠  ⁠di essere responsabile per danni
•⁠  ⁠di essere responsabile per multe
•⁠  ⁠di restituire il veicolo in buone condizioni
•⁠  ⁠di accettare le condizioni contrattuali
"""

        st.text_area(

            "Leggere prima di firmare",

            privacy_text,

            height=250

        )

        accetta = st.checkbox(
            "Accetto privacy e clausole"
        )

        # -------------------------
        # FIRMA
        # -------------------------

        st.write("Firma Cliente")

        canvas = st_canvas(
            height=150
        )

        submit = st.form_submit_button(
            "SALVA"
        )

        if submit:

            if not accetta:

                st.error(
                    "Devi accettare privacy"
                )

                st.stop()

            if canvas.image_data is None:

                st.error(
                    "Firma obbligatoria"
                )

                st.stop()

            numero_fattura = get_next_fattura()

            url_fronte = upload_file(
                patente_fronte,
                targa,
                "fronte"
            )

            url_retro = upload_file(
                patente_retro,
                targa,
                "retro"
            )

            url_privacy = upload_file(
                privacy_file,
                targa,
                "privacy"
            )

            img = Image.fromarray(
                canvas.image_data.astype(
                    "uint8"
                )
            )

            buffer = io.BytesIO()

            img.save(
                buffer,
                format="PNG"
            )

            firma_b64 = (
                base64.b64encode(
                    buffer.getvalue()
                ).decode()
            )

            dati = {

                "nome": nome,
                "cognome": cognome,
                "nazionalita": nazionalita,
                "codice_fiscale": codice_fiscale,
                "numero_patente": numero_patente,
                "telefono": telefono,
                "targa": targa,
                "inizio": str(inizio),
                "fine": str(fine),
                "prezzo": prezzo,
                "numero_fattura": numero_fattura,
                "firma": firma_b64,
                "url_fronte": url_fronte,
                "url_retro": url_retro,
                "url_privacy": url_privacy

            }

            supabase.table(
                "contratti"
            ).insert(
                dati
            ).execute()

            st.success(
                f"Noleggio salvato {numero_fattura}"
            )

# -------------------------
# ARCHIVIO
# -------------------------

elif menu == "Archivio":

    st.header("Archivio")

    cerca = st.text_input(
        "Cerca targa o nome"
    ).lower()

    res = supabase.table(
        "contratti"
    ).select("*") \
     .order("id", desc=True) \
     .execute()

    if res.data:

        for c in res.data:

            testo = (
                f"{c.get('targa')} "
                f"{c.get('cognome')}"
            ).lower()

            if cerca in testo:

                with st.expander(
                    f"{c.get('targa')} "
                    f"{c.get('numero_fattura')}"
                ):

                    st.download_button(
                        "Contratto",
                        genera_pdf(
                            c,
                            "CONTRATTO"
                        ),
                        file_name="contratto.pdf"
                    )

                    st.download_button(
                        "Ricevuta",
                        genera_pdf(
                            c,
                            "FATTURA"
                        ),
                        file_name="ricevuta.pdf"
                    )

                    st.download_button(
                        "Modulo Multe",
                        genera_pdf(
                            c,
                            "MULTE"
                        ),
                        file_name="multe.pdf"
                    )
