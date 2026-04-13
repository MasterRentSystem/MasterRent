import streamlit as st
from supabase import create_client, Client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from fpdf import FPDF
import io
import base64
from datetime import datetime

# -------------------
# DATI AZIENDA
# -------------------

DITTA = "BATTAGLIA RENT"
TITOLARE = "BATTAGLIA MARIANNA"
DETTAGLI_TITOLARE = "nata a Berlino il 13/01/1987 e residente in Forio alla Via Cognole n. 5"
INDIRIZZO = "Via Cognole n. 5, Forio (NA)"
DATI_IVA = "P.IVA: 10252601215 | C.F.: BTTMNN87A53Z112S"

# -------------------
# SUPABASE
# -------------------

URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(URL, KEY)

# -------------------
# UTILITY
# -------------------

def s(v):
    return "" if v is None else str(v)

def safe_text(text):
    return s(text).encode("latin-1", "replace").decode("latin-1")

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

        if res.data and res.data[0].get("numero_fattura"):
            return int(res.data[0]["numero_fattura"]) + 1

        return 1

    except:
        return 1

# -------------------

def upload_foto(file, targa, tipo):

    if file is None:
        return None

    try:

        img = Image.open(file)

        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        img.thumbnail((1000, 1000))

        buf = io.BytesIO()

        img.save(buf, format="JPEG", quality=85)

        nome = (
            f"{tipo}{targa}"
            f"{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
        )

        supabase.storage.from_("documenti").upload(
            nome,
            buf.getvalue(),
            {
                "content-type": "image/jpeg",
                "upsert": True
            }
        )

        return (
            supabase
            .storage
            .from_("documenti")
            .get_public_url(nome)
        )

    except Exception as e:

        st.error(f"Errore caricamento foto: {e}")

        return None

# -------------------

def get_firma(canvas):

    if canvas.image_data is not None:

        img = Image.fromarray(
            canvas.image_data.astype("uint8")
        )

        if img.getbbox() is None:
            return None

        buf = io.BytesIO()

        img.save(buf, format="PNG")

        return base64.b64encode(
            buf.getvalue()
        ).decode()

    return None

# -------------------
# PDF
# -------------------

def genera_pdf(c):

    pdf = FPDF()

    pdf.add_page()

    pdf.set_font("Arial", "B", 12)

    pdf.cell(0, 6, safe_text(DITTA), ln=True)
    pdf.cell(0, 6, safe_text(INDIRIZZO), ln=True)
    pdf.cell(0, 6, safe_text(DATI_IVA), ln=True)

    pdf.ln(10)

    nome = f"{s(c.get('nome'))} {s(c.get('cognome'))}"

    pdf.set_font("Arial", "B", 14)

    pdf.cell(
        0,
        10,
        "CONTRATTO DI NOLEGGIO SCOOTER",
        ln=True,
        align="C",
        border="B"
    )

    pdf.ln(5)

    pdf.set_font("Arial", "", 10)

    testo = f"""

Cliente: {nome}

Targa: {s(c.get('targa'))}

Patente: {s(c.get('numero_patente'))}

Periodo:
Dal {s(c.get('inizio'))}
Al {s(c.get('fine'))}

Prezzo:
EUR {s(c.get('prezzo'))}


CONDIZIONI GENERALI

1.⁠ ⁠Il cliente dichiara di possedere patente valida.

2.⁠ ⁠Responsabilità totale per danni.

3.⁠ ⁠In caso di furto paga il valore.

4.⁠ ⁠Multe a carico del cliente.

5.⁠ ⁠Restituzione con carburante.

6.⁠ ⁠Autorizzazione trattamento dati.


Approvazione artt 1341 e 1342 c.c.

"""

    pdf.multi_cell(
        0,
        5,
        safe_text(testo)
    )

    if c.get("firma"):

        try:

            pdf.image(
                io.BytesIO(
                    base64.b64decode(
                        c["firma"]
                    )
                ),
                x=130,
                y=pdf.get_y() + 5,
                w=50
            )

        except:

            pass

    out = pdf.output(dest="S")

    if isinstance(out, bytearray):
        return bytes(out)

    return out.encode("latin-1", "replace")

