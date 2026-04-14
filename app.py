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

# --- FUNZIONI UTILI ---
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

# --- MOTORE PDF ---
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
    
    pdf.set_font("Arial", "I", 8)
    pdf.multi_cell(0, 4, safe("Italiano: Il cliente dichiara di accettare le condizioni di noleggio e lo stato del mezzo.\nEnglish: The customer agrees to the rental terms and the vehicle condition."))
    
    pdf.ln(5)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, " DATI CLIENTE E MEZZO", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 7, safe(f"Conduttore: {c['nome']} {c['cognome']} | Patente: {c['numero_patente']}"), border=1, ln=True)
    pdf.cell(0, 7, safe(f"Veicolo: {c['modello']} | Targa: {c['targa']} | Benzina: {c['benzina']}"), border=1, ln=True)
    pdf.cell(0, 7, safe(f"Periodo: dal {c['inizio']} al {c['fine']}"), border=1, ln=True)
    
    pdf.ln(5)
    pdf.set_font("Arial", "B", 8)
    pdf.cell(0, 5, "CLAUSOLE E PRIVACY:", ln=True)
    pdf.set_font("Arial", "", 7)
    legale = ("Responsabilita per multe (Art. 126 bis CdS). Il cliente e custode del mezzo. "
              "In caso di danni verra trattenuto il deposito. Consenso al trattamento dati GDPR.")
    pdf.multi_cell(0, 4, safe(legale), border=1)

    if c.get("firma") and len(str(c["firma"])) > 100:
        pdf.image(io.BytesIO(base64.b64decode(c["firma"])), x=140, y=pdf.get_y()+5, w=45)
    
    res = pdf.output(dest="S")
    return bytes(res) if isinstance(res, (bytes, bytearray)) else res.encode("latin-1")

def genera_vigili(c):
    pdf = BRPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 10, "COMUNICAZIONE PER RINOTIFICA VERBALE", ln=True, align="C")
    pdf.set_font("Arial", "", 11)
    testo = (f"La sottoscritta {TITOLARE}, nata a {NATO_A}, titolare della ditta {DITTA}, "
             f"dichiara che in data {c['inizio']} il veicolo {c['modello']} targa {c['targa']} "
             f"era locato al sig. {c['nome']} {c['cognome']}, nato il {c['data_nascita']} a {c['luogo_nascita']}. "
             f"Residente in {c['indirizzo_cliente']}. Patente n. {c['numero_patente']}.")
    pdf.multi_cell(0, 7, safe(testo))
    pdf.ln(10)
    pdf.cell(0, 10, "In fede, Marianna Battaglia", align="R", ln=True)
    
    res = pdf.output(dest="S")
    return bytes(res) if isinstance(res, (bytes, bytearray)) else res.encode("latin-1")

# --- APP ---
st.set_page_config(page_title="Battaglia Rent Pro", layout="wide")

if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Password", type="password") == "1234":
        if st.button("Accedi"): st.session_state.auth = True; st.rerun()
    st.stop()

tab1, tab2 = st.tabs(["🆕 Nuovo Noleggio", "📂 Archivio"])

with tab1:
    with st.form("form_v11"):
        c1, c2, c3 = st.columns(3)
        nome = c1.text_input("Nome")
        cognome = c2.text_input("Cognome")
        cf = c3.text_input("C.F. / P.IVA")
        
        c4, c5 = st.columns(2)
        pec = c4.text_input("PEC")
        sdi = c5.text_input("SDI", value="0000000")
        
        c6, c7, c8 = st.columns(3)
        mod = c6.text_input("Modello")
        tar = c7.text_input("Targa").upper()
        pat = c8.text_input("N. Patente")
        
        c9, c10, c11 = st.columns(3)
        prz = c9.number_input("Prezzo (€)", min_value=0.0)
        ben = c10.selectbox("Benzina", ["1/8", "1/4", "1/2", "3/4", "Pieno"])
        dep = c11.number_input("Deposito (€)", min_value=0.0)
        
        c12, c13 = st.columns(2)
        ini = c12.date_input("Inizio")
        fin = c13.date_input("Fine")
        
        dat_n = st.text_input("Data Nascita (GG/MM/AAAA)")
        luo_n = st.text_input("Luogo Nascita")
        ind = st.text_input("Indirizzo Residenza")

        st.subheader("📸 Foto Patente")
        f_front = st.file_uploader("Fronte", type=['jpg','png','jpeg'])
        f_back = st.file_uploader("Retro", type=['jpg','png','jpeg'])
        
        st.write("Firma Cliente")
        canvas = st_canvas(height=150, width=400, stroke_width=3, key="sig_v11")

        if st.form_submit_button("REGISTRA"):
            img = Image.fromarray(canvas.image_data.astype("uint8"))
            buf = io.BytesIO(); img.save(buf, format="PNG")
            firma = base64.b64encode(buf.getvalue()).decode()
            
            u_f = upload_foto(f_front, tar, "F")
            u_r = upload_foto(f_back, tar, "R")
            
            num = get_prossimo_numero()
            dati = {
                "nome": nome, "cognome": cognome, "codice_fiscale": cf, "modello": mod, "targa": tar,
                "prezzo": prz, "inizio": str(ini), "fine": str(fin), "numero_fattura": num,
                "firma": firma, "url_fronte": u_f, "url_retro": u_r, "benzina": ben,
                "deposito": dep, "numero_patente": pat, "pec": pec, "codice_univoco": sdi,
                "data_nascita": dat_n, "luogo_nascita": luo_n, "indirizzo_cliente": ind,
                "data_creazione": datetime.now().isoformat()
            }
            supabase.table("contratti").insert(dati).execute()
            st.success(f"Salvato! N. {num}")

with tab2:
    search = st.text_input("🔍 Cerca")
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    for r in res.data:
        if search.lower() in f"{r['cognome']} {r['targa']}".lower():
            with st.expander(f"N. {r['numero_fattura']} - {r['targa']} ({r['cognome']})"):
                col1, col2 = st.columns(2)
                col1.download_button("📜 Contratto", genera_contratto(r), f"C_{r['id']}.pdf", key=f"btn_c_{r['id']}")
                col2.download_button("🚨 Vigili", genera_vigili(r), f"V_{r['id']}.pdf", key=f"btn_v_{r['id']}")
                
                st.write("---")
                f1, f2 = st.columns(2)
                if r.get("url_fronte"): f1.image(r["url_fronte"], caption="Fronte")
                if r.get("url_retro"): f2.image(r["url_retro"], caption="Retro")
