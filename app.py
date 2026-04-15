import streamlit as st
from supabase import create_client, Client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from fpdf import FPDF
import io
import base64
from datetime import datetime

# --- DATI AZIENDALI ---
DITTA = "BATTAGLIA RENT"
TITOLARE = "BATTAGLIA MARIANNA"
INDIRIZZO = "Via Cognole n. 5, Forio (NA)"
DATI_IVA = "P.IVA: 10252601215 | C.F.: BTTMNN87A53Z112S"
NATO_A = "Berlino (Germania) il 13/01/1987"

# Connessione
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

# --- PDF GENERATOR ---
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
    pdf.set_font("Arial", "B", 14); pdf.cell(0, 10, safe(f"CONTRATTO N. {c['numero_fattura']}"), ln=True, align="C")
    pdf.ln(5); pdf.set_font("Arial", "B", 10); pdf.cell(0, 7, " DATI RIEPILOGATIVI", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 7, safe(f"Cliente: {c['nome']} {c['cognome']} | Mezzo: {c['modello']} ({c['targa']})"), border=1, ln=True)
    pdf.cell(0, 7, safe(f"Periodo: dal {c['inizio']} al {c['fine']} | Prezzo: {c['prezzo']} EUR"), border=1, ln=True)
    
    firma_data = c.get("firma")
    if firma_data and len(str(firma_data)) > 100:
        try:
            if "," in str(firma_data): firma_data = str(firma_data).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(firma_data)), x=140, y=pdf.get_y()+5, w=45)
        except: pass
    return bytes(pdf.output(dest="S"))

def genera_fattura(c):
    pdf = BRPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14); pdf.cell(0, 10, safe(f"FATTURA N. {c['numero_fattura']}"), ln=True, align="C", border="B")
    pdf.ln(5); pdf.set_font("Arial", "B", 9)
    pdf.cell(95, 7, "FORNITORE", border=1); pdf.cell(95, 7, "CLIENTE", border=1, ln=True)
    pdf.set_font("Arial", "", 9)
    pdf.cell(95, 5, safe(DITTA), border="LR"); pdf.cell(95, 5, safe(f"{c['nome']} {c['cognome']}"), border="LR", ln=True)
    pdf.cell(95, 5, safe(DATI_IVA), border="LR"); pdf.cell(95, 5, safe(f"C.F.: {c['codice_fiscale']}"), border="LR", ln=True)
    pdf.cell(95, 5, safe(INDIRIZZO), border="LR"); pdf.cell(95, 5, safe(f"PEC: {c.get('pec', 'N/A')}"), border="LR", ln=True)
    pdf.cell(95, 5, "", border="LRB"); pdf.cell(95, 5, safe(f"SDI: {c.get('codice_univoco', '0000000')}"), border="LRB", ln=True)
    return bytes(pdf.output(dest="S"))

# --- INTERFACCIA ---
st.set_page_config(page_title="Battaglia Rent", layout="wide")

if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Password", type="password") == "1234":
        if st.button("Accedi"): st.session_state.auth = True; st.rerun()
    st.stop()

tab1, tab2 = st.tabs(["📝 Nuovo Noleggio", "📂 Archivio"])

with tab1:
    with st.form("form_v18"):
        c1, c2, c3 = st.columns(3)
        nome, cognome, cf = c1.text_input("Nome"), c2.text_input("Cognome"), c3.text_input("C.F. / ID")
        pec, sdi = st.text_input("PEC/Email"), st.text_input("SDI (Codice Univoco)", value="0000000")
        
        st.subheader("Mezzo e Noleggio")
        c4, c5, c6 = st.columns(3)
        mod, tar, pat = c4.text_input("Modello"), c5.text_input("Targa").upper(), c6.text_input("Patente")
        prz, dep = st.columns(2)
        prezzo, deposito = prz.number_input("Prezzo (€)"), dep.number_input("Deposito (€)")
        
        dat_n, luo_n, ind = st.text_input("Data Nascita"), st.text_input("Luogo Nascita"), st.text_input("Residenza")
        canvas = st_canvas(height=150, width=400, stroke_width=3, key="sig_v18")

        if st.form_submit_button("REGISTRA"):
            try:
                img = Image.fromarray(canvas.image_data.astype("uint8"))
                buf = io.BytesIO(); img.save(buf, format="PNG")
                firma = base64.b64encode(buf.getvalue()).decode()
                num = get_prossimo_numero()
                
                dati = {
                    "nome": nome, "cognome": cognome, "codice_fiscale": cf, "modello": mod, "targa": tar,
                    "prezzo": prezzo, "numero_fattura": num, "firma": firma, "pec": pec, 
                    "codice_univoco": sdi, "data_nascita": dat_n, "luogo_nascita": luo_n, 
                    "indirizzo_cliente": ind, "inizio": str(datetime.now().date())
                }
                supabase.table("contratti").insert(dati).execute()
                st.success(f"Noleggio {num} Salvato!")
            except Exception as e:
                st.error("Errore: Assicurati di aver aggiunto le colonne PEC e SDI su Supabase!")

with tab2:
    search = st.text_input("🔍 Cerca")
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    for r in res.data:
        if search.lower() in f"{s(r['cognome'])} {s(r['targa'])}".lower():
            with st.expander(f"N. {r['numero_fattura']} - {r['cognome']}"):
                col1, col2 = st.columns(2)
                col1.download_button("📜 Contratto", genera_contratto(r), f"C_{r['id']}.pdf", key=f"c_{r['id']}")
                col2.download_button("🧾 Fattura", genera_fattura(r), f"F_{r['id']}.pdf", key=f"f_{r['id']}")
