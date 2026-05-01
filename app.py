import streamlit as st
from supabase import create_client, Client
import base64
from datetime import datetime
from fpdf import FPDF
import io
import urllib.parse
from PIL import Image, ImageOps

# --- CONFIGURAZIONE BATTAGLIA RENT ---
DITTA = "BATTAGLIA RENT"
TITOLARE = "BATTAGLIA MARIANNA"
SEDE = "Via Cognole n. 5 - 80075 Forio (NA)"
PIVA = "10252601215"
CF_TITOLARE = "BTTMNN87A53Z112S"

# Connessione Database
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- FUNZIONI DI UTILITÀ ---
def safe(t): 
    return str(t).encode("latin-1", "replace").decode("latin-1")

def correggi_e_converti_foto(image_file):
    if image_file is not None:
        img = Image.open(image_file)
        img = ImageOps.exif_transpose(img)
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=70)
        return "data:image/jpeg;base64," + base64.b64encode(buffered.getvalue()).decode()
    return None

def get_prossimo_numero():
    try:
        res = supabase.table("contratti").select("numero_fattura").execute()
        nums = [int(r['numero_fattura']) for r in res.data if str(r['numero_fattura']).isdigit()]
        return max(nums) + 1 if nums else 1
    except: return 1

# --- GENERATORE FATTURA DI CORTESIA PDF ---
def genera_cortesia_pdf(c):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, DITTA, ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 5, f"{TITOLARE} - P.IVA {PIVA}", ln=True, align="C")
    pdf.cell(0, 5, safe(SEDE), ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"FATTURA DI CORTESIA N. {c['numero_fattura']}", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 7, f"Data: {c['data_inizio']}", ln=True)
    pdf.cell(0, 7, safe(f"Cliente: {c['nome']} {c['cognome']}"), ln=True)
    pdf.cell(0, 7, f"Codice Fiscale: {c['codice_fiscale']}", ln=True)
    pdf.ln(5)
    pdf.cell(140, 10, "DESCRIZIONE", 1)
    pdf.cell(50, 10, "PREZZO", 1, ln=True)
    pdf.cell(140, 10, safe(f"Noleggio scooter targa {c['targa']}"), 1)
    pdf.cell(50, 10, f"Euro {c['prezzo']:.2f}", 1, ln=True)
    pdf.ln(10)
    pdf.set_font("Arial", "I", 8)
    pdf.multi_cell(0, 5, "Documento non valido ai fini fiscali. La fattura elettronica ufficiale sara' trasmessa al Sistema di Interscambio.")
    return bytes(pdf.output(dest="S"))

# --- GENERATORE MODULO RINOTIFICA (IDENTICO A TUA FOTO) ---
def genera_rinotifica_pdf(c, v):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Times", "", 11)
    pdf.set_xy(110, 20)
    pdf.cell(0, 5, "Spett. le", ln=True)
    pdf.set_x(110)
    pdf.set_font("Times", "B", 11)
    pdf.cell(0, 5, safe(f"Polizia Locale di {v['comune']}"), ln=True)
    pdf.ln(15)
    pdf.set_font("Times", "B", 10)
    pdf.cell(20, 5, "OGGETTO:")
    pdf.set_font("Times", "", 10)
    pdf.cell(0, 5, f"RIFERIMENTO VS. ACCERTAMENTO VIOLAZIONE N. {v['num']} PROT. {v['prot']}")
    pdf.ln(10)
    testo = f"""In riferimento al Verbale di accertamento di infrazione al Codice della strada di cui all'oggetto, la sottoscritta BATTAGLIA MARIANNA nata a Berlino (Germania) il 13/01/1987 e residente in Forio alla Via Cognole n. 5 in qualita' di titolare dell'omonima ditta individuale, C.F.: {CF_TITOLARE} e P.IVA: {PIVA}
    
    DICHIARA
Ai sensi della L. 445/2000 che il veicolo modello {c['modello']} targato {c['targa']} il giorno {v['data']} era concesso in locazione senza conducente al signor:

COGNOME E NOME: {c['cognome'].upper()} {c['nome'].upper()}
LUOGO E DATA DI NASCITA: {c.get('luogo_nascita', '-').upper()} {c.get('data_nascita', '-')}
RESIDENZA: {c.get('indirizzo', '-').upper()}
IDENTIFICATO A MEZZO: Patente di Guida"""
    pdf.multi_cell(0, 6, safe(testo))
    pdf.ln(20)
    pdf.set_x(130); pdf.cell(0, 5, "In fede", ln=True, align="C")
    pdf.set_x(130); pdf.cell(0, 5, "Marianna Battaglia", ln=True, align="C")
    return bytes(pdf.output(dest="S"))

