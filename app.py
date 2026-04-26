import streamlit as st
from supabase import create_client, Client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from fpdf import FPDF
import io
import base64
from datetime import datetime
import xml.etree.ElementTree as ET

# --- CONFIGURAZIONE AZIENDALE (Fisso) ---
DITTA = "BATTAGLIA RENT"
TITOLARE = "BATTAGLIA MARIANNA"
INDIRIZZO = "Via Cognole n. 5"
CAP = "80075"
COMUNE = "Forio"
PROVINCIA = "NA"
NAZIONE = "IT"
PIVA = "10252601215"
CF_DITTA = "BTTMNN87A53Z112S"

# Connessione protetta Supabase
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# Helper functions
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

# --- GENERAZIONE XML PER ARUBA / ADE ---
def genera_xml_fattura(c):
    prezzo_totale = float(c.get('prezzo', 0))
    imponibile = round(prezzo_totale / 1.22, 2)
    imposta = round(prezzo_totale - imponibile, 2)
    data_doc = datetime.now().strftime("%Y-%m-%d")
    
    # Gestione SDI Stranieri
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

# --- FUNZIONI GENERAZIONE DOCUMENTI ---
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
    pdf.set_font("Arial", "", 9)
    pdf.cell(63, 7, safe(f"Mezzo: {c['modello']}"), border=1)
    pdf.cell(63, 7, safe(f"Targa: {c['targa']}"), border=1)
    pdf.cell(64, 7, safe(f"Prezzo: {c['prezzo']} EUR"), border=1, ln=True)
    pdf.ln(5); pdf.set_font("Arial", "B", 10); pdf.cell(0, 7, " CONDIZIONI ESSENZIALI DI NOLEGGIO", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "", 8)
    clausole = (
        "1. ASSICURAZIONE: Il veicolo e coperto da assicurazione R.C.A. solo verso terzi. "
        "2. DANNI E FURTO: Il cliente e responsabile di qualunque danno al veicolo, furto totale o parziale, incendio o smarrimento chiavi/accessori. "
        "Tali costi sono integralmente a carico del cliente. 3. CASCO: Il cliente ha l'obbligo di indossare il casco e rispettare il Codice della Strada. "
        "4. MULTE: Tutte le infrazioni commesse durante il noleggio sono a carico del cliente. "
        "5. PRIVACY: Il cliente autorizza il trattamento dei dati personali ai sensi del GDPR (Reg. UE 2016/679)."
    )
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
    pdf.ln(5); pdf.cell(150, 7, "TOTALE FATTURA:", align="R"); pdf.cell(40, 7, f"{p:.2f} EUR", border=1, ln=True)
    return bytes(pdf.output(dest="S"))

def genera_modulo_vigili_legale(c):
    pdf = BusinessPDF(); pdf.add_page()
    pdf.set_font("Arial", "B", 11); pdf.cell(0, 10, safe("Spett. le Polizia Locale"), ln=True, align="R")
    pdf.ln(5); pdf.set_font("Arial", "B", 10); pdf.cell(0, 7, safe("OGGETTO: COMUNICAZIONE DATI CONDUCENTE PER RINOTIFICA"), ln=True)
    pdf.ln(5); pdf.set_font("Arial", "", 10)
    testo = (f"La sottoscritta BATTAGLIA MARIANNA, titolare di {DITTA}, dichiara che il veicolo {c['modello']} "
             f"targa {c['targa']} era locato a {c['nome']} {c['cognome']}, nato a {c.get('luogo_nascita','') or ''} il {c.get('data_nascita','') or ''}, "
             f"residente in {c.get('indirizzo_cliente','') or ''}. Patente n. {c.get('numero_patente','') or ''}. Si richiede la rinotifica del verbale.")
    pdf.multi_cell(0, 6, safe(testo)); pdf.ln(15); pdf.cell(0, 10, "In fede, Marianna Battaglia", align="R", ln=True)
    return bytes(pdf.output(dest="S"))

# --- INTERFACCIA STREAMLIT ---
st.set_page_config(page_title="Battaglia Rent Pro", layout="wide")

# Auth Semplice
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    pwd = st.text_input("Password Accesso", type="password")
    if st.button("Accedi"):
        if pwd == "1234": st.session_state.auth = True; st.rerun()
        else: st.error("Password errata")
    st.stop()

t1, t2 = st.tabs(["📝 Nuovo Noleggio", "📂 Archivio"])

