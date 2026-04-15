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

# --- GENERATORE PDF BUSINESS ---
class BusinessPDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 6, safe(DITTA), ln=True)
        self.set_font("Arial", "", 8)
        self.cell(0, 4, safe(f"{TITOLARE} - {INDIRIZZO}"), ln=True)
        self.cell(0, 4, safe(DATI_FISCALI), ln=True)
        self.ln(5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

def genera_contratto_legale(c):
    pdf = BusinessPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, safe(f"CONTRATTO DI NOLEGGIO N. {c['numero_fattura']}"), ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(0, 5, "CONDIZIONI GENERALI / TERMS AND CONDITIONS", ln=True)
    pdf.set_font("Arial", "", 7)
    testo_legale = (
        "1. Patente obbligatoria e valida. 2. Responsabilità totale per danni, furto e incendio a carico del cliente. "
        "3. Carburante da riconsegnare allo stesso livello. 4. Multe e contravvenzioni a carico del locatario. "
        "5. Divieto di guida sotto effetto di alcol/droghe. 6. Il deposito cauzionale copre i piccoli danni.\n"
        "1. Valid license required. 2. Total responsibility for damage, theft and fire lies with the customer. "
        "3. Fuel to be returned at the same level. 4. Fines and penalties are the responsibility of the renter."
    )
    pdf.multi_cell(0, 4, safe(testo_legale), border=1)
    pdf.ln(5)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, " DETTAGLI / DETAILS", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "", 9)
    pdf.cell(95, 8, safe(f"Cliente: {c['nome']} {c['cognome']}"), border=1)
    pdf.cell(95, 8, safe(f"Patente: {c['numero_patente']}"), border=1, ln=True)
    pdf.cell(95, 8, safe(f"Veicolo: {c['modello']} ({c['targa']})"), border=1)
    pdf.cell(95, 8, safe(f"Periodo: {c['inizio']} / {c['fine']}"), border=1, ln=True)
    pdf.ln(10)
    pdf.cell(95, 20, "Firma Cliente / Signature:", border=1)
    pdf.cell(95, 20, "Firma Noleggiatore:", border=1, ln=True)
    
    firma = c.get("firma")
    if firma and len(str(firma)) > 100:
        try:
            if "," in str(firma): firma = str(firma).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(firma)), x=15, y=pdf.get_y()-15, w=35)
        except: pass
    return bytes(pdf.output(dest="S"))

def genera_modulo_vigili_legale(c):
    pdf = BusinessPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, safe("COMUNICAZIONE DATI CONDUCENTE (L. 445/2000)"), ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", "", 10)
    corpo = (f"La sottoscritta {TITOLARE}, titolare di {DITTA}, dichiara che il veicolo {c['modello']} "
             f"targa {c['targa']} era locato a {c['nome']} {c['cognome']}, nato il {c.get('data_nascita','')} "
             f"a {c.get('luogo_nascita','')}, residente in {c.get('indirizzo_cliente','')}. "
             f"Patente n. {c['numero_patente']}. Si richiede la rinotifica del verbale.")
    pdf.multi_cell(0, 7, safe(corpo))
    pdf.ln(20)
    pdf.cell(0, 10, "In fede, Marianna Battaglia", align="R", ln=True)
    return bytes(pdf.output(dest="S"))

