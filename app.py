import streamlit as st
from supabase import create_client, Client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from fpdf import FPDF
import io
import base64
from datetime import datetime

# --- CONFIGURAZIONE AZIENDALE ---
DITTA = "BATTAGLIA RENT"
TITOLARE = "BATTAGLIA MARIANNA"
INDIRIZZO = "Via Cognole n. 5"
CAP = "80075"
COMUNE = "Forio"
PROVINCIA = "NA"
NAZIONE = "IT"
PIVA = "10252601215"
CF_DITTA = "BTTMNN87A53Z112S"

# Connessione protetta
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

def upload_media(file, targa, tipo):
    if file is None: return None
    try:
        nome_file = f"{tipo}{targa}{datetime.now().strftime('%Y%m%d%H%M%S')}"
        content_type = file.type
        if "image" in content_type:
            img = Image.open(file)
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            img.thumbnail((800, 800))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75)
            data = buf.getvalue()
            nome_file += ".jpg"
        else:
            data = file.getvalue()
            nome_file += ".mp4" if "mp4" in content_type else ".mov"
        supabase.storage.from_("documenti").upload(nome_file, data, {"content-type": content_type})
        return supabase.storage.from_("documenti").get_public_url(nome_file)
    except: return None

# --- LOGICA GENERAZIONE XML ARUBA/AdE ---
def genera_xml_fattura(c):
    prezzo_totale = float(c['prezzo'])
    imponibile = round(prezzo_totale / 1.22, 2)
    imposta = round(prezzo_totale - imponibile, 2)
    data_doc = datetime.now().strftime("%Y-%m-%d")
    
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<p:FatturaElettronica versione="FPR12" xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2">
  <FatturaElettronicaHeader>
    <DatiTrasmissione>
      <IdTrasmittente><IdPaese>IT</IdPaese><IdCodice>{PIVA}</IdCodice></IdTrasmittente>
      <ProgressivoInvio>{c['numero_fattura']}</ProgressivoInvio>
      <FormatoTrasmissione>FPR12</FormatoTrasmissione>
      <CodiceDestinatario>{s(c.get('codice_univoco', '0000000'))}</CodiceDestinatario>
    </DatiTrasmissione>
    <CedentePrestatore>
      <DatiAnagrafici>
        <IdFiscaleIVA><IdPaese>IT</IdPaese><IdCodice>{PIVA}</IdCodice></IdFiscaleIVA>
        <Anagrafica><Denominazione>{DITTA}</Denominazione></Anagrafica>
        <RegimeFiscale>RF01</RegimeFiscale>
      </DatiAnagrafici>
      <Sede><Indirizzo>{INDIRIZZO}</Indirizzo><CAP>{CAP}</CAP><Comune>{COMUNE}</Comune><Provincia>{PROVINCIA}</Provincia><Nazione>IT</Nazione></Sede>
    </CedentePrestatore>
    <CessionarioCommittente>
      <DatiAnagrafici>
        <CodiceFiscale>{s(c['codice_fiscale']).upper()}</CodiceFiscale>
        <Anagrafica><Nome>{s(c['nome']).upper()}</Nome><Cognome>{s(c['cognome']).upper()}</Cognome></Anagrafica>
      </DatiAnagrafici>
    </CessionarioCommittente>
  </FatturaElettronicaHeader>
  <FatturaElettronicaBody>
    <DatiGenerali>
      <DatiGeneraliDocumento>
        <TipoDocumento>TD01</TipoDocumento><Divisa>EUR</Divisa><Data>{data_doc}</Data><Numero>{c['numero_fattura']}</Numero><ImportoTotaleDocumento>{prezzo_totale:.2f}</ImportoTotaleDocumento>
      </DatiGeneraliDocumento>
    </DatiGenerali>
    <DatiBeniServizi>
      <DettaglioLinee>
        <NumeroLinea>1</NumeroLinea><Descrizione>Noleggio {s(c['modello'])} targa {s(c['targa'])}</Descrizione>
        <PrezzoUnitario>{imponibile:.2f}</PrezzoUnitario><PrezzoTotale>{imponibile:.2f}</PrezzoTotale><AliquotaIVA>22.00</AliquotaIVA>
      </DettaglioLinee>
      <DatiRiepilogo><AliquotaIVA>22.00</AliquotaIVA><ImponibileImporto>{imponibile:.2f}</ImponibileImporto><Imposta>{imposta:.2f}</Imposta></DatiRiepilogo>
    </DatiBeniServizi>
  </FatturaElettronicaBody>
