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
INFO_TITOLARE = "nata a Berlino (Germania) il 13/01/1987 e residente in Forio alla Via Cognole n.5"

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
        
        # Comprimi le immagini per risparmiare spazio sul database
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

# --- PDF ENGINE ---
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 10)
        self.cell(0, 5, DITTA, ln=True, align="L")
        self.set_font("Arial", "", 8)
        self.cell(0, 4, f"di {TITOLARE} - {INDIRIZZO} - {COMUNE} (NA)", ln=True)
        self.cell(0, 4, f"P.IVA: {PIVA} | C.F.: {CF_DITTA}", ln=True)
        self.ln(5)

# --- 1. MODULO VIGILI ---
def genera_modulo_vigili(c):
    pdf = PDF(); pdf.add_page()
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 5, "Spett. le", ln=True, align="R")
    pdf.cell(0, 5, "Polizia Locale di ........................................", ln=True, align="R")
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 9)
    pdf.cell(0, 5, safe(f"OGGETTO: RIFERIMENTO VS. ACCERTAMENTO VIOLAZIONE N. {c.get('riferimento_multa', '..........')}"), ln=True)
    pdf.cell(0, 5, safe("COMUNICAZIONE LOCAZIONE VEICOLO"), ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", "", 10)
    testo_corpo = (f"In riferimento al Verbale di accertamento di infrazione al Codice della strada di cui all'oggetto, con la presente, la "
                   f"sottoscritta BATTAGLIA MARIANNA {INFO_TITOLARE}, in qualita di titolare dell'omonima ditta individuale, "
                   f"C.F. {CF_DITTA} e P.IVA {PIVA}")
    pdf.multi_cell(0, 5, safe(testo_corpo))
    pdf.ln(3)
    pdf.set_font("Arial", "B", 10); pdf.cell(0, 10, "DICHIARA", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    dichiarazione = (f"Ai sensi della L. 445/2000 che il veicolo modello {c['modello']} targato {c['targa']} il giorno {c['inizio']} "
                     f"era concesso in locazione senza conducente al signor:\n\n"
                     f"COGNOME E NOME: {c['cognome'].upper()} {c['nome'].upper()}\n"
                     f"LUOGO E DATA DI NASCITA: {c.get('luogo_nascita','')} il {c.get('data_nascita','')}\n"
                     f"RESIDENZA: {c.get('indirizzo_cliente','')}\n"
                     f"IDENTIFICATO A MEZZO: Patente di guida n. {c.get('numero_patente','')}")
    pdf.multi_cell(0, 6, safe(dichiarazione))
    pdf.ln(5)
    pdf.multi_cell(0, 5, safe("La presente al fine di procedere alla rinotifica nei confronti del locatario sopra indicato.\nSi allega: Copia del contratto di locazione e documento del trasgressore."))
    pdf.ln(10)
    pdf.cell(0, 5, "In fede", ln=True, align="R")
    pdf.cell(0, 5, "Marianna Battaglia", ln=True, align="R")
    return bytes(pdf.output(dest="S"))

# --- 2. CONTRATTO ---
def genera_contratto_completo(c):
    pdf = PDF(); pdf.add_page()
    pdf.set_font("Arial", "B", 12); pdf.cell(0, 10, safe(f"CONTRATTO DI NOLEGGIO N. {c['numero_fattura']}"), ln=True, align="C")
    
    pdf.set_font("Arial", "B", 10); pdf.cell(0, 8, " ANAGRAFICA CLIENTE", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "", 9)
    pdf.cell(95, 7, safe(f"Nome: {c['nome']} {c['cognome']}"), border="LR")
    pdf.cell(95, 7, safe(f"Nato il: {c.get('data_nascita','')} a: {c.get('luogo_nascita','')}"), border="R", ln=True)
    pdf.cell(95, 7, safe(f"Residenza: {c.get('indirizzo_cliente','')}"), border="LR")
    pdf.cell(95, 7, safe(f"Tel: {c.get('telefono','')} Nazionalita: {c.get('nazionalita','')}"), border="R", ln=True)
    pdf.cell(95, 7, safe(f"C.F.: {c['codice_fiscale']}"), border="LR")
    pdf.cell(95, 7, safe(f"Email/PEC: {c.get('pec','')}"), border="R", ln=True)
    pdf.cell(190, 1, "", border="T", ln=True)

    pdf.ln(2); pdf.set_font("Arial", "B", 10); pdf.cell(0, 8, " DATI NOLEGGIO", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "", 9)
    pdf.cell(63, 7, safe(f"Mezzo: {c['modello']}"), border=1)
    pdf.cell(63, 7, safe(f"Targa: {c['targa']}"), border=1)
    pdf.cell(64, 7, safe(f"Patente: {c.get('numero_patente','')}"), border=1, ln=True)
    pdf.cell(63, 7, safe(f"Inizio: {c['inizio']}"), border=1)
    pdf.cell(63, 7, safe(f"Fine: {c['fine']}"), border=1)
    pdf.cell(64, 7, safe(f"Prezzo: {c['prezzo']} EUR"), border=1, ln=True)

    pdf.ln(2); pdf.set_font("Arial", "B", 10); pdf.cell(0, 8, " CONDIZIONI ESSENZIALI DI NOLEGGIO", ln=True, border=1)
    pdf.set_font("Arial", "", 8)
    condizioni = ("1. ASSICURAZIONE: Il veicolo e coperto da assicurazione R.C.A. solo verso terzi. "
                  "2. DANNI E FURTO: Il cliente e responsabile di qualunque danno al veicolo, furto totale o parziale, incendio o smarrimento chiavi/accessori. Tali costi sono integralmente a carico del cliente. "
                  "3. CASCO: Il cliente ha l'obbligo di indossare il casco e rispettare il Codice della Strada. "
                  "4. MULTE: Tutte le infrazioni commesse durante il noleggio sono a carico del cliente. "
                  "5. PRIVACY: Ai sensi del Reg. UE 2016/679, il cliente autorizza BATTAGLIA RENT al trattamento dei dati personali per fini contrattuali e legali.")
    pdf.multi_cell(0, 4, safe(condizioni), border=1)

    pdf.ln(5); pdf.set_font("Arial", "B", 9); pdf.cell(0, 5, "FIRMA DEL CLIENTE (per accettazione clausole)", ln=True)
    pdf.cell(0, 5, f"Data: {datetime.now().strftime('%d/%m/%Y')}", ln=True)
    yf = pdf.get_y(); pdf.cell(80, 20, "", border=1)
    if c.get("firma"):
        try:
            f_data = str(c["firma"]).split(",")[1] if "," in str(c["firma"]) else str(c["firma"])
            pdf.image(io.BytesIO(base64.b64decode(f_data)), x=12, y=yf+1, w=35)
        except: pass
    return bytes(pdf.output(dest="S"))

# --- 3. FATTURA ---
def genera_fattura_completa(c):
    pdf = PDF(); pdf.add_page()
    pdf.set_font("Arial", "B", 14); pdf.cell(0, 10, safe(f"FATTURA N. {c['numero_fattura']}"), ln=True, align="C")
    p = float(c['prezzo']); imp = p/1.22; iva = p-imp
    pdf.set_font("Arial", "", 10)
    pdf.cell(95, 15, safe(f"CLIENTE:\n{c['nome']} {c['cognome']}\n{c['codice_fiscale']}"), 1)
    pdf.cell(95, 15, safe(f"DATA DOC: {datetime.now().strftime('%d/%m/%Y')}\nSDI: {c.get('codice_univoco','0000000')}"), 1, ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", "B", 10); pdf.cell(110, 8, "DESCRIZIONE", 1); pdf.cell(40, 8, "IVA", 1); pdf.cell(40, 8, "TOTALE", 1, ln=True)
    pdf.set_font("Arial", "", 10); pdf.cell(110, 10, safe(f"Noleggio {c['modello']} tg {c['targa']}"), 1); pdf.cell(40, 10, "22%", 1); pdf.cell(40, 10, f"{p:.2f}", 1, ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(0, 6, safe(f"METODO DI PAGAMENTO: {s(c.get('metodo_pagamento', 'NON SPECIFICATO')).upper()}"), ln=True)
    pdf.cell(0, 6, safe(f"STATO PAGAMENTO: {s(c.get('stato_pagamento', 'DA DEFINIRE')).upper()}"), ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", "B", 11); pdf.cell(150, 8, "TOTALE DA PAGARE:", 0, 0, "R"); pdf.cell(40, 8, f"{p:.2f} EUR", 1, ln=True)
    return bytes(pdf.output(dest="S"))

# --- 4. XML ARUBA ---
def genera_xml_fattura(c):
    p_tot = float(c.get('prezzo', 0))
    imp = round(p_tot / 1.22, 2)
    iva = round(p_tot - imp, 2)
    dt = datetime.now().strftime("%Y-%m-%d")
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

# --- INTERFACCIA ---
st.set_page_config(page_title="Battaglia Rent Management", layout="wide")

if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Password", type="password") == "1234":
        if st.button("Accedi"): st.session_state.auth = True; st.rerun()
    st.stop()

t1, t2 = st.tabs(["📝 REGISTRA NOLEGGIO", "📂 ARCHIVIO"])

with t1:
    with st.form("f_new", clear_on_submit=True):
        st.subheader("Anagrafica Cliente")
        c1, c2, c3 = st.columns(3)
        nome, cognome, naz = c1.text_input("Nome"), c2.text_input("Cognome"), c3.text_input("Nazionalità", "Italia")
        c4, c5, c6 = st.columns(3)
        cf, pat_n, tel = c4.text_input("Codice Fiscale"), c5.text_input("N. Patente"), c6.text_input("Telefono")
        c7, c8, c9 = st.columns(3)
        l_nas, d_nas, em = c7.text_input("Luogo Nascita"), c8.text_input("Data Nascita (gg/mm/aaaa)"), c9.text_input("Email/PEC")
        ind = st.text_input("Indirizzo Residenza Completo")
        
        st.subheader("Dati Noleggio e Pagamento")
        n1, n2, n3 = st.columns(3)
        mod, tar, sdi = n1.text_input("Modello"), n2.text_input("Targa").upper(), n3.text_input("Codice SDI", "0000000")
        
        p1, p2, p3 = st.columns(3)
        prezzo = p1.number_input("Prezzo Totale (€)", min_value=0.0)
        metodo = p2.selectbox("Metodo di Pagamento", ["Contanti", "POS", "Bonifico", "Altro"])
        stato = p3.selectbox("Stato Pagamento", ["Saldato", "Acconto", "Da Saldare"])
        
        d1, d2, d3 = st.columns(3)
        ini, fin = d1.date_input("Inizio"), d2.date_input("Fine")
        rif_multa = d3.text_input("Rif. Verbale (Solo per Modulo Vigili)")

        st.subheader("📸 Documenti e Stato Mezzo")
        v_m = st.file_uploader("Video/Foto Danni", type=["mp4","mov","jpg","png"])
        f_p = st.file_uploader("Patente Fronte", type=["jpg","png"])
        r_p = st.file_uploader("Patente Retro", type=["jpg","png"])

        canvas = st_canvas(height=150, width=400, stroke_width=3, key="sig", update_streamlit=True)
        accetto = st.checkbox("Il cliente accetta le clausole e il GDPR.")
        
        if st.form_submit_button("SALVA E GENERA"):
            if not (nome and tar and accetto): st.error("Dati obbligatori mancanti! Compila Nome, Targa e spunta l'accettazione.")
            else:
                num = get_prossimo_numero()
                
                check = supabase.table("contratti").select("id").eq("numero_fattura", num).execute()
                if len(check.data) > 0:
                    st.error("Errore: Numero fattura già esistente nel database. Riprova.")
                else:
                    u_v = upload_media(v_m, tar, "ST")
                    u_f = upload_media(f_p, tar, "F")
                    u_r = upload_media(r_p, tar, "R")
                    
                    img = Image.fromarray(canvas.image_data.astype("uint8"))
                    buf = io.BytesIO(); img.save(buf, format="PNG")
                    f_b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
                    
                    dati = {
                        "nome":nome, "cognome":cognome, "codice_fiscale":cf, "modello":mod, "targa":tar, 
                        "prezzo":prezzo, "numero_fattura":num, "firma":f_b64, "codice_univoco":sdi, 
                        "nazionalita":naz, "inizio":str(ini), "fine":str(fin), "numero_patente":pat_n, 
                        "telefono":tel, "luogo_nascita":l_nas, "data_nascita":d_nas, "pec":em, 
                        "indirizzo_cliente":ind, "metodo_pagamento":metodo, "stato_pagamento":stato,
                        "riferimento_multa": rif_multa, "url_video":u_v, "url_fronte":u_f, "url_retro":u_r
                    }
                    supabase.table("contratti").insert(dati).execute()
                    st.success(f"Noleggio N. {num} salvato con successo!")

with t2:
    search = st.text_input("🔍 Cerca per Cognome o Targa")
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    for idx, r in enumerate(res.data):
        if search.lower() in f"{s(r['cognome'])} {s(r['targa'])}".lower():
            with st.expander(f"📄 N. {r['numero_fattura']} - {r['cognome']} ({r['targa']})"):
                st.write(f"*Tel:* {r.get('telefono')} | *Patente:* {r.get('numero_patente')} | *Pagamento:* {r.get('metodo_pagamento')} ({r.get('stato_pagamento')})")
                st.write(f"*Periodo:* {r['inizio']} / {r['fine']}")
                
                c_m1, c_m2, c_m3 = st.columns(3)
                with c_m1:
                    if r.get('url_video'):
                        if ".mp4" in r['url_video'] or ".mov" in r['url_video']: st.video(r['url_video'])
                        else: st.image(r['url_video'], caption="Danni / Stato Mezzo")
                with c_m2:
                    if r.get('url_fronte'): st.image(r['url_fronte'], caption="Patente Fronte")
                with c_m3:
                    if r.get('url_retro'): st.image(r['url_retro'], caption="Patente Retro")
                
                st.markdown("---")
                b1, b2, b3, b4 = st.columns(4)
                b1.download_button("📜 Contratto", genera_contratto_completo(r), f"Contratto_{idx}.pdf", key=f"c_{idx}")
                b2.download_button("🧾 Fattura", genera_fattura_completa(r), f"Fattura_{idx}.pdf", key=f"f_{idx}")
                b3.download_button("🚨 Modulo Vigili", genera_modulo_vigili(r), f"Vigili_{idx}.pdf", key=f"v_{idx}")
                b4.download_button("📂 XML Aruba", genera_xml_fattura(r), f"IT{PIVA}{idx}.xml", key=f"x{idx}")
