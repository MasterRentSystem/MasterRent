import streamlit as st
import datetime
import pandas as pd
from supabase import create_client, Client
from fpdf import FPDF
import base64
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io

st.set_page_config(page_title="Rent Scooter", layout="centered")

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
# GENERA PDF
# -------------------------

def genera_pdf(d, tipo):

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11)

    def clean(t):

        if t is None:
            return ""

        return str(t).encode(
            "latin-1",
            "replace"
        ).decode(
            "latin-1"
        )

    if tipo == "CONTRATTO":

        testo = f"""
CONTRATTO DI NOLEGGIO

Cliente:
{d.get('nome')} {d.get('cognome')}

Veicolo:
{d.get('targa')}

Periodo:
{d.get('inizio')} - {d.get('fine')}

Prezzo:
Euro {d.get('prezzo')}
"""

        pdf.multi_cell(0, 8, clean(testo))

    elif tipo == "FATTURA":

        testo = f"""
Ricevuta {d.get('numero_fattura')}

Cliente:
{d.get('nome')} {d.get('cognome')}

Importo:
Euro {d.get('prezzo')}
"""

        pdf.multi_cell(0, 8, clean(testo))

    elif tipo == "MULTE":

        testo = f"""
DICHIARAZIONE DATI CONDUCENTE

Veicolo:
{d.get('targa')}

Cliente:
{d.get('nome')} {d.get('cognome')}
"""

        pdf.multi_cell(0, 8, clean(testo))

    # FIX STREAMLIT DEFINITIVO

    pdf_bytes = pdf.output(dest="S")

    if isinstance(pdf_bytes, str):

        pdf_bytes = pdf_bytes.encode("latin-1")

    if not isinstance(pdf_bytes, bytes):

        pdf_bytes = bytes(pdf_bytes)

    return pdf_bytes
# -------------------------
# MENU
# -------------------------

menu = st.sidebar.radio(

    "Menu",

    [
        "Nuovo Noleggio",
        "Archivio",
        "Report Guadagni",
        "Backup"
    ]

)

# -------------------------
# NUOVO NOLEGGIO
# -------------------------

if menu == "Nuovo Noleggio":

    st.header("Nuovo Noleggio")

    with st.form("form", clear_on_submit=True):

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

        st.subheader("Privacy e Clausole")

        st.text_area(
            "Leggere prima di firmare",
            """
Il cliente dichiara:

•⁠  ⁠di avere patente valida
•⁠  ⁠di essere responsabile per danni
•⁠  ⁠di essere responsabile per multe
•⁠  ⁠di accettare le condizioni contrattuali
""",
            height=200
        )

        accetta = st.checkbox(
            "Accetto privacy e clausole"
        )

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

            firma_b64 = base64.b64encode(
                buffer.getvalue()
            ).decode()

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
                "url_retro": url_retro

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
# ARCHIVIO + RICERCA VELOCE
# -------------------------

elif menu == "Archivio":

    st.header("Archivio")

    cerca = st.text_input(
        "Ricerca veloce targa o data"
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
                f"{c.get('inizio')}"
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

# -------------------------
# REPORT GUADAGNI
# -------------------------

elif menu == "Report Guadagni":

    st.header("Guadagni Mensili")

    res = supabase.table(
        "contratti"
    ).select("prezzo, inizio") \
     .execute()

    if res.data:

        df = pd.DataFrame(res.data)

        df["inizio"] = pd.to_datetime(
            df["inizio"]
        )

        df["mese"] = df["inizio"] \
            .dt.to_period("M")

        report = df.groupby(
            "mese"
        )["prezzo"].sum()

        st.write(report)

# -------------------------
# BACKUP
# -------------------------

elif menu == "Backup":

    st.header("Backup Dati")

    res = supabase.table(
        "contratti"
    ).select("*") \
     .execute()

    if res.data:

        df = pd.DataFrame(res.data)

        csv = df.to_csv(
            index=False
        )

        st.download_button(
            "Scarica Backup CSV",
            csv,
            file_name="backup_contratti.csv"
        )
        
