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

def upload_to_supabase(file, targa, prefix):
    try:
        file_name = f"{prefix}{targa}{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        bucket = "documenti"
        supabase.storage.from_(bucket).upload(file_name, file.getvalue())
        return supabase.storage.from_(bucket).get_public_url(file_name)
    except Exception as e:
        return None

# --- GENERATORE PDF (CORRETTO PER TIPI DIVERSI) ---
def genera_pdf_tipo(c, tipo):
    pdf = FPDF()
    pdf.add_page()
    
    # Intestazione per tutti
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, safe_text(DITTA), ln=True)
    pdf.set_font("Arial", "", 9)
    pdf.cell(0, 5, safe_text(INDIRIZZO_FISCALE), ln=True)
    pdf.cell(0, 5, safe_text(DATI_IVA), ln=True)
    pdf.ln(10)

    if tipo == "CONTRATTO":
        pdf.set_font("Arial", "B", 14); pdf.cell(0, 10, "CONTRATTO DI NOLEGGIO", ln=True, align="C", border="B"); pdf.ln(8)
        pdf.set_font("Arial", "", 10)
        testo = f"Cliente: {c.get('nome')} {c.get('cognome')}\nNato a: {c.get('luogo_nascita')} il {c.get('data_nascita')}\nTarga: {c.get('targa')}\nPeriodo: {c.get('inizio')} / {c.get('fine')}"
        pdf.multi_cell(0, 6, safe_text(testo))
        pdf.ln(5)
        pdf.set_font("Arial", "B", 9); pdf.cell(0, 5, "CLAUSOLE:", ln=True)
        pdf.set_font("Arial", "", 8); pdf.multi_cell(0, 5, safe_text("1. Responsabilita danni/furto.\n2. Multe a carico cliente.\n3. Carburante stesso livello."))

    elif tipo == "FATTURA":
        pdf.set_font("Arial", "B", 14); pdf.cell(0, 10, "RICEVUTA DI PAGAMENTO", ln=True, align="C", border="B"); pdf.ln(8)
        pdf.set_font("Arial", "B", 12); pdf.cell(0, 10, f"Ricevuta n. {c.get('numero_fattura')}", ln=True)
        pdf.ln(10)
        pdf.set_font("Arial", "B", 16); pdf.cell(0, 15, f"TOTALE INCASSATO: EUR {c.get('prezzo')}", ln=True, border=1, align="C")

    elif tipo == "MULTE":
        pdf.set_font("Arial", "B", 14); pdf.cell(0, 10, "COMUNICAZIONE LOCAZIONE (D.P.R. 445/2000)", ln=True, align="C", border="B"); pdf.ln(8)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 5, "Spett. le Polizia Locale", ln=True, align="R"); pdf.ln(5)
        testo_m = (f"La sottoscritta BATTAGLIA MARIANNA dichiara che il veicolo "
                   f"targato {c.get('targa')} il giorno {c.get('inizio')} era concesso a:\n\n"
                   f"NOME: {c.get('nome').upper()} {c.get('cognome').upper()}\n"
                   f"NATO A: {c.get('luogo_nascita')} IL {c.get('data_nascita')}\n"
                   f"PATENTE: {c.get('numero_patente')}\n\n"
                   f"Si allega contratto conforme all'originale.")
        pdf.multi_cell(0, 5, safe_text(testo_m))

    # Firma Cliente
    if c.get("firma"):
        try:
            pdf.ln(10)
            img_d = base64.b64decode(c["firma"])
            pdf.image(io.BytesIO(img_d), x=130, y=pdf.get_y(), w=50)
        except: pass
    pdf.ln(20); pdf.set_font("Arial", "B", 10); pdf.cell(0, 10, "Firma del Cliente", ln=True, align="R")
    
    return bytes(pdf.output())

# --- INTERFACCIA ---
if "autenticato" not in st.session_state: st.session_state.autenticato = False
if not st.session_state.autenticato:
    pwd = st.text_input("Password", type="password")
    if st.button("Entra"):
        if pwd == st.secrets["APP_PASSWORD"]: st.session_state.autenticato = True; st.rerun()
else:
    with st.form("main_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Nome"); cognome = col1.text_input("Cognome")
        targa = col2.text_input("Targa").upper(); prezzo = col2.number_input("Prezzo (€)", min_value=0.0)
        l_nas = col1.text_input("Luogo Nascita"); d_nas = col1.text_input("Data Nascita")
        pat = col2.text_input("Patente"); dep = col2.number_input("Deposito (€)", min_value=0.0)
        d_in = col1.date_input("Inizio"); d_out = col2.date_input("Fine")
        
        st.subheader("📸 Foto Patente")
        f1 = st.file_uploader("Fronte", type=['jpg','png'])
        f2 = st.file_uploader("Retro", type=['jpg','png'])
        
        st.write("✍️ Firma Cliente:")
        canvas = st_canvas(stroke_width=3, stroke_color="#000", background_color="#eee", height=150, width=400, key="canvas_v7")
        
        if st.form_submit_button("SALVA TUTTO"):
            # Gestione Firma
            firma_b64 = ""
            if canvas.image_data is not None:
                img = Image.fromarray(canvas.image_data.astype("uint8"))
                buf = io.BytesIO(); img.save(buf, format="PNG"); firma_b64 = base64.b64encode(buf.getvalue()).decode()
            
            # Gestione Foto
            url1 = upload_to_supabase(f1, targa, "fronte") if f1 else None
            url2 = upload_to_supabase(f2, targa, "retro") if f2 else None

            n_fatt = prossimo_numero_fattura()
            dati = {
                "nome": nome, "cognome": cognome, "targa": targa, "prezzo": prezzo, "deposito": dep,
                "inizio": str(d_in), "fine": str(d_out), "firma": firma_b64, "numero_fattura": n_fatt,
                "luogo_nascita": l_nas, "data_nascita": d_nas, "numero_patente": pat,
                "url_fronte": url1, "url_retro": url2
            }
            supabase.table("contratti").insert(dati).execute()
            st.success("Salvato!"); st.rerun()

    # --- ARCHIVIO ---
    st.divider()
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"Ricevuta {c['numero_fattura']} - {c['nome']} {c['cognome']} ({c['targa']})"):
            # Generiamo i PDF al momento del clic per evitare che siano uguali
            pdf_con = genera_pdf_tipo(c, "CONTRATTO")
            pdf_ric = genera_pdf_tipo(c, "FATTURA")
            pdf_mul = genera_pdf_tipo(c, "MULTE")
            
            c1, c2, c3 = st.columns(3)
            c1.download_button("📜 Contratto", pdf_con, f"Contratto_{c['id']}.pdf", key=f"c_{c['id']}")
            c2.download_button("💰 Ricevuta", pdf_ric, f"Ricevuta_{c['id']}.pdf", key=f"r_{c['id']}")
            c3.download_button("🚨 Multe", pdf_mul, f"Multe_{c['id']}.pdf", key=f"m_{c['id']}")
            
            if c.get("url_fronte"): st.link_button("👁️ Vedi Foto Fronte", c["url_fronte"])
            if c.get("url_retro"): st.link_button("👁️ Vedi Foto Retro", c["url_retro"])
