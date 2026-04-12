import streamlit as st
from supabase import create_client, Client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from fpdf import FPDF
import io
import base64
from datetime import datetime

# --- CONFIG ---
st.set_page_config(
    page_title="Battaglia Rent",
    page_icon="🛵",
    layout="wide"
)

# --- DATI AZIENDA ---
DITTA_INFO = {
    "ragione_sociale": "BATTAGLIA RENT",
    "indirizzo": "Via Cognole n. 5, Forio (NA)",
    "fiscale": "P.IVA: 10252601215 | C.F.: BTTMNN87A53Z112S"
}

# --- SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- FUNZIONI SICURE ---
def T(dato):
    if dato is None:
        return ""
    return str(dato)

def clean_pdf(testo):
    return T(testo).encode("latin-1", "replace").decode("latin-1")

# ---------------- PDF ----------------

def header(pdf):

    pdf.set_font("Arial", "B", 12)

    pdf.cell(
        0,
        6,
        clean_pdf(DITTA_INFO["ragione_sociale"]),
        ln=True
    )

    pdf.set_font("Arial", "", 9)

    pdf.cell(
        0,
        5,
        clean_pdf(DITTA_INFO["indirizzo"]),
        ln=True
    )

    pdf.cell(
        0,
        5,
        clean_pdf(DITTA_INFO["fiscale"]),
        ln=True
    )

    pdf.ln(5)

# ---------------- CONTRATTO ----------------

def pdf_contratto(d):

    pdf = FPDF()
    pdf.add_page()

    header(pdf)

    cliente = f"{T(d.get('nome'))} {T(d.get('cognome'))}"

    testo = f"""
CONTRATTO DI NOLEGGIO / RENTAL AGREEMENT

Cliente: {cliente}
CF / ID: {T(d.get('codice_fiscale'))}

Residenza: {T(d.get('residenza'))}

Targa: {T(d.get('targa'))}

Patente: {T(d.get('numero_patente'))}

Periodo:
dal {T(d.get('inizio'))}
al {T(d.get('fine'))}

Prezzo totale: EUR {T(d.get('prezzo'))}

-------------------------------------

CONDIZIONI DI NOLEGGIO

 1.⁠ ⁠Il conducente dichiara di essere in possesso di patente valida.

 2.⁠ ⁠Il locatario è responsabile di ogni danno causato al veicolo o a terzi.

 3.⁠ ⁠In caso di furto del veicolo, il locatario risponde dell'intero valore del mezzo.

 4.⁠ ⁠Tutte le contravvenzioni (multe) prese durante il periodo sono a carico del locatario.

 5.⁠ ⁠Il veicolo deve essere riconsegnato con lo stesso livello di carburante.

 6.⁠ ⁠Il veicolo può essere condotto esclusivamente dal cliente indicato nel presente contratto.

 7.⁠ ⁠In caso di incidente o sinistro, il locatario è obbligato ad avvisare immediatamente il locatore.

 8.⁠ ⁠In caso di smarrimento chiavi la penale è di € 250.

 9.⁠ ⁠Ogni ora di ritardo nella riconsegna comporta penale.

10.⁠ ⁠Il locatore è autorizzato a comunicare i dati del conducente alle autorità.

11.⁠ ⁠Foro competente: Napoli.

-------------------------------------

INFORMATIVA PRIVACY (GDPR)

Il cliente autorizza il trattamento dei dati personali e la conservazione digitale
dei documenti per fini fiscali e di pubblica sicurezza.

Firma Cliente
"""

    pdf.set_font("Arial", "", 9)

    pdf.multi_cell(
        0,
        5,
        clean_pdf(testo)
    )

    firma_raw = d.get("firma")

    if firma_raw:

        try:

            img_b = base64.b64decode(T(firma_raw))

            y = pdf.get_y()

            if y > 240:

                pdf.add_page()
                y = 20

            pdf.image(
                io.BytesIO(img_b),
                x=130,
                y=y + 5,
                w=50
            )

        except:
            pass

    return pdf.output(dest="S").encode("latin-1")

# ---------------- FATTURA ----------------

def pdf_fattura(d):

    pdf = FPDF()
    pdf.add_page()

    header(pdf)

    cliente = f"{T(d.get('nome'))} {T(d.get('cognome'))}"

    numero = T(d.get("numero_fattura"))

    testo = f"""
RICEVUTA DI PAGAMENTO

Numero: {numero}/A
Data: {datetime.now().strftime('%d/%m/%Y')}

Cliente: {cliente}

Descrizione:
Noleggio scooter targa {T(d.get('targa'))}

Totale:
EUR {T(d.get('prezzo'))}
"""

    pdf.set_font("Arial", "", 10)

    pdf.multi_cell(
        0,
        6,
        clean_pdf(testo)
    )

    return pdf.output(dest="S").encode("latin-1")