# --- GENERATORE XML SDI ---
def genera_xml_sdi(c):
    data_xml = datetime.now().strftime('%Y-%m-%d')
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<p:FatturaElettronica versione="FPR12" xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2">
    <FatturaElettronicaHeader>
        <CedentePrestatore><DatiAnagrafici><IdFiscaleIVA><IdPaese>IT</IdPaese><IdCodice>{PIVA}</IdCodice></IdFiscaleIVA><Anagrafica><Denominazione>{DITTA}</Denominazione></Anagrafica><RegimeFiscale>RF19</RegimeFiscale></DatiAnagrafici></CedentePrestatore>
        <CessionarioCommittente><DatiAnagrafici><IdFiscaleIVA><IdPaese>IT</IdPaese><IdCodice>{c['codice_fiscale']}</IdCodice></IdFiscaleIVA><Anagrafica><Nome>{c['nome']}</Nome><Cognome>{c['cognome']}</Cognome></Anagrafica></DatiAnagrafici></CessionarioCommittente>
    </FatturaElettronicaHeader>
    <FatturaElettronicaBody>
        <DatiGenerali><DatiGeneraliDocumento><TipoDocumento>TD01</TipoDocumento><Divisa>EUR</Divisa><Data>{data_xml}</Data><Numero>{c['numero_fattura']}</Numero><ImportoTotaleDocumento>{c['prezzo']:.2f}</ImportoTotaleDocumento></DatiGeneraliDocumento></DatiGenerali>
        <DatiBeniServizi><DettaglioLinee><NumeroLinea>1</NumeroLinea><Descrizione>Noleggio scooter {c['targa']}</Descrizione><PrezzoUnitario>{c['prezzo']:.2f}</PrezzoUnitario><PrezzoTotale>{c['prezzo']:.2f}</PrezzoTotale><AliquotaIVA>22.00</AliquotaIVA></DettaglioLinee></DatiBeniServizi>
    </FatturaElettronicaBody>
