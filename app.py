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

def upload_media(file, targa, tipo):
    if file is None: return None
    try:
        nome_file = f"{tipo}{targa}{datetime.now().strftime('%Y%m%d%H%M%S')}"
        content_type = file.type
        data = file.getvalue()
        if "image" in content_type:
            img = Image.open(file)
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            img.thumbnail((800, 800))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75)
            data = buf.getvalue()
            nome_file += ".jpg"
        else:
            nome_file += ".mp4" if "mp4" in content_type else ".mov"
        supabase.storage.from_("documenti").upload(nome_file, data, {"content-type": content_type})
        return supabase.storage.from_("documenti").get_public_url(nome_file)
    except: return None

# --- FUNZIONE XML PER ARUBA ---
def genera_xml_fattura(c):
    prezzo_totale = float(c.get('prezzo', 0))
    imponibile = round(prezzo_totale / 1.22, 2)
    imposta = round(prezzo_totale - imponibile, 2)
    data_doc = datetime.now().strftime("%Y-%m-%d")
    naz = str(c.get('nazionalita') or "").lower()
    codice_sdi = s(c.get('codice_univoco', '0000000'))
    if naz not in ['italia', 'it', 'italiana'] and naz != "":
        codice_sdi = "XXXXXXX"

    xml_data = f"""<?xml version="1.0" encoding="UTF-8"?>
<p:FatturaElettronica versione="FPR12" xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2">
  <FatturaElettronicaHeader>
    <DatiTrasmissione>
      <IdTrasmittente><IdPaese>IT</IdPaese><IdCodice>{PIVA}</IdCodice></IdTrasmittente>
      <ProgressivoInvio>{c.get('numero_fattura', '0')}</ProgressivoInvio>
      <FormatoTrasmissione>FPR12</FormatoTrasmissione>
      <CodiceDestinatario>{codice_sdi}</CodiceDestinatario>
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
        <CodiceFiscale>{s(c.get('codice_fiscale', '')).upper()}</CodiceFiscale>
        <Anagrafica><Nome>{s(c.get('nome', '')).upper()}</Nome><Cognome>{s(c.get('cognome', '')).upper()}</Cognome></Anagrafica>
      </DatiAnagrafici>
    </CessionarioCommittente>
  </FatturaElettronicaHeader>
  <FatturaElettronicaBody>
    <DatiGenerali>
      <DatiGeneraliDocumento>
        <TipoDocumento>TD01</TipoDocumento><Divisa>EUR</Divisa><Data>{data_doc}</Data><Numero>{c.get('numero_fattura', '0')}</Numero><ImportoTotaleDocumento>{prezzo_totale:.2f}</ImportoTotaleDocumento>
      </DatiGeneraliDocumento>
    </DatiGenerali>
    <DatiBeniServizi>
      <DettaglioLinee>
        <NumeroLinea>1</NumeroLinea><Descrizione>Noleggio veicolo {s(c.get('modello', ''))} targa {s(c.get('targa', ''))}</Descrizione><PrezzoUnitario>{imponibile:.2f}</PrezzoUnitario><PrezzoTotale>{imponibile:.2f}</PrezzoTotale><AliquotaIVA>22.00</AliquotaIVA>
      </DettaglioLinee>
      <DatiRiepilogo>
        <AliquotaIVA>22.00</AliquotaIVA><ImponibileImporto>{imponibile:.2f}</ImponibileImporto><Imposta>{imposta:.2f}</Imposta><EsigibilitaIVA>I</EsigibilitaIVA>
      </DatiRiepilogo>
    </DatiBeniServizi>
  </FatturaElettronicaBody>
</p:FatturaElettronica>"""
    return xml_data.encode('utf-8')

# --- CLASSE PDF BASE ---
class BusinessPDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 6, safe(DITTA), ln=True)
        self.set_font("Arial", "", 8)
        self.cell(0, 4, safe(f"{TITOLARE} - {INDIRIZZO}, {COMUNE}"), ln=True)
        self.cell(0, 4, safe(f"P.IVA: {PIVA} | C.F.: {CF_DITTA}"), ln=True)
        self.ln(5); self.line(10, self.get_y(), 200, self.get_y()); self.ln(5)

