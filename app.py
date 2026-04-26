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
        data = file.getvalue()
        if "image" in content_type:
            nome_file += ".jpg"
        else:
            nome_file += ".mp4" if "mp4" in content_type else ".mov"
        supabase.storage.from_("documenti").upload(nome_file, data, {"content-type": content_type})
        return supabase.storage.from_("documenti").get_public_url(nome_file)
    except: return None

# --- FUNZIONE GENERAZIONE XML (PER ARUBA/ADE) ---
def genera_xml_fattura(c):
    prezzo_totale = float(c['prezzo'])
    imponibile = round(prezzo_totale / 1.22, 2)
    imposta = round(prezzo_totale - imponibile, 2)
    data_doc = datetime.now().strftime("%Y-%m-%d")
    
    # Se il cliente è straniero (nazionalità non Italia), lo SDI diventa XXXXXXX
    codice_sdi = s(c.get('codice_univoco', '0000000'))
    if c.get('nazionalita', '').lower() not in ['italia', 'it', 'italiana']:
        codice_sdi = "XXXXXXX"

    xml_data = f"""<?xml version="1.0" encoding="UTF-8"?>
<p:FatturaElettronica versione="FPR12" xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2">
  <FatturaElettronicaHeader>
    <DatiTrasmissione>
      <IdTrasmittente><IdPaese>IT</IdPaese><IdCodice>{PIVA}</IdCodice></IdTrasmittente>
      <ProgressivoInvio>{c['numero_fattura']}</ProgressivoInvio>
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
        <NumeroLinea>1</NumeroLinea><Descrizione>Noleggio veicolo {s(c['modello'])} targa {s(c['targa'])}</Descrizione><PrezzoUnitario>{imponibile:.2f}</PrezzoUnitario><PrezzoTotale>{imponibile:.2f}</PrezzoTotale><AliquotaIVA>22.00</AliquotaIVA>
      </DettaglioLinee>
      <DatiRiepilogo>
        <AliquotaIVA>22.00</AliquotaIVA><ImponibileImporto>{imponibile:.2f}</ImponibileImporto><Imposta>{imposta:.2f}</Imposta><EsigibilitaIVA>I</EsigibilitaIVA>
      </DatiRiepilogo>
    </DatiBeniServizi>
  </FatturaElettronicaBody>
</p:FatturaElettronica>"""
    return xml_data.encode('utf-8')

# --- PDF FATTURA DI CORTESIA ---
def genera_fattura_pdf(c):
    pdf = FPDF(); pdf.add_page()
    pdf.set_font("Arial", "B", 12); pdf.cell(0, 10, safe(DITTA), ln=True)
    pdf.set_font("Arial", "", 14); pdf.cell(0, 10, safe(f"FATTURA N. {c['numero_fattura']}"), ln=True, align="C")
    pdf.ln(10); p = float(c['prezzo']); imp = p/1.22; iva = p-imp
    pdf.set_font("Arial", "", 10)
    pdf.cell(110, 10, safe(f"Noleggio {c['modello']} {c['targa']}"), border=1)
    pdf.cell(40, 10, "IVA 22%", border=1); pdf.cell(40, 10, f"{p:.2f} EUR", border=1, ln=True)
    return bytes(pdf.output(dest="S"))

# --- INTERFACCIA STREAMLIT ---
st.set_page_config(page_title="Battaglia Rent", layout="wide")

t1, t2 = st.tabs(["📝 Nuovo Noleggio", "📂 Archivio"])

with t1:
    with st.form("form_noleggio"):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Nome")
        cognome = col2.text_input("Cognome")
        nazionalita = st.selectbox("Nazionalità", ["Italia", "Estero"])
        cf = st.text_input("Codice Fiscale")
        modello = st.text_input("Modello Motorino")
        targa = st.text_input("Targa").upper()
        prezzo = st.number_input("Prezzo Totale", min_value=0.0)
        sdi = st.text_input("Codice SDI (se italiano)", value="0000000")
        
        video = st.file_uploader("Video/Foto Stato Mezzo", type=["mp4", "mov", "jpg", "png"])
        
        if st.form_submit_button("REGISTRA"):
            num = get_prossimo_numero()
            u_v = upload_media(video, targa, "VIDEO")
            dati = {
                "nome": nome, "cognome": cognome, "codice_fiscale": cf, "modello": modello, 
                "targa": targa, "prezzo": prezzo, "numero_fattura": num, "url_video": u_v,
                "codice_univoco": sdi, "nazionalita": nazionalita
            }
            supabase.table("contratti").insert(dati).execute()
            st.success(f"Registrato! Fattura N. {num}")

with t2:
    st.subheader("Archivio Contratti")
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    for r in res.data:
        with st.expander(f"Fattura {r['numero_fattura']} - {r['cognome']} ({r['targa']})"):
            # MOSTRA VIDEO
            if r.get('url_video'):
                st.video(r['url_video'])
            
            # TASTI DOWNLOAD
            col_a, col_b = st.columns(2)
            
            # 1. PDF PER IL CLIENTE
            col_a.download_button(
                "📜 Scarica PDF Cliente", 
                genera_fattura_pdf(r), 
                f"Fattura_{r['numero_fattura']}.pdf"
            )
            
            # 2. XML PER ARUBA (IL POSTINO DIGITALE)
            col_b.download_button(
                "📂 SCARICA XML ARUBA", 
                genera_xml_fattura(r), 
                f"IT{PIVA}DF{r['numero_fattura']}.xml",
                mime="text/xml"
            )
