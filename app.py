import streamlit as st
from supabase import create_client, Client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from fpdf import FPDF
import io
import base64
from datetime import datetime
import re

# --- CONFIGURAZIONE ---
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
    """Recupera il numero più alto ignorando formati non numerici"""
    try:
        res = supabase.table("contratti").select("numero_fattura").execute()
        numeri_validi = []
        for r in res.data:
            val = r.get("numero_fattura")
            # Prova a convertire in numero. Se è un testo come '2026-xxx', fallisce e passa oltre
            try:
                numeri_validi.append(int(val))
            except (ValueError, TypeError):
                continue
        
        if numeri_validi:
            return max(numeri_validi) + 1
        return 1
    except Exception as e:
        return 1

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

# --- CLASSE PDF PROFESSIONALE ---
class ProPDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 6, safe_text(DITTA), ln=True)
        self.set_font("Arial", "", 8)
        self.cell(0, 4, safe_text(f"{INDIRIZZO} | {DATI_IVA}"), ln=True)
        self.line(10, 25, 200, 25)
        self.ln(10)

def genera_pdf(c, tipo="CONTRATTO"):
    pdf = ProPDF()
    pdf.add_page()
    n_doc = s(c.get('numero_fattura'))
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, safe_text(f"{tipo} DI NOLEGGIO N. {n_doc}"), ln=True, align="C", border="B")
    pdf.ln(5)
    
    pdf.set_font("Arial", "", 10)
    info = (f"CLIENTE: {s(c.get('nome'))} {s(c.get('cognome'))}\n"
            f"NATO A: {s(c.get('luogo_nascita'))} IL {s(c.get('data_nascita'))}\n"
            f"RESIDENTE: {s(c.get('indirizzo_cliente'))}\n\n"
            f"VEICOLO: {s(c.get('modello'))} | TARGA: {s(c.get('targa'))}\n"
            f"INIZIO: {s(c.get('inizio'))} | FINE: {s(c.get('fine'))}\n"
            f"PREZZO: EUR {s(c.get('prezzo'))} | DEPOSITO: EUR {s(c.get('deposito'))}\n"
            f"BENZINA: {s(c.get('benzina'))}")
    pdf.multi_cell(0, 6, safe_text(info), border=1)
    
    firma_b64 = c.get("firma")
    if firma_b64 and len(str(firma_b64)) > 100:
        try:
            pdf.image(io.BytesIO(base64.b64decode(firma_b64)), x=140, y=pdf.get_y()+5, w=45)
        except: pass

    out = pdf.output(dest="S")
    return bytes(out) if not isinstance(out, str) else out.encode("latin-1", "replace")

# --- LOGIN ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    pwd = st.text_input("Password Gestionale", type="password")
    if st.button("ACCEDI"):
        if pwd == "1234": st.session_state.auth = True; st.rerun()
        else: st.error("Password errata")
    st.stop()

# --- APP ---
t1, t2 = st.tabs(["🆕 Emissione Noleggio", "📂 Archivio Storico"])

with t1:
    with st.form("form_finale_v9"):
        st.subheader("Anagrafica Cliente")
        c1, c2, c3 = st.columns(3)
        nome = c1.text_input("Nome")
        cognome = c2.text_input("Cognome")
        tel = c3.text_input("Telefono")
        
        c4, c5, c6 = st.columns(3)
        cf = c4.text_input("Codice Fiscale")
        luo = c5.text_input("Luogo Nascita")
        dat_n = c6.text_input("Data Nascita")
        
        ind = st.text_input("Indirizzo Residenza")
        naz = st.text_input("Nazionalità")
        
        st.subheader("Dati Scooter")
        c7, c8, c9 = st.columns(3)
        mod = c7.text_input("Modello")
        tar = c8.text_input("Targa").upper()
        ben = c9.selectbox("Benzina", ["1/8", "1/4", "1/2", "3/4", "Pieno"])
        pat = st.text_input("N. Patente")
        danni = st.text_area("Note Danni")
        
        c10, c11, c12, c13 = st.columns(4)
        prz = c10.number_input("Prezzo (€)", min_value=0.0)
        dep = c11.number_input("Deposito (€)", min_value=0.0)
        ini = c12.date_input("Inizio")
        fin = c13.date_input("Fine")
        
        st.subheader("Documenti e Firma")
        f_p = st.file_uploader("Foto FRONTE Patente", type=['jpg','png','jpeg'])
        r_p = st.file_uploader("Foto RETRO Patente", type=['jpg','png','jpeg'])
        
        canvas = st_canvas(height=150, width=450, stroke_width=3, key="sig_v9")
        accetto = st.checkbox("Il cliente accetta i termini legali e clausole sanzioni")

        if st.form_submit_button("REGISTRA NOLEGGIO"):
            if not nome or not tar or not accetto:
                st.error("Dati obbligatori mancanti!")
            else:
                with st.spinner("Salvataggio in corso..."):
                    # Firma
                    img_f = Image.fromarray(canvas.image_data.astype("uint8"))
                    buf_f = io.BytesIO()
                    img_f.save(buf_f, format="PNG")
                    firma_b64 = base64.b64encode(buf_f.getvalue()).decode()
                    
                    # Foto
                    u_f = upload_foto(f_p, tar, "F")
                    u_r = upload_foto(r_p, tar, "R")
                    
                    # Numero Fattura (Correzione Errore Base 10)
                    num_f = get_prossimo_numero()
                    
                    payload = {
                        "nome": nome, "cognome": cognome, "telefono": tel, "nazionalita": naz,
                        "codice_fiscale": cf, "luogo_nascita": luo, "data_nascita": dat_n,
                        "indirizzo_cliente": ind, "modello": mod, "targa": tar,
                        "numero_patente": pat, "benzina": ben, "note_danni": danni,
                        "prezzo": prz, "deposito": dep, "inizio": str(ini), "fine": str(fin),
                        "firma": firma_b64, "url_fronte": u_f, "url_retro": u_r,
                        "numero_fattura": num_f, "data_creazione": datetime.now().isoformat()
                    }
                    
                    try:
                        supabase.table("contratti").insert(payload).execute()
                        st.success(f"CONTRATTO N. {num_f} SALVATO!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Errore DB: {e}")

with t2:
    st.subheader("Cerca Contratti")
    search = st.text_input("Targa o Cognome").lower()
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    
    for r in res.data:
        if search in f"{r['cognome']} {r['targa']}".lower():
            with st.expander(f"N. {r['numero_fattura']} - {r['targa']} ({r['cognome']})"):
                c1, c2, c3 = st.columns(3)
                c1.download_button("📜 Contratto", genera_pdf(r, "CONTRATTO"), f"C_{r['id']}.pdf", key=f"c_{r['id']}")
                c2.download_button("💰 Ricevuta", genera_pdf(r, "FATTURA"), f"F_{r['id']}.pdf", key=f"f_{r['id']}")
                c3.download_button("🚨 Vigili", genera_pdf(r, "VIGILI"), f"V_{r['id']}.pdf", key=f"v_{r['id']}")
                
                if r.get("url_fronte"): st.image(r["url_fronte"], caption="Patente", width=400)
