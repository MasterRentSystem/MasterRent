import streamlit as st
from supabase import create_client, Client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from fpdf import FPDF
import io
import base64
from datetime import datetime
import time

# --- CONFIGURAZIONE AZIENDALE ---
DITTA = "BATTAGLIA RENT"
TITOLARE = "BATTAGLIA MARIANNA"
INDIRIZZO = "Via Cognole n. 5"
CAP = "80075"
COMUNE = "Forio"
PROVINCIA = "NA"
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
        data = file.getvalue()
        supabase.storage.from_("documenti").upload(nome_file, data, {"content-type": file.type})
        return supabase.storage.from_("documenti").get_public_url(nome_file)
    except: return None

# --- 1. PROGRESSIVO INVIO UNICO (PER XML ARUBA) ---
def genera_xml_fattura(c):
    p_tot = float(c.get('prezzo', 0))
    imp = round(p_tot / 1.22, 2)
    iva = round(p_tot - imp, 2)
    dt = datetime.now().strftime("%Y-%m-%d")
    # Progressivo alfanumerico basato su tempo per unicità assoluta
    prog_invio = f"PROG{int(time.time())}" 
    
    sdi = s(c.get('codice_univoco', '0000000'))
    if str(c.get('nazionalita')).lower() != "italia": sdi = "XXXXXXX"

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<p:FatturaElettronica versione="FPR12" xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2">
  <FatturaElettronicaHeader>
    <DatiTrasmissione>
      <IdTrasmittente><IdPaese>IT</IdPaese><IdCodice>{PIVA}</IdCodice></IdTrasmittente>
      <ProgressivoInvio>{prog_invio}</ProgressivoInvio>
      <FormatoTrasmissione>FPR12</FormatoTrasmissione>
      <CodiceDestinatario>{sdi}</CodiceDestinatario>
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
    <DatiGenerali><DatiGeneraliDocumento><TipoDocumento>TD01</TipoDocumento><Divisa>EUR</Divisa><Data>{dt}</Data><Numero>{c.get('numero_fattura', '0')}</Numero><ImportoTotaleDocumento>{p_tot:.2f}</ImportoTotaleDocumento></DatiGeneraliDocumento></DatiGenerali>
    <DatiBeniServizi>
      <DettaglioLinee><NumeroLinea>1</NumeroLinea><Descrizione>Noleggio {s(c.get('modello'))} tg {s(c.get('targa'))}</Descrizione><PrezzoUnitario>{imp:.2f}</PrezzoUnitario><PrezzoTotale>{imp:.2f}</PrezzoTotale><AliquotaIVA>22.00</AliquotaIVA></DettaglioLinee>
      <DatiRiepilogo><AliquotaIVA>22.00</AliquotaIVA><ImponibileImporto>{imp:.2f}</ImponibileImporto><Imposta>{iva:.2f}</Imposta><EsigibilitaIVA>I</EsigibilitaIVA></DatiRiepilogo>
    </DatiBeniServizi>
    <DatiPagamento><CondizioniPagamento>TP02</CondizioniPagamento><DettaglioPagamento><ModalitaPagamento>MP01</ModalitaPagamento><ImportoPagamento>{p_tot:.2f}</ImportoPagamento></DettaglioPagamento></DatiPagamento>
  </FatturaElettronicaBody>
