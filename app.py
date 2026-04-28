import streamlit as st
from supabase import create_client, Client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from fpdf import FPDF
import io
import base64
import random
from datetime import datetime
import urllib.parse

# --- CONFIGURAZIONE AZIENDALE ---
DITTA = "BATTAGLIA RENT"
TITOLARE = "BATTAGLIA MARIANNA"
PIVA = "10252601215"
CF_DITTA = "BTTMNN87A53Z112S"

# Connessione Supabase
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- FUNZIONI UTILI ---
def s(v): return "" if v is None else str(v)
def safe(t): return s(t).encode("latin-1", "replace").decode("latin-1")

def get_prossimo_numero():
    try:
        res = supabase.table("contratti").select("numero_fattura").execute()
        nums = [int(r['numero_fattura']) for r in res.data if str(r['numero_fattura']).isdigit()]
        return max(nums) + 1 if nums else 1
    except: return 1

def image_to_base64(uploaded_file):
    if uploaded_file is not None:
        return "data:image/png;base64," + base64.b64encode(uploaded_file.getvalue()).decode()
    return None

# --- MOTORE PDF ---
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 10)
        self.cell(0, 5, DITTA, ln=True)
        self.set_font("Arial", "", 8)
        self.cell(0, 4, f"P.IVA: {PIVA} | C.F.: {CF_DITTA}", ln=True)
        self.ln(5)

def genera_contratto_completo(c):
    pdf = PDF(); pdf.add_page()
    pdf.set_font("Arial", "B", 12); pdf.cell(0, 10, safe(f"CONTRATTO DI NOLEGGIO N. {c['numero_fattura']}"), ln=True, align="C")
    
    # Dati Noleggio Espansi
    pdf.set_font("Arial", "B", 9); pdf.cell(0, 7, " DATI CLIENTE E VEICOLO", 1, ln=True, fill=True)
    pdf.set_font("Arial", "", 9)
    testo_dati = (f"Cliente: {c['nome']} {c['cognome']} ({c['codice_fiscale']})\n"
                  f"Residenza: {c.get('indirizzo_cliente', 'N/D')}\n"
                  f"Patente: {c.get('numero_patente', 'N/D')}\n"
                  f"Mezzo: {c['modello']} tg: {c['targa']}\n"
                  f"Prezzo: {c['prezzo']} EUR")
    pdf.multi_cell(0, 6, safe(testo_dati), border=1)
    
    # Validazione OTP
    pdf.ln(5); pdf.set_font("Arial", "B", 9); pdf.cell(0, 6, "CERTIFICAZIONE FIRMA OTP", ln=True)
    pdf.set_font("Arial", "I", 8)
    pdf.multi_cell(0, 5, safe(f"Validato tramite OTP inviato al numero {c.get('pec')} in data {c.get('timestamp_firma')}. Codice: {c.get('otp_code')}"), border=1)
    
    # Firme
    pdf.ln(5); y_f = pdf.get_y()
    pdf.set_font("Arial", "B", 7)
    pdf.cell(95, 30, "Firma 1: Accettazione", border=1, align="L")
    pdf.cell(95, 30, "Firma 2: Art. 1341-1342 cc", border=1, align="L")
    
    try:
        if c.get("firma"):
            f1 = str(c["firma"]).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(f1)), x=15, y=y_f+5, w=40)
        if c.get("firma2"):
            f2 = str(c["firma2"]).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(f2)), x=110, y=y_f+5, w=40)
    except: pass
    
    return bytes(pdf.output(dest="S"))

# --- INTERFACCIA ---
st.set_page_config(page_title="Battaglia Rent", layout="wide")

if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Password", type="password") == "1234":
        if st.button("Accedi"): st.session_state.auth = True; st.rerun()
    st.stop()

tab1, tab2 = st.tabs(["📝 NUOVO NOLEGGIO", "📂 ARCHIVIO"])

