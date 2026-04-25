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

def upload_media(file, targa, tipo):
    if file is None: return None
    try:
        nome_file = f"{tipo}{targa}{datetime.now().strftime('%Y%m%d%H%M%S')}"
        content_type = file.type
        
        if "image" in content_type:
            img = Image.open(file)
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            img.thumbnail((800, 800))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75)
            data = buf.getvalue()
            nome_file += ".jpg"
        else:
            data = file.getvalue()
            nome_file += ".mp4" if "mp4" in content_type else ".mov"

        supabase.storage.from_("documenti").upload(nome_file, data, {"content-type": content_type})
        return supabase.storage.from_("documenti").get_public_url(nome_file)
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
    pdf.cell(190, 7, safe(f"Residenza: {c.get('indirizzo_cliente','')}"), border="LRB", ln=True)
    
    pdf.ln(3); pdf.set_font("Arial", "B", 10); pdf.cell(0, 7, " DATI NOLEGGIO", ln=True, fill=True, border=1)
    pdf.cell(63, 7, safe(f"Mezzo: {c['modello']}"), border=1)
    pdf.cell(63, 7, safe(f"Targa: {c['targa']}"), border=1)
    pdf.cell(64, 7, safe(f"Patente: {c['numero_patente']}"), border=1, ln=True)
    pdf.cell(95, 7, safe(f"Periodo: {c['inizio']} / {c['fine']}"), border=1)
    pdf.cell(95, 7, safe(f"Prezzo: {c['prezzo']} EUR"), border=1, ln=True)

    pdf.ln(5); pdf.set_font("Arial", "B", 10); pdf.cell(0, 7, " CONDIZIONI ESSENZIALI", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "", 8)
    clausole = ("1. ASSICURAZIONE: R.C.A. solo verso terzi. 2. DANNI/FURTO: A carico del cliente. 3. CASCO: Obbligatorio. 4. PRIVACY: Autorizzo GDPR.")
    pdf.multi_cell(0, 4, safe(clausole), border=1)

    pdf.ln(5); pdf.set_font("Arial", "B", 9); pdf.cell(0, 7, "FIRMA DEL CLIENTE", ln=True)
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
    pdf = BusinessPDF(); pdf.add_page()
    pdf.set_font("Arial", "B", 10); pdf.cell(0, 7, safe("COMUNICAZIONE DATI CONDUCENTE"), ln=True)
    pdf.set_font("Arial", "", 10)
    testo = f"Veicolo {c['modello']} targa {c['targa']} locato a {c['nome']} {c['cognome']}. Patente: {c['numero_patente']}."
    pdf.multi_cell(0, 6, safe(testo)); return bytes(pdf.output(dest="S"))

def genera_fattura_completa(c):
    pdf = BusinessPDF(); pdf.add_page()
    pdf.set_font("Arial", "B", 14); pdf.cell(0, 10, safe(f"FATTURA N. {c['numero_fattura']}"), ln=True, align="C")
    pdf.set_font("Arial", "", 10); pdf.ln(10)
    pdf.cell(0, 10, safe(f"Cliente: {c['nome']} {c['cognome']} - Importo: {c['prezzo']} EUR"), ln=True)
    return bytes(pdf.output(dest="S"))

# --- INTERFACCIA ---
st.set_page_config(page_title="Battaglia Rent Pro", layout="wide")
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Password", type="password") == "1234":
        if st.button("Accedi"): st.session_state.auth = True; st.rerun()
    st.stop()

t1, t2 = st.tabs(["📝 Nuovo Noleggio", "📂 Archivio"])

