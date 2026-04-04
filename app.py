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

def upload_image(file, name, targa):
    try:
        path = f"documenti/{targa}{name}{datetime.datetime.now().strftime('%H%M%s')}.jpg"
        supabase.storage.from_("documenti").upload(path, file.getvalue())
        return supabase.storage.from_("documenti").get_public_url(path)
    except: return None

# --- GENERATORE PDF PROFESSIONALE ---
def genera_pdf_tipo(c, tipo="CONTRATTO"):
    pdf = FPDF()
    pdf.add_page()
    
    # 1. INTESTAZIONE AZIENDALE FISSA (In alto a sinistra)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, safe_text(DITTA), ln=True)
    pdf.set_font("Arial", "", 9)
    pdf.cell(0, 5, safe_text(INDIRIZZO_FISCALE), ln=True)
    pdf.cell(0, 5, safe_text(DATI_IVA), ln=True)
    pdf.ln(10)

    # 2. TITOLO DEL DOCUMENTO
    titoli = {
        "CONTRATTO": "CONTRATTO DI NOLEGGIO / RENTAL AGREEMENT",
        "FATTURA": "RICEVUTA DI PAGAMENTO / PAYMENT RECEIPT",
        "MULTE": "COMUNICAZIONE LOCAZIONE VEICOLO (D.P.R. 445/2000)"
    }
    pdf.set_font("Arial", "B", 15)
    pdf.cell(0, 10, safe_text(titoli.get(tipo, "")), ln=True, align="C", border="B")
    pdf.ln(8)

    # 3. LOGICA SPECIFICA PER OGNI DOCUMENTO
    if tipo == "CONTRATTO":
        # --- SEZIONE CONTRATTO ---
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 7, "DATI DEL NOLEGGIO:", ln=True)
        pdf.set_font("Arial", "", 10)
        testo_noleggio = (
            f"Cliente: {c.get('nome')} {c.get('cognome')}\n"
            f"Nato a: {c.get('luogo_nascita', '________')} il {c.get('data_nascita', '________')}\n"
            f"Codice Fiscale: {c.get('codice_fiscale')}\n"
            f"Patente n.: {c.get('numero_patente')}\n"
            f"Veicolo Targa: {c.get('targa')}\n"
            f"Periodo: dal {c.get('inizio')} al {c.get('fine')}"
        )
        pdf.multi_cell(0, 6, safe_text(testo_noleggio))
        pdf.ln(5)
        
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 7, "CONDIZIONI GENERALI (CLAUSOLE):", ln=True)
        pdf.set_font("Arial", "", 9)
        clausole = (
            "1. RESPONSABILITA: Il cliente e responsabile per ogni danno, furto o incendio.\n"
            "2. MULTE: Le sanzioni amministrative sono a totale carico del conducente.\n"
            "3. CARBURANTE: Il veicolo va riconsegnato con lo stesso livello iniziale.\n"
            "4. DEPOSITO: La cauzione versata e di Euro " + str(c.get('deposito', 0)) + ".\n"
            "5. PRIVACY: I dati sono trattati secondo il Reg. UE 2016/679 (GDPR)."
        )
        pdf.multi_cell(0, 5, safe_text(clausole))

    elif tipo == "FATTURA":
        # --- SEZIONE FATTURA ---
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 7, f"Ricevuta n. {c.get('numero_fattura')} del {c.get('inizio')}", ln=True)
        pdf.ln(5)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 7, "DETTAGLIO PAGAMENTO:", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 7, f"Cliente: {c.get('nome')} {c.get('cognome')}", ln=True)
        pdf.cell(0, 7, f"Per noleggio veicolo targa: {c.get('targa')}", ln=True)
        pdf.ln(10)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 15, f"TOTALE INCASSATO: EUR {c.get('prezzo')}", ln=True, border=1, align="C")

    elif tipo == "MULTE":
        # --- SEZIONE MULTE (COPIATA DALLA TUA FOTO) ---
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 5, "Spett. le", ln=True, align="R")
        pdf.cell(0, 5, "Polizia Locale di ____________________", ln=True, align="R")
        pdf.ln(5)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 5, "OGGETTO: RIFERIMENTO VS. ACCERTAMENTO VIOLAZIONE N. _____________", ln=True)
        pdf.cell(0, 5, "         - COMUNICAZIONE LOCAZIONE VEICOLO", ln=True)
        pdf.ln(5)
        pdf.set_font("Arial", "", 10)
        testo_multe = (
            f"In riferimento al Verbale in oggetto, la sottoscritta BATTAGLIA MARIANNA, nata a Berlino "
            f"il 13/01/1987 e residente in Forio alla Via Cognole n. 5, titolare dell'omonima ditta, "
            f"C.F. BTTMNN87A53Z112S e P.IVA 10252601215, ai sensi del D.P.R. 445/2000 DICHIARA che il veicolo "
            f"targato {c.get('targa')} in data {c.get('inizio')} era concesso in locazione al signor:\n\n"
            f"COGNOME E NOME: {c.get('nome').upper()} {c.get('cognome').upper()}\n"
            f"NATO A: {c.get('luogo_nascita', '________')} IL {c.get('data_nascita', '________')}\n"
            f"RESIDENTE IN: {c.get('indirizzo', '__________________')}\n"
            f"PATENTE N.: {c.get('numero_patente')}\n\n"
            f"Si allega copia del contratto e documento. Il sottoscritto dichiara che la copia allegata "
            f"e conforme all'originale agli atti della ditta."
        )
        pdf.multi_cell(0, 5, safe_text(testo_multe))
        pdf.ln(10)
        pdf.cell(0, 5, "In fede, Marianna Battaglia", ln=True, align="R")

    # --- 4. SPAZIO FIRMA CLIENTE (Sempre in fondo a destra) ---
    if c.get("firma"):
        try:
            pdf.ln(5)
            img_data = base64.b64decode(c["firma"])
            y_firma = pdf.get_y()
            if y_firma > 230: pdf.add_page(); y_firma = 20
            pdf.image(io.BytesIO(img_data), x=130, y=y_firma, w=50)
            pdf.set_y(y_firma + 25)
        except: pass

    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 10, "Firma del Cliente (Noleggiante)", ln=True, align="R")
    
    return bytes(pdf.output())

