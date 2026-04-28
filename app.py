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
INFO_AZIENDA = "Via Cognole n. 5 - 80075 Forio (NA)"

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

# --- MOTORE PDF (CONTRATTO E CLAUSOLE) ---
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 10)
        self.cell(0, 5, DITTA, ln=True, align="L")
        self.set_font("Arial", "", 8)
        self.cell(0, 4, f"{INFO_AZIENDA} | P.IVA: {PIVA}", ln=True)
        self.ln(5)

def genera_contratto_completo(c):
    pdf = PDF(); pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, safe(f"CONTRATTO DI NOLEGGIO N. {c['numero_fattura']}"), ln=True, align="C")
    
    # Dati Cliente e Mezzo
    pdf.set_font("Arial", "B", 9); pdf.cell(0, 7, " DATI CLIENTE E VEICOLO", 1, ln=True, fill=True)
    pdf.set_font("Arial", "", 9)
    testo = (f"Cliente: {c['nome']} {c['cognome']} ({c['codice_fiscale']})\n"
             f"Indirizzo: {c.get('indirizzo_cliente', 'N/D')}\n"
             f"Patente: {c.get('numero_patente', 'N/D')}\n"
             f"Mezzo: {c['modello']} tg: {c['targa']}\n"
             f"Prezzo: {c['prezzo']} EUR | Periodo: {c.get('inizio')} - {c.get('fine')}")
    pdf.multi_cell(0, 6, safe(testo), border=1)
    
    # Firma OTP
    pdf.ln(5); pdf.set_font("Arial", "B", 9); pdf.cell(0, 6, "CERTIFICAZIONE FIRMA ELETTRONICA (OTP)", ln=True)
    pdf.set_font("Arial", "I", 8)
    pdf.multi_cell(0, 5, safe(f"Documento convalidato via OTP inviato al numero {c.get('pec')} in data {c.get('timestamp_firma')}. ID: {c.get('otp_code')}"), border=1)
    
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

    # --- PAGINA 2: LE 14 CLAUSOLE ---
    pdf.add_page()
    pdf.set_font("Arial", "B", 8); pdf.cell(95, 6, "CONDIZIONI GENERALI", 0, 0); pdf.cell(95, 6, "GENERAL CONDITIONS", 0, 1)
    pdf.set_font("Arial", "", 5.5)
    
    clausole_it = (
        "1) Il noleggio e' limitato all'isola d'Ischia. 2) Il mezzo deve essere guidato solo dal firmatario. "
        "3) Il cliente e' responsabile di ogni danno al veicolo, furto o incendio. 4) Le contravvenzioni sono a carico del cliente + 25.83 Euro spese gestione. "
        "5) Vietato il sub-noleggio. 6) Riconsegna obbligatoria entro l'orario stabilito. 7) Il veicolo viene consegnato in ottimo stato. "
        "8) Carburante a carico del cliente. 9) Fori competenti: Napoli. 10) Il cliente dichiara di aver visionato il mezzo. "
        "11) Smarrimento chiavi: addebito 250 Euro. 12) Casco obbligatorio per legge. 13) Assicurazione RCA inclusa. 14) Divieto di guida in stato di ebbrezza."
    )
    clausole_en = (
        "1) Rental is limited to Ischia island. 2) Only the signer is authorized to drive. "
        "3) Customer is liable for any damage, theft or fire. 4) Traffic fines are at customer's expense + 25.83 Euro admin fee. "
        "5) Sub-rental is forbidden. 6) Vehicle must be returned on time. 7) Vehicle is delivered in perfect condition. "
        "8) Fuel is at customer's expense. 9) Jurisdiction: Naples. 10) Customer declares to have inspected the vehicle. "
        "11) Loss of keys: 250 Euro charge. 12) Helmet is mandatory by law. 13) RCA Insurance included. 14) Drink-driving is strictly forbidden."
    )
    
    y_start = pdf.get_y()
    pdf.multi_cell(92, 3.5, safe(clausole_it), border=1)
    pdf.set_xy(105, y_start)
    pdf.multi_cell(92, 3.5, safe(clausole_en), border=1)
    
    return bytes(pdf.output(dest="S"))

