import streamlit as st
from supabase import create_client, Client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from fpdf import FPDF
import io
import base64
from datetime import datetime

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
    """Recupera il numero più alto e aggiunge 1"""
    try:
        # Cerchiamo il valore massimo nella colonna numero_fattura
        res = supabase.table("contratti").select("numero_fattura").order("numero_fattura", desc=True).limit(1).execute()
        if res.data and len(res.data) > 0:
            ultimo = res.data[0].get("numero_fattura")
            if ultimo:
                return int(ultimo) + 1
        return 1
    except Exception as e:
        st.warning(f"Errore recupero numero: {e}")
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

# --- PDF ---
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
    pdf.cell(0, 10, safe_text(f"{tipo} N. {n_doc}"), ln=True, align="C", border="B")
    pdf.ln(5)
    pdf.set_font("Arial", "", 10)
    info = f"CLIENTE: {s(c.get('nome'))} {s(c.get('cognome'))}\nTARGA: {s(c.get('targa'))}\nMODELLO: {s(c.get('modello'))}\nINIZIO: {s(c.get('inizio'))} | FINE: {s(c.get('fine'))}\nPREZZO: EUR {s(c.get('prezzo'))}"
    pdf.multi_cell(0, 6, safe_text(info), border=1)
    
    firma_b64 = c.get("firma")
    if firma_b64 and len(str(firma_b64)) > 50:
        try:
            pdf.image(io.BytesIO(base64.b64decode(firma_b64)), x=140, y=pdf.get_y()+5, w=40)
        except: pass

    out = pdf.output(dest="S")
    return bytes(out) if not isinstance(out, str) else out.encode("latin-1", "replace")

# --- LOGIN ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    pwd = st.text_input("Password", type="password")
    if st.button("Accedi"):
        if pwd == "1234": st.session_state.auth = True; st.rerun()
        else: st.error("Password errata")
    st.stop()

# --- APP ---
t1, t2 = st.tabs(["🆕 Nuovo Noleggio", "📂 Archivio"])

with t1:
    with st.form("form_v8", clear_on_submit=False): # Teniamo i dati in caso di errore
        st.subheader("Dati Cliente e Veicolo")
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome")
        cognome = c2.text_input("Cognome")
        targa = c1.text_input("Targa").upper()
        modello = c2.text_input("Modello")
        
        c3, c4, c5 = st.columns(3)
        prezzo = c3.number_input("Prezzo (€)", min_value=0.0)
        deposito = c4.number_input("Deposito (€)", min_value=0.0)
        benzina = c5.selectbox("Benzina", ["1/8", "1/4", "1/2", "3/4", "Pieno"])
        
        c6, c7 = st.columns(2)
        inizio = c6.date_input("Inizio", datetime.now())
        fine = c7.date_input("Fine", datetime.now())
        
        tel = st.text_input("Telefono")
        naz = st.text_input("Nazionalità")
        cf = st.text_input("Codice Fiscale")
        luo = st.text_input("Luogo Nascita")
        dat_n = st.text_input("Data Nascita")
        ind = st.text_input("Indirizzo Residenza")
        pat = st.text_input("N. Patente")
        danni = st.text_area("Note Danni")
        
        st.subheader("Documenti e Firma")
        f_p = st.file_uploader("Fronte Patente", type=['jpg','png'])
        r_p = st.file_uploader("Retro Patente", type=['jpg','png'])
        
        canvas = st_canvas(height=150, width=450, stroke_width=3, key="sig_v8")
        conferma = st.checkbox("Accetto i termini legali")

        if st.form_submit_button("💾 SALVA CONTRATTO"):
            if not nome or not targa or not conferma:
                st.error("Dati obbligatori mancanti!")
            else:
                with st.spinner("Salvataggio in corso..."):
                    try:
                        # 1. Prepariamo Firma e Foto
                        img_f = Image.fromarray(canvas.image_data.astype("uint8"))
                        buf_f = io.BytesIO()
                        img_f.save(buf_f, format="PNG")
                        firma_b64 = base64.b64encode(buf_f.getvalue()).decode()
                        
                        u_f = upload_foto(f_p, targa, "F")
                        u_r = upload_foto(r_p, targa, "R")
                        
                        # 2. Calcoliamo il numero
                        num_n = get_prossimo_numero()
                        
                        # 3. Creiamo l'oggetto da inviare
                        data_save = {
                            "nome": nome, "cognome": cognome, "telefono": tel, "nazionalita": naz,
                            "codice_fiscale": cf, "luogo_nascita": luo, "data_nascita": dat_n,
                            "indirizzo_cliente": ind, "modello": modello, "targa": targa,
                            "numero_patente": pat, "benzina": benzina, "note_danni": danni,
                            "prezzo": prezzo, "deposito": deposito, "inizio": str(inizio), "fine": str(fine),
                            "firma": firma_b64, "url_fronte": u_f, "url_retro": u_r,
                            "numero_fattura": num_n, "data_creazione": datetime.now().isoformat()
                        }
                        
                        # 4. ESEGUIAMO L'INSERIMENTO
                        res = supabase.table("contratti").insert(data_save).execute()
                        
                        if len(res.data) > 0:
                            st.success(f"✅ CONTRATTO N. {num_n} SALVATO NEL DATABASE!")
                            st.balloons()
                        else:
                            st.error("Errore: Il database non ha restituito dati. Verifica i permessi della tabella.")
                    except Exception as e:
                        st.error(f"❌ ERRORE CRITICO: {e}")

with t2:
    st.subheader("Registro Contratti")
    # Tasto per ricaricare i dati manualmente
    if st.button("🔄 Aggiorna Archivio"): st.rerun()
    
    search = st.text_input("Cerca per Cognome o Targa").lower()
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    
    if not res.data:
        st.info("Nessun contratto trovato nel database.")
    
    for r in res.data:
        if search in f"{r['cognome']} {r['targa']}".lower():
            with st.expander(f"N. {r['numero_fattura']} - {r['targa']} ({r['cognome']})"):
                c1, c2, c3 = st.columns(3)
                c1.download_button("📜 Contratto", genera_pdf(r, "CONTRATTO"), f"C_{r['id']}.pdf", key=f"c_{r['id']}")
                c2.download_button("💰 Ricevuta", genera_pdf(r, "FATTURA"), f"F_{r['id']}.pdf", key=f"f_{r['id']}")
                c3.download_button("🚨 Vigili", genera_pdf(r, "VIGILI"), f"V_{r['id']}.pdf", key=f"v_{r['id']}")
                
                if r.get("url_fronte"): st.image(r["url_fronte"], caption="Patente", width=300)
