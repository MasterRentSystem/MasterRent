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
INDIRIZZO = "Via Cognole n. 5, Forio (NA)"
DATI_FISCALI = "P.IVA: 10252601215 | C.F.: BTTMNN87A53Z112S"

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

def upload_foto(file, targa, tipo):
    if file is None: return None
    try:
        img = Image.open(file)
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
        img.thumbnail((800, 800))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=75)
        nome = f"{tipo}{targa}{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
        supabase.storage.from_("documenti").upload(nome, buf.getvalue(), {"content-type": "image/jpeg"})
        return supabase.storage.from_("documenti").get_public_url(nome)
    except: return None

# --- GENERAZIONE PDF ---
class BusinessPDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 6, safe(DITTA), ln=True)
        self.set_font("Arial", "", 8)
        self.cell(0, 4, safe(f"{TITOLARE} - {INDIRIZZO}"), ln=True)
        self.cell(0, 4, safe(DATI_FISCALI), ln=True)
        self.ln(5); self.line(10, self.get_y(), 200, self.get_y()); self.ln(5)

def genera_contratto_legale(c):
    pdf = BusinessPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14); pdf.cell(0, 10, safe(f"CONTRATTO DI NOLEGGIO N. {c['numero_fattura']}"), ln=True, align="C")
    pdf.ln(5); pdf.set_font("Arial", "B", 10); pdf.cell(0, 7, " ANAGRAFICA CLIENTE", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "", 9)
    pdf.cell(95, 7, safe(f"Nome: {c['nome']} {c['cognome']}"), border="LR")
    pdf.cell(95, 7, safe(f"Nazionalita: {c.get('nazionalita','')}"), border="R", ln=True)
    pdf.cell(95, 7, safe(f"Nato il: {c.get('data_nascita','')} a: {c.get('luogo_nascita','')}"), border="LR")
    pdf.cell(95, 7, safe(f"C.F.: {c['codice_fiscale']}"), border="R", ln=True)
    pdf.cell(190, 7, safe(f"Residenza: {c.get('indirizzo_cliente','')}"), border="LR", ln=True)
    pdf.cell(95, 7, safe(f"Tel: {c.get('telefono','')}"), border="LRB")
    pdf.cell(95, 7, safe(f"Email/PEC: {c.get('pec','')}"), border="RB", ln=True)
    pdf.ln(3); pdf.set_font("Arial", "B", 10); pdf.cell(0, 7, " DATI NOLEGGIO", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "", 9)
    pdf.cell(63, 7, safe(f"Mezzo: {c['modello']}"), border=1)
    pdf.cell(63, 7, safe(f"Targa: {c['targa']}"), border=1)
    pdf.cell(64, 7, safe(f"Patente: {c['numero_patente']}"), border=1, ln=True)
    pdf.cell(95, 7, safe(f"Inizio: {c['inizio']}  Fine: {c['fine']}"), border=1)
    pdf.cell(95, 7, safe(f"Prezzo: {c['prezzo']} EUR"), border=1, ln=True)
    pdf.ln(10); pdf.set_font("Arial", "B", 9); pdf.cell(0, 7, "FIRMA DEL CLIENTE", ln=True)
    y_f = pdf.get_y(); pdf.cell(100, 25, "", border=1)
    pdf.cell(90, 25, safe(f"Data: {datetime.now().strftime('%d/%m/%Y')}"), border=1, ln=True)
    firma = c.get("firma")
    if firma and len(str(firma)) > 100:
        try:
            if "," in str(firma): firma = str(firma).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(firma)), x=15, y=y_f+2, w=40)
        except: pass
    return bytes(pdf.output(dest="S"))

def genera_modulo_vigili_legale(c):
    pdf = BusinessPDF()
    pdf.add_page()
    pdf.set_font("Arial", "", 11); pdf.cell(0, 10, safe("Spett. le Polizia Locale"), ln=True, align="R")
    pdf.ln(5); pdf.set_font("Arial", "B", 10); pdf.cell(0, 7, safe("OGGETTO: RIFERIMENTO ACCERTAMENTO VIOLAZIONE - COMUNICAZIONE DATI"), ln=True)
    pdf.ln(5); pdf.set_font("Arial", "", 10)
    testo = (f"La sottoscritta BATTAGLIA MARIANNA, titolare di {DITTA}, dichiara ai sensi della l. 445/2000 che il veicolo {c['modello']} "
             f"targa {c['targa']} era locato a {c['nome']} {c['cognome']}, nato a {c.get('luogo_nascita','')} il {c.get('data_nascita','')}, "
             f"residente in {c.get('indirizzo_cliente','')}, nazionalita {c.get('nazionalita','')}. Patente n. {c['numero_patente']}.")
    pdf.multi_cell(0, 6, safe(testo)); pdf.ln(5); pdf.multi_cell(0, 6, safe("Si richiede la rinotifica del verbale. Si allega copia conforme del contratto."))
    pdf.ln(15); pdf.cell(0, 10, "In fede, Marianna Battaglia", align="R", ln=True)
    return bytes(pdf.output(dest="S"))