with t1:
    with st.form("main_form", clear_on_submit=True):
        st.subheader("Anagrafica Cliente")
        c1, c2, c3 = st.columns(3)
        nome = c1.text_input("Nome")
        cognome = c2.text_input("Cognome")
        nazionalita = c3.selectbox("Nazionalità", ["Italia", "Estero"])
        
        c4, c5, c6 = st.columns(3)
        cf = c4.text_input("C.F. / Documento ID")
        tel = c5.text_input("Telefono")
        email = c6.text_input("Email / PEC")
        
        c7, c8, c9 = st.columns(3)
        dat_n = c7.text_input("Data Nascita (gg/mm/aaaa)")
        luo_n = c8.text_input("Luogo Nascita")
        ind = c9.text_input("Residenza Completa")
        
        st.markdown("---")
        st.subheader("Dati Veicolo")
        m1, m2, m3 = st.columns(3)
        mod = m1.text_input("Modello")
        tar = m2.text_input("Targa").upper()
        pat = m3.text_input("N. Patente")
        
        d1, d2, d3 = st.columns(3)
        prezzo = d1.number_input("Prezzo Totale (€)", min_value=0.0)
        deposito = d2.number_input("Deposito Cauzionale (€)", min_value=0.0)
        sdi = d3.text_input("Codice SDI (7 cifre)", value="0000000")
        
        ini = st.date_input("Data Inizio")
        fin = st.date_input("Data Fine")
        
        st.markdown("---")
        st.subheader("📸 Archiviazione Documenti e Stato Mezzo")
        video_mezzo = st.file_uploader("Video o Foto Stato Motorino (Danni)", type=["mp4", "mov", "jpg", "png"])
        f_patente = st.file_uploader("Fronte Patente", type=["jpg", "png", "pdf"])
        r_patente = st.file_uploader("Retro Patente", type=["jpg", "png", "pdf"])
        
        st.write("### Firma Digitale Cliente")
        canvas = st_canvas(height=150, width=400, stroke_width=3, key="sig_final")
        accetto = st.checkbox("Dichiaro di aver preso visione e accettato le condizioni di noleggio.")
        
        if st.form_submit_button("💾 REGISTRA E GENERA"):
            if not accetto or not nome or not tar:
                st.error("❌ Compila i campi obbligatori (Nome, Targa e Accettazione)!")
            else:
                with st.spinner("Salvataggio in corso..."):
                    try:
                        # Firma
                        img_firma = Image.fromarray(canvas.image_data.astype("uint8"))
                        buf_f = io.BytesIO(); img_firma.save(buf_f, format="PNG")
                        firma_b64 = base64.b64encode(buf_f.getvalue()).decode()
                        
                        # Upload Files
                        u_v = upload_media(video_mezzo, tar, "STATO")
                        u_f = upload_media(f_patente, tar, "PAT_F")
                        u_r = upload_media(r_patente, tar, "PAT_R")
                        
                        num = get_prossimo_numero()
                        dati = {
                            "nome": nome, "cognome": cognome, "codice_fiscale": cf, "modello": mod, 
                            "targa": tar, "prezzo": prezzo, "deposito": deposito, "numero_fattura": num, 
                            "firma": firma_b64, "url_video": u_v, "url_fronte": u_f, "url_retro": u_r, 
                            "pec": email, "codice_univoco": sdi, "data_nascita": dat_n, 
                            "luogo_nascita": luo_n, "indirizzo_cliente": ind, "inizio": str(ini), 
                            "fine": str(fin), "numero_patente": pat, "nazionalita": nazionalita, "telefono": tel
                        }
                        supabase.table("contratti").insert(dati).execute()
                        st.success(f"✅ Noleggio N. {num} registrato con successo!")
                    except Exception as e: st.error(f"Errore: {e}")

with t2:
    search = st.text_input("🔍 Cerca per Cognome o Targa")
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    
    for r in res.data:
        if search.lower() in f"{s(r['cognome'])} {s(r['targa'])}".lower():
            with st.expander(f"📄 N. {r['numero_fattura']} - {r['cognome']} ({r['targa']})"):
                
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.write(f"*Cliente:* {r['nome']} {r['cognome']}")
                    st.write(f"*Periodo:* {r['inizio']} / {r['fine']}")
                
                # Visualizzazione Stato Mezzo e Patenti
                st.markdown("---")
                st.write("### 📸 Media Archiviati")
                cm1, cm2, cm3 = st.columns(3)
                with cm1:
                    if r.get('url_video'):
                        if ".mp4" in r['url_video'] or ".mov" in r['url_video']: st.video(r['url_video'])
                        else: st.image(r['url_video'], caption="Stato Veicolo")
                    else: st.info("Nessun video danni")
                with cm2:
                    if r.get('url_fronte'): st.image(r['url_fronte'], caption="Fronte Patente")
                with cm3:
                    if r.get('url_retro'): st.image(r['url_retro'], caption="Retro Patente")

                st.markdown("---")
                st.write("### 📥 Download Documenti Legali")
                dcol1, dcol2, dcol3, dcol4 = st.columns(4)
                
                dcol1.download_button("📜 Contratto", genera_contratto_legale(r), f"Contratto_{r['numero_fattura']}.pdf")
                dcol2.download_button("🧾 Fattura PDF", genera_fattura_completa(r), f"Fattura_{r['numero_fattura']}.pdf")
                dcol3.download_button("🚨 Modulo Vigili", genera_modulo_vigili_legale(r), f"Vigili_{r['numero_fattura']}.pdf")
                
                # TASTO XML ARUBA
                dcol4.download_button(
                    "📂 XML ARUBA", 
                    genera_xml_fattura(r), 
                    f"IT{PIVA}DF{r['numero_fattura']}.xml",
                    mime="text/xml"
                )
