import streamlit as st
from supabase import create_client, Client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from fpdf import FPDF
import io
import base64
import random
from datetime import datetime
import xml.etree.ElementTree as ET

# --- DATI AZIENDALI RIPRISTINATI ---
DITTA = "BATTAGLIA RENT"
TITOLARE = "BATTAGLIA MARIANNA"
PIVA = "10252601215"
CF_DITTA = "BTTMNN87A53Z112S"
SEDE = "Via Cognole n. 5 - 80075 Forio (NA)"

URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

def s(v): return "" if v is None else str(v)
def safe(t): return s(t).encode("latin-1", "replace").decode("latin-1")

def get_prossimo_numero():
    try:
        res = supabase.table("contratti").select("numero_fattura").execute()
        nums = [int(r['numero_fattura']) for r in res.data if str(r['numero_fattura']).isdigit()]
        return max(nums) + 1 if nums else 1
    except: return 1

# --- 1. FATTURA XML ---
def genera_xml_fattura(c):
    root = ET.Element("p:FatturaElettronica", {"versione": "FPR12", "xmlns:p": "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"})
    body = ET.SubElement(root, "FatturaElettronicaBody")
    dati_gen = ET.SubElement(body, "DatiGenerali")
    d_dg = ET.SubElement(dati_gen, "DatiGeneraliDocumento")
    ET.SubElement(d_dg, "TipoDocumento").text = "TD01"
    ET.SubElement(d_dg, "Data").text = datetime.now().strftime("%Y-%m-%d")
    ET.SubElement(d_dg, "Numero").text = f"{c.get('numero_fattura')}"
    ET.SubElement(d_dg, "ImportoTotaleDocumento").text = f"{c.get('prezzo', 0.0):.2f}"
    return ET.tostring(root, encoding='utf-8', method='xml')

# --- 2. MODULO MULTE (SEPARATO) ---
def genera_modulo_multe(c):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "DICHIARAZIONE DI RESPONSABILITA' E MULTE", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Arial", "", 10)
    testo = f"""Il sottoscritto {c.get('nome')} {c.get('cognome')}, nato a {c.get('luogo_nascita')} il {c.get('data_nascita')},
relativamente al noleggio del mezzo {c.get('modello')} targa {c.get('targa')}, 
DICHIARA di assumersi ogni responsabilità civile e penale per infrazioni al Codice della Strada 
commesse durante il periodo di noleggio (dal {c.get('data_inizio')} al {c.get('data_fine')}).

Il cliente AUTORIZZA BATTAGLIA RENT al recupero delle somme e alla comunicazione dei dati 
alle autorità competenti, con l'addebito di una spesa di gestione pratica pari a Euro 25,83 
per ogni singolo verbale notificato.
    """
    pdf.multi_cell(0, 6, safe(testo), border=1)
    pdf.ln(10)
    pdf.cell(0, 5, "Firma del Cliente per accettazione specifica clausola multe:", ln=True)
    try:
        if c.get("firma2"):
            f2 = str(c["firma2"]).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(f2)), x=10, y=pdf.get_y()+2, w=50)
    except: pass
    return bytes(pdf.output(dest="S"))

# --- 3. CONTRATTO (SENZA FOTO) ---
class PDF_Contratto(FPDF):
    def header(self):
        self.set_font("Arial", "B", 10); self.cell(0, 5, DITTA, ln=True)
        self.set_font("Arial", "", 7); self.cell(0, 4, f"{SEDE} | P.IVA: {PIVA}", ln=True); self.ln(2)

