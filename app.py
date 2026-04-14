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
    """Garantisce la numerazione sequenziale corretta"""
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

# --- GENERATORE PDF PROFESSIONALE ---
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
    
    # Dati Conduttore
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, " DATI DEL CONDUTTORE / CUSTOMER DETAILS", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 7, safe(f"Nome/Name: {c['nome']} {c['cognome']}"), border="LR", ln=True)
    pdf.cell(0, 7, safe(f"Nato a/Born in: {c['luogo_nascita']} il {c['data_nascita']}"), border="LR", ln=True)
    pdf.cell(0, 7, safe(f"Residenza/Address: {c['indirizzo_cliente']}"), border="LR", ln=True)
    pdf.cell(0, 7, safe(f"Patente/Driver License: {c['numero_patente']} | C.F.: {c['codice_fiscale']}"), border="LRB", ln=True)
    
    pdf.ln(5)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, " DATI NOLEGGIO / RENTAL DETAILS", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 7, safe(f"Veicolo/Vehicle: {c['modello']} | Targa/Plate: {c['targa']}"), border="LR", ln=True)
    pdf.cell(0, 7, safe(f"Inizio/Start: {c['inizio']} | Fine/End: {c['fine']}"), border="LR", ln=True)
    pdf.cell(0, 7, safe(f"Prezzo/Price: {c['prezzo']} EUR | Deposito/Deposit: {c['deposito']} EUR"), border="LRB", ln=True)

    # Firma
    firma_data = c.get("firma")
    if firma_data and len(str(firma_data)) > 100:
        try:
            if "," in str(firma_data): firma_data = str(firma_data).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(firma_data)), x=140, y=pdf.get_y()+5, w=45)
        except: pass
    
    return bytes(pdf.output(dest="S"))

def genera_fattura_aruba(c):
    pdf = BRPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, safe(f"FATTURA / INVOICE N. {c['numero_fattura']}"), ln=True, align="C", border="B")
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 10)
    pdf.cell(95, 7, "FORNITORE / SUPPLIER", border=1)
    pdf.cell(95, 7, "CLIENTE / CUSTOMER", border=1, ln=True)
    pdf.set_font("Arial", "", 9)
    pdf.cell(95, 5, safe(DITTA), border="LR")
    pdf.cell(95, 5, safe(f"{c['nome']} {c['cognome']}"), border="LR", ln=True)
    pdf.cell(95, 5, safe(DATI_IVA), border="LR")
    
    id_cliente = c['codice_fiscale'] if c['codice_fiscale'] else "ID ESTERO / FOREIGN ID"
    pdf.cell(95, 5, safe(f"C.F./Tax ID: {id_cliente}"), border="LR", ln=True)
    pdf.cell(95, 5, safe(INDIRIZZO), border="LR")
    pdf.cell(95, 5, safe(f"PEC/Email: {c.get('pec', 'N/A')}"), border="LR", ln=True)
    pdf.cell(95, 5, "", border="LRB")
    pdf.cell(95, 5, safe(f"SDI: {c.get('codice_univoco', '0000000')}"), border="LRB", ln=True)
    
    pdf.ln(10)
    pdf.cell(140, 8, "DESCRIZIONE / DESCRIPTION", border=1, fill=True)
    pdf.cell(50, 8, "TOTALE / TOTAL", border=1, fill=True, ln=True)
    pdf.cell(140, 10, safe(f"Rental Services - Scooter {c['modello']} ({c['targa']})"), border=1)
    pdf.cell(50, 10, f"{c['prezzo']} EUR", border=1, ln=True)
    
    return bytes(pdf.output(dest="S"))

# --- APP STREAMLIT ---
st.set_page_config(page_title="Battaglia Rent Pro", layout="wide")

if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    pwd = st.text_input("Accesso Gestionale", type="password")
    if st.button("Entra"):
        if pwd == "1234": st.session_state.auth = True; st.rerun()
    st.stop()

