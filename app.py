import streamlit as st
import datetime
from fpdf import FPDF
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io
import base64

# ------------------------------------------------
# CONFIGURAZIONE
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
    if text is None: return ""
    return str(text).encode("latin-1", "replace").decode("latin-1")

def prossimo_numero_fattura():
    try:
        res = supabase.table("contratti").select("numero_fattura").order("numero_fattura", desc=True).limit(1).execute()
        if res.data and len(res.data) > 0:
            ultimo = res.data[0].get("numero_fattura")
            if ultimo: return int(ultimo) + 1
        return 1
    except:
        return 1

def upload_to_supabase(file, targa, prefix):
    try:
        if file is None: return None
        nome_file = f"{prefix}{targa}{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        supabase.storage.from_("documenti").upload(nome_file, file.getvalue())
        return supabase.storage.from_("documenti").get_public_url(nome_file)
    except:
        return None

# ------------------------------------------------
# FUNZIONE PDF
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
        pdf.cell(0, 10, "CONTRATTO DI NOLEGGIO / RENTAL AGREEMENT", ln=True, align="C", border="B")
        pdf.ln(8)
        pdf.set_font("Arial", "", 10)
       testo = f"""
Cliente: {c.get('nome')} {c.get('cognome')}
Nazionalità: {c.get('nazionalita', '---')}
Codice Fiscale / ID: {c.get('codice_fiscale', '---')}
Residenza: {c.get('indirizzo_cliente', '---')}

Nato a: {c.get('luogo_nascita')}
Data nascita: {c.get('data_nascita')}
Patente: {c.get('numero_patente')}

Targa: {c.get('targa')}
Periodo: dal {c.get('inizio')} al {c.get('fine')}

Prezzo: EUR {c.get('prezzo')}
Deposito: EUR {c.get('deposito')}
"""
    elif tipo == "FATTURA":
        pdf.set_font("Arial", "B", 15)
        pdf.cell(0, 10, "RICEVUTA DI PAGAMENTO / RECEIPT", ln=True, align="C", border="B")
        pdf.ln(10)
        pdf.set_font("Arial", "", 10)
        testo = f"Numero Ricevuta: {c.get('numero_fattura')}\nData emissione: {oggi}\nCliente: {c.get('nome')} {c.get('cognome')}\nTarga: {c.get('targa')}\nPeriodo: dal {c.get('inizio')} al {c.get('fine')}"
        pdf.multi_cell(0, 6, safe_text(testo))
        pdf.ln(8)
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 15, f"TOTALE INCASSATO: EUR {c.get('prezzo')}", ln=True, border=1, align="C")

    elif tipo == "MULTE":
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "COMUNICAZIONE DATI CONDUCENTE", ln=True, align="C", border="B")
        pdf.ln(8)
        pdf.set_font("Arial", "", 10)
       testo = f"""
Spett.le Polizia Locale

Il veicolo TARGA: {c.get('targa')}
era condotto da: {c.get('nome')} {c.get('cognome')}

Nato a: {c.get('luogo_nascita')} il {c.get('data_nascita')}
Residente in: {c.get('indirizzo_cliente', '---')}
Codice Fiscale / ID: {c.get('codice_fiscale', '---')}
Patente: {c.get('numero_patente')}

Si allega copia del documento d'identità/patente.
Data: {oggi}
"""
    if c.get("firma"):
        try:
            firma_bytes = base64.b64decode(c["firma"])
            pdf.image(io.BytesIO(firma_bytes), x=130, y=pdf.get_y()+10, w=50)
        except: pass

    pdf.ln(25)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 10, "Firma Cliente", ln=True, align="R")
    
  # Genera il PDF come stringa o bytearray
    pdf_out = pdf.output(dest="S")
    
    # Se è una stringa, la codifichiamo
    if isinstance(pdf_out, str):
        return pdf_out.encode("latin-1")
    
    # Se è un bytearray (l'errore che ricevi), lo trasformiamo in bytes
    return bytes(pdf_out)
# ------------------------------------------------
# LOGICA APP
# ------------------------------------------------
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.title("🔐 Login Battaglia Rent")
    pwd = st.text_input("Inserisci Password", type="password")
    if st.button("Entra"):
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state.autenticato = True
            st.rerun()
        else:
            st.error("Password errata")
else:
    with st.form("nuovo_noleggio", clear_on_submit=True):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Nome")
        cognome = col1.text_input("Cognome")
        nazionalita = col1.selectbox("Nazionalità", ["Italiana", "Straniera"])
        
        # Il Codice Fiscale appare solo se la nazionalità è Italiana
        cf = ""
        if nazionalita == "Italiana":
            cf = col1.text_input("Codice Fiscale")
        else:
            cf = col1.text_input("ID / Passaporto (per Stranieri)")

        indirizzo_c = col1.text_area("Indirizzo di Residenza (completo per Vigili)")
        data_inizio = col1.date_input("Inizio Noleggio")
        
        targa = col2.text_input("Targa").upper()
        patente = col2.text_input("Numero Patente")
        luogo_nascita = col2.text_input("Luogo nascita")
        data_nascita = col2.text_input("Data nascita")
        prezzo = col2.number_input("Prezzo Totale (€)", min_value=0.0)
        deposito = col2.number_input("Deposito (€)", min_value=0.0)
        data_fine = col2.date_input("Fine Noleggio")

        st.subheader("📸 Documenti e Firma")
        f1, f2 = st.columns(2)
        fronte = f1.file_uploader("Fronte Patente", type=["jpg", "png", "jpeg"])
        retro = f2.file_uploader("Retro Patente", type=["jpg", "png", "jpeg"])
        
        canvas = st_canvas(stroke_width=3, stroke_color="#000", background_color="#eee", height=150, width=400, key="firma_nuova")

        if st.form_submit_button("💾 SALVA CONTRATTO"):
            if nome and cognome and targa:
                firma_b64 = ""
                if canvas.image_data is not None:
                    img = Image.fromarray(canvas.image_data.astype("uint8"))
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    firma_b64 = base64.b64encode(buf.getvalue()).decode()

                # Caricamento foto (Assicurati che il bucket "documenti" sia PUBLIC)
                url_f = upload_to_supabase(fronte, targa, "fronte")
                url_r = upload_to_supabase(retro, targa, "retro")
                n_fatt = prossimo_numero_fattura()

                dati = {
                    "nome": nome, "cognome": cognome, "targa": targa,
                    "prezzo": prezzo, "deposito": deposito,
                    "inizio": str(data_inizio), "fine": str(data_fine),
                    "firma": firma_b64, "numero_fattura": n_fatt,
                    "luogo_nascita": luogo_nascita, "data_nascita": data_nascita,
                    "numero_patente": patente, "url_fronte": url_f, "url_retro": url_r,
                    "codice_fiscale": cf, "indirizzo_cliente": indirizzo_c, "nazionalita": nazionalita
                }
                supabase.table("contratti").insert(dati).execute()
                st.success(f"Contratto n° {n_fatt} salvato correttamente!")
                st.rerun()
