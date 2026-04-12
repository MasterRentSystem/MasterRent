import streamlit as st
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from fpdf import FPDF
import io, base64
from datetime import datetime

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Battaglia Rent", layout="wide")

DITTA = "BATTAGLIA RENT"
INDIRIZZO = "Via Cognole n. 5, Forio (NA)"
PIVA = "P.IVA: 10252601215 | C.F.: BTTMNN87A53Z112S"

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

# =========================
# UTILS
# =========================
def safe(t):
    return "" if t is None else str(t)

def upload(file, targa, label):
    if file is None:
        return ""
    name = f"{targa}{label}{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
    supabase.storage.from_("documenti").upload(name, file.getvalue())
    return supabase.storage.from_("documenti").get_public_url(name)

def next_invoice():
    r = supabase.table("contratti").select("numero_fattura").order("id", desc=True).limit(1).execute()
    if r.data:
        return (r.data[0]["numero_fattura"] or 0) + 1
    return 1

def get_firma(img_data):
    if img_data is None:
        return ""
    img = Image.fromarray(img_data.astype("uint8"))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

# =========================
# PDF MULTA (VIGILI)
# =========================
def pdf_multa(c):
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, DITTA, ln=True)
    pdf.cell(0, 6, INDIRIZZO, ln=True)
    pdf.cell(0, 6, PIVA, ln=True)
    pdf.ln(5)

    testo = f"""Spett. le
Polizia Locale di ________________

OGGETTO: RIFERIMENTO VS. ACCERTAMENTO VIOLAZIONE N. ____ PROT. ____ - COMUNICAZIONE LOCAZIONE VEICOLO

In riferimento al verbale, la sottoscritta BATTAGLIA MARIANNA,
titolare della ditta {DITTA}, dichiara che:

Il veicolo targato {safe(c.get('targa'))} in data {safe(c.get('inizio'))}
era concesso in locazione a:

COGNOME E NOME: {safe(c.get('nome'))} {safe(c.get('cognome'))}
NATO A: {safe(c.get('luogo_nascita'))} il {safe(c.get('data_nascita'))}
RESIDENZA: {safe(c.get('indirizzo_cliente'))}
PATENTE: {safe(c.get('numero_patente'))}

Si allega contratto e documenti.

In fede
Marianna Battaglia
"""

    pdf.multi_cell(0, 5, testo)
    return pdf.output(dest="S").encode("latin-1")

# =========================
# CONTRATTO
# =========================
def pdf_contratto(c):
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, DITTA, ln=True)
    pdf.cell(0, 6, INDIRIZZO, ln=True)
    pdf.cell(0, 6, PIVA, ln=True)
    pdf.ln(5)

    testo = f"""
CONTRATTO DI NOLEGGIO SCOOTER

Cliente: {c.get('nome')} {c.get('cognome')}
CF: {c.get('codice_fiscale')}
Targa: {c.get('targa')}
Patente: {c.get('numero_patente')}
Periodo: {c.get('inizio')} - {c.get('fine')}
Prezzo: € {c.get('prezzo')}

CLAUSOLE LEGALI:
1.⁠ ⁠Responsabilità totale del conducente.
2.⁠ ⁠Multe sempre a carico cliente.
3.⁠ ⁠Furto/danni a carico locatario.
4.⁠ ⁠Divieto sub-noleggio.
5.⁠ ⁠Obbligo riconsegna nelle stesse condizioni.

GDPR:
Autorizza trattamento dati e conservazione documenti.

Firma Cliente
"""

    pdf.multi_cell(0, 5, testo)
    return pdf.output(dest="S").encode("latin-1")

# =========================
# FATTURA
# =========================
def pdf_fattura(c):
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, DITTA, ln=True)
    pdf.cell(0, 6, INDIRIZZO, ln=True)
    pdf.cell(0, 6, PIVA, ln=True)
    pdf.ln(5)

    testo = f"""
FATTURA / RICEVUTA

N° {c.get('numero_fattura')}
Cliente: {c.get('nome')} {c.get('cognome')}
Targa: {c.get('targa')}
Importo: € {c.get('prezzo')}
Deposito: € {c.get('deposito')}
"""

    pdf.multi_cell(0, 5, testo)
    return pdf.output(dest="S").encode("latin-1")

# =========================
# LOGIN
# =========================
if "ok" not in st.session_state:
    st.session_state.ok = False

if not st.session_state.ok:
    st.title("Login")
    if st.text_input("Password", type="password") == "1234":
        if st.button("Entra"):
            st.session_state.ok = True
            st.rerun()
    st.stop()

# =========================
# APP
# =========================
st.title("🚀 Battaglia Rent System")

tab1, tab2 = st.tabs(["Nuovo", "Archivio"])

# =========================
# NUOVO
# =========================
with tab1:
    with st.form("form"):
        c1, c2 = st.columns(2)

        nome = c1.text_input("Nome")
        cognome = c1.text_input("Cognome")
        cf = c1.text_input("Codice Fiscale")
        indirizzo = c1.text_area("Indirizzo")

        targa = c2.text_input("Targa").upper()
        patente = c2.text_input("Patente")
        nascita_l = c2.text_input("Luogo nascita")
        nascita_d = c2.text_input("Data nascita")

        prezzo = c2.number_input("Prezzo")
        deposito = c2.number_input("Deposito")

        inizio = st.date_input("Inizio")
        fine = st.date_input("Fine")

        f1, f2 = st.columns(2)
        fronte = f1.file_uploader("Fronte")
        retro = f2.file_uploader("Retro")

        firma = st_canvas(height=150, width=400, key="firma")

        if st.form_submit_button("SALVA"):
            inv = next_invoice()

            firma_b64 = get_firma(firma.image_data)

            u1 = upload(fronte, targa, "front")
            u2 = upload(retro, targa, "back")

            data = {
                "nome": nome,
                "cognome": cognome,
                "codice_fiscale": cf,
                "indirizzo_cliente": indirizzo,
                "targa": targa,
                "numero_patente": patente,
                "luogo_nascita": nascita_l,
                "data_nascita": nascita_d,
                "prezzo": prezzo,
                "deposito": deposito,
                "inizio": str(inizio),
                "fine": str(fine),
                "firma": firma_b64,
                "numero_fattura": inv,
                "url_fronte": u1,
                "url_retro": u2
            }

            supabase.table("contratti").insert(data).execute()
            st.success("Salvato!")

# =========================
# ARCHIVIO
# =========================
with tab2:
    rows = supabase.table("contratti").select("*").order("id", desc=True).execute()

    for c in rows.data:
        key = str(c["id"])

        with st.expander(f"{c.get('targa')} - {c.get('cognome')}"):

            st.download_button("📄 Contratto", pdf_contratto(c), f"contratto_{key}.pdf", key="c"+key)
            st.download_button("💰 Fattura", pdf_fattura(c), f"fattura_{key}.pdf", key="f"+key)
            st.download_button("🚨 Multe", pdf_multa(c), f"multa_{key}.pdf", key="m"+key)

            if c.get("url_fronte"):
                st.image(c["url_fronte"])
            if c.get("url_retro"):
                st.image(c["url_retro"])
