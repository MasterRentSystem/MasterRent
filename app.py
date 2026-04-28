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
supabase: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

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

# --- MOTORE PDF CON 2 FIRME E CLAUSOLE ---
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
    
    # Sezione Dati
    pdf.set_font("Arial", "B", 9); pdf.cell(0, 7, " DATI CLIENTE E NOLEGGIO", 1, ln=True, fill=True)
    pdf.set_font("Arial", "", 9)
    pdf.multi_cell(0, 6, safe(f"Cliente: {c['nome']} {c['cognome']} ({c['codice_fiscale']})\nMezzo: {c['modello']} tg: {c['targa']}\nPeriodo: {c['inizio']} - {c['fine']}\nPrezzo: {c['prezzo']} EUR"), border=1)
    
    # Certificazione OTP
    pdf.ln(5); pdf.set_font("Arial", "B", 9); pdf.cell(0, 6, "CERTIFICAZIONE FIRMA ELETTRONICA", ln=True)
    pdf.set_font("Arial", "I", 8)
    pdf.multi_cell(0, 5, safe(f"Documento convalidato tramite OTP inviato al numero {c.get('pec')} in data {c.get('timestamp_firma')}. ID: {c.get('otp_code')}"), border=1)
    
    # Firme
    pdf.ln(5); y_firma = pdf.get_y()
    pdf.set_font("Arial", "B", 8)
    pdf.cell(95, 30, "Firma 1: Accettazione", border=1, align="T")
    pdf.cell(95, 30, "Firma 2: Art. 1341-1342 cc", border=1, align="T")
    
    if c.get("firma"):
        f1 = str(c["firma"]).split(",")[1]
        pdf.image(io.BytesIO(base64.b64decode(f1)), x=15, y=y_firma+5, w=35)
    if c.get("firma2"):
        f2 = str(c["firma2"]).split(",")[1]
        pdf.image(io.BytesIO(base64.b64decode(f2)), x=110, y=y_firma+5, w=35)

    # Pagina 2 - Clausole Bilingue
    pdf.add_page()
    pdf.set_font("Arial", "B", 9); pdf.cell(95, 8, "CONDIZIONI GENERALI", 0, 0); pdf.cell(95, 8, "GENERAL CONDITIONS", 0, 1)
    pdf.set_font("Arial", "", 6)
    clausole_it = "1) Noleggio senza conducente... 3) Responsabilita danni/furto... 4) Multe + 25.83 Euro spese... 12) Casco obbligatorio..."
    clausole_en = "1) Rental without driver... 3) Damage/Theft liability... 4) Fines + 25.83 Euro fee... 12) Helmet mandatory..."
    y_cl = pdf.get_y()
    pdf.multi_cell(92, 4, safe(clausole_it), border=1)
    pdf.set_xy(105, y_cl)
    pdf.multi_cell(92, 4, safe(clausole_en), border=1)
    
    return bytes(pdf.output(dest="S"))

# --- INTERFACCIA STREAMLIT ---
st.set_page_config(page_title="Battaglia Rent", layout="wide")

if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Password", type="password") == "1234":
        if st.button("Accedi"): st.session_state.auth = True; st.rerun()
    st.stop()

tab1, tab2 = st.tabs(["📝 NUOVO NOLEGGIO", "📂 ARCHIVIO"])

with tab1:
    with st.form("noleggio_form"):
        c1, c2, c3 = st.columns(3)
        nome = c1.text_input("Nome")
        cognome = c2.text_input("Cognome")
        cellulare = c3.text_input("Cellulare (per WhatsApp)")
        
        c4, c5, c6 = st.columns(3)
        modello = c4.text_input("Mezzo")
        targa = c5.text_input("Targa").upper()
        prezzo = c6.number_input("Prezzo (€)", min_value=0.0)
        
        cf = st.text_input("Codice Fiscale")
        
        st.write("---")
        st.subheader("🖋️ Doppia Firma del Cliente")
        f1, f2 = st.columns(2)
        with f1: can1 = st_canvas(height=120, width=300, stroke_width=2, key="c1")
        with f2: can2 = st_canvas(height=120, width=300, stroke_width=2, key="c2")

        if st.form_submit_button("GENERA CODICE OTP"):
            if not (nome and cellulare): st.error("Inserisci Nome e Cellulare!")
            else:
                otp = str(random.randint(100000, 999999))
                st.session_state.current_otp = otp
                st.session_state.current_cell = cellulare
                
                # Creazione link WhatsApp
                msg = f"BATTAGLIA RENT: Ciao {nome}, il tuo codice per firmare il contratto e': {otp}"
                link_wa = f"https://wa.me/39{cellulare}?text={urllib.parse.quote(msg)}"
                st.markdown(f'### [📲 CLICCA QUI PER INVIARE IL CODICE SU WHATSAPP]({link_wa})')

    if "current_otp" in st.session_state:
        st.warning(f"In attesa del codice inserito dal cliente...")
        input_otp = st.text_input("Inserisci il codice che il cliente ha ricevuto")
        
        if st.button("✅ CONFERMA E SALVA CONTRATTO"):
            if input_otp == st.session_state.current_otp:
                # Trasformazione firme
                i1 = Image.fromarray(can1.image_data.astype("uint8"))
                b1 = io.BytesIO(); i1.save(b1, format="PNG")
                f1_64 = "data:image/png;base64," + base64.b64encode(b1.getvalue()).decode()
                
                i2 = Image.fromarray(can2.image_data.astype("uint8"))
                b2 = io.BytesIO(); i2.save(b2, format="PNG")
                f2_64 = "data:image/png;base64," + base64.b64encode(b2.getvalue()).decode()

                dati = {
                    "nome": nome, "cognome": cognome, "targa": targa, "prezzo": prezzo,
                    "firma": f1_64, "firma2": f2_64, "otp_code": st.session_state.current_otp,
                    "pec": st.session_state.current_cell, "modello": modello, "codice_fiscale": cf,
                    "timestamp_firma": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "numero_fattura": get_prossimo_numero()
                }
                supabase.table("contratti").insert(dati).execute()
                st.success("CONTRATTO FIRMATO E SALVATO CON SUCCESSO!")
                del st.session_state.current_otp
            else:
                st.error("Codice OTP errato!")

with tab2:
    search = st.text_input("🔍 Cerca")
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    for r in res.data:
        if search.lower() in f"{s(r['cognome'])} {s(r['targa'])}".lower():
            with st.expander(f"📄 N. {r['numero_fattura']} - {r['cognome']}"):
                b1, b2, b3 = st.columns(3)
                b1.download_button("📜 Contratto PDF", genera_contratto_completo(r), f"Contratto_{r['id']}.pdf")
                b2.download_button("📂 XML ARUBA", genera_xml_fattura(r), f"Fattura_{r['id']}.xml")
