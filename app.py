import streamlit as st
import datetime
from fpdf import FPDF
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io
import base64

st.set_page_config(layout="wide", page_title="Battaglia Rent Pro")

# --- DATI AZIENDA ---
DITTA = "BATTAGLIA MARIANNA"
INDIRIZZO_FISCALE = "Via Cognole, 5 - 80075 Forio (NA)"
DATI_IVA = "C.F. BTTMNN87A53Z112S - P. IVA 10252601215"

# --- DATABASE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def safe_text(text):
    if text is None: return ""
    return str(text).encode("latin-1", "replace").decode("latin-1")

def prossimo_numero_fattura():
    try:
        res = supabase.table("contratti").select("numero_fattura").order("numero_fattura", desc=True).limit(1).execute()
        if res.data and res.data[0]["numero_fattura"]:
            return int(res.data[0]["numero_fattura"]) + 1
        return 1
    except: return 1

def upload_image(file, name):
    """Carica l'immagine nello Storage di Supabase e restituisce l'URL"""
    try:
        path = f"public/{name}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
        supabase.storage.from_("documenti").upload(path, file.getvalue())
        return supabase.storage.from_("documenti").get_public_url(path)
    except:
        return None

# --- GENERATORE PDF ---
def genera_pdf_tipo(c, tipo="CONTRATTO"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 6, safe_text(DITTA), ln=True)
    pdf.set_font("Arial", "", 9)
    pdf.cell(0, 5, safe_text(INDIRIZZO_FISCALE), ln=True)
    pdf.cell(0, 5, safe_text(DATI_IVA), ln=True)
    pdf.ln(10)

    titoli = {"CONTRATTO": "CONTRATTO DI NOLEGGIO", "FATTURA": "RICEVUTA DI PAGAMENTO", "MULTE": "MODULO DICHIARAZIONE CONDUCENTE"}
    pdf.set_font("Arial", "B", 15)
    pdf.cell(0, 10, safe_text(titoli.get(tipo, "")), ln=True, align="C", border="B")
    pdf.ln(8)

    pdf.set_font("Arial", "", 10)
    testo = (f"Ricevuta N: {c.get('numero_fattura')}\n"
             f"Cliente: {c.get('nome')} {c.get('cognome')}\n"
             f"CF: {c.get('codice_fiscale')} - Patente: {c.get('numero_patente')}\n"
             f"Targa: {c.get('targa')}\n"
             f"Periodo: dal {c.get('inizio')} al {c.get('fine')}")
    pdf.multi_cell(0, 6, safe_text(testo))
    
    if tipo == "MULTE":
        pdf.ln(10)
        pdf.multi_cell(0, 6, safe_text("Il sottoscritto dichiara di essere stato alla guida del veicolo sopra indicato e si assume la responsabilità di eventuali infrazioni."))

    if c.get("firma"):
        try:
            pdf.ln(10)
            img_data = base64.b64decode(c["firma"])
            pdf.image(io.BytesIO(img_data), x=130, y=pdf.get_y(), w=50)
        except: pass

    pdf.ln(30)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 10, "Firma del Cliente", ln=True, align="R")
    return bytes(pdf.output())

# --- INTERFACCIA ---
if "autenticato" not in st.session_state: st.session_state.autenticato = False

if not st.session_state.autenticato:
    pwd = st.text_input("Password", type="password")
    if st.button("Entra"):
        if pwd == st.secrets["APP_PASSWORD"]: 
            st.session_state.autenticato = True
            st.rerun()
else:
    st.header(f"Nuovo Noleggio - {DITTA}")
    
    with st.form("form_completo", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome")
            cognome = st.text_input("Cognome")
            cf = st.text_input("Codice Fiscale")
            patente = st.text_input("Numero Patente")
        with col2:
            targa = st.text_input("Targa").upper()
            prezzo = st.number_input("Prezzo (€)", min_value=0.0)
            inizio = st.date_input("Inizio")
            fine = st.date_input("Fine")

        st.subheader("📸 Foto Documenti (per Vigili)")
        f_fronte = st.file_uploader("Fronte Patente", type=['jpg', 'jpeg', 'png'])
        f_retro = st.file_uploader("Retro Patente", type=['jpg', 'jpeg', 'png'])

        st.subheader("✍️ Firma Cliente")
        canvas = st_canvas(stroke_width=3, stroke_color="#000", background_color="#eee", height=150, width=400, key="canvas_final")
        
        accetto = st.checkbox("Accetto Condizioni e Privacy GDPR")
        
        if st.form_submit_button("SALVA E GENERA"):
            if not accetto or not nome or not targa:
                st.error("Compila i campi obbligatori!")
            else:
                # 1. Carica Immagini nello Storage
                url_f = upload_image(f_fronte, f"fronte_{targa}") if f_fronte else None
                url_r = upload_image(f_retro, f"retro_{targa}") if f_retro else None

                # 2. Gestione Firma
                firma_b64 = ""
                if canvas.image_data is not None:
                    img = Image.fromarray(canvas.image_data.astype("uint8"))
                    buf = io.BytesIO(); img.save(buf, format="PNG")
                    firma_b64 = base64.b64encode(buf.getvalue()).decode()

                n_fatt = prossimo_numero_fattura()
                dati = {
                    "nome": nome, "cognome": cognome, "codice_fiscale": cf, "targa": targa,
                    "prezzo": prezzo, "inizio": str(inizio), "fine": str(fine), "numero_patente": patente,
                    "firma": firma_b64, "numero_fattura": n_fatt, "url_fronte": url_f, "url_retro": url_r
                }
                
                supabase.table("contratti").insert(dati).execute()
                st.success(f"Contratto n. {n_fatt} salvato con foto!")
                st.rerun()

    st.divider()
    st.subheader("Archivio")
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"{c['nome']} {c['cognome']} - {c['targa']}"):
            c1, c2, c3 = st.columns(3)
            c1.download_button("📜 Contratto", genera_pdf_tipo(c, "CONTRATTO"), f"Contratto_{c['id']}.pdf")
            c2.download_button("🚨 Modulo Multe", genera_pdf_tipo(c, "MULTE"), f"Multe_{c['id']}.pdf")
            
            # Tasti per vedere le foto se caricate
            if c.get("url_fronte"): st.link_button("👁️ Vedi Fronte Patente", c["url_fronte"])
            if c.get("url_retro"): st.link_button("👁️ Vedi Retro Patente", c["url_retro"])