with tab1:
    with st.form("main_form"):
        st.subheader("👤 Anagrafica Cliente")
        c1, c2, c3 = st.columns(3)
        nome = c1.text_input("Nome")
        cognome = c2.text_input("Cognome")
        cell = c3.text_input("Cellulare WhatsApp (es. 3331234567)")
        
        c4, c5 = st.columns(2)
        indirizzo = c4.text_input("Indirizzo di Residenza")
        patente_num = c5.text_input("Numero Patente")
        cf = st.text_input("Codice Fiscale")

        st.subheader("🛵 Dati Veicolo")
        c6, c7, c8 = st.columns(3)
        mod = c6.text_input("Modello")
        trg = c7.text_input("Targa").upper()
        prz = c8.number_input("Prezzo (€)", min_value=0.0)

        st.subheader("📸 Documenti e Stato Mezzo")
        f1, f2 = st.columns(2)
        foto_pat = f1.file_uploader("Foto Patente", type=['png', 'jpg', 'jpeg'])
        foto_dan = f2.file_uploader("Foto Danni / Stato Mezzo", type=['png', 'jpg', 'jpeg'])
        
        st.write("---")
        st.subheader("🖋️ Firme")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            st.caption("Firma 1: Contratto")
            can1 = st_canvas(height=120, width=300, stroke_width=2, key="s1")
        with col_f2:
            st.caption("Firma 2: Clausole")
            can2 = st_canvas(height=120, width=300, stroke_width=2, key="s2")

        if st.form_submit_button("1. GENERA E INVIA OTP"):
            if not (nome and cell and trg): st.error("Inserisci Nome, Cellulare e Targa!")
            else:
                otp = str(random.randint(100000, 999999))
                st.session_state.otp = otp
                st.session_state.target = cell
                # Pulizia numero: togliamo spazi se presenti
                clean_cell = cell.replace(" ", "").replace("+", "")
                if not clean_cell.startswith("39"): clean_cell = "39" + clean_cell
                
                msg = f"BATTAGLIA RENT: Il tuo codice di firma per il mezzo {trg} e': {otp}"
                link = f"https://wa.me/{clean_cell}?text={urllib.parse.quote(msg)}"
                st.markdown(f"### [📲 CLICCA QUI PER INVIARE IL MESSAGGIO SU WHATSAPP]({link})")
                st.info("Dopo aver cliccato sopra e inviato il messaggio su WhatsApp, inserisci il codice qui sotto.")

    if "otp" in st.session_state:
        v_otp = st.text_input("Inserisci il codice ricevuto dal cliente")
        if st.button("2. CONFERMA E SALVA TUTTO"):
            if v_otp == st.session_state.otp:
                # Trasformazione immagini
                i1 = Image.fromarray(can1.image_data.astype("uint8")); b1 = io.BytesIO(); i1.save(b1, format="PNG")
                f1_64 = "data:image/png;base64," + base64.b64encode(b1.getvalue()).decode()
                i2 = Image.fromarray(can2.image_data.astype("uint8")); b2 = io.BytesIO(); i2.save(b2, format="PNG")
                f2_64 = "data:image/png;base64," + base64.b64encode(b2.getvalue()).decode()

                dati = {
                    "nome": nome, "cognome": cognome, "targa": trg, "prezzo": prz, "modello": mod,
                    "codice_fiscale": cf, "indirizzo_cliente": indirizzo, "numero_patente": patente_num,
                    "firma": f1_64, "firma2": f2_64, "otp_code": st.session_state.otp, 
                    "pec": st.session_state.target, "timestamp_firma": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "numero_fattura": get_prossimo_numero(),
                    "foto_patente": image_to_base64(foto_pat),
                    "foto_danni": image_to_base64(foto_dan)
                }
                supabase.table("contratti").insert(dati).execute()
                st.success("✅ CONTRATTO SALVATO E ARCHIVIATO!")
                del st.session_state.otp
            else: st.error("Codice errato")

with tab2:
    search = st.text_input("🔍 Cerca")
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    for r in res.data:
        if search.lower() in f"{s(r['cognome'])} {s(r['targa'])}".lower():
            with st.expander(f"Contratto {r['numero_fattura']} - {r['cognome']}"):
                st.write(f"Patente: {r.get('numero_patente')} | Cell: {r.get('pec')}")
                st.download_button("📜 Scarica PDF", genera_contratto_completo(r), f"Contratto_{r['id']}.pdf")   b2.download_button("📂 XML", genera_xml_fattura(r), f"Fattura_{r['id']}.xml")
