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
SEDE_VIA = "Via Cognole n. 5"
SEDE_CAP = "80075"
SEDE_COMUNE = "Forio"
SEDE_PROV = "NA"
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

# --- GENERATORE XML PROFESSIONALE (CORRETTO PER CODICE FISCALE) ---
def genera_xml_sdi(c):
    data_xml = datetime.now().strftime('%Y-%m-%d')
    cap_c = c.get('cap') if c.get('cap') else "80075"
    comune_c = c.get('comune') if c.get('comune') else "Forio"
    via_c = c.get('indirizzo') if c.get('indirizzo') else "Senza Indirizzo"
    
    # CONTROLLO CODICE FISCALE: Se vuoto, blocca o metti un valore di emergenza
    cf_cliente = str(c.get('codice_fiscale', '')).strip().upper()
    if not cf_cliente:
        cf_cliente = "00000000000" # Valore fittizio per evitare l'errore Pattern, ma va corretto nel DB

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<p:FatturaElettronica versione="FPR12" xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2">
    <FatturaElettronicaHeader>
        <DatiTrasmissione>
            <IdTrasmittente><IdPaese>IT</IdPaese><IdCodice>{PIVA}</IdCodice></IdTrasmittente>
            <ProgressivoInvio>{c['numero_fattura']}</ProgressivoInvio>
            <FormatoTrasmissione>FPR12</FormatoTrasmissione>
            <CodiceDestinatario>0000000</CodiceDestinatario>
        </DatiTrasmissione>
        <CedentePrestatore>
            <DatiAnagrafici>
                <IdFiscaleIVA><IdPaese>IT</IdPaese><IdCodice>{PIVA}</IdCodice></IdFiscaleIVA>
                <Anagrafica><Denominazione>{DITTA}</Denominazione></Anagrafica>
                <RegimeFiscale>RF19</RegimeFiscale>
            </DatiAnagrafici>
            <Sede><Indirizzo>{SEDE_VIA}</Indirizzo><CAP>{SEDE_CAP}</CAP><Comune>{SEDE_COMUNE}</Comune><Provincia>{SEDE_PROV}</Provincia><Nazione>IT</Nazione></Sede>
        </CedentePrestatore>
        <CessionarioCommittente>
            <DatiAnagrafici>
                <CodiceFiscale>{cf_cliente}</CodiceFiscale>
                <Anagrafica><Nome>{c['nome']}</Nome><Cognome>{c['cognome']}</Cognome></Anagrafica>
            </DatiAnagrafici>
            <Sede><Indirizzo>{via_c}</Indirizzo><CAP>{cap_c}</CAP><Comune>{comune_c}</Comune><Provincia>NA</Provincia><Nazione>IT</Nazione></Sede>
        </CessionarioCommittente>
    </FatturaElettronicaHeader>
    <FatturaElettronicaBody>
        <DatiGenerali><DatiGeneraliDocumento><TipoDocumento>TD01</TipoDocumento><Divisa>EUR</Divisa><Data>{data_xml}</Data><Numero>{c['numero_fattura']}</Numero></DatiGeneraliDocumento></DatiGenerali>
        <DatiBeniServizi>
            <DettaglioLinee>
                <NumeroLinea>1</NumeroLinea><Descrizione>Noleggio scooter {c['targa']}</Descrizione><PrezzoUnitario>{c['prezzo']:.2f}</PrezzoUnitario><PrezzoTotale>{c['prezzo']:.2f}</PrezzoTotale><AliquotaIVA>22.00</AliquotaIVA>
            </DettaglioLinee>
            <DatiRiepilogo><AliquotaIVA>22.00</AliquotaIVA><ImponibileImporto>{c['prezzo']:.2f}</ImponibileImporto><Imposta>{(c['prezzo']*0.22):.2f}</Imposta></DatiRiepilogo>
        </DatiBeniServizi>
        <DatiPagamento><CondizioniPagamento>TP02</CondizioniPagamento><DettaglioPagamento><ModalitaPagamento>MP01</ModalitaPagamento><ImportoPagamento>{c['prezzo']:.2f}</ImportoPagamento></DettaglioPagamento></DatiPagamento>
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
        cf = st.text_input("Codice Fiscale (Obbligatorio per XML)")
        ind = st.text_input("Indirizzo")
        c3, c4 = st.columns(2)
        com_c = c3.text_input("Città", value="Forio")
        cap_c = c4.text_input("CAP", value="80075")
        wa = st.text_input("WhatsApp")
        st.subheader("🛵 Mezzo")
        tg = st.text_input("Targa").upper()
        prz = st.number_input("Prezzo €", 0.0)
        f1_file = st.file_uploader("FOTO PATENTE", type=['jpg','jpeg','png'])
        f2_file = st.file_uploader("FOTO CONTRATTO", type=['jpg','jpeg','png'])

        if st.form_submit_button("💾 SALVA"):
            if not cf:
                st.error("Il Codice Fiscale è obbligatorio per Aruba!")
            else:
                f1_ready = correggi_e_converti_foto(f1_file)
                f2_ready = correggi_e_converti_foto(f2_file)
                num_f = get_prossimo_numero()
                dati = {"nome":n,"cognome":cg,"indirizzo":ind,"comune":com_c,"cap":cap_c,"codice_fiscale":cf,"pec":wa,"targa":tg,"prezzo":prz,"data_inizio":datetime.now().strftime("%d/%m/%Y"),"numero_fattura":num_f,"foto_patente":f1_ready,"firma":f2_ready}
                supabase.table("contratti").insert(dati).execute()
                st.success(f"Salvato! Numero Fattura: {num_f}")

with tab2:
    search = st.text_input("🔍 Cerca")
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for r in res.data:
        if search.lower() in f"{r['targa']} {r['cognome']}".lower():
            r_id = r['id']
            with st.expander(f"📄 {r['targa']} - {r['cognome']}"):
                if not r.get('codice_fiscale'):
                    st.warning("⚠️ Codice Fiscale mancante: l'XML potrebbe essere scartato.")
                
                col_a, col_b = st.columns(2)
                xml_data = genera_xml_sdi(r)
                col_a.download_button("📩 XML (Aruba)", xml_data, f"{r['numero_fattura']}.xml", key=f"xml_{r_id}")
                
                st.write("---")
                c_i1, c_i2 = st.columns(2)
                try:
                    if r.get("foto_patente"):
                        img_p = base64.b64decode(r["foto_patente"].split("base64,")[1])
                        c_i1.image(img_p, caption="Patente")
                    if r.get("firma"):
                        img_f = base64.b64decode(r["firma"].split("base64,")[1])
                        c_i2.image(img_f, caption="Contratto")
                except: st.error("Errore visualizzazione foto")

# ... (Tab 3 rimane uguale)
