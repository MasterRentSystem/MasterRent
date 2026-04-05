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
        testo = f"Cliente: {c.get('nome')} {c.get('cognome')}\nNato a: {c.get('luogo_nascita')}\nData nascita: {c.get('data_nascita')}\nPatente: {c.get('numero_patente')}\nTarga: {c.get('targa')}\nPeriodo: dal {c.get('inizio')} al {c.get('fine')}\nPrezzo: EUR {c.get('prezzo')}\nDeposito: EUR {c.get('deposito')}"
        pdf.multi_cell(0, 6, safe_text(testo))

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
        testo = f"Spett.le Polizia Locale\n\nIl veicolo TARGA: {c.get('targa')}\nera condotto da: {c.get('nome')} {c.get('cognome')}\nNato a: {c.get('luogo_nascita')}\nData nascita: {c.get('data_nascita')}\nPatente: {c.get('numero_patente')}\nData: {oggi}"
        pdf.multi_cell(0, 6, safe_text(testo))

    if c.get("firma"):
        try:
            firma_bytes = base64.b64decode(c["firma"])
            pdf.image(io.BytesIO(firma_bytes), x=130, y=pdf.get_y()+10, w=50)
        except: pass

    pdf.ln(25)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 10, "Firma Cliente", ln=True, align="R")
    
    pdf_out = pdf.output(dest="S")
    return pdf_out.encode("latin-1") if isinstance(pdf_out, str) else pdf_out

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
    # --- FORM NUOVO NOLEGGIO ---
    st.title("🛵 Nuovo Noleggio Scooter")
    with st.form("nuovo_noleggio", clear_on_submit=True):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Nome")
        cognome = col1.text_input("Cognome")
        luogo_nascita = col1.text_input("Luogo nascita")
        data_nascita = col1.text_input("Data nascita")
        data_inizio = col1.date_input("Inizio Noleggio")
        
        targa = col2.text_input("Targa").upper()
        prezzo = col2.number_input("Prezzo Totale (€)", min_value=0.0)
        deposito = col2.number_input("Deposito Cauzionale (€)", min_value=0.0)
        patente = col2.text_input("Numero Patente")
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

                url_f = upload_to_supabase(fronte, targa, "fronte")
                url_r = upload_to_supabase(retro, targa, "retro")
                n_fatt = prossimo_numero_fattura()

                dati = {
                    "nome": nome, "cognome": cognome, "targa": targa,
                    "prezzo": prezzo, "deposito": deposito,
                    "inizio": str(data_inizio), "fine": str(data_fine),
                    "firma": firma_b64, "numero_fattura": n_fatt,
                    "luogo_nascita": luogo_nascita, "data_nascita": data_nascita,
                    "numero_patente": patente, "url_fronte": url_f, "url_retro": url_r
                }
                supabase.table("contratti").insert(dati).execute()
                st.success(f"Contratto n° {n_fatt} salvato!")
                st.rerun()
            else:
                st.error("Compila i campi obbligatori (Nome, Cognome, Targa)")

    # --- ARCHIVIO ---
    st.divider()
    st.subheader("📂 Archivio Contratti")
    try:
        res = supabase.table("contratti").select("*").order("id", desc=True).execute()
        if res.data:
            for c in res.data:
                label = f"📄 {c.get('numero_fattura')} - {c.get('nome')} {c.get('cognome')} ({c.get('targa')})"
                with st.expander(label):
                    c1, c2, c3 = st.columns(3)
                    id_c = c.get('id')
                    c1.download_button("📜 Contratto", genera_pdf_tipo(c, "CONTRATTO"), f"Contratto_{id_c}.pdf", "application/pdf", key=f"c_{id_c}")
                    c2.download_button("💰 Ricevuta", genera_pdf_tipo(c, "FATTURA"), f"Ricevuta_{id_c}.pdf", "application/pdf", key=f"r_{id_c}")
                    c3.download_button("🚨 Multe", genera_pdf_tipo(c, "MULTE"), f"Multe_{id_c}.pdf", "application/pdf", key=f"m_{id_c}")
                    
                    if c.get("url_fronte") or c.get("url_retro"):
                        st.write("---")
                        col_f1, col_f2 = st.columns(2)
                        if c.get("url_fronte"): col_f1.link_button("👁️ Vedi Fronte", c["url_fronte"])
                        if c.get("url_retro"): col_f2.link_button("👁️ Vedi Retro", c["url_retro"])
        else:
            st.info("Archivio vuoto.")
    except Exception as e:
        st.error(f"Errore caricamento: {e}")
