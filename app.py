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

# --- MOTORE FATTURA XML ---
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
      <DatiAnagrafici><IdFiscaleIVA><IdPaese>IT</IdPaese><IdCodice>{PIVA}</IdCodice></IdFiscaleIVA><Anagrafica><Denominazione>{DITTA}</Denominazione></Anagrafica><RegimeFiscale>RF01</RegimeFiscale></DatiAnagrafici>
    </CedentePrestatore>
    <CessionarioCommittente>
      <DatiAnagrafici><CodiceFiscale>{s(c.get('codice_fiscale', '')).upper()}</CodiceFiscale><Anagrafica><Nome>{s(c.get('nome', '')).upper()}</Nome><Cognome>{s(c.get('cognome', '')).upper()}</Cognome></Anagrafica></DatiAnagrafici>
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
        self.cell(0, 5, DITTA, ln=True, align="L")
        self.set_font("Arial", "", 8)
        self.cell(0, 4, f"{INFO_AZIENDA} | P.IVA: {PIVA}", ln=True)
        self.ln(5)

def genera_contratto_completo(c):
    pdf = PDF(); pdf.add_page()
    pdf.set_font("Arial", "B", 12); pdf.cell(0, 10, safe(f"CONTRATTO DI NOLEGGIO N. {c['numero_fattura']}"), ln=True, align="C")
    
    # Dati
    pdf.set_font("Arial", "B", 9); pdf.cell(0, 7, " DATI CLIENTE E VEICOLO", 1, ln=True, fill=True)
    pdf.set_font("Arial", "", 9)
    testo = (f"Cliente: {c['nome']} {c['cognome']} ({c['codice_fiscale']})\n"
             f"Indirizzo: {c.get('indirizzo_cliente', 'N/D')}\n"
             f"Patente: {c.get('numero_patente', 'N/D')}\n"
             f"Mezzo: {c['modello']} tg: {c['targa']}\n"
             f"Prezzo: {c['prezzo']} EUR | Periodo: {c.get('inizio')} - {c.get('fine')}")
    pdf.multi_cell(0, 6, safe(testo), border=1)
    
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

    # Pagina 2: Clausole
    pdf.add_page()
    pdf.set_font("Arial", "B", 8); pdf.cell(95, 6, "CONDIZIONI GENERALI", 0, 0); pdf.cell(95, 6, "GENERAL CONDITIONS", 0, 1)
    pdf.set_font("Arial", "", 5.5)
    it = ("1) Uso Ischia. 2) Solo firmatario autorizzato. 3) Cliente responsabile danni/furto. 4) Multe + 25.83 Euro. 5) No sub-noleggio. 6) Riconsegna in tempo. 11) Smarrimento chiavi 250 Euro. 12) Casco obbligatorio.")
    en = ("1) Ischia only. 2) Signer only. 3) Customer liable for damage/theft. 4) Fines + 25.83 Euro fee. 5) No sub-rental. 6) Prompt return. 11) Keys loss 250 Euro. 12) Helmet mandatory.")
    y_cl = pdf.get_y()
    pdf.multi_cell(92, 4, safe(it), border=1); pdf.set_xy(105, y_cl); pdf.multi_cell(92, 4, safe(en), border=1)
    return bytes(pdf.output(dest="S"))

def genera_modulo_vigili(c):
    pdf = PDF(); pdf.add_page()
    pdf.set_font("Arial", "B", 12); pdf.cell(0, 10, "COMUNICAZIONE DATI CONDUCENTE (Art. 196 CdS)", ln=True, align="C")
    pdf.set_font("Arial", "", 10); pdf.ln(10)
    testo = (f"In data {c.get('inizio')} il veicolo tg. {c['targa']} modello {c['modello']}\n"
             f"era affidato a: {c['nome']} {c['cognome']}\nCF: {c['codice_fiscale']}\nPATENTE: {c.get('numero_patente')}")
    pdf.multi_cell(0, 8, safe(testo)); return bytes(pdf.output(dest="S"))

# --- INTERFACCIA ---
st.set_page_config(page_title="Battaglia Rent Admin", layout="wide")
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Password", type="password") == "1234":
        if st.button("Accedi"): st.session_state.auth = True; st.rerun()
    st.stop()

t1, t2 = st.tabs(["📝 NUOVO", "📂 ARCHIVIO"])
with t1:
    with st.form("f"):
        c1, c2, c3 = st.columns(3)
        n, cg, wa = c1.text_input("Nome"), c2.text_input("Cognome"), c3.text_input("WhatsApp")
        c4, c5, c6 = st.columns(3)
        cf, ind, pat = c4.text_input("CF"), c5.text_input("Indirizzo"), c6.text_input("Patente")
        c7, c8, c9 = st.columns(3)
        mod, tg, pz = c7.text_input("Mezzo"), c8.text_input("Targa").upper(), c9.number_input("Prezzo (€)", 0.0)
        f1, f2 = st.columns(2)
        fp, fd = f1.file_uploader("Patente"), f2.file_uploader("Danni")
        
        st.subheader("🖋️ Firme")
        col_f1, col_f2 = st.columns(2)
        with col_f1: can1 = st_canvas(height=120, width=300, key="sig1")
        with col_f2: can2 = st_canvas(height=120, width=300, key="sig2")

        if st.form_submit_button("1. INVIA OTP"):
            cod = str(random.randint(100000, 999999))
            st.session_state.otp_code = cod
            clean_wa = wa.replace(" ","").replace("+","")
            if not clean_wa.startswith("39"): clean_wa = "39" + clean_wa
            msg = f"Codice firma: {cod}"; url = f"https://wa.me/{clean_wa}?text={urllib.parse.quote(msg)}"
            st.markdown(f"### [📲 CLICCA QUI PER WHATSAPP]({url})")

    if "otp_code" in st.session_state:
        if st.button("2. SALVA"):
            # Salvataggio dati
            dati = {
                "nome": n, "cognome": cg, "targa": tg, "prezzo": pz, "modello": mod, "codice_fiscale": cf,
                "indirizzo_cliente": ind, "numero_patente": pat, "otp_code": st.session_state.otp_code, "pec": wa,
                "timestamp_firma": datetime.now().strftime("%d/%m/%Y %H:%M"), "numero_fattura": get_prossimo_numero(),
                "inizio": str(datetime.now().date()), "fine": str(datetime.now().date()),
                "firma": "data:image/png;base64," + base64.b64encode(io.BytesIO(Image.fromarray(can1.image_data.astype("uint8")).tobytes()).getvalue()).decode() if can1.image_data is not None else "",
                "firma2": "data:image/png;base64," + base64.b64encode(io.BytesIO(Image.fromarray(can2.image_data.astype("uint8")).tobytes()).getvalue()).decode() if can2.image_data is not None else ""
            }
            supabase.table("contratti").insert(dati).execute()
            st.success("✅ SALVATO!")
            del st.session_state.otp_code

with t2:
    q = st.text_input("🔍 Cerca")
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    for r in res.data:
        if q.lower() in f"{s(r['cognome'])} {s(r['targa'])}".lower():
            with st.expander(f"📄 N. {r['numero_fattura']} - {r['cognome']}"):
                c1, c2, c3 = st.columns(3)
                c1.download_button("📜 Contratto", genera_contratto_completo(r), f"C_{r['id']}.pdf")
                c2.download_button("👮 Vigili", genera_modulo_vigili(r), f"V_{r['id']}.pdf")
                c3.download_button("📂 XML", genera_xml_fattura(r), f"F_{r['id']}.xml")
