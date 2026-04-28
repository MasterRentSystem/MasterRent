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

# --- DATI FISSI ---
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

# --- GENERATORE XML FATTURA ELETTRONICA ---
def genera_xml_fattura(c):
    root = ET.Element("p:FatturaElettronica", {
        "versione": "FPR12",
        "xmlns:ds": "http://www.w3.org/2000/09/xmldsig#",
        "xmlns:p": "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2",
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance"
    })
    
    # Intestazione e Dati Trasmissione
    header = ET.SubElement(root, "FatturaElettronicaHeader")
    trasm = ET.SubElement(header, "DatiTrasmissione")
    id_trasm = ET.SubElement(trasm, "IdTrasmittente")
    ET.SubElement(id_trasm, "IdPaese").text = "IT"
    ET.SubElement(id_trasm, "IdCodice").text = PIVA
    ET.SubElement(trasm, "ProgressivoInvio").text = f"{c['numero_fattura']}"
    ET.SubElement(trasm, "FormatoTrasmissione").text = "FPR12"
    ET.SubElement(trasm, "CodiceDestinatario").text = s(c.get('codice_sdi', '0000000'))

    # Cedente (Marianna)
    cedente = ET.SubElement(header, "CedentePrestatore")
    dati_anag = ET.SubElement(cedente, "DatiAnagrafici")
    id_fisc = ET.SubElement(dati_anag, "IdFiscaleIVA")
    ET.SubElement(id_fisc, "IdPaese").text = "IT"
    ET.SubElement(id_fisc, "IdCodice").text = PIVA
    ET.SubElement(dati_anag, "CodiceFiscale").text = CF_DITTA
    anag = ET.SubElement(dati_anag, "Anagrafica")
    ET.SubElement(anag, "Denominazione").text = DITTA
    ET.SubElement(dati_anag, "RegimeFiscale").text = "RF19" # Regime Forfettario

    # Cessionario (Cliente)
    cliente = ET.SubElement(header, "CessionarioCommittente")
    dati_anag_cl = ET.SubElement(cliente, "DatiAnagrafici")
    ET.SubElement(dati_anag_cl, "CodiceFiscale").text = s(c.get('codice_fiscale'))
    anag_cl = ET.SubElement(dati_anag_cl, "Anagrafica")
    ET.SubElement(anag_cl, "Nome").text = s(c['nome'])
    ET.SubElement(anag_cl, "Cognome").text = s(c['cognome'])

    # Corpo Fattura
    body = ET.SubElement(root, "FatturaElettronicaBody")
    dati_gen = ET.SubElement(body, "DatiGenerali")
    dati_fatt = ET.SubElement(dati_gen, "DatiGeneraliDocumento")
    ET.SubElement(dati_fatt, "TipoDocumento").text = "TD01"
    ET.SubElement(dati_fatt, "Divisa").text = "EUR"
    ET.SubElement(dati_fatt, "Data").text = datetime.now().strftime("%Y-%m-%d")
    ET.SubElement(dati_fatt, "Numero").text = f"{c['numero_fattura']}"
    ET.SubElement(dati_fatt, "ImportoTotaleDocumento").text = f"{c['prezzo']:.2f}"

    dati_beni = ET.SubElement(body, "DatiBeniServizi")
    linea = ET.SubElement(dati_beni, "DettaglioLinee")
    ET.SubElement(linea, "NumeroLinea").text = "1"
    ET.SubElement(linea, "Descrizione").text = f"Noleggio {c['modello']} targa {c['targa']}"
    ET.SubElement(linea, "PrezzoUnitario").text = f"{c['prezzo']:.2f}"
    ET.SubElement(linea, "PrezzoTotale").text = f"{c['prezzo']:.2f}"
    ET.SubElement(linea, "AliquotaIVA").text = "0.00"
    ET.SubElement(linea, "Natura").text = "N2.2" # Non imponibile forfettari

    return ET.tostring(root, encoding='utf-8', method='xml')

# --- MOTORE PDF (UNICA PAGINA) ---
class PDF_Contratto(FPDF):
    def header(self):
        self.set_font("Arial", "B", 10)
        self.cell(0, 5, DITTA, ln=True, align="L")
        self.set_font("Arial", "", 7)
        self.cell(0, 4, f"{SEDE} | P.IVA: {PIVA}", ln=True)
        self.ln(2)

