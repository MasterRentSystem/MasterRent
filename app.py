import streamlit as st
from supabase import create_client, Client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from fpdf import FPDF
import io
import base64
from datetime import datetime

# ------------------------------------------------
# CONFIGURAZIONE SUPABASE
# ------------------------------------------------

URL = "INSERISCI_TUO_URL"
KEY = "INSERISCI_TUA_KEY"

supabase: Client = create_client(URL, KEY)

# ------------------------------------------------
# FUNZIONI UTILITY
# ------------------------------------------------

def safe_text(t):
    if t is None:
        return ""
    return str(t).encode("latin-1", "replace").decode("latin-1")

def upload_to_supabase(file, targa, tipo):
    if file is None:
        return ""

    try:
        nome_file = f"{targa}{tipo}{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"

        supabase.storage.from_("documenti").upload(
            nome_file,
            file.getvalue(),
            {"content-type": "image/jpeg"}
        )

        url = supabase.storage.from_("documenti").get_public_url(nome_file)

        return url

    except Exception as e:
        st.error(f"Errore upload {tipo}: {e}")
        return ""

def prossimo_numero_fattura():
    try:
        res = (
            supabase.table("contratti")
            .select("numero_fattura")
            .order("id", desc=True)
            .limit(1)
            .execute()
        )

        if res.data and res.data[0].get("numero_fattura"):
            return int(res.data[0]["numero_fattura"]) + 1

        return 1

    except:
        return 1

# ------------------------------------------------
# GENERAZIONE PDF
# ------------------------------------------------

def genera_pdf(c, tipo):

    pdf = FPDF()
    pdf.add_page()

    oggi = datetime.now().strftime("%d/%m/%Y")

    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "BATTAGLIA RENT", ln=True, align="C")

    pdf.ln(5)

    if tipo == "CONTRATTO":

        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "CONTRATTO DI NOLEGGIO", ln=True, align="C")

        testo = f"""
Cliente: {c.get('nome')} {c.get('cognome')}

Codice Fiscale: {c.get('codice_fiscale')}

Residenza: {c.get('indirizzo_cliente')}

Telefono: {c.get('telefono')}

Targa: {c.get('targa')}

Patente: {c.get('numero_patente')}

Periodo: dal {c.get('inizio')} al {c.get('fine')}

Prezzo: Euro {c.get('prezzo')}

Deposito: Euro {c.get('deposito')}

CLAUSOLE:

Il cliente dichiara di essere in possesso di patente valida.

Si assume ogni responsabilità per danni e multe.

Autorizza il trattamento dati personali (GDPR).
"""

    elif tipo == "FATTURA":

        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "RICEVUTA DI PAGAMENTO", ln=True, align="C")

        testo = f"""
Ricevuta n° {c.get('numero_fattura')}

Data: {oggi}

Cliente: {c.get('nome')} {c.get('cognome')}

Targa: {c.get('targa')}

Importo: Euro {c.get('prezzo')}

Deposito: Euro {c.get('deposito')}
"""

    else:

        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "DICHIARAZIONE SOSTITUTIVA (L.445/2000)", ln=True, align="C")

        testo = f"""
La sottoscritta dichiara che il veicolo:

TARGA: {c.get('targa')}

in data {c.get('inizio')}

era locato al Sig.

{c.get('nome')} {c.get('cognome')}

nato a {c.get('luogo_nascita')}

il {c.get('data_nascita')}

Patente: {c.get('numero_patente')}

Firma titolare: ________________
"""

    pdf.set_font("Arial", "", 11)

    pdf.multi_cell(0, 7, safe_text(testo))

    if c.get("firma"):

        try:

            firma_bytes = base64.b64decode(c["firma"])

            pdf.image(
                io.BytesIO(firma_bytes),
                x=130,
                y=pdf.get_y() + 5,
                w=50
            )

        except:
            pass

    out = pdf.output(dest="S")

    if isinstance(out, str):
        return out.encode("latin-1")

    return out

# ------------------------------------------------
# LOGIN
# ------------------------------------------------

if not st.session_state.get("login", False):

    st.title("Accesso Master Rent")

    password = st.text_input(
        "Password",
        type="password"
    )

    if st.button("Accedi"):

        if password == "1234":

            st.session_state.login = True

            st.rerun()

        else:

            st.error("Password errata")

# ------------------------------------------------
# APP PRINCIPALE
# ------------------------------------------------