</p:FatturaElettronica>""".encode('utf-8')

class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 11)
        self.cell(0, 5, DITTA, ln=True)
        self.set_font("Arial", "", 8)
        self.cell(0, 4, f"{INDIRIZZO} - {COMUNE} (NA) | P.IVA: {PIVA}", ln=True)
        self.line(10, self.get_y()+2, 200, self.get_y()+2); self.ln(8)

# --- 2. GDPR NEL CONTRATTO ---
def genera_contratto_completo(c):
    pdf = PDF(); pdf.add_page()
    pdf.set_font("Arial", "B", 14); pdf.cell(0, 10, safe(f"CONTRATTO DI NOLEGGIO N. {c['numero_fattura']}"), ln=True, align="C")
    
    # Sezione Dati
    pdf.set_font("Arial", "B", 10); pdf.cell(0, 8, " 1. ANAGRAFICA E MEZZO", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "", 9)
    pdf.multi_cell(0, 5, safe(f"Cliente: {c['nome']} {c['cognome']} | CF: {c['codice_fiscale']}\nMezzo: {c['modello']} | Targa: {c['targa']}\nPeriodo: {c['inizio']} / {c['fine']}"), border=1)
    
    # GDPR CLAUSE
    pdf.ln(2); pdf.set_font("Arial", "B", 10); pdf.cell(0, 8, " 2. INFORMATIVA PRIVACY (GDPR)", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "", 7)
    gdpr_text = (f"Ai sensi del Reg. UE 2016/679, il cliente autorizza {DITTA} al trattamento dei dati personali per fini contrattuali e legali. "
                 "I dati saranno conservati per la durata prevista dalla legge e non ceduti a terzi, salvo autorita competenti.")
    pdf.multi_cell(0, 4, safe(gdpr_text), border=1)

    pdf.ln(2); pdf.set_font("Arial", "B", 10); pdf.cell(0, 8, " 3. CONDIZIONI GENERALI", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "", 7)
    pdf.multi_cell(0, 4, safe("Il cliente e responsabile di danni, furto e violazioni del codice della strada."), border=1)
    
    pdf.ln(5); pdf.set_font("Arial", "B", 10); pdf.cell(0, 10, "FIRMA PER ACCETTAZIONE E GDPR", ln=True)
    yf = pdf.get_y(); pdf.cell(80, 20, "", border=1)
    if c.get("firma"):
        try:
            f_data = str(c["firma"]).split(",")[1] if "," in str(c["firma"]) else str(c["firma"])
            pdf.image(io.BytesIO(base64.b64decode(f_data)), x=12, y=yf+2, w=40)
        except: pass
    return bytes(pdf.output(dest="S"))

# --- 3. DETTAGLIO PAGAMENTO IN FATTURA ---
def genera_fattura_completa(c):
    pdf = PDF(); pdf.add_page()
    pdf.set_font("Arial", "B", 14); pdf.cell(0, 10, safe(f"FATTURA N. {c['numero_fattura']}"), ln=True, align="C")
    p = float(c['prezzo']); imp = p/1.22; iva = p-imp
    
    pdf.set_font("Arial", "", 10); pdf.cell(95, 10, safe(f"CLIENTE:\n{c['nome']} {c['cognome']}\n{c['codice_fiscale']}"), 1)
    pdf.cell(95, 10, safe(f"DATA: {datetime.now().strftime('%d/%m/%Y')}\nSDI: {c.get('codice_univoco','0000000')}"), 1, ln=True)
    
    pdf.ln(10); pdf.set_font("Arial", "B", 10); pdf.cell(110, 8, "DESCRIZIONE", 1); pdf.cell(40, 8, "IVA", 1); pdf.cell(40, 8, "TOTALE", 1, ln=True)
    pdf.set_font("Arial", "", 10); pdf.cell(110, 10, safe(f"Noleggio {c['modello']} tg {c['targa']}"), 1); pdf.cell(40, 10, "22%", 1); pdf.cell(40, 10, f"{p:.2f}", 1, ln=True)
    
    pdf.ln(5); pdf.set_font("Arial", "B", 9)
    pdf.cell(0, 7, safe(f"MODALITA DI PAGAMENTO: CONTANTI / POS / BONIFICO"), ln=True)
    pdf.cell(0, 7, safe(f"STATO PAGAMENTO: SALDATO"), ln=True)
    
    pdf.set_font("Arial", "B", 11); pdf.cell(150, 8, "TOTALE DA PAGARE:", 0, 0, "R"); pdf.cell(40, 8, f"{p:.2f} EUR", 1, ln=True)
    return bytes(pdf.output(dest="S"))

def genera_modulo_vigili(c):
    pdf = PDF(); pdf.add_page()
    pdf.set_font("Arial", "B", 11); pdf.cell(0, 10, "OGGETTO: RINOTIFICA VERBALE DI CONTESTAZIONE", ln=True)
    pdf.set_font("Arial", "", 11)
    testo = f"Il veicolo {c['modello']} targa {c['targa']} era locato a {c['nome']} {c['cognome']}, nato il {c.get('data_nascita','')} a {c.get('luogo_nascita','')}."
    pdf.multi_cell(0, 7, safe(testo))
    return bytes(pdf.output(dest="S"))

# --- INTERFACCIA ---
st.set_page_config(page_title="Battaglia Rent Blindata", layout="wide")

if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Password", type="password") == "1234":
        if st.button("Accedi"): st.session_state.auth = True; st.rerun()
    st.stop()

t1, t2 = st.tabs(["📝 REGISTRA", "📂 ARCHIVIO"])

with t1:
    with st.form("f_new", clear_on_submit=True):
        st.subheader("Dati Cliente")
        c1, c2, c3 = st.columns(3)
        nome, cognome, naz = c1.text_input("Nome"), c2.text_input("Cognome"), c3.selectbox("Nazionalità", ["Italia", "Estero"])
        c4, c5, c6 = st.columns(3)
        cf, pat_n, tel = c4.text_input("Codice Fiscale"), c5.text_input("N. Patente"), c6.text_input("Telefono")
        c7, c8 = st.columns(2)
        l_nas, d_nas = c7.text_input("Luogo Nascita"), c8.text_input("Data Nascita")
        ind = st.text_input("Indirizzo Residenza")
        em = st.text_input("Email / PEC")
        
        st.subheader("Dati Noleggio")
        n1, n2, n3 = st.columns(3)
        mod, tar, sdi = n1.text_input("Modello"), n2.text_input("Targa").upper(), n3.text_input("Codice SDI", "0000000")
        n4, n5, n6 = st.columns(3)
        prezzo, dep, ini = n4.number_input("Prezzo"), n5.number_input("Deposito"), n6.date_input("Inizio")
        fin = st.date_input("Fine")
        
        st.subheader("Foto/Video")
        v_m = st.file_uploader("Danni", type=["mp4","mov","jpg","png"])
        f_p = st.file_uploader("Patente F", type=["jpg","png"])
        r_p = st.file_uploader("Patente R", type=["jpg","png"])
        
        canvas = st_canvas(height=150, width=400, stroke_width=3, key="sig")
        accetto = st.checkbox("Accetto Condizioni e Informativa Privacy GDPR.")
        
        if st.form_submit_button("SALVA"):
            if not (nome and tar and accetto): st.error("Dati mancanti!")
            else:
                num = get_prossimo_numero()
                
                # --- 4. UNIQUE NUMERO FATTURA (CONTROLLO DB) ---
                check = supabase.table("contratti").select("id").eq("numero_fattura", num).execute()
                if len(check.data) > 0:
                    st.error("Errore: Numero fattura già esistente. Riprova.")
                else:
                    u_v, u_f, u_r = upload_media(v_m, tar, "ST"), upload_media(f_p, tar, "F"), upload_media(r_p, tar, "R")
                    img = Image.fromarray(canvas.image_data.astype("uint8"))
                    buf = io.BytesIO(); img.save(buf, format="PNG")
                    f_b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
                    
                    dati = {"nome":nome, "cognome":cognome, "codice_fiscale":cf, "modello":mod, "targa":tar, "prezzo":prezzo, "deposito":dep, "numero_fattura":num, "firma":f_b64, "url_video":u_v, "url_fronte":u_f, "url_retro":u_r, "codice_univoco":sdi, "nazionalita":naz, "inizio":str(ini), "fine":str(fin), "numero_patente":pat_n, "telefono":tel, "luogo_nascita":l_nas, "data_nascita":d_nas, "pec":em, "indirizzo_cliente":ind}
                    supabase.table("contratti").insert(dati).execute()
                    st.success(f"Registrato N. {num}")

with t2:
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    for idx, r in enumerate(res.data):
        with st.expander(f"📄 N. {r['numero_fattura']} - {r['cognome']} ({r['targa']})"):
            b1, b2, b3, b4 = st.columns(4)
            b1.download_button("📜 Contratto", genera_contratto_completo(r), f"Contr_{idx}.pdf", key=f"c_{idx}")
            b2.download_button("🧾 Fattura", genera_fattura_completa(r), f"Fatt_{idx}.pdf", key=f"f_{idx}")
            b3.download_button("🚨 Vigili", genera_modulo_vigili(r), f"Vig_{idx}.pdf", key=f"v_{idx}")
            b4.download_button("📂 XML Aruba", genera_xml_fattura(r), f"IT{PIVA}{idx}.xml", key=f"x{idx}")
