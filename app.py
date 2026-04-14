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

URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- UTILITY ---
def s(v): return "" if v is None else str(v)

def safe_text(text):
    return s(text).encode("latin-1", "replace").decode("latin-1")

def get_prossimo_numero():
    try:
        res = supabase.table("contratti").select("numero_fattura").order("numero_fattura", desc=True).limit(1).execute()
        if res.data and res.data[0].get("numero_fattura"):
            return int(res.data[0]["numero_fattura"]) + 1
        return 1
    except: return 1

# --- CLASSE PDF PROFESSIONALE ---
class ProPDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 6, safe_text(DITTA), ln=True)
        self.set_font("Arial", "", 8)
        self.cell(0, 4, safe_text(f"{INDIRIZZO} | {DATI_IVA}"), ln=True)
        self.line(10, 25, 200, 25)
        self.ln(10)

def genera_pdf_professionale(c, tipo="CONTRATTO"):
    pdf = ProPDF()
    pdf.add_page()
    n_doc = s(c.get('numero_fattura'))
    data_doc = s(c.get('data_creazione'))[:10] if c.get('data_creazione') else datetime.now().strftime("%Y-%m-%d")

    pdf.set_font("Arial", "B", 14)
    if tipo == "CONTRATTO": titolo = f"CONTRATTO DI NOLEGGIO N. {n_doc}"
    elif tipo == "FATTURA": titolo = f"RICEVUTA FISCALE N. {n_doc}"
    else: titolo = "DICHIARAZIONE DATI CONDUCENTE"
    
    pdf.cell(0, 10, safe_text(titolo), ln=True, align="C", border="B")
    pdf.set_font("Arial", "I", 9)
    pdf.cell(0, 8, f"Data: {data_doc}", ln=True, align="R")
    pdf.ln(5)

    # Tabella Cliente
    pdf.set_fill_color(245, 245, 245)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, " DATI CLIENTE", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "", 10)
    info = f"Nome: {s(c.get('nome'))} {s(c.get('cognome'))} | CF: {s(c.get('codice_fiscale'))}\nNato a: {s(c.get('luogo_nascita'))} ({s(c.get('data_nascita'))})\nResidenza: {s(c.get('indirizzo_cliente'))} | Tel: {s(c.get('telefono'))}"
    pdf.multi_cell(0, 6, safe_text(info), border=1)
    pdf.ln(5)

    # Dati Veicolo
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, " DETTAGLI NOLEGGIO", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "", 10)
    pdf.cell(95, 7, safe_text(f"Modello: {c.get('modello')}"), border=1)
    pdf.cell(95, 7, safe_text(f"Targa: {c.get('targa')}"), border=1, ln=True)
    pdf.cell(95, 7, safe_text(f"Inizio: {c.get('inizio')}"), border=1)
    pdf.cell(95, 7, safe_text(f"Fine: {c.get('fine')}"), border=1, ln=True)
    pdf.cell(95, 7, safe_text(f"Benzina: {c.get('benzina')}"), border=1)
    pdf.cell(95, 7, safe_text(f"Prezzo: EUR {c.get('prezzo')}"), border=1, ln=True)

    if tipo == "CONTRATTO":
        pdf.ln(5)
        pdf.set_font("Arial", "B", 8)
        pdf.cell(0, 5, "CLAUSOLE:", ln=True)
        pdf.set_font("Arial", "", 7)
        pdf.multi_cell(0, 4, safe_text("Responsabilita danni, furto e multe a carico del locatario (artt. 1341-1342 c.c.). Autorizzazione dati GDPR."))
        
        firma_b64 = c.get("firma")
        if firma_b64 and len(str(firma_b64)) > 50:
            try:
                pdf.image(io.BytesIO(base64.b64decode(firma_b64)), x=140, y=pdf.get_y()+2, w=40)
            except: pass

    out = pdf.output(dest="S")
    return bytes(out) if not isinstance(out, str) else out.encode("latin-1", "replace")

# --- LOGIN ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Password", type="password") == "1234":
        if st.button("Accedi"): st.session_state.auth = True; st.rerun()
    st.stop()

# --- APP ---
t1, t2 = st.tabs(["🆕 Nuovo", "📂 Archivio"])

with t1:
    with st.form("form_final", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        n = c1.text_input("Nome")
        cog = c2.text_input("Cognome")
        tel = c3.text_input("Telefono")
        naz = c1.text_input("Nazionalità")
        cf = c2.text_input("Codice Fiscale")
        luo = c3.text_input("Luogo Nascita")
        dat_n = c1.text_input("Data Nascita")
        ind = st.text_input("Indirizzo")
        
        c4, c5, c6 = st.columns(3)
        mod = c4.text_input("Modello")
        tar = c5.text_input("Targa").upper()
        ben = c6.selectbox("Benzina", ["1/8", "1/4", "1/2", "3/4", "PIENO"])
        pat = st.text_input("N. Patente")
        danni = st.text_area("Note Danni")
        
        c7, c8, c9, c10 = st.columns(4)
        prz = c7.number_input("Prezzo (€)", min_value=0.0)
        dep = c8.number_input("Deposito (€)", min_value=0.0)
        ini = c9.date_input("Inizio")
        fin = c10.date_input("Fine")
        
        canvas = st_canvas(height=120, width=400, stroke_width=3, key="canvas_main")
        accetto = st.checkbox("Accetto termini legali")

        if st.form_submit_button("REGISTRA"):
            if not n or not tar or not accetto:
                st.error("Mancano dati!")
            else:
                img_f = Image.fromarray(canvas.image_data.astype("uint8"))
                buf_f = io.BytesIO()
                img_f.save(buf_f, format="PNG")
                firma_b64 = base64.b64encode(buf_f.getvalue()).decode()
                num_n = get_prossimo_numero()
                
                data_save = {
                    "nome": n, "cognome": cog, "telefono": tel, "nazionalita": naz,
                    "codice_fiscale": cf, "luogo_nascita": luo, "data_nascita": dat_n,
                    "indirizzo_cliente": ind, "modello": mod, "targa": tar,
                    "numero_patente": pat, "benzina": ben, "note_danni": danni,
                    "prezzo": prz, "deposito": dep, "inizio": str(ini), "fine": str(fin),
                    "firma": firma_b64, "numero_fattura": num_n, "data_creazione": datetime.now().isoformat()
                }
                supabase.table("contratti").insert(data_save).execute()
                st.success(f"Salvato N. {num_n}!")

with t2:
    search = st.text_input("🔍 Cerca...").lower()
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    for r in res.data:
        if search in f"{r['cognome']} {r['targa']}".lower():
            # USIAMO ID UNICI PER I PULSANTI (Parametro key)
            with st.expander(f"DOC N. {r['numero_fattura']} | {r['targa']} - {r['cognome']}"):
                col1, col2, col3 = st.columns(3)
                col1.download_button("📜 Contratto", genera_pdf_professionale(r, "CONTRATTO"), 
                                   f"Contr_{r['numero_fattura']}.pdf", key=f"btn_c_{r['id']}")
                col2.download_button("💰 Ricevuta", genera_pdf_professionale(r, "FATTURA"), 
                                   f"Fatt_{r['numero_fattura']}.pdf", key=f"btn_f_{r['id']}")
                col3.download_button("🚨 Vigili", genera_pdf_professionale(r, "VIGILI"), 
                                   f"Vigili_{r['numero_fattura']}.pdf", key=f"btn_v_{r['id']}")