</p:FatturaElettronica>"""
    return xml.encode('utf-8')

# --- INTERFACCIA APP ---
st.set_page_config(page_title="BATTAGLIA RENT", layout="centered")

if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    pwd = st.text_input("Password Accesso", type="password")
    if st.button("ACCEDI"):
        if pwd == "1234": st.session_state.auth = True; st.rerun()
    st.stop()

tab1, tab2, tab3 = st.tabs(["📝 NUOVO", "📂 ARCHIVIO", "🚨 MULTE"])

with tab1:
    with st.form("registrazione"):
        st.subheader("👤 Dati Cliente")
        c1, c2 = st.columns(2)
        n = c1.text_input("Nome")
        cg = c2.text_input("Cognome")
        ln = st.text_input("Luogo Nascita")
        dn = st.text_input("Data Nascita (GG/MM/AAAA)")
        ind = st.text_input("Indirizzo Residenza")
        cf = st.text_input("Codice Fiscale")
        wa = st.text_input("WhatsApp (es. 39333...)")
        st.subheader("🛵 Mezzo")
        tg = st.text_input("Targa").upper()
        mod = st.text_input("Modello")
        prz = st.number_input("Prezzo Totale €", 0.0)
        st.subheader("📸 Foto Documenti")
        f1_file = st.file_uploader("FOTO PATENTE", type=['jpg','jpeg','png'])
        f2_file = st.file_uploader("FOTO CONTRATTO FIRMATO", type=['jpg','jpeg','png'])

        if st.form_submit_button("💾 SALVA NOLEGGIO"):
            if not n or not tg or not f2_file:
                st.error("Mancano dati obbligatori (Nome, Targa o Foto Contratto)!")
            else:
                with st.spinner("Elaborazione foto..."):
                    f1_ready = correggi_e_converti_foto(f1_file)
                    f2_ready = correggi_e_converti_foto(f2_file)
                    num_f = get_prossimo_numero()
                    dati = {"nome":n,"cognome":cg,"luogo_nascita":ln,"data_nascita":dn,"indirizzo":ind,"codice_fiscale":cf,"pec":wa,"modello":mod,"targa":tg,"prezzo":prz,"data_inizio":datetime.now().strftime("%d/%m/%Y"),"numero_fattura":num_f,"foto_patente":f1_ready,"firma":f2_ready}
                    supabase.table("contratti").insert(dati).execute()
                    st.success(f"Archiviato con successo! Fattura N. {num_f}")

with tab2:
    search = st.text_input("🔍 Cerca per Targa o Cognome")
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for r in res.data:
        if search.lower() in f"{r['targa']} {r['cognome']}".lower():
            r_id = r['id']
            with st.expander(f"📄 {r['targa']} - {r['cognome']}"):
                st.write(f"Fattura N. {r['numero_fattura']} del {r['data_inizio']}")
                
                c_btn1, c_btn2 = st.columns(2)
                
                # XML per Aruba (con KEY UNICA)
                xml_data = genera_xml_sdi(r)
                c_btn1.download_button(
                    label="📩 XML (Aruba)", 
                    data=xml_data, 
                    file_name=f"{r['numero_fattura']}.xml",
                    key=f"xml_{r_id}"
                )
                
                # PDF Cortesia (con KEY UNICA)
                pdf_c = genera_cortesia_pdf(r)
                c_btn2.download_button(
                    label="📄 PDF CORTESIA", 
                    data=pdf_c, 
                    file_name=f"Fattura_{r['cognome']}.pdf",
                    key=f"pdf_{r_id}"
                )
                
                st.write("---")
                # Foto
                c_i1, c_i2 = st.columns(2)
                try:
                    if r.get("foto_patente"):
                        img_p = base64.b64decode(r["foto_patente"].split("base64,")[1])
                        c_i1.image(img_p, caption="Patente")
                    if r.get("firma"):
                        img_f = base64.b64decode(r["firma"].split("base64,")[1])
                        c_i2.image(img_f, caption="Contratto")
                except: st.error("Impossibile visualizzare le foto.")

with tab3:
    st.subheader("🚨 Gestione Multe / Rinotifica")
    tg_m = st.text_input("Targa del mezzo multato").upper()
    v_c = st.text_input("Polizia Locale di (es. Serrara Fontana)")
    v_d = st.text_input("Data Infrazione (GG/MM/AAAA)")
    v_n = st.text_input("Verbale N.")
    v_p = st.text_input("Prot.")
    
    if st.button("📄 GENERA MODULO VIGILI"):
        db_res = supabase.table("contratti").select("*").eq("targa", tg_m).order("id", desc=True).execute()
        if db_res.data:
            cliente = db_res.data[0]
            pdf_v = genera_rinotifica_pdf(cliente, {"comune":v_c,"data":v_d,"num":v_n,"prot":v_p})
            st.download_button("📩 SCARICA MODULO PRONTO", pdf_v, f"Rinotifica_{tg_m}.pdf")
        else: 
            st.error("Nessun noleggio trovato per questa targa.")