def genera_pdf_compatto(c):
    pdf = PDF_Contratto()
    pdf.add_page()
    w = pdf.epw

    # Header Titolo
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, safe(f"CONTRATTO DI LOCAZIONE N. {c['numero_fattura']}"), ln=True, align="C")

    # Dati Cliente e Mezzo (Affiancati per risparmiare spazio)
    pdf.set_font("Arial", "B", 8)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(w/2, 6, " DATI CLIENTE", 1, 0, fill=True)
    pdf.cell(w/2, 6, " DETTAGLI NOLEGGIO", 1, 1, fill=True)
    
    pdf.set_font("Arial", "", 7)
    y_top = pdf.get_y()
    cl_info = f"{c['nome']} {c['cognome']} ({c.get('nazionalita')})\nC.F: {c.get('codice_fiscale')}\nPatente: {c.get('numero_patente')}\nRes: {c.get('indirizzo_cliente')}"
    pdf.multi_cell(w/2, 4, safe(cl_info), border=1)
    
    pdf.set_xy(w/2 + 10, y_top)
    nl_info = f"Mezzo: {c['modello']} - {c['targa']}\nInizio: {c.get('data_inizio')} {c.get('ora_inizio')}\nFine: {c.get('data_fine')} {c.get('ora_fine')}\nPagamento: {c.get('prezzo')} EUR ({c.get('metodo_pagamento')})"
    pdf.multi_cell(w/2, 4, safe(nl_info), border=1)

    # CLAUSOLE (In 2 colonne piccole)
    pdf.ln(2)
    pdf.set_font("Arial", "B", 8)
    pdf.cell(0, 5, "CONDIZIONI GENERALI / GENERAL CONDITIONS", ln=True)
    pdf.set_font("Arial", "", 5.5)
    
    clausole = [
        "1. Isola d'Ischia: uso limitato al territorio isolano.", "1. Limited to Ischia island only.",
        "2. Guida: ammessa solo al firmatario del contratto.", "2. Only the signer is allowed to drive.",
        "3. Danni: cliente responsabile per danni, furto, incendio.", "3. Customer liable for damages, theft, fire.",
        "4. Multe: a carico cliente + 25,83 Euro gestione.", "4. Fines + 25.83 Euro fee charged to customer.",
        "5. Sub-noleggio: severamente vietato.", "5. Sub-rental is strictly forbidden.",
        "6. Ritardo: >30 min comporta addebito 1 giorno extra.", "6. Delay >30 min costs 1 extra rental day.",
        "7. Carburante: riconsegna con stesso livello iniziale.", "7. Return vehicle with same fuel level.",
        "8. Foro: competenza esclusiva Foro di Napoli.", "8. Jurisdiction: Court of Naples.",
        "9. Chiavi: smarrimento penale Euro 250,00.", "9. Lost keys penalty: Euro 250.00.",
        "10. Casco: obbligatorio. Responsabilita' del cliente.", "10. Helmet mandatory. Customer's full responsibility.",
        "11. Stato: mezzo ricevuto in perfetto stato d'uso.", "11. Vehicle received in perfect condition.",
        "12. Assicurazione: RCA inclusa come da legge.", "12. RCA Insurance included as per law.",
        "13. Alcool/Droga: divieto assoluto di guida alterata.", "13. No driving under influence of alcohol/drugs.",
        "14. Furto: in caso di furto, cliente responsabile.", "14. Customer responsible in case of theft."
    ]

    for i in range(0, len(clausole), 2):
        pdf.cell(w/2, 3.5, safe(clausole[i]), border='B')
        pdf.cell(w/2, 3.5, safe(clausole[i+1]), border='B', ln=1)

    # PRIVACY
    pdf.ln(1)
    pdf.set_font("Arial", "B", 7)
    pdf.cell(0, 4, "INFORMATIVA PRIVACY / PRIVACY POLICY", ln=True)
    pdf.set_font("Arial", "", 5.5)
    privacy_text = ("I dati sono trattati per finalita' contrattuali (D.Lgs 196/03). Il conferimento e' obbligatorio. / "
                    "Data is processed for contract purposes. Providing data is mandatory.")
    pdf.multi_cell(0, 3, safe(privacy_text), border=1)

    # FIRME (SOTTILE)
    pdf.ln(2)
    pdf.set_font("Arial", "B", 7)
    y_f = pdf.get_y()
    pdf.cell(w/2 - 2, 25, "Firma Cliente / Customer Signature", border=1)
    pdf.set_xy(w/2 + 12, y_f)
    pdf.cell(w/2 - 2, 25, "Approvazione Clausole (1341-1342 cc)", border=1)
    
    try:
        if c.get("firma"):
            f1 = str(c["firma"]).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(f1)), x=20, y=y_f+5, w=30)
        if c.get("firma2"):
            f2 = str(c["firma2"]).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(f2)), x=115, y=y_f+5, w=30)
    except: pass

    return bytes(pdf.output(dest="S"))

