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

# --- GENERATORE MODULO RINOTIFICA (IDENTICO A TUA FOTO) ---
def genera_rinotifica_pdf(c, v):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Times", "", 11)
    pdf.set_xy(110, 20)
    pdf.cell(0, 5, "Spett. le", ln=True)
    pdf.set_x(110)
    pdf.set_font("Times", "B", 11)
    pdf.cell(0, 5, f"Polizia Locale di {v['comune']}", ln=True)
    pdf.ln(15)
    pdf.set_font("Times", "B", 10)
    pdf.cell(20, 5, "OGGETTO:")
    pdf.set_font("Times", "", 10)
    pdf.cell(0, 5, f"RIFERIMENTO VS. ACCERTAMENTO VIOLAZIONE N. {v['num']} PROT. {v['prot']}")
    pdf.ln(10)
    testo = f"""In riferimento al Verbale... la sottoscritta BATTAGLIA MARIANNA nata a Berlino (Germania) il 13/01/1987 e residente in Forio alla Via Cognole n. 5 in qualita' di titolare dell'omonima ditta individuale, C.F.: {CF_TITOLARE} e P.IVA: {PIVA}
    
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
    pwd = st.text_input("Password", type="password")
    if st.button("ACCEDI"):
        if pwd == "1234": st.session_state.auth = True; st.rerun()
    st.stop()

tab1, tab2, tab3 = st.tabs(["📝 NUOVO", "📂 ARCHIVIO", "🚨 MULTE"])

with tab1:
    with st.form("registrazione"):
        st.subheader("👤 Cliente")
        c1, c2 = st.columns(2)
        n = c1.text_input("Nome")
        cg = c2.text_input("Cognome")
        ln = st.text_input("Luogo Nascita")
        dn = st.text_input("Data Nascita")
        ind = st.text_input("Indirizzo Residenza")
        cf = st.text_input("Codice Fiscale")
        wa = st.text_input("WhatsApp (es. 39333...)")
        st.subheader("🛵 Mezzo")
        tg = st.text_input("Targa").upper()
        mod = st.text_input("Modello")
        prz = st.number_input("Prezzo €", 0.0)
        st.subheader("📸 Foto")
        f1_file = st.file_uploader("FOTO PATENTE", type=['jpg','jpeg','png'])
        f2_file = st.file_uploader("FOTO CONTRATTO", type=['jpg','jpeg','png'])

        if st.form_submit_button("💾 SALVA"):
            if not n or not tg or not f2_file:
                st.error("Mancano dati o foto contratto!")
            else:
                f1_ready = correggi_e_converti_foto(f1_file)
                f2_ready = correggi_e_converti_foto(f2_file)
                num_f = get_prossimo_numero()
                dati = {"nome":n,"cognome":cg,"luogo_nascita":ln,"data_nascita":dn,"indirizzo":ind,"codice_fiscale":cf,"pec":wa,"modello":mod,"targa":tg,"prezzo":prz,"data_inizio":datetime.now().strftime("%d/%m/%Y"),"numero_fattura":num_f,"foto_patente":f1_ready,"firma":f2_ready}
                supabase.table("contratti").insert(dati).execute()
                st.success(f"Salvato! Fattura {num_f}")

with tab2:
    search = st.text_input("🔍 Cerca")
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for r in res.data:
        if search.lower() in f"{r['targa']} {r['cognome']}".lower():
            with st.expander(f"📄 {r['targa']} - {r['cognome']}"):
                col_a, col_b = st.columns(2)
                xml_data = genera_xml_sdi(r)
                col_a.download_button("📩 SCARICA XML (Aruba)", xml_data, f"{r['numero_fattura']}.xml")
                
                # Visualizzazione foto con correzione errore
                st.write("---")
                c_i1, c_i2 = st.columns(2)
                try:
                    if r.get("foto_patente"):
                        img_p = base64.b64decode(r["foto_patente"].split("base64,")[1])
                        c_i1.image(img_p, caption="Patente")
                    if r.get("firma"):
                        img_f = base64.b64decode(r["firma"].split("base64,")[1])
                        c_i2.image(img_f, caption="Contratto")
                except: st.error("Errore foto")

with tab3:
    st.subheader("🚨 Crea Rinotifica")
    tg_m = st.text_input("Targa mezzo multato").upper()
    v_c = st.text_input("Polizia Locale di...")
    v_d = st.text_input("Data Infrazione")
    v_n = st.text_input("Verbale N.")
    v_p = st.text_input("Prot.")
    if st.button("📄 GENERA MODULO"):
        db_res = supabase.table("contratti").select("*").eq("targa", tg_m).execute()
        if db_res.data:
            pdf_v = genera_rinotifica_pdf(db_res.data[0], {"comune":v_c,"data":v_d,"num":v_n,"prot":v_p})
            st.download_button("📩 SCARICA PDF", pdf_v, f"Rinotifica_{tg_m}.pdf")
        else: st.error("Targa non trovata!")