with t1:
    with st.form("form_registrazione"):
        c1, c2, c3 = st.columns(3)
        nome, cognome, naz = c1.text_input("Nome"), c2.text_input("Cognome"), c3.text_input("Nazionalita")
        c4, c5, c6 = st.columns(3)
        cf, tel, pec = c4.text_input("C.F. / ID"), c5.text_input("Telefono"), c6.text_input("Email / PEC")
        c7, c8, c9 = st.columns(3)
        dat_n, luo_n, ind = c7.text_input("Data Nascita"), c8.text_input("Luogo Nascita"), c9.text_input("Residenza")
        m1, m2, m3 = st.columns(3)
        mod, tar, pat = m1.text_input("Modello"), m2.text_input("Targa").upper(), m3.text_input("N. Patente")
        d1, d2, d3 = st.columns(3)
        prezzo, deposito, sdi = d1.number_input("Prezzo"), d2.number_input("Deposito"), d3.text_input("SDI", value="0000000")
        ini, fin = st.date_input("Inizio"), st.date_input("Fine")
        
        st.subheader("📹 Stato del Veicolo & Patente")
        video_mezzo = st.file_uploader("Video o Foto Danni (Stato Motorino)", type=["mp4", "mov", "jpg", "png"])
        f1, f2 = st.file_uploader("Fronte Patente"), st.file_uploader("Retro Patente")
        
        st.write("### Firma Cliente")
        canvas = st_canvas(height=150, width=400, stroke_width=3, key="sig_v26")
        accetto = st.checkbox("Accetto le condizioni di noleggio e privacy.")
        
        if st.form_submit_button("💾 REGISTRA"):
            if not accetto or not nome or not tar: st.error("❌ Compila i campi obbligatori e accetta le clausole!")
            else:
                try:
                    img = Image.fromarray(canvas.image_data.astype("uint8"))
                    buf = io.BytesIO(); img.save(buf, format="PNG")
                    firma = base64.b64encode(buf.getvalue()).decode()
                    
                    u_v = upload_media(video_mezzo, tar, "DANNI")
                    u_f = upload_media(f1, tar, "F")
                    u_r = upload_media(f2, tar, "R")
                    num = get_prossimo_numero()
                    
                    dati = {
                        "nome": nome, "cognome": cognome, "codice_fiscale": cf, "modello": mod, "targa": tar, 
                        "prezzo": prezzo, "deposito": deposito, "numero_fattura": num, "firma": firma, 
                        "url_video": u_v, "url_fronte": u_f, "url_retro": u_r, "pec": pec, 
                        "codice_univoco": sdi, "data_nascita": dat_n, "luogo_nascita": luo_n, 
                        "indirizzo_cliente": ind, "inizio": str(ini), "fine": str(fin), 
                        "numero_patente": pat, "nazionalita": naz, "telefono": tel
                    }
                    supabase.table("contratti").insert(dati).execute()
                    st.success(f"✅ Contratto {num} salvato!")
                except Exception as e: st.error(f"Errore: {e}")

with t2:
    search = st.text_input("🔍 Cerca per Cognome o Targa")
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    for r in res.data:
        if search.lower() in f"{s(r['cognome'])} {s(r['targa'])}".lower():
            with st.expander(f"N. {r['numero_fattura']} - {r['cognome']} ({r['targa']})"):
                
                st.write("### 🛵 Stato del Motorino")
                if r.get('url_video'):
                    if any(ext in r['url_video'].lower() for ext in ['.mp4', '.mov']):
                        st.video(r['url_video'])
                    else:
                        st.image(r['url_video'], use_container_width=True)
                else: st.info("Nessun video/foto stato motorino.")

                st.write("### 🪪 Documenti Patente")
                c_p1, c_p2 = st.columns(2)
                if r.get('url_fronte'): c_p1.image(r['url_fronte'], caption="Fronte")
                if r.get('url_retro'): c_p2.image(r['url_retro'], caption="Retro")
                
                st.markdown("---")
                ca, cb, cc = st.columns(3)
                ca.download_button("📜 Contratto", genera_contratto_legale(r), f"C_{r['id']}.pdf", key=f"c_{r['id']}")
                cb.download_button("🧾 Fattura", genera_fattura_completa(r), f"F_{r['id']}.pdf", key=f"f_{r['id']}")
                cc.download_button("🚨 Vigili", genera_modulo_vigili_legale(r), f"V_{r['id']}.pdf", key=f"v_{r['id']}")