# --- FUNZIONI DOCUMENTI PDF ---
def genera_contratto_legale(c):
    pdf = BusinessPDF(); pdf.add_page()
    pdf.set_font("Arial", "B", 14); pdf.cell(0, 10, safe(f"CONTRATTO DI NOLEGGIO N. {c['numero_fattura']}"), ln=True, align="C")
    pdf.ln(5); pdf.set_font("Arial", "B", 10); pdf.cell(0, 7, " ANAGRAFICA CLIENTE", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "", 9)
    pdf.cell(95, 7, safe(f"Nome: {c['nome']} {c['cognome']}"), border="LR")
    pdf.cell(95, 7, safe(f"Nazionalita: {c.get('nazionalita','') or ''}"), border="R", ln=True)
    pdf.cell(190, 7, safe(f"C.F.: {c['codice_fiscale']}"), border="LR", ln=True)
    pdf.cell(190, 7, safe(f"Residenza: {c.get('indirizzo_cliente','') or ''}"), border="LRB", ln=True)
    pdf.ln(3); pdf.set_font("Arial", "B", 10); pdf.cell(0, 7, " DATI NOLEGGIO", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "", 9); pdf.cell(63, 7, safe(f"Mezzo: {c['modello']}"), border=1)
    pdf.cell(63, 7, safe(f"Targa: {c['targa']}"), border=1); pdf.cell(64, 7, safe(f"Prezzo: {c['prezzo']} EUR"), border=1, ln=True)
    pdf.ln(5); pdf.set_font("Arial", "B", 10); pdf.cell(0, 7, " CONDIZIONI ESSENZIALI", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "", 8)
    clausole = "1. Assicurazione RCA inclusa verso terzi. 2. Danni e furto a carico del cliente. 3. Obbligo di casco. 4. Autorizzo trattamento dati GDPR."
    pdf.multi_cell(0, 4, safe(clausole), border=1)
    pdf.ln(10); pdf.set_font("Arial", "B", 9); pdf.cell(0, 7, "FIRMA DEL CLIENTE", ln=True)
    y_f = pdf.get_y(); pdf.cell(100, 25, "", border=1)
    firma = c.get("firma")
    if firma and len(str(firma)) > 100:
        try:
            if "," in str(firma): firma = str(firma).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(firma)), x=15, y=y_f+2, w=40)
        except: pass
    return bytes(pdf.output(dest="S"))

def genera_fattura_completa(c):
    pdf = BusinessPDF(); pdf.add_page()
    pdf.set_font("Arial", "B", 14); pdf.cell(0, 10, safe(f"FATTURA N. {c['numero_fattura']}"), ln=True, align="C", border="B")
    pdf.ln(10); p = float(c['prezzo']); imp = p/1.22; iva = p-imp
    pdf.set_font("Arial", "B", 9); pdf.cell(95, 7, "CEDENTE", border=1, fill=True); pdf.cell(95, 7, "CESSIONARIO", border=1, fill=True, ln=True)
    pdf.set_font("Arial", "", 9); pdf.multi_cell(95, 5, safe(f"{DITTA}\n{TITOLARE}\n{INDIRIZZO}\nP.IVA: {PIVA}"), border=1)
    pdf.set_xy(105, pdf.get_y()-20); pdf.multi_cell(95, 5, safe(f"{c['nome']} {c['cognome']}\nCF: {c['codice_fiscale']}\nSDI: {c.get('codice_univoco','0000000')}"), border=1)
    pdf.ln(15); pdf.set_font("Arial", "B", 10); pdf.cell(110, 8, "DESCRIZIONE", border=1); pdf.cell(40, 8, "IVA", border=1); pdf.cell(40, 8, "TOTALE", border=1, ln=True)
    pdf.set_font("Arial", "", 10); pdf.cell(110, 10, safe(f"Noleggio {c['modello']} ({c['targa']})"), border=1); pdf.cell(40, 10, "22%", border=1); pdf.cell(40, 10, f"{p:.2f} EUR", border=1, ln=True)
    return bytes(pdf.output(dest="S"))

def genera_modulo_vigili_legale(c):
    pdf = BusinessPDF(); pdf.add_page()
    pdf.set_font("Arial", "B", 11); pdf.cell(0, 10, safe("Spett. le Polizia Locale"), ln=True, align="R")
    pdf.ln(5); pdf.set_font("Arial", "B", 10); pdf.cell(0, 7, safe("OGGETTO: COMUNICAZIONE DATI CONDUCENTE"), ln=True)
    pdf.ln(5); pdf.set_font("Arial", "", 10)
    testo = f"Il veicolo {c['modello']} targa {c['targa']} era locato a {c['nome']} {c['cognome']}. Si richiede rinotifica verbali."
    pdf.multi_cell(0, 6, safe(testo))
    return bytes(pdf.output(dest="S"))

# --- INTERFACCIA STREAMLIT ---
st.set_page_config(page_title="Battaglia Rent Pro", layout="wide")