# ---------------- MULTE ----------------

def pdf_multa(d):

    pdf = FPDF()
    pdf.add_page()

    header(pdf)

    cliente = f"{T(d.get('nome'))} {T(d.get('cognome'))}"

    testo = f"""
Spett.le
Polizia Locale di ________________

OGGETTO:
COMUNICAZIONE LOCAZIONE VEICOLO

La sottoscritta
BATTAGLIA MARIANNA

DICHIARA

Ai sensi della L. 445/2000

che il veicolo targato:

{T(d.get('targa'))}

in data:

{T(d.get('inizio'))}

era concesso in locazione al signor:

COGNOME E NOME:
{cliente}

LUOGO E DATA DI NASCITA:
______________

RESIDENZA:
______________

PATENTE:
{T(d.get('numero_patente'))}

Si allega:

•⁠  ⁠copia contratto
•⁠  ⁠copia documento

In fede

Marianna Battaglia
"""

    pdf.set_font("Arial", "", 10)

    pdf.multi_cell(
        0,
        6,
        clean_pdf(testo)
    )

    return pdf.output(dest="S").encode("latin-1")

# ---------------- LOGIN ----------------

if "log" not in st.session_state:
    st.session_state.log = False

if not st.session_state.log:

    st.title("Accesso")

    pw = st.text_input(
        "Password",
        type="password"
    )

    if pw == "1234":

        if st.button("Entra"):

            st.session_state.log = True
            st.rerun()

# ---------------- APP ----------------

else:

    mode = st.sidebar.selectbox(
        "Menu",
        ["Nuovo", "Archivio"]
    )

    if mode == "Nuovo":

        st.title("Nuovo Noleggio")

        with st.form("form"):

            col1, col2 = st.columns(2)

            nome = col1.text_input("Nome")

            cognome = col1.text_input("Cognome")

            residenza = col1.text_input("Residenza")

            targa = col2.text_input("Targa").upper()

            prezzo = col2.number_input(
                "Prezzo",
                min_value=0.0
            )

            patente = col2.text_input("Patente")

            cf = col1.text_input("Codice Fiscale")

            data_inizio = st.date_input("Inizio")

            data_fine = st.date_input("Fine")

            canvas = st_canvas(
                stroke_width=2,
                height=150,
                width=400,
                key="firma_canvas"
            )

            if st.form_submit_button("Salva"):

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

                res = supabase.table(
                    "contratti"
                ).select(
                    "numero_fattura"
                ).order(
                    "id",
                    desc=True
                ).limit(
                    1
                ).execute()

                if res.data:

                    try:

                        nf = int(
                            res.data[0]["numero_fattura"]
                        ) + 1

                    except:

                        nf = 1

                else:

                    nf = 1

                obj = {

                    "nome": T(nome),
                    "cognome": T(cognome),
                    "residenza": T(residenza),
                    "targa": T(targa),
                    "prezzo": float(prezzo),
                    "inizio": T(data_inizio),
                    "fine": T(data_fine),
                    "firma": T(firma_b64),
                    "numero_fattura": int(nf),
                    "numero_patente": T(patente),
                    "codice_fiscale": T(cf)

                }

                supabase.table(
                    "contratti"
                ).insert(
                    obj
                ).execute()

                st.success("Salvato")

                st.rerun()

    if mode == "Archivio":

        st.title("Archivio")

        rows = supabase.table(
            "contratti"
        ).select(
            "*"
        ).order(
            "id",
            desc=True
        ).execute()

        for r in rows.data:

            label = f"{T(r.get('targa'))} - {T(r.get('cognome'))}"

            with st.expander(label):

                st.download_button(
                    "📜 Contratto",
                    data=pdf_contratto(r),
                    file_name=f"Contratto_{T(r.get('id'))}.pdf",
                    mime="application/pdf",
                    key=f"contratto_{T(r.get('id'))}"
                )

                st.download_button(
                    "💰 Fattura",
                    data=pdf_fattura(r),
                    file_name=f"Fattura_{T(r.get('id'))}.pdf",
                    mime="application/pdf",
                    key=f"fattura_{T(r.get('id'))}"
                )

                st.download_button(
                    "🚓 Modulo Multe",
                    data=pdf_multa(r),
                    file_name=f"Multe_{T(r.get('id'))}.pdf",
                    mime="application/pdf",
                    key=f"multe_{T(r.get('id'))}"
                )
