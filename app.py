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
INDIRIZZO = "Via Cognole n. 5"
CAP = "80075"
COMUNE = "Forio"
PROVINCIA = "NA"
PIVA = "10252601215"
CF_DITTA = "BTTMNN87A53Z112S"
INFO_TITOLARE = "nata a Berlino (Germania) il 13/01/1987 e residente in Forio alla Via Cognole n.5"

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

# --- MOTORE XML ARUBA ---
def genera_xml_fattura(c):
    p_tot = float(c.get('prezzo', 0))
    imp = round(p_tot / 1.22, 2)
    iva = round(p_tot - imp, 2)
    dt = datetime.now().strftime("%Y-%m-%d")
    sdi = s(c.get('codice_univoco', '0000000'))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<p:FatturaElettronica versione="FPR12" xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2">
  <FatturaElettronicaHeader>
    <DatiTrasmissione>
      <IdTrasmittente><IdPaese>IT</IdPaese><IdCodice>{PIVA}</IdCodice></IdTrasmittente>
      <ProgressivoInvio>{int(datetime.now().timestamp())}</ProgressivoInvio>
      <FormatoTrasmissione>FPR12</FormatoTrasmissione>
      <CodiceDestinatario>{sdi}</CodiceDestinatario>
    </DatiTrasmissione>
    <CedentePrestatore>
      <DatiAnagrafici>
        <IdFiscaleIVA><IdPaese>IT</IdPaese><IdCodice>{PIVA}</IdCodice></IdFiscaleIVA>
        <Anagrafica><Denominazione>{DITTA}</Denominazione></Anagrafica>
        <RegimeFiscale>RF01</RegimeFiscale>
      </DatiAnagrafici>
    </CedentePrestatore>
    <CessionarioCommittente>
      <DatiAnagrafici>
        <CodiceFiscale>{s(c.get('codice_fiscale', '')).upper()}</CodiceFiscale>
        <Anagrafica><Nome>{s(c.get('nome', '')).upper()}</Nome><Cognome>{s(c.get('cognome', '')).upper()}</Cognome></Anagrafica>
      </DatiAnagrafici>
    </CessionarioCommittente>
  </FatturaElettronicaHeader>
  <FatturaElettronicaBody>
    <DatiGenerali><DatiGeneraliDocumento><TipoDocumento>TD01</TipoDocumento><Divisa>EUR</Divisa><Data>{dt}</Data><Numero>{c.get('numero_fattura', '0')}</Numero><ImportoTotaleDocumento>{p_tot:.2f}</ImportoTotaleDocumento></DatiGeneraliDocumento></DatiGenerali>
    <DatiBeniServizi>
      <DettaglioLinee><NumeroLinea>1</NumeroLinea><Descrizione>Noleggio {s(c.get('modello'))} tg {s(c.get('targa'))}</Descrizione><PrezzoUnitario>{imp:.2f}</PrezzoUnitario><PrezzoTotale>{imp:.2f}</PrezzoTotale><AliquotaIVA>22.00</AliquotaIVA></DettaglioLinee>
      <DatiRiepilogo><AliquotaIVA>22.00</AliquotaIVA><ImponibileImporto>{imp:.2f}</ImponibileImporto><Imposta>{iva:.2f}</Imposta></DatiRiepilogo>
    </DatiBeniServizi>
  </FatturaElettronicaBody>
