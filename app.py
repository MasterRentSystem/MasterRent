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

# --- GENERATORE PDF ---
def genera_pdf_tipo(c, tipo="CONTRATTO"):
    pdf = FPDF()
    pdf.add_page()
    
    # INTESTAZIONE
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 6, safe_text(DITTA), ln=True)
    pdf.set_font("Arial", "", 9)
    pdf.cell(0, 5, safe_text(INDIRIZZO_FISCALE), ln=True)
    pdf.cell(0, 5, safe_text(DATI_IVA), ln=True)
    pdf.ln(10)

    # TITOLO
    titoli = {
        "CONTRATTO": "CONTRATTO DI NOLEGGIO / RENTAL AGREEMENT",
        "FATTURA": "RICEVUTA DI PAGAMENTO / RECEIPT",
        "MULTE": "DICHIARAZIONE DATI CONDUCENTE"
    }
    pdf.set_font("Arial", "B", 15)
    pdf.cell(0, 10, safe_text(titoli.get(tipo, "DOCUMENTO")), ln=True, align="C", border="B")
    pdf.ln(8)

    # DATI CLIENTE
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, "DETTAGLI:", ln=True)
    pdf.set_font("Arial", "", 10)
    
    testo_cliente = (
        f"Cliente: {c.get('nome')} {c.get('cognome')}\n"
        f"Codice Fiscale: {c.get('codice_fiscale')}\n"
        f"Patente n.: {c.get('numero_patente')}\n"
        f"Targa Veicolo: {c.get('targa')}\n"
        f"Periodo: dal {c.get('inizio')} al {c.get('fine')}"
    )
    pdf.multi_cell(0, 6, safe_text(testo_cliente))
    pdf.ln(5)

    # CORPO SPECIFICO
    if tipo == "CONTRATTO":
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 7, "CONDIZIONI GENERALI:", ln=True)
        pdf.set_font("Arial", "", 8)
        clausole = (
            "1. Il cliente dichiara di ricevere il veicolo in ottimo stato.\n"
            "2. Responsabilita per danni, furto e incendio a carico del cliente.\n"
            "3. Il veicolo deve tornare con lo stesso livello di carburante.\n"
            "4. Deposito Cauzionale versato: Euro " + str(c.get('deposito')) + ".\n"
            "5. I dati sono trattati secondo il Regolamento UE 2016/679 (GDPR)."
        )
        pdf.multi_cell(0, 5, safe_text(clausole))

    elif tipo == "FATTURA":
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, f"Ricevuta n.: {c.get('numero_fattura')}", ln=True)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 12, f"TOTALE PAGATO: EUR {c.get('prezzo')}", ln=True)

    elif tipo == "MULTE":
        pdf.ln(5)
        pdf.multi_cell(0, 6, safe_text("Il conducente sopra indicato dichiara di aver avuto la disponibilita del veicolo nel periodo indicato e si assume la piena responsabilita per eventuali violazioni al Codice della Strada."))

    # FIRMA
    if c.get("firma"):
        try:
            firma_bytes = base64.b64decode(c["firma"])
            img = Image.open(io.BytesIO(firma_bytes))
            temp = io.BytesIO(); img.save(temp, format="PNG"); temp.seek(0)
            
            y_attuale = pdf.get_y()
            if y_attuale > 240: pdf.add_page(); y_attuale = 20
            pdf.image(temp, x=130, y=y_attuale + 5, w=50)
        except: pass

    pdf.ln(25)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 10, "Firma del Cliente", ln=True, align="R")
    
    return bytes(pdf.output())

# --- LOGIN ---
if "autenticato" not in st.session_state: st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.title("Accesso Battaglia Rent")
    pwd = st.text_input("Password", type="password")
    if st.button("Entra"):
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state.autenticato = True
            st.rerun()
else:
    st.header(f"Gestione Noleggio - {DITTA}")
    
    # FORM DI INSERIMENTO
    with st.form("nuovo_noleggio", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome")
            cognome = st.text_input("Cognome")
            cf = st.text_input("Codice Fiscale")
            indirizzo = st.text_input("Residenza")
        with col2:
            patente = st.text_input("Numero Patente")
            targa = st.text_input("Targa").upper()
            prezzo = st.number_input("Prezzo Totale (€)", min_value=0.0)
            deposito = st.number_input("Cauzione (€)", min_value=0.0)
        
        d1, d2 = st.columns(2)
        with d1: data_in = st.date_input("Inizio Noleggio")
        with d2: data_out = st.date_input("Fine Noleggio")

        st.write("Firma qui:")
        canvas = st_canvas(stroke_width=3, stroke_color="#000", background_color="#eee", height=150, width=400, key="firma_c")
        
        accetto = st.checkbox("Accetto Condizioni Contrattuali e Privacy GDPR")
        
        btn_salva = st.form_submit_button("SALVA DATI E GENERA DOCUMENTI")

        if btn_salva:
            if not accetto:
                st.error("Devi accettare le condizioni per proseguire.")
            elif not nome or not targa:
                st.error("Nome e Targa sono obbligatori.")
            else:
                # Conversione firma
                firma_b64 = ""
                if canvas.image_data is not None:
                    img_f = Image.fromarray(canvas.image_data.astype("uint8"))
                    buf = io.BytesIO(); img_f.save(buf, format="PNG")
                    firma_b64 = base64.b64encode(buf.getvalue()).decode()

                n_fatt = prossimo_numero_fattura()
                
                dati = {
                    "nome": nome, "cognome": cognome, "codice_fiscale": cf, "indirizzo": indirizzo,
                    "numero_patente": patente, "targa": targa, "prezzo": prezzo, "deposito": deposito,
                    "inizio": str(data_in), "fine": str(data_out), "firma": firma_b64, "numero_fattura": n_fatt
                }
                
                supabase.table("contratti").insert(dati).execute()
                st.success(f"Contratto n. {n_fatt} salvato correttamente!")
                st.rerun()

    # ARCHIVIO
    st.divider()
    st.subheader("Archivio Contratti")
    try:
        res = supabase.table("contratti").select("*").order("id", desc=True).execute()
        for c in res.data:
            with st.expander(f"📄 {c['nome']} {c['cognome']} - {c['targa']} (Ricevuta {c['numero_fattura']})"):
                c1, c2, c3 = st.columns(3)
                c1.download_button("📜 Contratto", genera_pdf_tipo(c, "CONTRATTO"), f"Contratto_{c['id']}.pdf")
                c2.download_button("💰 Ricevuta", genera_pdf_tipo(c, "FATTURA"), f"Ricevuta_{c['id']}.pdf")
                c3.download_button("🚨 Multe", genera_pdf_tipo(c, "MULTE"), f"Multe_{c['id']}.pdf")
    except:
        st.write("Nessun contratto in archivio.")
