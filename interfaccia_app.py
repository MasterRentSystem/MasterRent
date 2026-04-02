import streamlit as st
import datetime
from fpdf import FPDF
from supabase import create_client

# -----------------------------
# CONFIGURAZIONE PAGINA
# -----------------------------

st.set_page_config(
    page_title="MasterRent Ischia",
    layout="wide"
)

st.title("🛵 MasterRent - Gestione Noleggi")

# -----------------------------
# CONNESSIONE SUPABASE
# -----------------------------

try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except Exception as e:
    st.error("Errore connessione Supabase")
    st.stop()

# -----------------------------
# FUNZIONE PULIZIA TESTO
# -----------------------------

def clean_text(text):

    if not text:
        return ""

    replacements = {
        "à": "a",
        "è": "e",
        "é": "e",
        "ì": "i",
        "ò": "o",
        "ù": "u",
        "€": "Euro"
    }

    for k, v in replacements.items():
        text = str(text).replace(k, v)

    return text.encode("latin-1", "ignore").decode("latin-1")

# -----------------------------
# GENERAZIONE PDF CONTRATTO
# -----------------------------

def genera_contratto_bytes(c):

    pdf = FPDF()

    pdf.add_page()

    pdf.set_font("Arial", "B", 16)

    pdf.cell(
        0,
        10,
        "CONTRATTO DI NOLEGGIO SCOOTER",
        ln=True,
        align="C"
    )

    pdf.ln(10)

    pdf.set_font("Arial", size=12)

    testo = f"""
CLIENTE: {c['cliente']}

TARGA: {c['targa']}

CODICE FISCALE: {c.get('cf','')}

DATA: {c['data_inizio']}

Il cliente dichiara di ricevere il veicolo
in perfette condizioni.

Le multe e i danni sono a carico del cliente.

Firma Cliente:

__________________________
"""

    pdf.multi_cell(
        0,
        8,
        clean_text(testo)
    )

    return pdf.output(
        dest="S"
    ).encode("latin-1")

# -----------------------------
# GENERAZIONE PDF RICEVUTA
# -----------------------------

def genera_ricevuta_bytes(c):

    pdf = FPDF()

    pdf.add_page()

    pdf.set_font("Arial", "B", 16)

    pdf.cell(
        0,
        10,
        "RICEVUTA DI PAGAMENTO",
        ln=True,
        align="C"
    )

    pdf.ln(15)

    pdf.set_font("Arial", size=12)

    pdf.cell(
        0,
        10,
        clean_text(f"Ricevuto da: {c['cliente']}"),
        ln=True
    )

    pdf.cell(
        0,
        10,
        clean_text(f"Per veicolo: {c['targa']}"),
        ln=True
    )

    pdf.ln(20)

    pdf.set_font("Arial", "B", 22)

    pdf.cell(
        0,
        20,
        clean_text(f"TOTALE EURO: {c['prezzo']}"),
        border=1,
        ln=True,
        align="C"
    )

    return pdf.output(
        dest="S"
    ).encode("latin-1")

# -----------------------------
# GENERAZIONE PDF VIGILI
# -----------------------------

def genera_vigili_bytes(c):

    pdf = FPDF()

    pdf.add_page()

    pdf.set_font("Arial", "B", 14)

    pdf.cell(
        0,
        10,
        "COMUNICAZIONE DATI CONDUCENTE",
        ln=True,
        align="C"
    )

    pdf.ln(10)

    pdf.set_font("Arial", size=12)

    testo = f"""
Il sottoscritto comunica che il veicolo
con targa {c['targa']}

era condotto da:

{c['cliente']}

Codice Fiscale:

{c.get('cf','')}

ai sensi della Legge 445/2000.
"""

    pdf.multi_cell(
        0,
        8,
        clean_text(testo)
    )

    return pdf.output(
        dest="S"
    ).encode("latin-1")

# -----------------------------
# INTERFACCIA
# -----------------------------

tab1, tab2, tab3 = st.tabs(
    [
        "📝 Nuovo Noleggio",
        "🗄️ Archivio",
        "🚨 Multe"
    ]
)

# -----------------------------
# NUOVO NOLEGGIO
# -----------------------------

with tab1:

    with st.form("form_noleggio"):

        col1, col2 = st.columns(2)

        nome = col1.text_input("Nome Cliente")

        targa = col1.text_input(
            "Targa"
        ).upper()

        prezzo = col2.number_input(
            "Prezzo (€)",
            min_value=0.0
        )

        cf = col2.text_input(
            "Codice Fiscale"
        )

        privacy = st.checkbox(
            "Accetto termini e condizioni"
        )

        if st.form_submit_button(
            "💾 SALVA NOLEGGIO"
        ):

            if nome and targa and privacy:

                dati = {
                    "cliente": nome,
                    "targa": targa,
                    "prezzo": prezzo,
                    "cf": cf,
                    "data_inizio": str(
                        datetime.date.today()
                    )
                }

                supabase.table(
                    "contratti"
                ).insert(
                    dati
                ).execute()

                st.success(
                    "Noleggio salvato"
                )

            else:

                st.error(
                    "Compila tutti i campi"
                )

# -----------------------------
# ARCHIVIO
# -----------------------------

with tab2:

    st.subheader(
        "Storico Noleggi"
    )

    try:

        response = supabase.table(
            "contratti"
        ).select(
            "*"
        ).order(
            "id",
            desc=True
        ).execute()

        contratti = response.data

        for c in contratti:

            with st.expander(
                f"{c['cliente']} - {c['targa']}"
            ):

                col1, col2 = st.columns(2)

                contratto_bytes = genera_contratto_bytes(c)

                ricevuta_bytes = genera_ricevuta_bytes(c)

                col1.download_button(
                    label="📜 SCARICA CONTRATTO",
                    data=contratto_bytes,
                    file_name=f"Contratto_{c['id']}.pdf",
                    mime="application/pdf",
                    key=f"contratto_{c['id']}"
                )

                col2.download_button(
                    label="💰 SCARICA RICEVUTA",
                    data=ricevuta_bytes,
                    file_name=f"Ricevuta_{c['id']}.pdf",
                    mime="application/pdf",
                    key=f"ricevuta_{c['id']}"
                )

    except Exception:

        st.info(
            "Nessun dato trovato"
        )

# -----------------------------
# MULTE
# -----------------------------

with tab3:

    st.subheader(
        "Gestione Multe"
    )

    targa_multa = st.text_input(
        "Inserisci Targa"
    ).upper()

    if targa_multa:

        response = supabase.table(
            "contratti"
        ).select(
            "*"
        ).eq(
            "targa",
            targa_multa
        ).execute()

        if response.data:

            c = response.data[0]

            vigili_bytes = genera_vigili_bytes(c)

            st.download_button(
                label="🚨 SCARICA MODULO VIGILI",
                data=vigili_bytes,
                file_name=f"Vigili_{targa_multa}.pdf",
                mime="application/pdf",
                key=f"vigili_{c['id']}"
            )

        else:

            st.warning(
                "Nessun contratto trovato"
            )