</p:FatturaElettronica>"""
    return xml.encode('utf-8')

# --- GENERAZIONE PDF (VERSIONE ORIGINALE COMPLETA) ---
class BusinessPDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 6, safe(DITTA), ln=True)
        self.set_font("Arial", "", 8)
        self.cell(0, 4, safe(f"{TITOLARE} - {INDIRIZZO}, {COMUNE}"), ln=True)
        self.cell(0, 4, safe(f"P.IVA: {PIVA} | C.F.: {CF_DITTA}"), ln=True)
        self.ln(5); self.line(10, self.get_y(), 200, self.get_y()); self.ln(5)

def genera_contratto_legale(c):
    pdf = BusinessPDF(); pdf.add_page()
    pdf.set_font("Arial", "B", 14); pdf.cell(0, 10, safe(f"CONTRATTO DI NOLEGGIO N. {c['numero_fattura']}"), ln=True, align="C")
    
    pdf.ln(5); pdf.set_font("Arial", "B", 10); pdf.cell(0, 7, " ANAGRAFICA CLIENTE", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "", 9)
    pdf.cell(95, 7, safe(f"Nome: {c['nome']} {c['cognome']}"), border="LR")
    pdf.cell(95, 7, safe(f"Nazionalita: {c.get('nazionalita','')}"), border="R", ln=True)
    pdf.cell(95, 7, safe(f"Nato il: {c.get('data_nascita','')} a: {c.get('luogo_nascita','')}"), border="LR")
    pdf.cell(95, 7, safe(f"C.F.: {c['codice_fiscale']}"), border="R", ln=True)
    pdf.cell(190, 7, safe(f"Residenza: {c.get('indirizzo_cliente','')}"), border="LR", ln=True)
    pdf.cell(95, 7, safe(f"Tel: {c.get('telefono','')}"), border="LRB")
    pdf.cell(95, 7, safe(f"Email/PEC: {c.get('pec','')}"), border="RB", ln=True)
    
    pdf.ln(3); pdf.set_font("Arial", "B", 10); pdf.cell(0, 7, " DATI NOLEGGIO", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "", 9)
    pdf.cell(63, 7, safe(f"Mezzo: {c['modello']}"), border=1)
    pdf.cell(63, 7, safe(f"Targa: {c['targa']}"), border=1)
    pdf.cell(64, 7, safe(f"Patente: {c['numero_patente']}"), border=1, ln=True)
    pdf.cell(95, 7, safe(f"Inizio: {c['inizio']}  Fine: {c['fine']}"), border=1)
    pdf.cell(95, 7, safe(f"Prezzo: {c['prezzo']} EUR"), border=1, ln=True)

    pdf.ln(5); pdf.set_font("Arial", "B", 10); pdf.cell(0, 7, " CONDIZIONI ESSENZIALI DI NOLEGGIO", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "", 8)
    clausole = ("1. ASSICURAZIONE: R.C.A. solo verso terzi. 2. DANNI/FURTO: A carico del cliente. "
                "3. CASCO: Obbligatorio. 4. MULTE: A carico del cliente. 5. PRIVACY: Autorizzo GDPR.")
    pdf.multi_cell(0, 4, safe(clausole), border=1)

    pdf.ln(5); pdf.set_font("Arial", "B", 9); pdf.cell(0, 7, "FIRMA DEL CLIENTE", ln=True)
    y_f = pdf.get_y(); pdf.cell(100, 25, "", border=1)
    pdf.cell(90, 25, safe(f"Data: {datetime.now().strftime('%d/%m/%Y')}"), border=1, ln=True)
    firma = c.get("firma")
    if firma and len(str(firma)) > 100:
        try:
            if "," in str(firma): firma = str(firma).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(firma)), x=15, y=y_f+2, w=40)
        except: pass
    return bytes(pdf.output(dest="S"))

def genera_fattura_pdf(c):
    pdf = BusinessPDF(); pdf.add_page()
    pdf.set_font("Arial", "B", 14); pdf.cell(0, 10, safe(f"FATTURA N. {c['numero_fattura']}"), ln=True, align="C", border="B")
    pdf.ln(10); pdf.set_font("Arial", "B", 9); pdf.cell(95, 7, "CEDENTE", border=1, fill=True); pdf.cell(95, 7, "CESSIONARIO", border=1, fill=True, ln=True)
    pdf.set_font("Arial", "", 9); pdf.multi_cell(95, 5, safe(f"{DITTA}\n{TITOLARE}\n{INDIRIZZO}\n{COMUNE}\nP.IVA {PIVA}"), border=1)
    pdf.set_xy(105, pdf.get_y()-20); pdf.multi_cell(95, 5, safe(f"{c['nome']} {c['cognome']}\nCF: {c['codice_fiscale']}\nSDI: {c.get('codice_univoco','0000000')}"), border=1)
    pdf.ln(15); p = float(c['prezzo']); imp = p/1.22; iva = p-imp
    pdf.set_font("Arial", "B", 10); pdf.cell(110, 8, "DESCRIZIONE", border=1); pdf.cell(40, 8, "IVA", border=1); pdf.cell(40, 8, "TOTALE", border=1, ln=True)
    pdf.set_font("Arial", "", 10); pdf.cell(110, 10, safe(f"Noleggio {c['modello']} ({c['targa']})"), border=1); pdf.cell(40, 10, "22%", border=1); pdf.cell(40, 10, f"{p:.2f} EUR", border=1, ln=True)
    pdf.ln(5); pdf.cell(150, 7, "TOTALE FATTURA:", align="R"); pdf.cell(40, 7, f"{p:.2f} EUR", border=1, ln=True)
    return bytes(pdf.output(dest="S"))

def genera_modulo_vigili_legale(c):
    pdf = BusinessPDF(); pdf.add_page()
    pdf.set_font("Arial", "B", 10); pdf.cell(0, 7, safe("OGGETTO: COMUNICAZIONE DATI CONDUCENTE PER RINOTIFICA"), ln=True)
    pdf.set_font("Arial", "", 10)
    testo = (f"La sottoscritta BATTAGLIA MARIANNA dichiara che il veicolo {c['modello']} targa {c['targa']} "
             f"era locato a {c['nome']} {c['cognome']}, nato a {c.get('luogo_nascita','')} il {c.get('data_nascita','')}, "
             f"residente in {c.get('indirizzo_cliente','')}. Patente n. {c['numero_patente']}.")
    pdf.multi_cell(0, 6, safe(testo)); return bytes(pdf.output(dest="S"))

# --- INTERFACCIA STREAMLIT ---
st.set_page_config(page_title="Battaglia Rent Pro", layout="wide")
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Password", type="password") == "1234":
        if st.button("Accedi"): st.session_state.auth = True; st.rerun()
    st.stop()

t1, t2 = st.tabs(["📝 Nuovo Noleggio", "📂 Archivio"])

with t1:
    with st.form("form_master", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        nome, cognome, naz = c1.text_input("Nome"), c2.text_input("Cognome"), c3.text_input("Nazionalità")
        c4, c5, c6 = st.columns(3)
        cf, tel, pec = c4.text_input("C.F. / ID"), c5.text_input("Telefono"), c6.text_input("Email / PEC")
        c7, c8, c9 = st.columns(3)
        dat_n, luo_n, ind = c7.text_input("Data Nascita"), c8.text_input("Luogo Nascita"), c9.text_input("Residenza")
        m1, m2, m3 = st.columns(3)
        mod, tar, pat = m1.text_input("Modello"), m2.text_input("Targa").upper(), m3.text_input("N. Patente")
        d1, d2, d3 = st.columns(3)
        prezzo, deposito, sdi = d1.number_input("Prezzo"), d2.number_input("Deposito"), d3.text_input("SDI", value="0000000")
        ini, fin = st.date_input("Inizio"), st.date_input("Fine")
        
        st.subheader("📹 Stato Veicolo & Documenti")
        video_mezzo = st.file_uploader("Video/Foto Stato Motorino", type=["mp4", "mov", "jpg", "png"])
        f1, f2 = st.file_uploader("Fronte Patente"), st.file_uploader("Retro Patente")
        
        canvas = st_canvas(height=150, width=400, stroke_width=3, key="sig_master")
        accetto = st.checkbox("Accetto le condizioni di noleggio e privacy.")
        
        if st.form_submit_button("💾 REGISTRA NOLEGGIO"):
            if not accetto or not nome or not tar: st.error("❌ Compila i campi obbligatori!")
            else:
                try:
                    img = Image.fromarray(canvas.image_data.astype("uint8"))
                    buf = io.BytesIO(); img.save(buf, format="PNG")
                    firma = base64.b64encode(buf.getvalue()).decode()
                    u_v = upload_media(video_mezzo, tar, "VIDEO")
                    u_f = upload_media(f1, tar, "F")
                    u_r = upload_media(f2, tar, "R")
                    num = get_prossimo_numero()
                    dati = {"nome": nome, "cognome": cognome, "codice_fiscale": cf, "modello": mod, "targa": tar, "prezzo": prezzo, "deposito": deposito, "numero_fattura": num, "firma": firma, "url_video": u_v, "url_fronte": u_f, "url_retro": u_r, "pec": pec, "codice_univoco": sdi, "data_nascita": dat_n, "luogo_nascita": luo_n, "indirizzo_cliente": ind, "inizio": str(ini), "fine": str(fin), "numero_patente": pat, "nazionalita": naz, "telefono": tel}
                    supabase.table("contratti").insert(dati).execute()
                    st.success(f"✅ Noleggio N. {num} salvato!")
                except Exception as e: st.error(f"Errore: {e}")

with t2:
    search = st.text_input("🔍 Cerca Cognome o Targa")
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    for r in res.data:
        if search.lower() in f"{s(r['cognome'])} {s(r['targa'])}".lower():
            with st.expander(f"N. {r['numero_fattura']} - {r['cognome']} ({r['targa']})"):
                st.write("### 🛵 Stato del Ve
