import streamlit as st
from supabase import create_client, Client
import base64
from datetime import datetime
from fpdf import FPDF
import io
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
        try:
            img = Image.open(image_file)
            img = ImageOps.exif_transpose(img)
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG", quality=70)
            return "data:image/jpeg;base64," + base64.b64encode(buffered.getvalue()).decode()
        except Exception:
            return None
    return None

def get_prossimo_numero():
    try:
        res = supabase.table("contratti").select("numero_fattura").execute()
        nums = [int(r['numero_fattura']) for r in res.data if str(r['numero_fattura']).isdigit()]
        return max(nums) + 1 if nums else 1
    except: return 1

# --- GENERATORE XML ---
def genera_xml_sdi(c):
    data_xml = datetime.now().strftime('%Y-%m-%d')
    cap_c = c.get('cap') if c.get('cap') else "80075"
    comune_c = c.get('comune') if c.get('comune') else "Forio"
    via_c = c.get('indirizzo') if c.get('indirizzo') else "Senza Indirizzo"
    cf_cliente = str(c.get('codice_fiscale', '')).strip().upper()
    if not cf_cliente: cf_cliente = "00000000000"

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<p:FatturaElettronica versione="FPR12" xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2">
    <FatturaElettronicaHeader>
        <DatiTrasmissione>
            <IdTrasmittente><IdPaese>IT</IdPaese><IdCodice>01879020517</IdCodice></IdTrasmittente>
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

# --- GENERATORE MODULO MULTE ---
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
    testo = f"""In riferimento al Verbale in oggetto, la sottoscritta BATTAGLIA MARIANNA nata a Berlino (Germania) il 13/01/1987 e residente in Forio alla Via Cognole n. 5 in qualita' di titolare della ditta {DITTA}, P.IVA {PIVA}, DICHIARA che il veicolo modello {c.get('modello', 'Scooter')} targato {c['targa']} il giorno {v['data']} era locato a:

COGNOME E NOME: {c['cognome'].upper()} {c['nome'].upper()}
NATO A: {c.get('luogo_nascita', '-').upper()} IL {c.get('data_nascita', '-')}
RESIDENZA: {c.get('indirizzo', '-').upper()} ({c.get('comune', '-').upper()})
CODICE FISCALE: {c['codice_fiscale'].upper()}"""
    pdf.multi_cell(0, 6, safe(testo))
    pdf.ln(20); pdf.set_x(130); pdf.cell(0, 5, "In fede, Marianna Battaglia", align="C")
    return bytes(pdf.output(dest="S"))

# --- APP ---
st.set_page_config(page_title="BATTAGLIA RENT", layout="centered")

if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    pwd = st.text_input("Password", type="password")
    if st.button("ACCEDI"):
        if pwd == "1234": st.session_state.auth = True; st.rerun()
    st.stop()

tab1, tab2, tab3 = st.tabs(["📝 NUOVO", "📂 ARCHIVIO", "🚨 MULTE"])

with tab1:
    with st.form("reg"):
        st.subheader("👤 Cliente")
        c1, c2 = st.columns(2)
        n, cg = c1.text_input("Nome"), c2.text_input("Cognome")
        cf = st.text_input("Codice Fiscale")
        ln, dn = c1.text_input("Luogo Nascita"), c2.text_input("Data Nascita")
        ind = st.text_input("Indirizzo")
        com_c, cap_c = c1.text_input("Città", "Forio"), c2.text_input("CAP", "80075")
        wa = st.text_input("WhatsApp")
        st.subheader("🛵 Mezzo")
        tg, mod = c1.text_input("Targa").upper(), c2.text_input("Modello")
        prz = st.number_input("Prezzo €", 0.0)
        f1, f2 = st.file_uploader("FOTO PATENTE"), st.file_uploader("FOTO CONTRATTO")

        if st.form_submit_button("💾 SALVA"):
            num_f = get_prossimo_numero()
            dati = {"nome":n,"cognome":cg,"codice_fiscale":cf,"indirizzo":ind,"comune":com_c,"cap":cap_c,"luogo_nascita":ln,"data_nascita":dn,"targa":tg,"modello":mod,"prezzo":prz,"pec":wa,"numero_fattura":num_f,"data_inizio":datetime.now().strftime("%d/%m/%Y"),"foto_patente":correggi_e_converti_foto(f1),"firma":correggi_e_converti_foto(f2)}
            supabase.table("contratti").insert(dati).execute()
            st.success(f"Archiviato! Fattura {num_f}")

with tab2:
    search = st.text_input("🔍 Cerca")
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for r in res.data:
        if search.lower() in f"{r['targa']} {r['cognome']}".lower():
            with st.expander(f"📄 {r['targa']} - {r['cognome']}"):
                st.download_button("📩 XML (Aruba)", genera_xml_sdi(r), f"{r['numero_fattura']}.xml", key=f"x_{r['id']}")
                c_i1, c_i2 = st.columns(2)
                
                # PROTEZIONE CONTRO IMMAGINI CORROTTE
                for key, col in [("foto_patente", c_i1), ("firma", c_i2)]:
                    img_str = r.get(key)
                    if img_str and "base64," in img_str:
                        try:
                            img_data = base64.b64decode(img_str.split("base64,")[1])
                            col.image(img_data, use_container_width=True)
                        except Exception:
                            col.warning(f"{key} non leggibile")
                    else:
                        col.info(f"{key} mancante")

with tab3:
    st.subheader("🚨 Multe")
    tg_m = st.text_input("Targa").upper()
    v_c, v_d = st.text_input("Comune Polizia"), st.text_input("Data Infrazione")
    v_n, v_p = st.text_input("Verbale N."), st.text_input("Prot.")
    if st.button("📄 GENERA MODULO"):
        db = supabase.table("contratti").select("*").eq("targa", tg_m).order("id", desc=True).execute()
        if db.data: st.download_button("📩 SCARICA", genera_rinotifica_pdf(db.data[0],{"comune":v_c,"data":v_d,"num":v_n,"prot":v_p}), f"Multe_{tg_m}.pdf")
        else: st.error("Targa non trovata")
