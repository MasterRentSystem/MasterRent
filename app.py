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
import xml.etree.ElementTree as ET

# --- CONFIGURAZIONE AZIENDALE ---
DITTA = "BATTAGLIA RENT"
TITOLARE = "BATTAGLIA MARIANNA"
PIVA = "10252601215"
CF_DITTA = "BTTMNN87A53Z112S"
SEDE = "Via Cognole n. 5 - 80075 Forio (NA)"

# Connessione Supabase
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

# --- GENERATORE XML FATTURA ---
def genera_xml_fattura(c):
    root = ET.Element("p:FatturaElettronica", {"versione": "FPR12", "xmlns:p": "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"})
    header = ET.SubElement(root, "FatturaElettronicaHeader")
    trasm = ET.SubElement(header, "DatiTrasmissione")
    id_trasm = ET.SubElement(trasm, "IdTrasmittente")
    ET.SubElement(id_trasm, "IdPaese").text = "IT"
    ET.SubElement(id_trasm, "IdCodice").text = PIVA
    ET.SubElement(trasm, "ProgressivoInvio").text = f"{c['numero_fattura']}"
    ET.SubElement(trasm, "FormatoTrasmissione").text = "FPR12"
    ET.SubElement(trasm, "CodiceDestinatario").text = s(c.get('codice_sdi', '0000000'))
    
    cedente = ET.SubElement(header, "CedentePrestatore")
    dati_anag = ET.SubElement(cedente, "DatiAnagrafici")
    id_f = ET.SubElement(dati_anag, "IdFiscaleIVA")
    ET.SubElement(id_f, "IdPaese").text = "IT"
    ET.SubElement(id_f, "IdCodice").text = PIVA
    ET.SubElement(dati_anag, "RegimeFiscale").text = "RF19"
    
    body = ET.SubElement(root, "FatturaElettronicaBody")
    dati_gen = ET.SubElement(body, "DatiGenerali")
    d_dg = ET.SubElement(dati_gen, "DatiGeneraliDocumento")
    ET.SubElement(d_dg, "TipoDocumento").text = "TD01"
    ET.SubElement(d_dg, "Data").text = datetime.now().strftime("%Y-%m-%d")
    ET.SubElement(d_dg, "Numero").text = f"{c['numero_fattura']}"
    ET.SubElement(d_dg, "ImportoTotaleDocumento").text = f"{c['prezzo']:.2f}"
    
    return ET.tostring(root, encoding='utf-8', method='xml')

# --- MOTORE PDF (VERSIONE CORRETTA) ---
class PDF_Final(FPDF):
    def header(self):
        self.set_font("Arial", "B", 10)
        self.cell(0, 5, DITTA, ln=True)
        self.set_font("Arial", "", 7)
        self.cell(0, 4, f"{SEDE} | P.IVA: {PIVA}", ln=True)
        self.ln(2)

def genera_pdf_unificato(c):
    pdf = PDF_Final()
    pdf.add_page()
    w = pdf.epw

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, safe(f"CONTRATTO E FATTURA N. {c['numero_fattura']}"), ln=True, align="C")

    # Dati Cliente e Mezzo
    pdf.set_font("Arial", "B", 8); pdf.set_fill_color(240, 240, 240)
    pdf.cell(w/2, 6, " DATI CLIENTE", 1, 0, fill=True)
    pdf.cell(w/2, 6, " DETTAGLI NOLEGGIO", 1, 1, fill=True)
    
    pdf.set_font("Arial", "", 7)
    y_start = pdf.get_y()
    info_c = f"Nome: {c['nome']} {c['cognome']}\nC.F: {c.get('codice_fiscale')}\nPatente: {c.get('numero_patente')}\nNazionalita': {c.get('nazionalita')}"
    pdf.multi_cell(w/2, 4, safe(info_c), border=1)
    
    pdf.set_xy(w/2 + 10, y_start)
    info_n = f"Mezzo: {c['modello']} ({c['targa']})\nDal: {c.get('data_inizio')} Al: {c.get('data_fine')}\nTotale: {c['prezzo']} EUR\nPagato: {c.get('pagato')} ({c.get('metodo_pagamento')})"
    pdf.multi_cell(w/2, 4, safe(info_n), border=1)

    # Clausole IT/EN
    pdf.ln(2); pdf.set_font("Arial", "B", 7); pdf.cell(0, 4, "CONDIZIONI GENERALI / TERMS", ln=True)
    pdf.set_font("Arial", "", 5.5)
    cl = [
        "1. Isola d'Ischia: uso limitato all'isola.", "1. Limited to Ischia island.",
        "2. Guida: ammessa solo al firmatario.", "2. Only signer is allowed to drive.",
        "3. Danni: cliente responsabile danni/furto.", "3. Customer liable for damage/theft.",
        "4. Multe: a carico cliente + 25.83 Euro fee.", "4. Fines + 25.83 Euro fee to customer.",
        "5. Riconsegna: >30 min ritardo = 1gg extra.", "5. Delay >30 min = 1 extra day fee.",
        "6. Carburante: riconsegna stesso livello.", "6. Return with same fuel level.",
        "7. Chiavi: smarrimento Euro 250,00.", "7. Lost keys penalty: Euro 250.00.",
        "8. Casco: obbligatorio per legge.", "8. Helmet is mandatory."
    ]
    for i in range(0, len(cl), 2):
        pdf.cell(w/2, 3.5, safe(cl[i]), border='B')
        pdf.cell(w/2, 3.5, safe(cl[i+1]), border='B', ln=1)

    # Privacy
    pdf.set_font("Arial", "", 5.5)
    pdf.multi_cell(0, 3, "Privacy: I dati sono trattati per fini contrattuali (D.Lgs 196/03). / Data processed for contract purposes.", border=1)

    # Firme e Foto
    pdf.ln(2)
    y_f = pdf.get_y()
    
    # Foto miniaturizzate
    try:
        if c.get("foto_patente"):
            p_img = str(c["foto_patente"]).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(p_img)), x=10, y=y_f, w=40, h=25)
        if c.get("foto_mezzo"):
            m_img = str(c["foto_mezzo"]).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(m_img)), x=55, y=y_f, w=40, h=25)
    except: pass

    # Box Firme (CORRETTO: align='L' invece di 'T')
    pdf.set_xy(100, y_f)
    pdf.set_font("Arial", "B", 6)
    pdf.cell(45, 25, "Firma Cliente", border=1, align="L")
    pdf.set_xy(150, y_f)
    pdf.cell(45, 25, "Approvazione Clausole", border=1, align="L")

    try:
        if c.get("firma"):
            f1 = str(c["firma"]).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(f1)), x=105, y=y_f+5, w=35)
        if c.get("firma2"):
            f2 = str(c["firma2"]).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(f2)), x=155, y=y_f+5, w=35)
    except: pass

    return bytes(pdf.output(dest="S"))