</p:FatturaElettronica>""".encode('utf-8')

# --- MOTORE PDF ---
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 10)
        self.cell(0, 5, DITTA, ln=True)
        self.set_font("Arial", "", 8)
        self.cell(0, 4, f"di {TITOLARE} - {INDIRIZZO} - {COMUNE}", ln=True)
        self.cell(0, 4, f"P.IVA: {PIVA} | C.F.: {CF_DITTA}", ln=True)
        self.ln(5)

def genera_contratto_completo(c):
    pdf = PDF(); pdf.add_page()
    pdf.set_font("Arial", "B", 12); pdf.cell(0, 10, safe(f"CONTRATTO DI NOLEGGIO N. {c['numero_fattura']}"), ln=True, align="C")
    
    # Dati Noleggio
    pdf.set_font("Arial", "B", 9); pdf.cell(0, 7, " DATI CLIENTE E NOLEGGIO", 1, ln=True, fill=True)
    pdf.set_font("Arial", "", 9)
    testo_dati = (f"Cliente: {c['nome']} {c['cognome']} ({c['codice_fiscale']})\n"
                  f"Mezzo: {c['modello']} tg: {c['targa']}\n"
                  f"Periodo: {c['inizio']} - {c['fine']}\n"
                  f"Prezzo: {c['prezzo']} EUR")
    pdf.multi_cell(0, 6, safe(testo_dati), border=1)
    
    # Certificazione Firma
    pdf.ln(5); pdf.set_font("Arial", "B", 9); pdf.cell(0, 6, "CERTIFICAZIONE FIRMA ELETTRONICA", ln=True)
    pdf.set_font("Arial", "I", 8)
    info_firma = f"Validato tramite OTP inviato al numero {c.get('pec')} in data {c.get('timestamp_firma')}. ID: {c.get('otp_code')}"
    pdf.multi_cell(0, 5, safe(info_firma), border=1)
    
    # Firme (CORRETTO: align='L' invece di 'T')
    pdf.ln(5); y_f = pdf.get_y()
    pdf.set_font("Arial", "B", 7)
    pdf.cell(95, 30, "Firma 1: Accettazione Contratto", border=1, align="L")
    pdf.cell(95, 30, "Firma 2: Approvazione Art. 1341-1342 cc", border=1, align="L")
    
    try:
        if c.get("firma"):
            f1 = str(c["firma"]).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(f1)), x=15, y=y_f+8, w=40)
        if c.get("firma2"):
            f2 = str(c["firma2"]).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(f2)), x=110, y=y_f+8, w=40)
    except: pass

    # Pagina 2 - Clausole
    pdf.add_page()
    pdf.set_font("Arial", "B", 9); pdf.cell(95, 8, "CONDIZIONI GENERALI", 0, 0); pdf.cell(95, 8, "GENERAL CONDITIONS", 0, 1)
    pdf.set_font("Arial", "", 6)
    c_it = "1) Noleggio senza conducente per l'isola d'Ischia... 3) Il cliente e' responsabile di danni e furto... 4) Multe + 25.83 Euro spese gestione..."
    c_en = "1) Rental for Ischia island only... 3) Customer is liable for damages and theft... 4) Fines + 25.83 Euro admin fee..."
    curr_y = pdf.get_y()
    pdf.multi_cell(92, 4, safe(c_it), border=1)
    pdf.set_xy(105, curr_y)
    pdf.multi_cell(92, 4, safe(c_en), border=1)
    
    return bytes(pdf.output(dest="S"))

def genera_fattura_completa(c):
    pdf = PDF(); pdf.add_page()
    pdf.set_font("Arial", "B", 14); pdf.cell(0, 10, safe(f"FATTURA N. {c['numero_fattura']}"), ln=True, align="C")
    p = float(c.get('prezzo', 0)); imp = p/1.22
    pdf.set_font("Arial", "", 10)
    pdf.cell(190, 15, safe(f"CLIENTE: {c['nome']} {c['cognome']} - CF: {c['codice_fiscale']}"), 1, ln=True)
    pdf.ln(5); pdf.cell(110, 8, "DESCRIZIONE", 1); pdf.cell(40, 8, "IVA", 1); pdf.cell(40, 8, "TOTALE", 1, ln=True)
    pdf.cell(110, 10, safe(f"Noleggio {c['modello']} tg {c['targa']}"), 1); pdf.cell(40, 10, "22%", 1); pdf.cell(40, 10, f"{p:.2f}", 1, ln=True)
    return bytes(pdf.output(dest="S"))

# --- INTERFACCIA ---
st.set_page_config(page_title="Battaglia Rent", layout="wide")

if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Password", type="password") == "1234":
        if st.button("Entra"): st.session_state.auth = True; st.rerun()
    st.stop()

t1, t2 = st.tabs(["📝 NUOVO NOLEGGIO", "📂 ARCHIVIO"])

with t1:
    with st.form("f_noleggio"):
        col1, col2, col3 = st.columns(3)
        n = col1.text_input("Nome")
        cg = col2.text_input("Cognome")
        tel = col3.text_input("Cellulare (WhatsApp)")
        
        col4, col5, col6 = st.columns(3)
        m = col4.text_input("Mezzo")
        tg = col5.text_input("Targa").upper()
        pz = col6.number_input("Prezzo (€)", min_value=0.0)
        
        cf = st.text_input("Codice Fiscale")
        
        st.write("---")
        st.subheader("🖋️ Firme Grafiche")
        f_c1, f_c2 = st.columns(2)
        with f_c1: can1 = st_canvas(height=120, width=300, stroke_width=2, key="sig1")
        with f_col2 := f_c2: can2 = st_canvas(height=120, width=300, stroke_width=2, key="sig2")

        if st.form_submit_button("GENERA OTP E INVIA"):
            if not (n and tg and tel): st.error("Nome, Targa e Cellulare sono obbligatori!")
            else:
                cod = str(random.randint(100000, 999999))
                st.session_state.otp = cod
                st.session_state.cell = tel
                msg = f"BATTAGLIA RENT: Ciao {n}, il tuo codice firma e': {cod}"
                link = f"https://wa.me/39{tel}?text={urllib.parse.quote(msg)}"
                st.markdown(f"### [📲 CLICCA QUI PER INVIARE IL CODICE WHATSAPP]({link})")

    if "otp" in st.session_state:
        st.warning("⚠️ Inserisci il codice ricevuto dal cliente per salvare")
        c_val = st.text_input("Codice OTP")
        if st.button("✅ CONFERMA E SALVA"):
            if c_val == st.session_state.otp:
                # Firme -> Base64
                img1 = Image.fromarray(can1.image_data.astype("uint8")); buf1 = io.BytesIO(); img1.save(buf1, format="PNG")
                f1_b = "data:image/png;base64," + base64.b64encode(buf1.getvalue()).decode()
                img2 = Image.fromarray(can2.image_data.astype("uint8")); buf2 = io.BytesIO(); img2.save(buf2, format="PNG")
                f2_b = "data:image/png;base64," + base64.b64encode(buf2.getvalue()).decode()

                dati = {
                    "nome": n, "cognome": cg, "targa": tg, "prezzo": pz, "firma": f1_b, "firma2": f2_b,
                    "otp_code": st.session_state.otp, "pec": st.session_state.cell, "modello": m,
                    "codice_fiscale": cf, "timestamp_firma": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "numero_fattura": get_prossimo_numero(), "inizio": str(datetime.now().date()), "fine": str(datetime.now().date())
                }
                supabase.table("contratti").insert(dati).execute()
                st.success("Contratto firmato e archiviato!")
                del st.session_state.otp
            else: st.error("Codice OTP non valido")

with t2:
    search = st.text_input("🔍 Cerca")
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    for r in res.data:
        if search.lower() in f"{s(r['cognome'])} {s(r['targa'])}".lower():
            with st.expander(f"📄 N. {r['numero_fattura']} - {r['cognome']} ({r['targa']})"):
                b1, b2 = st.columns(2)
                # IL FIX È QUI: Ora genera_contratto_completo non darà più errore
                b1.download_button("📜 Contratto PDF", genera_contratto_completo(r), f"Contratto_{r['id']}.pdf")
                b2.download_button("📂 XML ARUBA", genera_xml_fattura(r), f"Fattura_{r['id']}.xml")
