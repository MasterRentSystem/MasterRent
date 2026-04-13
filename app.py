import streamlit as st
from supabase import create_client, Client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from fpdf import FPDF
import io
import base64
from datetime import datetime

# --- DATI AZIENDA ---
DITTA = "BATTAGLIA RENT"
TITOLARE = "BATTAGLIA MARIANNA"
DETTAGLI_TITOLARE = "nata a Berlino il 13/01/1987 e residente in Forio alla Via Cognole n. 5"
INDIRIZZO = "Via Cognole n. 5, Forio (NA)"
DATI_IVA = "P.IVA: 10252601215 | C.F.: BTTMNN87A53Z112S"

# --- SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- UTILITY ---
def s(v): return "" if v is None else str(v)

def safe_text(text):
    return s(text).encode("latin-1", "replace").decode("latin-1")

def prossimo_numero_fattura():
    try:
        res = supabase.table("contratti").select("numero_fattura").order("numero_fattura", desc=True).limit(1).execute()
        return int(res.data[0]["numero_fattura"]) + 1 if res.data and res.data[0].get("numero_fattura") else 1
    except: return 1

def upload_foto(file, targa, tipo):
    if file is None: return None
    try:
        img = Image.open(file)
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
        img.thumbnail((1000, 1000))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        nome = f"{tipo}{targa}{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
        supabase.storage.from_("documenti").upload(nome, buf.getvalue(), {"content-type": "image/jpeg"})
        return supabase.storage.from_("documenti").get_public_url(nome)
    except: return None

def get_firma(canvas):
    if canvas.image_data is not None:
        img = Image.fromarray(canvas.image_data.astype("uint8"))
        if img.getbbox() is None: return None
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    return None

# --- MOTORE PDF MULTI-DOCUMENTO ---
def genera_pdf(c, tipo="CONTRATTO"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, safe_text(DITTA), ln=True)
    pdf.set_font("Arial", "", 8)
    pdf.cell(0, 4, safe_text(INDIRIZZO), ln=True)
    pdf.cell(0, 4, safe_text(DATI_IVA), ln=True)
    pdf.ln(10)

    n_c = f"{s(c.get('nome'))} {s(c.get('cognome'))}"
    targa = s(c.get('targa'))

    if tipo == "CONTRATTO":
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "CONTRATTO DI NOLEGGIO SCOOTER", ln=True, align="C", border="B")
        pdf.ln(5)
        pdf.set_font("Arial", "", 10)
        corpo = f"""CLIENTE: {n_c} | NAZIONALITA': {s(c.get('nazionalita'))}
NATO A: {s(c.get('luogo_nascita'))} IL {s(c.get('data_nascita'))}
RESIDENTE: {s(c.get('indirizzo_cliente'))} | C.F.: {s(c.get('codice_fiscale'))}
VEICOLO: {targa} | PATENTE: {s(c.get('numero_patente'))}
PERIODO: Dal {s(c.get('inizio'))} Al {s(c.get('fine'))} | PREZZO: EUR {s(c.get('prezzo'))}

CLAUSOLE VESSATORIE (Art. 1341-1342 c.c.):
1.⁠ ⁠Il cliente si assume la piena responsabilita per danni, furto o incendio.
2.⁠ ⁠Le sanzioni amministrative (multe) sono a totale carico del locatario.
3.⁠ ⁠Il cliente dichiara di aver controllato il veicolo e trovarlo in perfetto stato.
4.⁠ ⁠E' vietata la cessione del veicolo a terzi.
5.⁠ ⁠Autorizzazione al trattamento dati ai sensi del GDPR 679/2016."""
        pdf.multi_cell(0, 5, safe_text(corpo))
        if c.get("firma"):
            pdf.image(io.BytesIO(base64.b64decode(c["firma"])), x=130, y=pdf.get_y()+5, w=50)

    elif tipo == "MULTE":
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "COMUNICAZIONE DATI CONDUCENTE (PER VIGILI)", ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("Arial", "", 10)
        testo = f"""Spett.le Comando Polizia Locale,
La sottoscritta {TITOLARE}, titolare di {DITTA}, dichiara che il veicolo 
targato {targa} in data {s(c.get('inizio'))} era concesso in locazione a:

NOME E COGNOME: {n_c}
NATO A: {s(c.get('luogo_nascita'))} IL {s(c.get('data_nascita'))}
RESIDENTE IN: {s(c.get('indirizzo_cliente'))}
CODICE FISCALE: {s(c.get('codice_fiscale'))}
PATENTE: {s(c.get('numero_patente'))}

Si allega copia del contratto. In fede, Marianna Battaglia"""
        pdf.multi_cell(0, 5, safe_text(testo))

    elif tipo == "FATTURA":
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, f"RICEVUTA N. {s(c.get('numero_fattura'))}/A", ln=True, align="C", border="B")
        pdf.ln(10)
        pdf.set_font("Arial", "", 11)
        pdf.cell(0, 8, f"Spett.le: {n_c}", ln=True)
        pdf.cell(0, 8, f"Indirizzo: {s(c.get('indirizzo_cliente'))}", ln=True)
        pdf.ln(5)
        pdf.cell(0, 8, f"Servizio: Noleggio Scooter targa {targa}", ln=True)
        pdf.cell(0, 8, f"Periodo: {s(c.get('inizio'))} / {s(c.get('fine'))}", ln=True)
        pdf.ln(10)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, f"TOTALE PAGATO: EUR {s(c.get('prezzo'))}", align="R")

    out = pdf.output(dest="S")
    return bytes(out) if isinstance(out, bytearray) else out.encode("latin-1", "replace")

