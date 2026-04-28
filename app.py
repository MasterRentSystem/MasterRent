import streamlit as st
from supabase import create_client, Client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from fpdf import FPDF
import io
import base64
import random
from datetime import datetime
import xml.etree.ElementTree as ET

# --- CONFIGURAZIONE BATTAGLIA RENT ---
DITTA = "BATTAGLIA RENT"
TITOLARE = "BATTAGLIA MARIANNA"
PIVA = "10252601215"
CF_DITTA = "BTTMNN87A53Z112S"
SEDE = "Via Cognole n. 5 - 80075 Forio (NA)"

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

# --- 1. GENERATORE FATTURA XML ---
def genera_xml_fattura(c):
    root = ET.Element("p:FatturaElettronica", {"versione": "FPR12", "xmlns:p": "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"})
    body = ET.SubElement(root, "FatturaElettronicaBody")
    dati_gen = ET.SubElement(body, "DatiGenerali")
    d_dg = ET.SubElement(dati_gen, "DatiGeneraliDocumento")
    ET.SubElement(d_dg, "TipoDocumento").text = "TD01"
    ET.SubElement(d_dg, "Data").text = datetime.now().strftime("%Y-%m-%d")
    ET.SubElement(d_dg, "Numero").text = f"{c.get('numero_fattura')}"
    ET.SubElement(d_dg, "ImportoTotaleDocumento").text = f"{c.get('prezzo', 0):.2f}"
    return ET.tostring(root, encoding='utf-8', method='xml')

# --- 2. GENERATORE MODULO MULTE ---
def genera_modulo_multe(c):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "DICHIARAZIONE DI RESPONSABILITA' E MULTE", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Arial", "", 10)
    testo = f"""Il sottoscritto {c.get('nome')} {c.get('cognome')}, nato a {c.get('luogo_nascita')} il {c.get('data_nascita')},
relativamente al noleggio del mezzo {c.get('modello')} targa {c.get('targa')}, 
DICHIARA di assumersi ogni responsabilità civile e penale per infrazioni al Codice della Strada 
commesse durante il periodo di noleggio (dal {c.get('data_inizio')} al {c.get('data_fine')}).

Il cliente AUTORIZZA BATTAGLIA RENT al recupero delle somme e alla comunicazione dei dati 
alle autorità competenti, con l'addebito di una spesa di gestione pratica pari a Euro 25,83 
per ogni singolo verbale notificato.
    """
    pdf.multi_cell(0, 6, safe(testo), border=1)
    pdf.ln(10)
    pdf.cell(0, 5, "Firma del Cliente per accettazione specifica delle clausole multe:", ln=True)
    try:
        if c.get("firma2"):
            f2 = str(c["firma2"]).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(f2)), x=10, y=pdf.get_y()+2, w=50)
    except: pass
    return bytes(pdf.output(dest="S"))

# --- 3. CONTRATTO (SENZA FOTO) ---
class PDF_Contratto(FPDF):
    def header(self):
        self.set_font("Arial", "B", 10); self.cell(0, 5, DITTA, ln=True)
        self.set_font("Arial", "", 7); self.cell(0, 4, f"{SEDE} | P.IVA: {PIVA}", ln=True); self.ln(2)

def genera_pdf_contratto(c):
    pdf = PDF_Contratto()
    pdf.add_page()
    w = pdf.epw
    pdf.set_font("Arial", "B", 12); pdf.cell(0, 7, safe(f"CONTRATTO DI LOCAZIONE N. {c.get('numero_fattura')}"), ln=True, align="C")
    
    pdf.set_font("Arial", "B", 8); pdf.set_fill_color(230, 230, 230)
    pdf.cell(w, 5, " DATI CLIENTE", 1, 1, fill=True)
    pdf.set_font("Arial", "", 7)
    pdf.cell(w/2, 5, safe(f"Nome: {c.get('nome')} {c.get('cognome')}"), 1)
    pdf.cell(w/2, 5, safe(f"Codice Fiscale: {c.get('codice_fiscale')}"), 1, 1)
    pdf.cell(w/3, 5, safe(f"Nato a: {c.get('luogo_nascita')}"), 1)
    pdf.cell(w/3, 5, safe(f"Data: {c.get('data_nascita')}"), 1)
    pdf.cell(w/3, 5, safe(f"Patente: {c.get('numero_patente')}"), 1, 1)
    pdf.cell(w, 5, safe(f"Indirizzo: {c.get('indirizzo')}"), 1, 1)

    pdf.ln(1); pdf.set_font("Arial", "B", 8); pdf.cell(w, 5, " DETTAGLI NOLEGGIO", 1, 1, fill=True)
    pdf.set_font("Arial", "", 7)
    pdf.cell(w/4, 5, safe(f"Mezzo: {c.get('modello')}"), 1)
    pdf.cell(w/4, 5, safe(f"Targa: {c.get('targa')}"), 1)
    pdf.cell(w/4, 5, safe(f"Inizio: {c.get('data_inizio')} {c.get('ora_inizio')}"), 1)
    pdf.cell(w/4, 5, safe(f"Fine: {c.get('data_fine')} {c.get('ora_fine')}"), 1, 1)
    
    pdf.ln(5); pdf.set_font("Arial", "B", 8); pdf.cell(0, 5, "FIRMA DEL CLIENTE", ln=True)
    try:
        if c.get("firma"):
            f1 = str(c["firma"]).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(f1)), x=10, y=pdf.get_y(), w=40)
    except: pass
    return bytes(pdf.output(dest="S"))

# --- INTERFACCIA ---
st.set_page_config(page_title="BATTAGLIA RENT", layout="wide")

