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
DATI_IVA = "P.IVA: 10252601215 | C.F.: BTTMNN87A53Z112S"
NATO_A = "Berlino (Germania) il 13/01/1987"

# Connessione Database
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- UTILITY ---
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

# --- GENERATORE PDF ---
class BRPDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 6, safe(DITTA), ln=True)
        self.set_font("Arial", "", 8)
        self.cell(0, 4, safe(f"{TITOLARE} - {INDIRIZZO}"), ln=True)
        self.cell(0, 4, safe(DATI_IVA), ln=True)
        self.line(10, self.get_y()+2, 200, self.get_y()+2)
        self.ln(10)

def genera_contratto(c):
    pdf = BRPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, safe(f"CONTRATTO DI NOLEGGIO N. {c['numero_fattura']}"), ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Arial", "I", 8)
    pdf.multi_cell(0, 4, safe("Il conduttore accetta il veicolo nello stato in cui si trova. Responsabilità per danni e sanzioni a carico del cliente.\nThe customer accepts the vehicle in its current condition. Responsibility for damages/fines lies with the customer."))
    pdf.ln(5)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, " DATI CLIENTE E MEZZO", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 7, safe(f"Nome: {c['nome']} {c['cognome']} | Patente: {c['numero_patente']}"), border="LR", ln=True)
    pdf.cell(0, 7, safe(f"Veicolo: {c['modello']} | Targa: {c['targa']} | Benzina: {c['benzina']}"), border="LR", ln=True)
    pdf.cell(0, 7, safe(f"Dal: {c['inizio']} Al: {c['fine']} | Prezzo: {c['prezzo']} EUR"), border="LRB", ln=True)
    
    firma_data = c.get("firma")
    if firma_data and len(str(firma_data)) > 100:
        try:
            if "," in str(firma_data): firma_data = str(firma_data).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(firma_data)), x=140, y=pdf.get_y()+5, w=45)
        except: pass
    return bytes(pdf.output(dest="S"))

def genera_vigili(c):
    pdf = BRPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, safe("COMUNICAZIONE DATI CONDUCENTE PER VERBALE"), ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Arial", "", 11)
    testo = (f"La sottoscritta {TITOLARE}, nata a {NATO_A}, titolare di {DITTA}, dichiara che "
             f"il veicolo {c['modello']} targa {c['targa']} era locato a {c['nome']} {c['cognome']}, "
             f"nato il {c['data_nascita']} a {c['luogo_nascita']}, residente in {c['indirizzo_cliente']}. "
             f"Patente n. {c['numero_patente']}. Si richiede la rinotifica del verbale.")
    pdf.multi_cell(0, 7, safe(testo))
    pdf.ln(10)
    pdf.cell(0, 10, "Firma: Marianna Battaglia", align="R", ln=True)
    return bytes(pdf.output(dest="S"))

def genera_fattura_aruba(c):
    pdf = BRPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, safe(f"FATTURA N. {c['numero_fattura']}"), ln=True, align="C", border="B")
    pdf.ln(5)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(95, 7, "CEDENTE", border=1); pdf.cell(95, 7, "CESSIONARIO (CLIENTE)", border=1, ln=True)
    pdf.set_font("Arial", "", 9)
    pdf.cell(95, 5, safe(DITTA), border="LR"); pdf.cell(95, 5, safe(f"{c['nome']} {c['cognome']}"), border="LR", ln=True)
    pdf.cell(95, 5, safe(DATI_IVA), border="LR"); pdf.cell(95, 5, safe(f"C.F./ID: {c['codice_fiscale']}"), border="LR", ln=True)
    pdf.cell(95, 5, safe(INDIRIZZO), border="LR"); pdf.cell(95, 5, safe(f"PEC: {c.get('pec', 'N/A')}"), border="LR", ln=True)
    pdf.cell(95, 5, "", border="LRB"); pdf.cell(95, 5, safe(f"SDI: {c.get('codice_univoco', '0000000')}"), border="LRB", ln=True)
    pdf.ln(10)
    pdf.cell(140, 8, "DESCRIZIONE", border=1, fill=True); pdf.cell(50, 8, "TOTALE", border=1, fill=True, ln=True)
    pdf.cell(140, 10, safe(f"Noleggio Scooter {c['modello']} - Targa {c['targa']}"), border=1)
    pdf.cell(50, 10, f"{c['prezzo']} EUR", border=1, ln=True)
    return bytes(pdf.output(dest="S"))