else:

    st.title("Nuovo Noleggio Scooter")

    with st.form(
        "form_noleggio",
        clear_on_submit=True
    ):

        col1, col2 = st.columns(2)

        nome = col1.text_input("Nome")

        cognome = col1.text_input("Cognome")

        telefono = col1.text_input("Telefono")

        cf = col1.text_input("Codice Fiscale")

        indirizzo = col1.text_area("Indirizzo")

        naz = col1.selectbox(
            "Nazionalità",
            ["Italiana", "Straniera"]
        )

        targa = col2.text_input("Targa").upper()

        patente = col2.text_input("Numero Patente")

        luogo = col2.text_input("Luogo nascita")

        data_nascita = col2.text_input("Data nascita")

        prezzo = col2.number_input(
            "Prezzo",
            min_value=0.0
        )

        deposito = col2.number_input(
            "Deposito",
            min_value=0.0
        )

        d1, d2 = st.columns(2)

        inizio = d1.date_input(
            "Inizio Noleggio"
        )

        fine = d2.date_input(
            "Fine Noleggio"
        )

        st.subheader("Documenti")

        fronte = st.file_uploader(
            "Fronte patente"
        )

        retro = st.file_uploader(
            "Retro patente"
        )

        st.subheader("Privacy e Clausole")

        st.text_area(
            "Informativa",
            """
Il cliente dichiara:

•⁠  ⁠patente valida
•⁠  ⁠responsabilità per multe
•⁠  ⁠autorizza trattamento dati GDPR
•⁠  ⁠accetta condizioni noleggio
""",
            height=150
        )

        accetta = st.checkbox(
            "Accetto condizioni"
        )

        st.subheader("Firma")

        canvas = st_canvas(
            stroke_width=3,
            stroke_color="#000",
            background_color="#eee",
            height=150,
            width=400,
            key="firma_canvas"
        )

        if st.form_submit_button(
            "SALVA CONTRATTO"
        ):

            if not accetta:

                st.error(
                    "Accetta le condizioni"
                )

            elif nome and cognome and targa:

                try:

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

                    numero = prossimo_numero_fattura()

                    dati = {

                        "nome": nome,
                        "cognome": cognome,
                        "telefono": telefono,
                        "targa": targa,
                        "prezzo": prezzo,
                        "deposito": deposito,
                        "inizio": str(inizio),
                        "fine": str(fine),
                        "firma": firma_b64,
                        "numero_fattura": numero,
                        "luogo_nascita": luogo,
                        "data_nascita": data_nascita,
                        "numero_patente": patente,
                        "codice_fiscale": cf,
                        "indirizzo_cliente": indirizzo,
                        "nazionalita": naz,
                        "url_fronte": url_f,
                        "url_retro": url_r

                    }

                    supabase.table(
                        "contratti"
                    ).insert(
                        dati
                    ).execute()

                    st.success(
                        f"Contratto {numero} salvato"
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"Errore: {e}"
                    )

            else:

                st.error(
                    "Compila Nome Cognome Targa"
                )

    st.divider()

    st.subheader(
        "Archivio Contratti"
    )

    try:

        res = supabase.table(
            "contratti"
        ).select(
            "*"
        ).order(
            "id",
            desc=True
        ).execute()

        if res.data:

            ricerca = st.text_input(
                "Cerca targa o cognome"
            ).lower()

            for c in res.data:

                testo = f"{c.get('targa','')} {c.get('cognome','')}".lower()

                if ricerca in testo:

                    with st.expander(
                        f"{c.get('targa')} - {c.get('cognome')}"
                    ):

                        p1 = genera_pdf(
                            c,
                            "CONTRATTO"
                        )

                        p2 = genera_pdf(
                            c,
                            "FATTURA"
                        )

                        p3 = genera_pdf(
                            c,
                            "MULTE"
                        )

                        col1, col2, col3 = st.columns(3)

                        col1.download_button(
                            "Contratto",
                            p1,
                            file_name=f"contratto_{c['id']}.pdf",
                            mime="application/pdf",
                            key=f"contratto_{c['id']}"
                        )

                        col2.download_button(
                            "Ricevuta",
                            p2,
                            file_name=f"ricevuta_{c['id']}.pdf",
                            mime="application/pdf",
                            key=f"ricevuta_{c['id']}"
                        )

                        col3.download_button(
                            "Modulo Multe",
                            p3,
                            file_name=f"multe_{c['id']}.pdf",
                            mime="application/pdf",
                            key=f"multe_{c['id']}"
                        )

    except Exception as e:

        st.error(
            f"Errore archivio: {e}"
        )