# --- INTERFACCIA APP ---
if "autenticato" not in st.session_state: st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.title("Accesso Battaglia Rent")
    pwd = st.text_input("Password", type="password")
    if st.button("Entra"):
        if pwd == st.secrets["APP_PASSWORD"]: 
            st.session_state.autenticato = True
            st.rerun()
else:
    st.header(f"Gestione Noleggi - {DITTA}")
    
    with st.form("nuovo_contratto", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome")
            cognome = st.text_input("Cognome")
            cf = st.text_input("Codice Fiscale")
            patente = st.text_input("Numero Patente")
        with col2:
            targa = st.text_input("Targa").upper()
            prezzo = st.number_input("Prezzo (€)", min_value=0.0)
            deposito = st.number_input("Deposito (€)", min_value=0.0)
            data_in = st.date_input("Inizio")
            data_out = st.date_input("Fine")

        st.divider()
        st.subheader("📸 Foto Documenti (per Vigili)")
        f_fronte = st.file_uploader("Fronte Patente", type=['jpg','png','jpeg'])
        f_retro = st.file_uploader("Retro Patente", type=['jpg','png','jpeg'])

        st.divider()
        st.subheader("⚖️ Clausole Legali (Leggere al cliente)")
        st.info("""
        1. *Responsabilità:* Il cliente risponde di danni, furto e incendio.
        2. *Multe:* Responsabilità totale del conducente per ogni verbale.
        3. *Carburante:* Riconsegna allo stesso livello.
        4. *Privacy:* I dati sono protetti dal GDPR (Reg. UE 2016/679).
        """)
        accetto = st.checkbox("IL CLIENTE ACCETTA TUTTE LE CONDIZIONI SOPRA INDICATE")

        st.write("Firma Cliente:")
        canvas = st_canvas(stroke_width=3, stroke_color="#000", background_color="#eee", height=150, width=400, key="firma_v5")
        
        if st.form_submit_button("💾 SALVA E GENERA DOCUMENTI"):
            if not accetto or not nome or not targa:
                st.error("⚠️ Errore: Nome, Targa e Accettazione sono obbligatori!")
            else:
                # Caricamento Foto
                u_fronte = upload_image(f_fronte, "fronte", targa) if f_fronte else None
                u_retro = upload_image(f_retro, "retro", targa) if f_retro else None

                # Gestione Firma
                firma_b64 = ""
                if canvas.image_data is not None:
                    img_f = Image.fromarray(canvas.image_data.astype("uint8"))
                    buf = io.BytesIO(); img_f.save(buf, format="PNG")
                    firma_b64 = base64.b64encode(buf.getvalue()).decode()

                n_fatt = prossimo_numero_fattura()
                
                dati = {
                    "nome": nome, "cognome": cognome, "codice_fiscale": cf, "numero_patente": patente,
                    "targa": targa, "prezzo": prezzo, "deposito": deposito, "inizio": str(data_in),
                    "fine": str(data_out), "firma": firma_b64, "numero_fattura": n_fatt,
                    "url_fronte": u_fronte, "url_retro": u_retro
                }
                
                supabase.table("contratti").insert(dati).execute()
                st.success(f"✅ Contratto n. {n_fatt} salvato!")
                st.rerun()

   # --- SEZIONE ARCHIVIO (Controlla che i nomi siano identici) ---
    st.divider()
    st.subheader("📋 Archivio Contratti")
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    
    for c in res.data:
        with st.expander(f"📄 {c['nome']} {c['cognome']} - {c['targa']} (Ricevuta {c['numero_fattura']})"):
            col_a, col_b, col_c = st.columns(3)
            
            # IL SEGRETO È QUI: Il secondo pezzetto deve dire "CONTRATTO", "FATTURA" o "MULTE"
            col_a.download_button(
                label="📜 Scarica Contratto",
                data=genera_pdf_tipo(c, "CONTRATTO"),
                file_name=f"Contratto_{c['numero_fattura']}.pdf",
                key=f"btn_con_{c['id']}"
            )
            
            col_b.download_button(
                label="💰 Scarica Ricevuta",
                data=genera_pdf_tipo(c, "FATTURA"),
                file_name=f"Ricevuta_{c['numero_fattura']}.pdf",
                key=f"btn_ric_{c['id']}"
            )
            
            col_c.download_button(
                label="🚨 Modulo Multe",
                data=genera_pdf_tipo(c, "MULTE"),
                file_name=f"Modulo_Multe_{c['id']}.pdf",
                key=f"btn_mul_{c['id']}"
            )