# --- LOGIN ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Password", type="password") == "1234":
        if st.button("Accedi"): st.session_state.auth = True; st.rerun()
    st.stop()

# --- APP ---
tab1, tab2 = st.tabs(["🆕 Nuovo", "📂 Archivio"])

with tab1:
    with st.form("main_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome")
        cognome = c1.text_input("Cognome")
        nazion = c2.text_input("Nazionalità")
        cf = c2.text_input("Codice Fiscale")
        luogo = c1.text_input("Luogo Nascita")
        data_n = c2.text_input("Data Nascita (GG/MM/AAAA)")
        ind = st.text_area("Indirizzo Residenza")
        
        c3, c4, c5 = st.columns(3)
        targa = c3.text_input("Targa").upper()
        patente = c4.text_input("Patente")
        prezzo = c5.number_input("Prezzo (€)", min_value=0.0)
        
        ini, fin = st.columns(2)
        inizio = ini.date_input("Inizio")
        fine = fin.date_input("Fine")
        
        f_doc = st.file_uploader("Fronte Patente")
        r_doc = st.file_uploader("Retro Patente")
        
        st.warning("Informativa: Il cliente dichiara di essere responsabile di danni e multe.")
        accetto = st.checkbox("Accetto i termini e l'informativa privacy")
        
        st.write("Firma Cliente:")
        canvas = st_canvas(height=150, width=400, stroke_width=3, key="sig")

        if st.form_submit_button("💾 SALVA TUTTO"):
            firma = get_firma(canvas)
            if not nome or not targa or not accetto or firma is None:
                st.error("Dati mancanti, firma assente o termini non accettati!")
            else:
                with st.spinner("Salvataggio..."):
                    uf = upload_foto(f_doc, targa, "F")
                    ur = upload_foto(r_doc, targa, "R")
                    supabase.table("contratti").insert({
                        "nome": nome, "cognome": cognome, "nazionalita": nazion, "codice_fiscale": cf,
                        "luogo_nascita": luogo, "data_nascita": data_n, "indirizzo_cliente": ind,
                        "targa": targa, "numero_patente": patente, "prezzo": prezzo,
                        "inizio": str(inizio), "fine": str(fine), "firma": firma,
                        "url_fronte": uf, "url_retro": ur, "numero_fattura": prossimo_numero_fattura()
                    }).execute()
                    st.success("Registrato con successo!")

with tab2:
    search = st.text_input("🔍 Cerca per Cognome o Targa").lower()
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for r in res.data:
        if search in f"{r['cognome']} {r['targa']}".lower():
            with st.expander(f"📄 {r['targa']} - {r['cognome'].upper()}"):
                col1, col2, col3 = st.columns(3)
                col1.download_button("📜 Contratto", genera_pdf(r, "CONTRATTO"), f"Contratto_{r['targa']}.pdf")
                col2.download_button("💰 Fattura", genera_pdf(r, "FATTURA"), f"Fattura_{r['id']}.pdf")
                col3.download_button("🚨 Modulo Vigili", genera_pdf(r, "MULTE"), f"Vigili_{r['targa']}.pdf")
                if r.get("url_fronte"): st.image(r["url_fronte"], width=300)