def genera_fattura_completa(c):
    pdf = BusinessPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14); pdf.cell(0, 10, safe(f"FATTURA N. {c['numero_fattura']}"), ln=True, align="C", border="B")
    pdf.ln(10); pdf.set_font("Arial", "B", 9); pdf.cell(95, 7, "CEDENTE", border=1, fill=True); pdf.cell(95, 7, "CESSIONARIO", border=1, fill=True, ln=True)
    pdf.set_font("Arial", "", 9)
    pdf.multi_cell(95, 5, safe(f"{DITTA}\n{TITOLARE}\n{INDIRIZZO}\n{DATI_FISCALI}"), border=1)
    pdf.set_xy(105, pdf.get_y()-20)
    pdf.multi_cell(95, 5, safe(f"{c['nome']} {c['cognome']}\nCF: {c['codice_fiscale']}\nPEC: {c.get('pec','')}\nSDI: {c.get('codice_univoco','0000000')}"), border=1)
    pdf.ln(15); p = float(c['prezzo']); imp = p/1.22; iva = p-imp
    pdf.set_font("Arial", "B", 10); pdf.cell(110, 8, "DESCRIZIONE", border=1); pdf.cell(40, 8, "IVA", border=1); pdf.cell(40, 8, "TOTALE", border=1, ln=True)
    pdf.set_font("Arial", "", 10); pdf.cell(110, 10, safe(f"Noleggio Scooter {c['modello']} ({c['targa']})"), border=1); pdf.cell(40, 10, "22%", border=1); pdf.cell(40, 10, f"{p:.2f} EUR", border=1, ln=True)
    pdf.ln(5); pdf.cell(150, 7, "IMPONIBILE:", align="R"); pdf.cell(40, 7, f"{imp:.2f}", border=1, ln=True)
    pdf.cell(150, 7, "IVA 22%:", align="R"); pdf.cell(40, 7, f"{iva:.2f}", border=1, ln=True)
    pdf.cell(150, 7, "TOTALE FATTURA:", align="R"); pdf.cell(40, 7, f"{p:.2f} EUR", border=1, ln=True)
    return bytes(pdf.output(dest="S"))

# --- APP ---
st.set_page_config(page_title="Battaglia Rent Pro", layout="wide")
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Password", type="password") == "1234":
        if st.button("Accedi"): st.session_state.auth = True; st.rerun()
    st.stop()

t1, t2 = st.tabs(["📝 Nuovo Noleggio", "📂 Archivio"])
with t1:
    # Campi fuori dal form per maggiore stabilità
    c1, c2, c3 = st.columns(3)
    nome = c1.text_input("Nome")
    cognome = c2.text_input("Cognome")
    naz = c3.text_input("Nazionalita")
    
    c4, c5, c6 = st.columns(3)
    cf = c4.text_input("C.F. / ID")
    tel = c5.text_input("Telefono")
    pec = c6.text_input("Email / PEC")
    
    c7, c8, c9 = st.columns(3)
    dat_n = c7.text_input("Data Nascita")
    luo_n = c8.text_input("Luogo Nascita")
    ind = c9.text_input("Residenza")
    
    m1, m2, m3 = st.columns(3)
    mod = m1.text_input("Modello")
    tar = m2.text_input("Targa").upper()
    pat = m3.text_input("N. Patente")
    
    d1, d2, d3 = st.columns(3)
    prezzo = d1.number_input("Prezzo", min_value=0.0)
    deposito = d2.number_input("Deposito", min_value=0.0)
    sdi = d3.text_input("SDI", value="0000000")
    
    ini = st.date_input("Inizio")
    fin = st.date_input("Fine")
    
    f1 = st.file_uploader("Fronte Patente")
    f2 = st.file_uploader("Retro Patente")
    
    st.write("### Firma Cliente")
    canvas = st_canvas(height=150, width=400, stroke_width=3, key="sig_v24")
    
    # IL CHECKBOX ORA È BEN VISIBILE QUI
    st.markdown("---")
    accetto = st.checkbox("*IL CLIENTE DICHIARA DI AVER LETTO E ACCETTATO LE CONDIZIONI DI NOLEGGIO E LA PRIVACY.*")
    
    if st.button("💾 REGISTRA NOLEGGIO"):
        if not accetto:
            st.error("❌ Devi spuntare la casella di accettazione per salvare!")
        elif not nome or not cognome or not tar:
            st.error("❌ Nome, Cognome e Targa sono obbligatori!")
        else:
            try:
                with st.spinner("Salvataggio in corso..."):
                    img = Image.fromarray(canvas.image_data.astype("uint8"))
                    buf = io.BytesIO(); img.save(buf, format="PNG")
                    firma = base64.b64encode(buf.getvalue()).decode()
                    u_f, u_r = upload_foto(f1, tar, "F"), upload_foto(f2, tar, "R")
                    num = get_prossimo_numero()
                    
                    dati = {"nome": nome, "cognome": cognome, "codice_fiscale": cf, "modello": mod, "targa": tar, "prezzo": prezzo, "deposito": deposito, "numero_fattura": num, "firma": firma, "url_fronte": u_f, "url_retro": u_r, "pec": pec, "codice_univoco": sdi, "data_nascita": dat_n, "luogo_nascita": luo_n, "indirizzo_cliente": ind, "inizio": str(ini), "fine": str(fin), "numero_patente": pat, "nazionalita": naz, "telefono": tel}
                    
                    supabase.table("contratti").insert(dati).execute()
                    st.success(f"✅ Contratto N. {num} salvato correttamente!")
            except Exception as e: 
                st.error(f"Errore tecnico: {e}")

with t2:
    search = st.text_input("🔍 Cerca per Cognome o Targa")
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    for r in res.data:
        if search.lower() in f"{s(r['cognome'])} {s(r['targa'])}".lower():
            with st.expander(f"N. {r['numero_fattura']} - {r['cognome']} ({r['targa']})"):
                ca, cb, cc = st.columns(3)
                ca.download_button("📜 Contratto", genera_contratto_legale(r), f"C_{r['id']}.pdf", key=f"ca_{r['id']}")
                cb.download_button("🧾 Fattura", genera_fattura_completa(r), f"F_{r['id']}.pdf", key=f"fb_{r['id']}")
                cc.download_button("🚨 Vigili", genera_modulo_vigili_legale(r), f"V_{r['id']}.pdf", key=f"vc_{r['id']}")
