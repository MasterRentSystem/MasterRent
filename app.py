import streamlit as st
import datetime
from fpdf import FPDF
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io
import base64

# ------------------------------------------------
# CONFIG
# ------------------------------------------------

st.set_page_config(
    layout="wide",
    page_title="Battaglia Rent Pro",
    initial_sidebar_state="collapsed"
)

DITTA = "BATTAGLIA MARIANNA"
INDIRIZZO_FISCALE = "Via Cognole, 5 - 80075 Forio (NA)"
DATI_IVA = "C.F. BTTMNN87A53Z112S - P. IVA 10252601215"

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

        if file is None:
            return None

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

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, safe_text(DITTA), ln=True)

    pdf.set_font("Arial", "", 9)
    pdf.cell(0, 5, safe_text(INDIRIZZO_FISCALE), ln=True)
    pdf.cell(0, 5, safe_text(DATI_IVA), ln=True)

    pdf.ln(8)

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

Il veicolo:

TARGA:
{c.get('targa')}

era condotto da:

{c.get('nome')} {c.get('cognome')}

Nato a:
{c.get('luogo_nascita')}

Data nascita:
{c.get('data_nascita')}

Patente:
{c.get('numero_patente')}

Data:
{oggi}
"""

        pdf.multi_cell(
            0,
            6,
            safe_text(testo)
        )

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

    st.title("🔐 Login Battaglia Rent")

    pwd = st.text_input(
        "Inserisci Password",
        type="password"
    )

    if st.button("Entra"):

        if pwd == st.secrets["APP_PASSWORD"]:

            st.session_state.autenticato = True
            st.rerun()

        else:

            st.error("Password errata")

# ------------------------------------------------
# APP
# ------------------------------------------------

else:

    st.title("🛵 Nuovo Noleggio Scooter")

    with st.form("nuovo_noleggio", clear_on_submit=True):

        col1, col2 = st.columns(2)

        nome = col1.text_input("Nome")
        cognome = col1.text_input("Cognome")
        luogo_nascita = col1.text_input("Luogo nascita")
        data_nascita = col1.text_input("Data nascita")
        data_inizio = col1.date_input("Inizio Noleggio")

        targa_input = col2.text_input("Targa")
        targa = targa_input.upper() if targa_input else ""

        prezzo = col2.number_input(
            "Prezzo Totale (€)",
            min_value=0.0
        )

        deposito = col2.number_input(
            "Deposito Cauzionale (€)",
            min_value=0.0
        )

        patente = col2.text_input("Numero Patente")
        data_fine = col2.date_input("Fine Noleggio")

        st.subheader("📸 Documenti Patente")

        f_col1, f_col2 = st.columns(2)

        fronte = f_col1.file_uploader(
            "Fronte Patente",
            type=["jpg", "png", "jpeg"]
        )

        retro = f_col2.file_uploader(
            "Retro Patente",
            type=["jpg", "png", "jpeg"]
        )

        st.subheader("✍️ Firma Cliente")

        canvas = st_canvas(
            stroke_width=3,
            stroke_color="#000",
            background_color="#eee",
            height=150,
            width=400,
            key="firma_nuova"
        )

        if st.form_submit_button("💾 SALVA E GENERA"):

            if not nome or not cognome or not targa:

                st.error(
                    "Nome, Cognome e Targa sono obbligatori!"
                )

            else:

                firma_b64 = ""

                if canvas.image_data is not None:

                    img = Image.fromarray(
                        canvas.image_data.astype("uint8")
                    )

                    buf = io.BytesIO()

                    img.save(
                        buf,
                        format="PNG"
                    )

                    firma_b64 = base64.b64encode(
                        buf.getvalue()
                    ).decode()

                url_f = upload_to_supabase(
                    fronte,
                    targa,
                    "fronte"
                )

                url_r = upload_to_supabase(
                    retro,
                    targa,
                    "retro"
                )

                n_fatt = prossimo_numero_fattura()

                dati = {
                    "nome": nome,
                    "cognome": cognome,
                    "targa": targa,
                    "prezzo": prezzo,
                    "deposito": deposito,
                    "inizio": str(data_inizio),
                    "fine": str(data_fine),
                    "firma": firma_b64,
                    "numero_fattura": n_fatt,
                    "luogo_nascita": luogo_nascita,
                    "data_nascita": data_nascita,
                    "numero_patente": patente,
                    "url_fronte": url_f,
                    "url_retro": url_r
                }

                supabase.table(
                    "contratti"
                ).insert(
                    dati
                ).execute()

                st.success(
                    f"Contratto n° {n_fatt} salvato!"
                )

                st.rerun()

st.divider()

    st.subheader("📂 Archivio Contratti")

    try:

        res = (
            supabase
            .table("contratti")
            .select("*")
            .order("id", desc=True)
            .execute()
        )

        if not res.data:

            st.info("Nessun contratto presente.")

        else:

            for c in res.data:

                nome = c.get("nome") or ""
                cognome = c.get("cognome") or ""
                targa = c.get("targa") or ""
                numero = c.get("numero_fattura") or "?"

                with st.expander(
                    f"📄 {numero} - {nome} {cognome} ({targa})"
                ):

                    col1, col2, col3 = st.columns(3)

                    try:

                        pdf_contratto = genera_pdf_tipo(
                            c,
                            "CONTRATTO"
                        )

                        pdf_ricevuta = genera_pdf_tipo(
                            c,
                            "FATTURA"
                        )

                        pdf_multe = genera_pdf_tipo(
                            c,
                            "MULTE"
                        )

                        col1.download_button(
                            "📜 Contratto",
                            pdf_contratto,
                            f"Contratto_{targa}.pdf",
                            "application/pdf"
                        )

                        col2.download_button(
                            "💰 Ricevuta",
                            pdf_ricevuta,
                            f"Ricevuta_{numero}.pdf",
                            "application/pdf"
                        )

                        col3.download_button(
                            "🚨 Modulo Multe",
                            pdf_multe,
                            f"Multe_{targa}.pdf",
                            "application/pdf"
                        )

                    except Exception as pdf_error:

                        st.error("Errore generazione PDF:")
                        st.error(pdf_error)

    except Exception as e:

        st.error("Errore archivio:")
        st.error(e)