# --- MOTORE MODULO VIGILI (ART. 196) ---
def genera_modulo_vigili(c):
    pdf = PDF(); pdf.add_page()
    pdf.set_font("Arial", "B", 12); pdf.cell(0, 10, "COMUNICAZIONE DATI CONDUCENTE (Art. 196 CdS)", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.ln(10)
    testo = (f"La sottoscritta {TITOLARE}, titolare della ditta {DITTA},\n"
             f"comunica che in data {c.get('inizio')} il veicolo tg. {c['targa']}\n"
             f"modello {c['modello']} era affidato al Sig./Sig.ra:\n\n"
             f"NOME: {c['nome']}  COGNOME: {c['cognome']}\n"
             f"NATO IL: {c.get('data_nascita', 'N/D')}\n"
             f"CODICE FISCALE: {c['codice_fiscale']}\n"
             f"RESIDENZA: {c.get('indirizzo_cliente', 'N/D')}\n"
             f"PATENTE N.: {c.get('numero_patente', 'N/D')}\n\n"
             f"Il suddetto si assume ogni responsabilità civile e penale per l'utilizzo del mezzo.")
    pdf.multi_cell(0, 8, safe(testo))
    pdf.ln(20)
    pdf.cell(0, 10, "Firma del Titolare: __________________", ln=True, align="R")
    return bytes(pdf.output(dest="S"))

# --- INTERFACCIA STREAMLIT ---
st.set_page_config(page_title="Battaglia Rent Admin", layout="wide")

if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Password", type="password") == "1234":
        if st.button("Accedi"): st.session_state.auth = True; st.rerun()
    st.stop()

tab1, tab2 = st.tabs(["📝 NUOVO CONTRATTO", "📂 ARCHIVIO E MODULI"])

with tab1:
    with st.form("form_noleggio"):
        st.subheader("👤 Cliente")
        c1, c2, c3 = st.columns(3)
        n = c1.text_input("Nome")
        cg = c2.text_input("Cognome")
        wa = c3.text_input("WhatsApp (es. 3331234567)")
        
        c4, c5, c6 = st.columns(3)
        cf = c4.text_input("Codice Fiscale")
        ind = c5.text_input("Indirizzo Residenza")
        pat = c6.text_input("Numero Patente")
        
        st.subheader("🛵 Mezzo e Prezzo")
        c7, c8, c9 = st.columns(3)
        mod = c7.text_input("Modello")
        tg = c8.text_input("Targa").upper()
        pz = c9.number_input("Prezzo Totale (€)", min_value=0.0)

        st.subheader("📸 Foto Documenti e Danni")
        f1, f2 = st.columns(2)
        foto_p = f1.file_uploader("Carica Patente", type=['jpg','png'])
        foto_d = f2.file_uploader("Carica Foto Danni/Stato Mezzo", type=['jpg','png'])

        st.write("---")
        st.subheader("🖋️ Doppia Firma")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            st.caption("Firma 1: Accettazione")
            can1 = st_canvas(height=120, width=300, stroke_width=2, key="sig1")
        with col_f2:
            st.caption("Firma 2: Clausole Vessatorie")
            can2 = st_canvas(height=120, width=300, stroke_width=2, key="sig2")

        if st.form_submit_button("1. GENERA OTP E INVIA"):
            if not (n and wa and tg): st.error("Mancano dati obbligatori!")
            else:
                cod = str(random.randint(100000, 999999))
                st.session_state.otp_code = cod
                clean_wa = wa.replace(" ","").replace("+","")
                if not clean_wa.startswith("39"): clean_wa = "39" + clean_wa
                
                msg = f"BATTAGLIA RENT: Il tuo codice per firmare il noleggio della targa {tg} e': {cod}"
                url_wa = f"https://wa.me/{clean_wa}?text={urllib.parse.quote(msg)}"
                st.markdown(f"### [📲 CLICCA QUI PER INVIARE IL CODICE]({url_wa})")

    if "otp_code" in st.session_state:
        v_otp = st.text_input("Inserisci Codice dettato dal cliente")
        if st.button("2. SALVA CONTRATTO"):
            if v_otp == st.session_state.otp_code:
                # Converti firme
                i1 = Image.fromarray(can1.image_data.astype("uint8")); b1 = io.BytesIO(); i1.save(b1, format="PNG")
                f1_64 = "data:image/png;base64," + base64.b64encode(b1.getvalue()).decode()
                i2 = Image.fromarray(can2.image_data.astype("uint8")); b2 = io.BytesIO(); i2.save(b2, format="PNG")
                f2_64 = "data:image/png;base64," + base64.b64encode(b2.getvalue()).decode()

                dati = {
                    "nome": n, "cognome": cg, "targa": tg, "prezzo": pz, "modello": mod,
                    "codice_fiscale": cf, "indirizzo_cliente": ind, "numero_patente": pat,
                    "firma": f1_64, "firma2": f2_64, "otp_code": st.session_state.otp_code,
                    "pec": wa, "timestamp_firma": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "numero_fattura": get_prossimo_numero(), "inizio": str(datetime.now().date()), "fine": str(datetime.now().date()),
                    "foto_patente": image_to_base64(foto_p), "foto_danni": image_to_base64(foto_d)
                }
                supabase.table("contratti").insert(dati).execute()
                st.success("✅ CONTRATTO ARCHIVIATO!")
                del st.session_state.otp_code
            else: st.error("OTP errato")

with tab2:
    s_query = st.text_input("🔍 Cerca (Cognome o Targa)")
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    for r in res.data:
        if s_query.lower() in f"{s(r['cognome'])} {s(r['targa'])}".lower():
            with st.expander(f"📄 N. {r['numero_fattura']} - {r['cognome']} ({r['targa']})"):
                c1, c2, c3 = st.columns(3)
                c1.download_button("📜 Contratto + Clausole", genera_contratto_completo(r), f"Contratto_{r['id']}.pdf")
                c2.download_button("👮 Modulo Vigili", genera_modulo_vigili(r), f"Modulo_Vigili_{r['id']}.pdf")
                c3.download_button("📂 XML Aruba", genera_xml_fattura(r) if 'genera_xml_fattura' in globals() else b"", f"Fattura_{r['id']}.xml")