# --- APP ---
st.set_page_config(page_title="Battaglia Rent Pro", layout="wide")

if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    pwd = st.text_input("Password", type="password")
    if st.button("Accedi") and pwd == "1234":
        st.session_state.auth = True
        st.rerun()
    st.stop()

t1, t2 = st.tabs(["📝 Nuovo Noleggio", "📂 Archivio"])

with t1:
    with st.form("form_v16"):
        c1, c2, c3 = st.columns(3)
        nome, cognome, cf = c1.text_input("Nome"), c2.text_input("Cognome"), c3.text_input("C.F. / ID Estero")
        pec, sdi = st.text_input("PEC/Email"), st.text_input("SDI", value="0000000")
        st.subheader("Veicolo")
        c4, c5, c6 = st.columns(3)
        mod, tar, pat = c4.text_input("Modello"), c5.text_input("Targa").upper(), c6.text_input("N. Patente")
        c7, c8, c9 = st.columns(3)
        prz, dep = c7.number_input("Prezzo (€)", min_value=0.0), c8.number_input("Deposito (€)", min_value=0.0)
        ben = c9.selectbox("Benzina", ["1/8", "1/4", "1/2", "3/4", "Pieno"])
        d1, d2 = st.columns(2)
        ini, fin = d1.date_input("Inizio"), d2.date_input("Fine")
        dat_n, luo_n, ind = st.text_input("Data Nascita"), st.text_input("Luogo Nascita"), st.text_input("Indirizzo")
        f_f, f_r = st.file_uploader("Fronte Patente"), st.file_uploader("Retro Patente")
        canvas = st_canvas(height=150, width=400, stroke_width=3, key="canvas_v16")
        if st.form_submit_button("SALVA"):
            img = Image.fromarray(canvas.image_data.astype("uint8"))
            buf = io.BytesIO(); img.save(buf, format="PNG")
            firma = base64.b64encode(buf.getvalue()).decode()
            u_f, u_r = upload_foto(f_f, tar, "F"), upload_foto(f_r, tar, "R")
            num = get_prossimo_numero()
            dati = {"nome": nome, "cognome": cognome, "codice_fiscale": cf, "modello": mod, "targa": tar, "prezzo": prz, "inizio": str(ini), "fine": str(fin), "numero_fattura": num, "firma": firma, "url_fronte": u_f, "url_retro": u_r, "benzina": ben, "deposito": dep, "numero_patente": pat, "pec": pec, "codice_univoco": sdi, "data_nascita": dat_n, "luogo_nascita": luo_n, "indirizzo_cliente": ind, "data_creazione": datetime.now().isoformat()}
            supabase.table("contratti").insert(dati).execute()
            st.success(f"Registrato N. {num}!")

with t2:
    search = st.text_input("🔍 Cerca Cognome o Targa")
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    for r in res.data:
        if search.lower() in f"{r['cognome']} {r['targa']}".lower():
            with st.expander(f"N. {r['numero_fattura']} - {r['cognome']} ({r['targa']})"):
                col1, col2, col3 = st.columns(3)
                # IL SEGRETO: Usiamo r['id'] per rendere ogni pulsante unico al mondo
                col1.download_button("📜 Contratto", data=genera_contratto(r), file_name=f"C_{r['id']}.pdf", mime="application/pdf", key=f"btn_c_{r['id']}")
                col2.download_button("🧾 Fattura", data=genera_fattura_aruba(r), file_name=f"F_{r['id']}.pdf", mime="application/pdf", key=f"btn_f_{r['id']}")
                col3.download_button("🚨 Vigili", data=genera_vigili(r), file_name=f"V_{r['id']}.pdf", mime="application/pdf", key=f"btn_v_{r['id']}")
                st.write("---")
                f1, f2 = st.columns(2)
                if r.get("url_fronte"): f1.image(r["url_fronte"], caption="Fronte")
                if r.get("url_retro"): f2.image(r["url_retro"], caption="Retro")