if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Password", type="password") == "1234":
        if st.button("ACCEDI"): st.session_state.auth = True; st.rerun()
    st.stop()

tab1, tab2 = st.tabs(["📝 NUOVO", "📂 ARCHIVIO"])

with tab1:
    with st.form("main_form"):
        st.subheader("👤 ANAGRAFICA")
        c1, c2, c3 = st.columns(3)
        nome = c1.text_input("Nome")
        cognome = c2.text_input("Cognome")
        cf = c3.text_input("Codice Fiscale")
        
        c4, c5, c6 = st.columns(3)
        l_nas = c4.text_input("Luogo di Nascita")
        d_nas = c5.text_input("Data di Nascita")
        naz = c6.text_input("Nazionalità")
        
        c7, c8, c9 = st.columns(3)
        ind = c7.text_input("Indirizzo")
        eml = c8.text_input("Email")
        sdi = c9.text_input("Codice SDI", "0000000")

        st.subheader("🛵 NOLEGGIO")
        m1, m2, m3, m4 = st.columns(4)
        mod = m1.text_input("Modello")
        targa = m2.text_input("Targa").upper()
        pat = m3.text_input("N. Patente")
        wa = m4.text_input("WhatsApp")

        d1, d2, d3, d4 = st.columns(4)
        di, oi = d1.date_input("Data Inizio"), d2.time_input("Ora Inizio")
        df, of = d3.date_input("Data Fine"), d4.time_input("Ora Fine")

        st.subheader("💰 PAGAMENTO")
        p1, p2, p3, p4 = st.columns(4)
        prz = p1.number_input("Prezzo (€)", 0.0)
        met = p2.selectbox("Metodo", ["Contanti", "Carta", "Bonifico"])
        sta = p3.selectbox("Stato", ["Pagato", "Da Pagare"])
        rif = p4.text_input("Riferimento Multa")
        vid = st.text_input("URL Video")

        st.subheader("📸 FOTO")
        f1, f2 = st.columns(2)
        f_p = f1.camera_input("Foto Patente")
        f_m = f2.camera_input("Foto Mezzo")
        
        st.subheader("🖋️ FIRME")
        s1, s2 = st.columns(2)
        with s1: can1 = st_canvas(height=100, width=380, stroke_width=1, key="c1")
        with s2: can2 = st_canvas(height=100, width=380, stroke_width=1, key="c2")

        if st.form_submit_button("SALVA E GENERA"):
            def b64(f): return "data:image/png;base64," + base64.b64encode(f.getvalue()).decode() if f else ""
            def cnv(c):
                if c.image_data is not None:
                    img = Image.fromarray(c.image_data.astype("uint8"))
                    buf = io.BytesIO(); img.save(buf, format="PNG")
                    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
                return ""
            
            st.session_state.temp = {
                "nome": nome, "cognome": cognome, "codice_fiscale": cf, "luogo_nascita": l_nas,
                "data_nascita": d_nas, "nazionalita": naz, "indirizzo": ind, "email": eml, "codice_sdi": sdi,
                "modello": mod, "targa": targa, "numero_patente": pat, "pec": wa,
                "data_inizio": di.strftime("%d/%m/%Y"), "ora_inizio": oi.strftime("%H:%M"),
                "data_fine": df.strftime("%d/%m/%Y"), "ora_fine": of.strftime("%H:%M"),
                "prezzo": prz, "metodo_pagamento": met, "stato_pagamento": sta, "riferimento_multa": rif,
                "video_url": vid, "foto_patente": b64(f_p), "foto_mezzo": b64(f_m), "firma": cnv(can1), "firma2": cnv(can2)
            }
            st.warning("Dati pronti. Inserisci un codice a tua scelta per confermare l'archiviazione.")

    if "temp" in st.session_state:
        conf = st.text_input("Conferma Salvataggio (scrivi 'OK')")
        if st.button("ARCHIVIA ORA"):
            if conf.upper() == "OK":
                st.session_state.temp["numero_fattura"] = get_prossimo_numero()
                supabase.table("contratti").insert(st.session_state.temp).execute()
                st.success("✅ ARCHIVIATO!")
                del st.session_state.temp
            else: st.error("Scrivi OK")

with tab2:
    q = st.text_input("🔍 Cerca")
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    for r in res.data:
        if q.lower() in f"{s(r['cognome'])} {s(r['targa'])}".lower():
            with st.expander(f"📁 {r['numero_fattura']} - {r['cognome']} ({r['targa']})"):
                c1, c2, c3 = st.columns(3)
                c1.download_button("📜 CONTRATTO", genera_pdf_contratto(r), f"C_{r['id']}.pdf", key=f"c_{r['id']}")
                c2.download_button("👮 MODULO MULTE", genera_modulo_multe(r), f"M_{r['id']}.pdf", key=f"m_{r['id']}")
                c3.download_button("💾 FATTURA XML", genera_xml_fattura(r), f"F_{r['id']}.xml", key=f"x_{r['id']}")
                
                st.write("---")
                st.write("🖼️ *FOTO ALLEGATE*")
                f_a, f_b = st.columns(2)
                if r.get("foto_patente"):
                    p_d = base64.b64decode(str(r["foto_patente"]).split(",")[1])
                    f_a.download_button("📸 Scarica Patente", p_d, "patente.png", "image/png", key=f"fp_{r['id']}")
                if r.get("foto_mezzo"):
                    m_d = base64.b64decode(str(r["foto_mezzo"]).split(",")[1])
                    f_b.download_button("📸 Scarica Mezzo", m_d, "mezzo.png", "image/png", key=f"fm_{r['id']}")