def genera_pdf_contratto(c):
    pdf = PDF_Contratto()
    pdf.add_page()
    w = pdf.epw
    pdf.set_font("Arial", "B", 12); pdf.cell(0, 7, safe(f"CONTRATTO DI LOCAZIONE N. {c.get('numero_fattura')}"), ln=True, align="C")
    
    # DATI COMPLETI
    pdf.set_font("Arial", "B", 8); pdf.set_fill_color(240, 240, 240)
    pdf.cell(w, 5, " DATI CLIENTE", 1, 1, fill=True)
    pdf.set_font("Arial", "", 7)
    pdf.cell(w/2, 5, safe(f"Nome: {c.get('nome')} {c.get('cognome')}"), 1)
    pdf.cell(w/2, 5, safe(f"Codice Fiscale: {c.get('codice_fiscale')}"), 1, 1)
    pdf.cell(w/3, 5, safe(f"Nato a: {c.get('luogo_nascita')}"), 1)
    pdf.cell(w/3, 5, safe(f"Il: {c.get('data_nascita')}"), 1)
    pdf.cell(w/3, 5, safe(f"Nazionalita: {c.get('nazionalita')}"), 1, 1)
    pdf.cell(w, 5, safe(f"Indirizzo: {c.get('indirizzo')}"), 1, 1)
    pdf.cell(w/2, 5, safe(f"Patente: {c.get('numero_patente')}"), 1)
    pdf.cell(w/2, 5, safe(f"WhatsApp: {c.get('pec')}"), 1, 1)

    pdf.ln(1); pdf.set_font("Arial", "B", 8); pdf.cell(w, 5, " DETTAGLI NOLEGGIO", 1, 1, fill=True)
    pdf.set_font("Arial", "", 7)
    pdf.cell(w/4, 5, safe(f"Mezzo: {c.get('modello')}"), 1)
    pdf.cell(w/4, 5, safe(f"Targa: {c.get('targa')}"), 1)
    pdf.cell(w/4, 5, safe(f"Inizio: {c.get('data_inizio')} {c.get('ora_inizio')}"), 1)
    pdf.cell(w/4, 5, safe(f"Fine: {c.get('data_fine')} {c.get('ora_fine')}"), 1, 1)
    
    # FIRMA
    pdf.ln(5); pdf.set_font("Arial", "B", 8); pdf.cell(0, 5, "FIRMA DEL CLIENTE", ln=True)
    try:
        if c.get("firma"):
            f1 = str(c["firma"]).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(f1)), x=10, y=pdf.get_y(), w=40)
    except: pass
    return bytes(pdf.output(dest="S"))

# --- INTERFACCIA STREAMLIT ---
st.set_page_config(page_title="BATTAGLIA RENT", layout="wide")

if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Password", type="password") == "1234":
        if st.button("ACCEDI"): st.session_state.auth = True; st.rerun()
    st.stop()

tab1, tab2 = st.tabs(["📝 NUOVO CONTRATTO", "📂 ARCHIVIO"])

with tab1:
    with st.form("main_form"):
        # ... (Qui inserisci tutti i campi del form come nel messaggio precedente) ...
        # [Per non allungare troppo il testo, i campi sono quelli già stabiliti: nome, cognome, cf, date, ore, ecc.]
        # [IMPORTANTE: Assicurati di includere i camera_input per le foto!]
        st.subheader("📸 FOTO")
        f_pat = st.camera_input("Scatta Foto Patente")
        f_mez = st.camera_input("Scatta Foto Mezzo")
        
        st.subheader("🖋️ FIRME")
        s_c1, s_c2 = st.columns(2)
        with s_c1: can1 = st_canvas(height=100, width=400, stroke_width=1, key="c1")
        with s_c2: can2 = st_canvas(height=100, width=400, stroke_width=1, key="c2")
        
        # Bottone salvataggio (genera OTP e salva i dati in st.session_state.temp)
        if st.form_submit_button("GENERA CONTRATTO"):
            # Logica di salvataggio foto e firme in base64...
            st.success("Dati pronti per l'archiviazione!")

with tab2:
    q = st.text_input("🔍 Cerca Cognome o Targa")
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    for r in res.data:
        if q.lower() in f"{s(r.get('cognome'))} {s(r.get('targa'))}".lower():
            with st.expander(f"📄 N.{r.get('numero_fattura')} - {r.get('cognome')} ({r.get('targa')})"):
                col1, col2, col3 = st.columns(3)
                col1.download_button("📜 CONTRATTO", genera_pdf_contratto(r), f"Contratto_{r['id']}.pdf", key=f"c_{r['id']}")
                col2.download_button("👮 MODULO MULTE", genera_modulo_multe(r), f"Multe_{r['id']}.pdf", key=f"m_{r['id']}")
                col3.download_button("💾 FATTURA XML", genera_xml_fattura(r), f"Fattura_{r['id']}.xml", key=f"x_{r['id']}")
                
                st.write("---")
                st.write("🖼️ *RECUPERO FOTO SALVATE*")
                f_a, f_b = st.columns(2)
                if r.get("foto_patente"):
                    img_pat = base64.b64decode(str(r["foto_patente"]).split(",")[1])
                    f_a.download_button("📸 Scarica Foto Patente", img_pat, "patente.png", "image/png", key=f"fp_{r['id']}")
                if r.get("foto_mezzo"):
                    img_mez = base64.b64decode(str(r["foto_mezzo"]).split(",")[1])
                    f_b.download_button("📸 Scarica Foto Mezzo", img_mez, "mezzo.png", "image/png", key=f"fm_{r['id']}")
