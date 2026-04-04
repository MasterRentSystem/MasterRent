import streamlit as st
import datetime
from fpdf import FPDF
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io
import base64

# Configurazione Pagina
st.set_page_config(layout="wide", page_title="Battaglia Rent Pro")

# --- DATI AZIENDA ---
DITTA = "BATTAGLIA MARIANNA"
INDIRIZZO_FISCALE = "Via Cognole, 5 - 80075 Forio (NA)"
DATI_IVA = "C.F. BTTMNN87A53Z112S - P. IVA 10252601215"

# --- CONNESSIONE DATABASE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def safe_text(text):
    if text is None: return ""
    return str(text).encode("latin-1", "replace").decode("latin-1")

def prossimo_numero_fattura():
    try:
        # Cerchiamo il numero più alto già salvato
        res = supabase.table("contratti").select("numero_fattura").order("numero_fattura", desc=True).limit(1).execute()
        if res.data and res.data[0]["numero_fattura"]:
            return int(res.data[0]["numero_fattura"]) + 1
        return 1
    except:
        return 1

def upload_image(file, name, targa):
    try:
        path = f"documenti/{targa}{name}{datetime.datetime.now().strftime('%H%M%S')}.jpg"
        supabase.storage.from_("documenti").upload(path, file.getvalue())
        return supabase.storage.from_("documenti").get_public_url(path)
    except: return None

# --- GENERATORE PDF UNICO PER TUTTI I TIPI ---
def genera_pdf_tipo(c, tipo):
    pdf = FPDF()
    pdf.add_page()
    
    # 1. Intestazione fissa per tutti
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, safe_text(DITTA), ln=True)
    pdf.set_font("Arial", "", 9)
    pdf.cell(0, 5, safe_text(INDIRIZZO_FISCALE), ln=True)
    pdf.cell(0, 5, safe_text(DATI_IVA), ln=True)
    pdf.ln(10)

    # 2. Titolo variabile
    titoli = {
        "CONTRATTO": "CONTRATTO DI NOLEGGIO / RENTAL AGREEMENT",
        "FATTURA": "RICEVUTA DI PAGAMENTO / PAYMENT RECEIPT",
        "MULTE": "COMUNICAZIONE LOCAZIONE VEICOLO (D.P.R. 445/2000)"
    }
    pdf.set_font("Arial", "B", 15)
    pdf.cell(0, 10, safe_text(titoli.get(tipo, "")), ln=True, align="C", border="B")
    pdf.ln(8)

    # 3. Logica differenziata
    if tipo == "CONTRATTO":
        pdf.set_font("Arial", "B", 10); pdf.cell(0, 7, "DETTAGLI NOLEGGIO:", ln=True)
        pdf.set_font("Arial", "", 10)
        testo = f"Cliente: {c.get('nome')} {c.get('cognome')}\nNato a: {c.get('luogo_nascita')} il {c.get('data_nascita')}\nTarga: {c.get('targa')}\nPeriodo: {c.get('inizio')} / {c.get('fine')}"
        pdf.multi_cell(0, 6, safe_text(testo))
        pdf.ln(5)
        pdf.set_font("Arial", "B", 10); pdf.cell(0, 7, "CLAUSOLE:", ln=True)
        pdf.set_font("Arial", "", 8)
        pdf.multi_cell(0, 5, safe_text("1. Responsabilita danni/furto.\n2. Multe a carico cliente.\n3. Carburante stesso livello.\n4. Deposito: Euro " + str(c.get('deposito', 0))))

    elif tipo == "FATTURA":
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, f"Ricevuta n. {c.get('numero_fattura')}", ln=True)
        pdf.ln(10)
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 15, f"TOTALE INCASSATO: EUR {c.get('prezzo')}", ln=True, border=1, align="C")

    elif tipo == "MULTE":
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 5, "Spett. le Polizia Locale", ln=True, align="R"); pdf.ln(5)
        pdf.set_font("Arial", "B", 10); pdf.cell(0, 5, "OGGETTO: COMUNICAZIONE LOCAZIONE VEICOLO", ln=True); pdf.ln(5)
        pdf.set_font("Arial", "", 10)
        testo_m = (f"La sottoscritta BATTAGLIA MARIANNA, ai sensi del D.P.R. 445/2000, dichiara che il veicolo "
                   f"targato {c.get('targa')} in data {c.get('inizio')} era concesso in locazione a:\n\n"
                   f"NOME: {c.get('nome').upper()} {c.get('cognome').upper()}\n"
                   f"NATO A: {c.get('luogo_nascita')} IL {c.get('data_nascita')}\n"
                   f"PATENTE: {c.get('numero_patente')}\n\n"
                   f"In fede, Marianna Battaglia")
        pdf.multi_cell(0, 5, safe_text(testo_m))

    # Firma (Solo per chi deve firmare)
    if c.get("firma"):
        try:
            pdf.ln(10)
            img_d = base64.b64decode(c["firma"])
            pdf.image(io.BytesIO(img_d), x=130, y=pdf.get_y(), w=50)
        except: pass
    pdf.ln(20)
    pdf.set_font("Arial", "B", 10); pdf.cell(0, 10, "Firma del Cliente", ln=True, align="R")
    
    return bytes(pdf.output())