# -------------------
# LOGIN
# -------------------

if "auth" not in st.session_state:

    st.session_state.auth = False

if not st.session_state.auth:

    password = st.text_input(
        "Password",
        type="password"
    )

    if st.button("Accedi"):

        if password == "1234":

            st.session_state.auth = True

            st.rerun()

        else:

            st.error("Password errata")

    st.stop()

# -------------------
# INTERFACCIA
# -------------------

tab1, tab2 = st.tabs(
    [
        "Nuovo contratto",
        "Archivio"
    ]
)

# -------------------
# NUOVO CONTRATTO
# -------------------

with tab1:

    with st.form(
        "form_noleggio",
        clear_on_submit=True
    ):

        nome = st.text_input("Nome")

        cognome = st.text_input("Cognome")

        targa = (
            st.text_input("Targa")
            .upper()
        )

        patente = st.text_input(
            "Numero patente"
        )

        prezzo = st.number_input(
            "Prezzo (€)",
            min_value=0.0
        )

        inizio = st.date_input(
            "Inizio"
        )

        fine = st.date_input(
            "Fine"
        )

        fronte = st.file_uploader(
            "Patente fronte"
        )

        retro = st.file_uploader(
            "Patente retro"
        )

        st.markdown(
            """
### Informativa Privacy e Clausole

Il cliente dichiara:

•⁠  ⁠di possedere patente valida
•⁠  ⁠di essere responsabile del veicolo
•⁠  ⁠di pagare eventuali multe
•⁠  ⁠di autorizzare il trattamento dati

Ai sensi degli artt. 1341 e 1342 c.c.
"""
        )

        accetto = st.checkbox(
            "Ho letto e accetto le condizioni"
        )

        st.write("Firma del cliente")

        canvas = st_canvas(
            height=150,
            width=400
        )

        if st.form_submit_button(
            "SALVA CONTRATTO"
        ):

            if not nome:

                st.error(
                    "Inserire nome"
                )

                st.stop()

            if not targa:

                st.error(
                    "Inserire targa"
                )

                st.stop()

            if not accetto:

                st.error(
                    "Devi accettare le clausole"
                )

                st.stop()

            firma = get_firma(
                canvas
            )

            if firma is None:

                st.error(
                    "Firma obbligatoria"
                )

                st.stop()

            with st.spinner(
                "Salvataggio..."
            ):

                url_f = upload_foto(
                    fronte,
                    targa,
                    "front"
                )

                url_r = upload_foto(
                    retro,
                    targa,
                    "back"
                )

                supabase.table(
                    "contratti"
                ).insert(

                    {
                        "nome": nome,
                        "cognome": cognome,
                        "targa": targa,
                        "numero_patente": patente,
                        "prezzo": prezzo,
                        "inizio": str(inizio),
                        "fine": str(fine),
                        "firma": firma,
                        "numero_fattura":
                        prossimo_numero_fattura(),
                        "url_fronte": url_f,
                        "url_retro": url_r,
                        "created_at":
                        datetime.now().isoformat()
                    }

                ).execute()

                st.success(
                    "Contratto salvato"
                )

# -------------------
# ARCHIVIO
# -------------------

with tab2:

    st.subheader(
        "Storico contratti"
    )

    res = (
        supabase
        .table("contratti")
        .select("*")
        .order("id", desc=True)
        .execute()
    )

    for r in res.data:

        with st.expander(
            f"{r['targa']} - {r['cognome']}"
        ):

            st.download_button(
                "Scarica contratto",
                genera_pdf(r),
                file_name=
                f"contratto_{r['targa']}.pdf"
            )

            if r.get("url_fronte"):

                st.image(
                    r["url_fronte"],
                    caption="Fronte patente",
                    width=300
                )

            if r.get("url_retro"):

                st.image(
                    r["url_retro"],
                    caption="Retro patente",
                    width=300
                )