# --- INTERFACCIA STREAMLIT ---
st.set_page_config(page_title="BATTAGLIA RENT PRO", layout="wide")

if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Password", type="password") == "1234":
        if st.button("ACCEDI"): st.session_state.auth = True; st.rerun()
    st.stop()

t1, t2 = st.tabs(["📝 NUOVO CONTRATTO", "📂 ARCHIVIO"])

with t1:
    with st.form("main_form"):
        col1, col2, col3 = st.columns(3)
        mod = col1.text_input("Modello")
        tg = col2.text_input("Targa").upper()
        prz = col3.number_input("Prezzo (€)", 0.0)
        
        c_a1, c_a2, c_a3 = st.columns(3)
        nome = c_a1.text_input("Nome")
        cognome = c_a2.text_input("Cognome")
        wa = c_a3.text_input("WhatsApp")
        
        c_a4, c_a5, c_a6 = st.columns(3)
        cf = c_a4.text_input("Codice Fiscale")
        sdi = c_a5.text_input("Codice SDI / PEC")
        naz = c_a6.text_input("Nazionalità")
        
        # Orari
        o1, o2 = st.columns(2)
        d_in = o1.date_input("Data Inizio")
        h_in = o1.time_input("Ora Inizio")
        d_fi = o2.date_input("Data Fine")
        h_fi = o2.time_input("Ora Fine")

        st.subheader("🖋️ FIRME")
        f1, f2 = st.columns(2)
        with f1: can1 = st_canvas(height=120, width=350, stroke_width=1, key="c1")
        with f2: can2 = st_canvas(height=120, width=350, stroke_width=1, key="c2")

        if st.form_submit_button("GENERA OTP"):
            otp = str(random.randint(100000, 999999))
            st.session_state.temp = {
                "nome": nome, "cognome": cognome, "targa": tg, "prezzo": prz, "modello": mod,
                "data_inizio": d_in.strftime("%d/%m/%Y"), "ora_inizio": h_in.strftime("%H:%M"),
                "data_fine": d_fi.strftime("%d/%m/%Y"), "ora_fine": h_fi.strftime("%H:%M"),
                "codice_fiscale": cf, "codice_sdi": sdi, "nazionalita": naz, "pec": wa, "otp_code": otp
            }
            # Cattura firme
            def b64(c):
                if c.image_data is not None:
                    img = Image.fromarray(c.image_data.astype("uint8"))
                    buf = io.BytesIO(); img.save(buf, format="PNG")
                    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
                return ""
            st.session_state.temp["firma"] = b64(can1)
            st.session_state.temp["firma2"] = b64(can2)
            
            msg = urllib.parse.quote(f"Codice Firma: {otp}")
            st.markdown(f"### [📲 INVIA WHATSAPP](https://wa.me/{wa}?text={msg})")

    if "temp" in st.session_state:
        v = st.text_input("Inserisci OTP")
        if st.button("SALVA E CHIUDI"):
            if v == st.session_state.temp["otp_code"]:
                st.session_state.temp["numero_fattura"] = get_prossimo_numero()
                supabase.table("contratti").insert(st.session_state.temp).execute()
                st.success("ARCHIVIATO!")
                del st.session_state.temp
            else: st.error("Errore OTP")

with t2:
    q = st.text_input("🔍 Cerca")
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    for r in res.data:
        if q.lower() in f"{s(r['cognome'])} {s(r['targa'])}".lower():
            with st.expander(f"📄 N. {r['numero_fattura']} - {r['cognome']}"):
                b1, b2 = st.columns(2)
                b1.download_button("📜 Contratto Unico (PDF)", genera_pdf_compatto(r), f"Contratto_{r['id']}.pdf")
                b2.download_button("💾 Fattura Elettronica (XML)", genera_xml_fattura(r), f"Fattura_{r['numero_fattura']}.xml", "text/xml")