# --- LOGIN ---
if "autenticato" not in st.session_state: st.session_state.autenticato = False
if not st.session_state.autenticato:
    pwd = st.text_input("Password", type="password")
    if st.button("Entra"):
        if pwd == st.secrets["APP_PASSWORD"]: st.session_state.autenticato = True; st.rerun()
else:
    # --- FORM ---
    with st.form("main_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome"); cognome = c1.text_input("Cognome"); cf = c1.text_input("CF")
        targa = c2.text_input("Targa").upper(); prezzo = c2.number_input("Prezzo", min_value=0.0); dep = c2.number_input("Deposito", min_value=0.0)
        l_nas = c1.text_input("Luogo Nascita"); d_nas = c1.text_input("Data Nascita (gg/mm/aaaa)")
        pat = c2.text_input("Patente"); ind = c1.text_input("Indirizzo Residenza")
        d_in = c1.date_input("Inizio"); d_out = c2.date_input("Fine")
        
        st.write("Firma Cliente:")
        canvas = st_canvas(stroke_width=3, stroke_color="#000", background_color="#eee", height=150, width=400, key="canvas_v6")
        
        if st.form_submit_button("SALVA"):
            firma_b64 = ""
            if canvas.image_data is not None:
                img = Image.fromarray(canvas.image_data.astype("uint8"))
                buf = io.BytesIO(); img.save(buf, format="PNG"); firma_b64 = base64.b64encode(buf.getvalue()).decode()
            
            n_fatt = prossimo_numero_fattura()
            dati = {
                "nome": nome, "cognome": cognome, "codice_fiscale": cf, "targa": targa, "prezzo": prezzo,
                "deposito": dep, "inizio": str(d_in), "fine": str(d_out), "firma": firma_b64, 
                "numero_fattura": n_fatt, "luogo_nascita": l_nas, "data_nascita": d_nas, "numero_patente": pat, "indirizzo": ind
            }
            supabase.table("contratti").insert(dati).execute()
            st.success(f"Salvato come n. {n_fatt}!"); st.rerun()

    # --- ARCHIVIO ---
    st.divider()
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"Ricevuta {c['numero_fattura']} - {c['nome']} {c['cognome']} ({c['targa']})"):
            col_a, col_b, col_c = st.columns(3)
            # QUI FORZIAMO I TIPI DIVERSI
            col_a.download_button("📜 Contratto", genera_pdf_tipo(c, "CONTRATTO"), f"Contratto_{c['id']}.pdf", key=f"c{c['id']}")
            col_b.download_button("💰 Ricevuta", genera_pdf_tipo(c, "FATTURA"), f"Ricevuta_{c['id']}.pdf", key=f"r{c['id']}")
            col_c.download_button("🚨 Modulo Multe", genera_pdf_tipo(c, "MULTE"), f"Multe_{c['id']}.pdf", key=f"m{c['id']}")
