import streamlit as st
import datetime
import pandas as pd
from supabase import create_client, Client
from fpdf import FPDF
import base64
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io

# -------------------------
# CONFIGURAZIONE
# -------------------------

st.set_page_config(
    page_title="Battaglia Rent",
    layout="centered"
)

# -------------------------
# CONNESSIONE SUPABASE
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

        st.title("🔒 Accesso")

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
            .filter(
                "numero_fattura",
                "ilike",
                f"{year}-%"
            ) \
            .order(
                "numero_fattura",
                desc=True
            ) \
            .limit(1) \
            .execute()

        if not res.data:

            return f"{year}-001"

        last_num = int(
            res.data[0]["numero_fattura"]
            .split("-")[1]
        )

        return f"{year}-{str(last_num + 1).zfill(3)}"

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
# GENERA PDF
# -------------------------

def genera_pdf(d, tipo):

    pdf = FPDF()

    pdf.add_page()

    pdf.set_font(
        "Arial",
        "B",
        14
    )

    def clean(text):

        if text is None:
            return ""

        return str(text) \
            .encode(
                "latin-1",
                "replace"
            ) \
            .decode(
                "latin-1"
            )

    if tipo == "CONTRATTO":

        pdf.cell(
            0,
            10,
            "CONTRATTO DI NOLEGGIO SCOOTER",
            ln=True,
            align="C"
        )

        pdf.ln(10)

        pdf.set_font(
            "Arial",
            "",
            11
        )

        testo = f"""
Cliente: {d.get('nome')} {d.get('cognome')}
Nazionalità: {d.get('nazionalita')}
Codice Fiscale: {d.get('codice_fiscale')}
Numero Patente: {d.get('numero_patente')}

Veicolo: {d.get('targa')}
Periodo: {d.get('inizio')} - {d.get('fine')}

Prezzo: Euro {d.get('prezzo')}

Il cliente dichiara:

•⁠  ⁠di aver ricevuto il veicolo in buone condizioni
•⁠  ⁠di essere responsabile per danni e multe
•⁠  ⁠di rispettare il codice della strada
•⁠  ⁠di autorizzare il trattamento dati personali
ai sensi del GDPR
"""

        pdf.multi_cell(
            0,
            8,
            clean(testo)
        )

    elif tipo == "FATTURA":

        pdf.cell(
            0,
            10,
            clean(
                f"Ricevuta N. {d.get('numero_fattura')}"
            ),
            ln=True,
            align="C"
        )

        pdf.ln(10)

        pdf.set_font(
            "Arial",
            "",
            11
        )

        pdf.cell(
            0,
            10,
            clean(
                f"Cliente: {d.get('nome')} {d.get('cognome')}"
            ),
            ln=True
        )

        pdf.cell(
            0,
            10,
            clean(
                f"Importo: Euro {d.get('prezzo')}"
            ),
            ln=True
        )

    elif tipo == "MULTE":

        pdf.cell(
            0,
            10,
            "DICHIARAZIONE DATI CONDUCENTE",
            ln=True,
            align="C"
        )

        pdf.ln(10)

        pdf.set_font(
            "Arial",
            "",
            11
        )

        testo = f"""
Il veicolo targa {d.get('targa')}
in data {d.get('inizio')}
era affidato al Sig.

{d.get('nome')} {d.get('cognome')}
Nazionalità: {d.get('nazionalita')}
Patente: {d.get('numero_patente')}
Telefono: {d.get('telefono')}
"""

        pdf.multi_cell(
            0,
            8,
            clean(testo)
        )

    pdf_bytes = pdf.output(
        dest="S"
    )

    if isinstance(
        pdf_bytes,
        str
    ):
        pdf_bytes = pdf_bytes.encode(
            "latin-1"
        )

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

        nazionalita = st.text_input(
            "Nazionalità"
        )

        codice_fiscale = st.text_input(
            "Codice Fiscale"
        )

        numero_patente = st.text_input(
            "Numero Patente"
        )

        telefono = st.text_input(
            "Telefono"
        )

        targa = st.text_input(
            "Targa"
        )

        inizio = st.date_input(
            "Inizio"
        )

        fine = st.date_input(
            "Fine"
        )

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

        privacy = st.file_uploader(
            "Foto informativa privacy firmata"
        )

        st.write("Firma Cliente")

        canvas = st_canvas(
            height=150
        )

        submit = st.form_submit_button(
            "SALVA"
        )

        if submit:

            if canvas.image_data is None or canvas.image_data.sum() == 0:

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
                privacy,
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
                "data:image/png;base64,"
                + base64.b64encode(
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
                f"Noleggio salvato - Fattura {numero_fattura}"
            )

# -------------------------
# ARCHIVIO
# -------------------------

elif menu == "Archivio":

    st.header("Archivio Noleggi")

    cerca = st.text_input(
        "Cerca"
    ).lower()

    res = supabase.table(
        "contratti"
    ).select("*").order(
        "id",
        desc=True
    ).execute()

    if res.data:

        for c in res.data:

            testo = (
                f"{c.get('targa')} "
                f"{c.get('cognome')} "
                f"{c.get('numero_fattura')}"
            ).lower()

            if cerca in testo:

                with st.expander(

                    f"{c.get('numero_fattura')} "
                    f"{c.get('targa')}"

                ):

                    col1, col2 = st.columns(2)

                    with col1:

                        st.download_button(
                            "Contratto",
                            genera_pdf(
                                c,
                                "CONTRATTO"
                            ),
                            file_name="contratto.pdf"
                        )

                        st.download_button(
                            "Modulo Multe",
                            genera_pdf(
                                c,
                                "MULTE"
                            ),
                            file_name="multe.pdf"
                        )

                    with col2:

                        st.download_button(
                            "Ricevuta",
                            genera_pdf(
                                c,
                                "FATTURA"
                            ),
                            file_name="ricevuta.pdf"
                        )

                        if c.get(
                            "url_fronte"
                        ):

                            st.link_button(
                                "Foto Patente",
                                c.get(
                                    "url_fronte"
                                )
                            )