def genera_fattura_completa(c):
    pdf = BusinessPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, safe(f"FATTURA N. {c['numero_fattura']}"), ln=True, align="C", border="B")
    pdf.ln(5)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(95, 7, "CEDENTE (BATTAGLIA RENT)", border=1)
    pdf.cell(95, 7, "CESSIONARIO (CLIENTE)", border=1, ln=True)
    pdf.set_font("Arial", "", 9)
    pdf.cell(95, 25, safe(f"{DITTA}\n{INDIRIZZO}\n{DATI_FISCALI}"), border=1)
    pdf.cell(95, 25, safe(f"{c['nome']} {c['cognome']}\nCF: {c['codice_fiscale']}\nSDI: {c.get('codice_univoco','0000000')}"), border=1, ln=True)
    pdf.ln(10)
    
    prezzo = float(c['prezzo'])
    imponibile = prezzo / 1.22
    iva = prezzo - imponibile
    
    pdf.set_font("Arial", "B", 10)
    pdf.cell(110, 8, "DESCRIZIONE", border=1); pdf.cell(40, 8, "IVA", border=1); pdf.cell(40, 8, "TOTALE", border=1, ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(110, 10, safe(f"Noleggio Scooter {c['modello']} ({c['targa']})"), border=1)
    pdf.cell(40, 10, "22%", border=1)
    pdf.cell(40, 10, f"{prezzo:.2f} EUR", border=1, ln=True)
    pdf.ln(5)
    pdf.cell(150, 8, "IMPONIBILE:", align="R"); pdf.cell(40, 8, f"{imponibile:.2f} EUR", border=1, ln=True)
    pdf.cell(150, 8, "IVA 22%:", align="R"); pdf.cell(40, 8, f"{iva:.2f} EUR", border=1, ln=True)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(150, 8, "TOTALE FATTURA:", align="R"); pdf.cell(40, 8, f"{prezzo:.2f} EUR", border=1, ln=True)
    return bytes(pdf.output(dest="S"))

# --- INTERFACCIA STREAMLIT ---
st.set_page_config(page_title="Battaglia Rent Gestionale", layout="wide")

if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    pwd = st.text_input("Password Accesso", type="password")
    if st.button("Accedi") and pwd == "1234":
        st.session_state.auth = True
        st.rerun()
    st.stop()

t1, t2 = st.tabs(["📝 Nuovo Noleggio", "📂 Archivio"])

with t1:
    with st.form("form_vFinal"):
        st.subheader("👤 Dati Cliente")
        c1, c2, c3 = st.columns(3)
        nome, cognome, cf = c1.text_input("Nome"), c2.text_input("Cognome"), c3.text_input("C.F. / ID")
        pec, sdi = st.text_input("PEC/Email"), st.text_input("SDI", value="0000000")
        dat_n, luo_n, ind = st.text_input("Data Nascita"), st.text_input("Luogo Nascita"), st.text_input("Indirizzo Residenza")
        
        st.subheader("🛵 Dati Noleggio")
        c4, c5, c6 = st.columns(3)
        mod, tar, pat = c4.text_input("Modello"), c5.text_input("Targa").upper(), c6.text_input("N. Patente")
        prz, dep = st.columns(2)
        prezzo, deposito = prz.number_input("Prezzo Totale (€)"), dep.number_input("Deposito (€)")
        ini, fin = st.date_input("Inizio"), st.date_input("Fine")
        
        f1, f2 = st.file_uploader("Fronte Patente"), st.file_uploader("Retro Patente")
        st.write("Firma Cliente")
        canvas = st_canvas(height=150, width=400, stroke_width=3, key="sig_vFinal")

        if st.form_submit_button("REGISTRA"):
            try:
                img = Image.fromarray(canvas.image_data.astype("uint8"))
                buf = io.BytesIO(); img.save(buf, format="PNG")
                firma = base64.b64encode(buf.getvalue()).decode()
                u_f, u_r = upload_foto(f1, tar, "F"), upload_foto(f2, tar, "R")
                num = get_prossimo_numero()
                
                dati = {
                    "nome": nome, "cognome": cognome, "codice_fiscale": cf, "modello": mod, "targa": tar,
                    "prezzo": prezzo, "deposito": deposito, "numero_fattura": num, "firma": firma,
                    "url_fronte": u_f, "url_retro": u_r, "pec": pec, "codice_univoco": sdi,
                    "data_nascita": dat_n, "luogo_nascita": luo_n, "indirizzo_cliente": ind,
                    "inizio": str(ini), "fine": str(fin), "numero_patente": pat
                }
                supabase.table("contratti").insert(dati).execute()
                st.success(f"Salvato! N. {num}")
            except Exception as e:
                st.error(f"Errore: {e}")

with t2:
    search = st.text_input("🔍 Cerca")
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    for r in res.data:
        if search.lower() in f"{s(r['cognome'])} {s(r['targa'])}".lower():
            with st.expander(f"N. {r['numero_fattura']} - {r['cognome']} ({r['targa']})"):
                c_pdf, f_pdf, v_pdf = genera_contratto_legale(r), genera_fattura_completa(r), genera_modulo_vigili_legale(r)
                c_a, c_b, c_c = st.columns(3)
                c_a.download_button("📜 Contratto", c_pdf, f"C_{r['id']}.pdf", mime="application/pdf", key=f"c_{r['id']}")
                c_b.download_button("🧾 Fattura", f_pdf, f"F_{r['id']}.pdf", mime="application/pdf", key=f"f_{r['id']}")
                c_c.download_button("🚨 Vigili", v_pdf, f"V_{r['id']}.pdf", mime="application/pdf", key=f"v_{r['id']}")
                if r.get("url_fronte"): st.image(r["url_fronte"], width=300)
