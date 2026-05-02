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

# --- GENERATORE XML PROFESSIONALE (PER ARUBA) ---
def genera_xml_sdi(c):
    data_xml = datetime.now().strftime('%Y-%m-%d')
    cap_c = c.get('cap') if c.get('cap') else "80075"
    comune_c = c.get('comune') if c.get('comune') else "Forio"
    via_c = c.get('indirizzo') if c.get('indirizzo') else "Senza Indirizzo"
    cf_cliente = str(c.get('codice_fiscale', '')).strip().upper()
    
    if not cf_cliente or cf_cliente == "XXXXXXXXXXXXXXXX":
        cf_valido = "00000000000"
    else:
        cf_valido = cf_cliente

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
                <CodiceFiscale>{cf_valido}</CodiceFiscale>
                <Anagrafica><Nome>{c['nome']}</Nome><Cognome>{c['cognome']}</Cognome></Anagrafica>
            </DatiAnagrafici>
            <Sede><Indirizzo>{via_c}</Indirizzo><CAP>{cap_c if cf_cliente != "XXXXXXXXXXXXXXXX" else "00000"}</CAP><Comune>{comune_c}</Comune><Provincia>NA</Provincia><Nazione>IT</Nazione></Sede>
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

# --- GENERATORE FATTURA DI CORTESIA (PDF PER CLIENTE) ---
def genera_cortesia_pdf(c):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, DITTA, ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 5, f"{SEDE_VIA} - {SEDE_CAP} {SEDE_COMUNE}", ln=True, align="C")
    pdf.cell(0, 5, f"P.IVA: {PIVA}", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"RICEVUTA DI CORTESIA N. {c['numero_fattura']}", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 7, f"Data: {c['data_inizio']}", ln=True)
    pdf.cell(0, 7, f"Cliente: {c['nome']} {c['cognome']}", ln=True)
    pdf.cell(0, 7, f"Codice Fiscale: {c['codice_fiscale']}", ln=True)
    pdf.ln(5)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(140, 10, "Descrizione", 1, 0, "L", True)
    pdf.cell(50, 10, "Importo", 1, 1, "R", True)
    pdf.cell(140, 10, f"Noleggio Scooter targa {c['targa']}", 1)
    pdf.cell(50, 10, f"Euro {c['prezzo']:.2f}", 1, 1, "R")
    pdf.ln(10)
    pdf.set_font("Arial", "I", 9)
    pdf.multi_cell(0, 5, "La presente non costituisce fattura valida ai fini fiscali. La fattura elettronica ufficiale sara' inviata tramite il Sistema di Interscambio.")
    return bytes(pdf.output(dest="S"))

# --- GENERATORE MODULO RINOTIFICA MULTE ---
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

# --- INTERFACCIA APP ---
st.set_page_config(page_title="BATTAGLIA RENT", layout="centered")

if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    pwd = st.text_input("Password", type="password")
    if st.button("ACCEDI"):
        if pwd == "1234":
            st.session_state.auth = True
            st.rerun()
    st.stop()

tab1, tab2, tab3 = st.tabs(["📝 NUOVO", "📂 ARCHIVIO", "🚨 MULTE"])

with tab1:
    with st.form("reg"):
        st.subheader("👤 Cliente")
        c1, c2 = st.columns(2)
        n, cg = c1.text_input("Nome"), c2.text_input("Cognome")
        cf = st.text_input("Codice Fiscale (o 16 'X' per stranieri)")
        ln, dn = c1.text_input("Luogo Nascita"), c2.text_input("Data Nascita")
        ind = st.text_input("Indirizzo")
        com_c, cap_c = c1.text_input("Città", "Forio"), c2.text_input("CAP", "80075")
        wa = st.text_input("WhatsApp (es: 39333123456)")
        st.subheader("🛵 Mezzo")
        tg, mod = c1.text_input("Targa").upper(), c2.text_input("Modello")
        prz = st.number_input("Prezzo €", 0.0)
        f1, f2 = st.file_uploader("FOTO PATENTE"), st.file_uploader("FOTO CONTRATTO")

        if st.form_submit_button("💾 SALVA"):
            num_f = get_prossimo_numero()
            dati = {"nome":n,"cognome":cg,"codice_fiscale":cf,"indirizzo":ind,"comune":com_c,"cap":cap_c,"luogo_nascita":ln,"data_nascita":dn,"targa":tg,"modello":mod,"prezzo":prz,"pec":wa,"numero_fattura":num_f,"data_inizio":datetime.now().strftime("%d/%m/%Y"),"foto_patente":correggi_e_converti_foto(f1),"firma":correggi_e_converti_foto(f2)}
            supabase.table("contratti").insert(dati).execute()
            st.success(f"Archiviato con successo! Fattura {num_f}")

with tab2:
    search = st.text_input("🔍 Cerca per Targa o Cognome")
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for r in res.data:
        if search.lower() in f"{r['targa']} {r['cognome']}".lower():
            with st.expander(f"📄 {r['targa']} - {r['cognome']}"):
                
                col_a, col_b, col_c = st.columns(3)
                
                # Download XML per Aruba
                xml_data = genera_xml_sdi(r)
                col_a.download_button("📩 XML Aruba", xml_data, f"{r['numero_fattura']}.xml", key=f"x_{r['id']}")
                
                # Download PDF Cortesia
                pdf_c = genera_cortesia_pdf(r)
                col_b.download_button("📄 PDF Cliente", pdf_c, f"Ricevuta_{r['targa']}.pdf", key=f"p_{r['id']}")
                
                # Tasto WhatsApp
                num_wa = ''.join(filter(str.isdigit, str(r.get('pec', ''))))
                msg = urllib.parse.quote(f"Ciao {r['nome']}, ecco la ricevuta del tuo noleggio {DITTA}. Grazie!")
                col_c.link_button("💬 Chat WA", f"https://wa.me/{num_wa}?text={msg}")

                st.write("---")
                c_i1, c_i2 = st.columns(2)
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
    st.subheader("🚨 Gestione Multe")
    tg_m = st.text_input("Inserisci Targa").upper()
    v_c, v_d = st.text_input("Comune Polizia"), st.text_input("Data Infrazione")
    v_n, v_p = st.text_input("Verbale N."), st.text_input("Prot.")
    if st.button("📄 GENERA MODULO RINOTIFICA"):
        db = supabase.table("contratti").select("*").eq("targa", tg_m).order("id", desc=True).execute()
        if db.data:
            pdf_v = genera_rinotifica_pdf(db.data[0], {"comune":v_c,"data":v_d,"num":v_n,"prot":v_p})
            st.download_button("📩 SCARICA MODULO", pdf_v, f"Rinotifica_{tg_m}.pdf")
        else:
            st.error("Targa non trovata in archivio!")
