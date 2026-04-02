
import streamlit as st
import datetime
import base64
from fpdf import FPDF
from supabase import create_client
from streamlit_drawable_canvas import st_canvas

st.set_page_config(layout="wide")

st.title("🛵 MasterRent - Noleggio Scooter")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]

supabase = create_client(url, key)

# -----------------------------
# NUMERO FATTURA PROGRESSIVO
# -----------------------------

def prossimo_numero():

    anno = datetime.date.today().year

    res = supabase.table("contatore_fatture").select("*").eq("anno", anno).execute()

    if not res.data:

        supabase.table("contatore_fatture").insert({

            "anno": anno,
            "ultimo_numero": 1

        }).execute()

        return 1

    numero = res.data[0]["ultimo_numero"] + 1

    supabase.table("contatore_fatture").update({

        "ultimo_numero": numero

    }).eq("anno", anno).execute()

    return numero

# -----------------------------
# PULIZIA TESTO PDF
# -----------------------------

def clean(t):

    if not t:
        return ""

    return str(t).encode("latin-1", "ignore").decode("latin-1")

# -----------------------------
# PDF CONTRATTO
# -----------------------------

def pdf_contratto(c):

    pdf = FPDF()

    pdf.add_page()

    pdf.set_font("Arial", "B", 16)

    pdf.cell(0, 10,
        "CONTRATTO DI NOLEGGIO / RENTAL AGREEMENT",
        ln=True,
        align="C"
    )

    pdf.ln(10)

    pdf.set_font("Arial", size=12)

    testo = f"""

Cliente / Customer:

{c['nome']} {c['cognome']}

Targa / Plate:

{c['targa']}

Numero Patente / Driving License:

{c['numero_patente']}

Prezzo / Price:

Euro {c['prezzo']}

Il cliente e responsabile per:

•⁠  ⁠danni
•⁠  ⁠multe
•⁠  ⁠uso improprio

The customer is responsible for:

•⁠  ⁠damages
•⁠  ⁠fines
•⁠  ⁠improper use

Firma / Signature

"""

    pdf.multi_cell(
        0,
        8,
        clean(testo)
    )

    return pdf.output(dest="S").encode("latin-1")

# -----------------------------
# PDF FATTURA
# -----------------------------

def pdf_fattura(c):

    pdf = FPDF()

    pdf.add_page()

    pdf.set_font("Arial", "B", 18)

    pdf.cell(
        0,
        10,
        f"FATTURA N. {c['numero_fattura']}",
        ln=True,
        align="C"
    )

    pdf.ln(15)

    pdf.set_font("Arial", size=12)

    pdf.cell(
        0,
        10,
        clean(f"Cliente: {c['nome']} {c['cognome']}"),
        ln=True
    )

    pdf.cell(
        0,
        10,
        clean(f"Targa: {c['targa']}"),
        ln=True
    )

    pdf.set_font("Arial", "B", 20)

    pdf.cell(
        0,
        20,
        clean(f"Totale Euro {c['prezzo']}"),
        border=1,
        ln=True,
        align="C"
    )

    return pdf.output(dest="S").encode("latin-1")

# -----------------------------
# NUOVO CONTRATTO
# -----------------------------

with st.form("contratto"):

    col1, col2 = st.columns(2)

    nome = col1.text_input("Nome")
    cognome = col1.text_input("Cognome")

    telefono = col1.text_input("Telefono")
    email = col1.text_input("Email")

    codice_fiscale = col1.text_input("Codice fiscale")

    numero_patente = col2.text_input("Numero patente")

    targa = col2.text_input("Targa").upper()

    prezzo = col2.number_input("Prezzo", min_value=0.0)

    deposito = col2.number_input("Deposito", min_value=0.0)

    st.write("Firma cliente")

    canvas = st_canvas(
        stroke_width=3,
        height=150,
        width=400
    )

    privacy = st.checkbox(
        "Accetto privacy GDPR"
    )

    submit = st.form_submit_button(
        "SALVA CONTRATTO"
    )

    if submit:

        if not privacy:

            st.error("Devi accettare la privacy")

        else:

            numero = prossimo_numero()

            firma_base64 = ""

            if canvas.image_data is not None:

                firma_base64 = base64.b64encode(
                    canvas.image_data.tobytes()
                ).decode()

            dati = {

                "numero_fattura": numero,

                "nome": nome,
                "cognome": cognome,

                "telefono": telefono,
                "email": email,

                "codice_fiscale": codice_fiscale,

                "numero_patente": numero_patente,

                "targa": targa,

                "prezzo": prezzo,
                "deposito": deposito,

                "privacy": True,

                "firma": firma_base64

            }

            supabase.table(
                "contratti"
            ).insert(
                dati
            ).execute()

            st.success(
                f"Contratto salvato - Fattura n. {numero}"
            )

# -----------------------------
# ARCHIVIO
# -----------------------------

st.divider()

st.header("Archivio contratti")

res = supabase.table(
    "contratti"
).select(
    "*"
).order(
    "id",
    desc=True
).execute()

for c in res.data:

    with st.expander(

        f"{c['numero_fattura']} - {c['nome']} {c['cognome']} - {c['targa']}"

    ):

        contratto_bytes = pdf_contratto(c)

        fattura_bytes = pdf_fattura(c)

        col1, col2 = st.columns(2)

        col1.download_button(

            "SCARICA CONTRATTO",
            data=contratto_bytes,
            file_name=f"Contratto_{c['numero_fattura']}.pdf",
            mime="application/pdf",
            key=f"contratto_{c['id']}"

        )

        col2.download_button(

            "SCARICA FATTURA",
            data=fattura_bytes,
            file_name=f"Fattura_{c['numero_fattura']}.pdf",
            mime="application/pdf",
            key=f"fattura_{c['id']}"

        )