if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    pwd = st.text_input("Password", type="password")
    if st.button("Accedi"):
        if pwd == "1234": st.session_state.auth = True; st.rerun()
        else: st.error("Password errata")
    st.stop()

t1, t2 = st.tabs(["📝 Nuovo Noleggio", "📂 Archivio"])

with t1:
    with st.form("main_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        nome, cognome, nazionalita = c1.text_input("Nome"), c2.text_input("Cognome"), c3.selectbox("Nazionalità", ["Italia", "Estero"])
        c4, c5, c6 = st.columns(3)
        cf, tel, email = c4.text_input("C.F. / Documento"), c5.text_input("Telefono"), c6.text_input("Email")
        m1, m2, m3 = st.columns(3)
        mod, tar, pat = m1.text_input("Modello"), m2.text_input("Targa").upper(), m3.text_input("N. Patente")
        d1, d2, d3 = st.columns(3)
        prezzo, deposito, sdi = d1.number_input("Prezzo (€)"), d2.number_input("Deposito (€)"), d3.text_input("SDI", value="0000000")
        ini, fin = st.date_input("Inizio"), st.date_input("Fine")
        st.subheader("📸 Foto/Video")
        v_m = st.file_uploader("Danni Veicolo", type=["mp4", "mov", "jpg", "png"])
        f_p = st.file_uploader("Fronte Patente")
        r_p = st.file_uploader("Retro Patente")
        canvas = st_canvas(height=150, width=400, stroke_width=3, key="sig_main")
        accetto = st.checkbox("Accetto le condizioni.")
        
        if st.form_submit_button("💾 REGISTRA"):
            if not accetto or not nome or not tar: st.error("Dati mancanti!")
            else:
                try:
                    img = Image.fromarray(canvas.image_data.astype("uint8"))
                    buf = io.BytesIO(); img.save(buf, format="PNG")
                    firma = base64.b64encode(buf.getvalue()).decode()
                    u_v = upload_media(v_m, tar, "ST"); u_f = upload_media(f_p, tar, "F"); u_r = upload_media(r_p, tar, "R")
                    num = get_prossimo_numero()
                    dati = {"nome": nome, "cognome": cognome, "codice_fiscale": cf, "modello": mod, "targa": tar, "prezzo": prezzo, "deposito": deposito, "numero_fattura": num, "firma": firma, "url_video": u_v, "url_fronte": u_f, "url_retro": u_r, "codice_univoco": sdi, "nazionalita": nazionalita, "inizio": str(ini), "fine": str(fin), "numero_patente": pat, "telefono": tel}
                    supabase.table("contratti").insert(dati).execute()
                    st.success(f"Registrato N. {num}")
                except Exception as e: st.error(f"Errore: {e}")

with t2:
    search = st.text_input("🔍 Cerca Cognome o Targa")
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    
    # AGGIUNTO idx PER EVITARE DUPLICATE KEY ERROR
    for idx, r in enumerate(res.data):
        if search.lower() in f"{s(r['cognome'])} {s(r['targa'])}".lower():
            n_f = r['numero_fattura']
            # Usiamo idx come parte della chiave per essere sicuri al 100% che sia unica
            with st.expander(f"📄 N. {n_f} - {r['cognome']} ({r['targa']})"):
                st.write(f"*Periodo:* {r['inizio']} / {r['fine']}")
                cm1, cm2, cm3 = st.columns(3)
                with cm1:
                    if r.get('url_video'):
                        if ".mp4" in r['url_video'] or ".mov" in r['url_video']: st.video(r['url_video'])
                        else: st.image(r['url_video'], caption="Danni")
                with cm2:
                    if r.get('url_fronte'): st.image(r['url_fronte'], caption="Patente F")
                with cm3:
                    if r.get('url_retro'): st.image(r['url_retro'], caption="Patente R")

                st.markdown("---")
                dcol1, dcol2, dcol3, dcol4 = st.columns(4)
                
                # CHIAVI UNICHE AL 100% (n_f + idx)
                dcol1.download_button("📜 Contratto", genera_contratto_legale(r), f"Contratto_{n_f}.pdf", key=f"cnt_{n_f}_{idx}")
                dcol2.download_button("🧾 Fattura PDF", genera_fattura_completa(r), f"Fattura_{n_f}.pdf", key=f"fat_{n_f}_{idx}")
                dcol3.download_button("🚨 Vigili", genera_modulo_vigili_legale(r), f"Vigili_{n_f}.pdf", key=f"vig_{n_f}_{idx}")
                dcol4.download_button("📂 XML ARUBA", genera_xml_fattura(r), f"IT{PIVA}DF{n_f}.xml", mime="text/xml", key=f"xml_{n_f}_{idx}")