# --- INTERFACCIA STREAMLIT ---
st.set_page_config(page_title="BATTAGLIA RENT", layout="wide")

if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Password", type="password") == "1234":
        if st.button("ACCEDI"): st.session_state.auth = True; st.rerun()
    st.stop()

tab1, tab2 = st.tabs(["📝 NUOVO NOLEGGIO", "📂 ARCHIVIO"])

with tab1:
    with st.form("main_form"):
        c1, c2, c3 = st.columns(3)
        mod = c1.text_input("Modello")
        tg = c2.text_input("Targa").upper()
        prz = c3.number_input("Prezzo (€)", 0.0)
        
        c4, c5, c6 = st.columns(3)
        n, cg, wa = c4.text_input("Nome"), c5.text_input("Cognome"), c6.text_input("WhatsApp")
        
        c7, c8, c9 = st.columns(3)
        cf, pat, naz = c7.text_input("Codice Fiscale"), c8.text_input("Patente"), c9.text_input("Nazionalità")
        
        o1, o2 = st.columns(2)
        met = o1.selectbox("Metodo", ["Cash", "Carta"])
        pag = o2.selectbox("Pagato", ["Sì", "No"])

        st.subheader("📸 FOTO")
        f1, f2 = st.columns(2)
        foto_pat = f1.camera_input("Scatta Foto Patente")
        foto_mot = f2.camera_input("Scatta Foto Stato Motorino")

        st.subheader("🖋️ FIRME")
        s1, s2 = st.columns(2)
        with s1: can1 = st_canvas(height=120, width=400, stroke_width=1, key="c1")
        with s2: can2 = st_canvas(height=120, width=400, stroke_width=1, key="c2")

        if st.form_submit_button("SALVA E GENERA OTP"):
            def get_b64(file):
                return "data:image/png;base64," + base64.b64encode(file.getvalue()).decode() if file else ""
            def get_canvas(can):
                if can.image_data is not None:
                    img = Image.fromarray(can.image_data.astype("uint8"))
                    buf = io.BytesIO(); img.save(buf, format="PNG")
                    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
                return ""

            otp = str(random.randint(100000, 999999))
            st.session_state.temp = {
                "nome": n, "cognome": cg, "targa": tg, "prezzo": prz, "modello": mod,
                "data_inizio": datetime.now().strftime("%d/%m/%Y"), "data_fine": "", 
                "codice_fiscale": cf, "numero_patente": pat, "nazionalita": naz, "pec": wa,
                "metodo_pagamento": met, "pagato": pag, "otp_code": otp,
                "foto_patente": get_b64(foto_pat), "foto_mezzo": get_b64(foto_mot),
                "firma": get_canvas(can1), "firma2": get_canvas(can2)
            }
            st.markdown(f"### [📲 INVIA OTP](https://wa.me/{wa}?text=Codice+Firma:+{otp})")

    if "temp" in st.session_state:
        v = st.text_input("Inserisci OTP")
        if st.button("CONFERMA"):
            if v == st.session_state.temp["otp_code"]:
                st.session_state.temp["numero_fattura"] = get_prossimo_numero()
                supabase.table("contratti").insert(st.session_state.temp).execute()
                st.success("✅ SALVATO!")
                del st.session_state.temp
            else: st.error("OTP Errato")

with tab2:
    q = st.text_input("🔍 Cerca")
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    for r in res.data:
        if q.lower() in f"{s(r['cognome'])} {s(r['targa'])}".lower():
            with st.expander(f"📄 {r['numero_fattura']} - {r['cognome']}"):
                col_a, col_b = st.columns(2)
                col_a.download_button("📜 Scarica Contratto", genera_pdf_unificato(r), f"Contratto_{r['id']}.pdf")
                col_b.download_button("💾 Scarica XML", genera_xml_fattura(r), f"Fattura_{r['numero_fattura']}.xml")