t1, t2 = st.tabs(["📝 Nuovo Noleggio", "📂 Archivio"])

with t1:
    with st.form("form_v15"):
        st.subheader("👤 Dati Cliente (Italiano o Straniero)")
        c1, c2, c3 = st.columns(3)
        nome, cognome = c1.text_input("Nome"), c2.text_input("Cognome")
        cf = c3.text_input("Codice Fiscale / ID Estero")
        pec = st.text_input("PEC o Email")
        sdi = st.text_input("Codice SDI (Stranieri: 0000000)", value="0000000")
        
        st.subheader("🛵 Dati Noleggio")
        c6, c7, c8 = st.columns(3)
        mod, tar = c6.text_input("Modello Scooter"), c7.text_input("Targa").upper()
        pat = c8.text_input("N. Patente")
        
        c9, c10, c11 = st.columns(3)
        prz = c9.number_input("Prezzo Totale (€)", min_value=0.0)
        dep = c10.number_input("Deposito Cauzionale (€)", min_value=0.0)
        ben = c11.selectbox("Livello Benzina", ["1/8", "1/4", "1/2", "3/4", "Pieno"])
        
        c12, c13 = st.columns(2)
        ini, fin = c12.date_input("Inizio"), c13.date_input("Fine")
        dat_n, luo_n = st.text_input("Data di Nascita"), st.text_input("Luogo di Nascita")
        ind = st.text_input("Indirizzo Residenza")

        st.subheader("📸 Documenti")
        f_front = st.file_uploader("Fronte Patente", type=['jpg','png','jpeg'])
        f_back = st.file_uploader("Retro Patente", type=['jpg','png','jpeg'])
        
        st.write("Firma Cliente")
        canvas = st_canvas(height=150, width=400, stroke_width=3, key="sig_v15")

        if st.form_submit_button("REGISTRA NOLEGGIO"):
            img = Image.fromarray(canvas.image_data.astype("uint8"))
            buf = io.BytesIO(); img.save(buf, format="PNG")
            firma = base64.b64encode(buf.getvalue()).decode()
            u_f, u_r = upload_foto(f_front, tar, "F"), upload_foto(f_back, tar, "R")
            num_seq = get_prossimo_numero()
            
            dati = {
                "nome": nome, "cognome": cognome, "codice_fiscale": cf, "modello": mod, "targa": tar,
                "prezzo": prz, "inizio": str(ini), "fine": str(fin), "numero_fattura": num_seq,
                "firma": firma, "url_fronte": u_f, "url_retro": u_r, "benzina": ben,
                "deposito": dep, "numero_patente": pat, "pec": pec, "codice_univoco": sdi,
                "data_nascita": dat_n, "luogo_nascita": luo_n, "indirizzo_cliente": ind,
                "data_creazione": datetime.now().isoformat()
            }
            supabase.table("contratti").insert(dati).execute()
            st.success(f"Registrato! Numero: {num_seq}")

with t2:
    search = st.text_input("🔍 Cerca")
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    for r in res.data:
        if search.lower() in f"{r['cognome']} {r['targa']}".lower():
            with st.expander(f"Doc N. {r['numero_fattura']} - {r['cognome']} ({r['targa']})"):
                col1, col2 = st.columns(2)
                # Forza il passaggio in byte per evitare StreamlitAPIException
                pdf_contratto = genera_contratto(r)
                pdf_fattura = genera_fattura_aruba(r)
                
                col1.download_button("📜 Contratto", data=pdf_contratto, file_name=f"Contratto_{r['numero_fattura']}.pdf", mime="application/pdf")
                col2.download_button("🧾 Fattura Aruba", data=pdf_fattura, file_name=f"Fattura_{r['numero_fattura']}.pdf", mime="application/pdf")
                
                st.write("---")
                f1, f2 = st.columns(2)
                if r.get("url_fronte"): f1.image(r["url_fronte"], caption="Fronte Patente")
                if r.get("url_retro"): f2.image(r["url_retro"], caption="Retro Patente")
