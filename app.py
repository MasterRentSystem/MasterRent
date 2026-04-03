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
    
    # 1. INTESTAZIONE AZIENDALE (Sempre presente)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, safe_text(DITTA), ln=True)
    pdf.set_font("Arial", "", 9)
    pdf.cell(0, 5, safe_text(INDIRIZZO_FISCALE), ln=True)
    pdf.cell(0, 5, safe_text(DATI_IVA), ln=True)
    pdf.ln(10)

    # 2. TITOLO DOCUMENTO DISTINTO
    titoli = {
        "CONTRATTO": "CONTRATTO DI NOLEGGIO / RENTAL AGREEMENT",
        "FATTURA": "RICEVUTA DI PAGAMENTO / PAYMENT RECEIPT",
        "MULTE": "MODULO DICHIARAZIONE CONDUCENTE (PER AUTORITA)"
    }
    pdf.set_font("Arial", "B", 15)
    pdf.cell(0, 10, safe_text(titoli.get(tipo, "")), ln=True, align="C", border="B")
    pdf.ln(8)

    # 3. DATI NOLEGGIO
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, "DETTAGLI DEL SERVIZIO:", ln=True)
    pdf.set_font("Arial", "", 10)
    testo_base = (
        f"Ricevuta N: {c.get('numero_fattura')} | Targa: {c.get('targa')}\n"
        f"Cliente: {c.get('nome')} {c.get('cognome')}\n"
        f"Codice Fiscale: {c.get('codice_fiscale')} | Patente: {c.get('numero_patente')}\n"
        f"Periodo: dal {c.get('inizio')} al {c.get('fine')}"
    )
    pdf.multi_cell(0, 6, safe_text(testo_base))
    pdf.ln(5)

    # 4. CONTENUTO SPECIFICO
    if tipo == "CONTRATTO":
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 7, "CONDIZIONI GENERALI DI NOLEGGIO:", ln=True)
        pdf.set_font("Arial", "", 8)
        clausole = (
            "1. RESPONSABILITA: Il cliente e interamente responsabile per danni, furto o incendio.\n"
            "2. MULTE: Le violazioni al Codice della Strada sono a totale carico del firmatario.\n"
            "3. CARBURANTE: Il veicolo deve essere riconsegnato con lo stesso livello iniziale.\n"
            "4. DEPOSITO: La cauzione versata e di Euro " + str(c.get('deposito', 0)) + ".\n"
            "5. PRIVACY: Trattamento dati ai sensi del Reg. UE 2016/679 (GDPR)."
        )
        pdf.multi_cell(0, 5, safe_text(clausole))

    elif tipo == "FATTURA":
        pdf.ln(5)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 12, f"TOTALE PAGATO: EUR {c.get('prezzo')}", ln=True, border=1, align="C")
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 10, "Pagamento ricevuto a mezzo contanti/carta. Documento valido ai fini fiscali.", ln=True)

    elif tipo == "MULTE":
        pdf.ln(5)
        pdf.set_font("Arial", "B", 10)
        testo_multe = (
            "Il sottoscritto dichiara, sotto la propria responsabilita civile e penale, di essere stato "
            "alla guida del veicolo sopra indicato nel periodo segnalato e di assumersi la piena "
            "responsabilita per eventuali infrazioni rilevate dagli organi di Polizia."
        )
        pdf.multi_cell(0, 6, safe_text(testo_multe))

    # 5. FIRMA CLIENTE
    if c.get("firma"):
        try:
            pdf.ln(5)
            img_data = base64.b64decode(c["firma"])
            y_pos = pdf.get_y()
            if y_pos > 230: pdf.add_page(); y_pos = 20
            pdf.image(io.BytesIO(img_data), x=130, y=y_pos, w=50)
        except: pass

    pdf.ln(25)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 10, "Firma del Cliente per Accettazione", ln=True, align="R")
    
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

    # --- ARCHIVIO ---
    st.divider()
    st.subheader("📋 Archivio Contratti")
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"📄 {c['nome']} {c['cognome']} - {c['targa']} (Ricevuta {c['numero_fattura']})"):
            c1, c2, c3 = st.columns(3)
            c1.download_button("📜 Contratto", genera_pdf_tipo(c, "CONTRATTO"), f"Contratto_{c['id']}.pdf")
            c2.download_button("💰 Ricevuta", genera_pdf_tipo(c, "FATTURA"), f"Ricevuta_{c['id']}.pdf")
            c3.download_button("🚨 Modulo Multe", genera_pdf_tipo(c, "MULTE"), f"Multe_{c['id']}.pdf")
            
            if c.get("url_fronte") or c.get("url_retro"):
                st.write("---")
                st.write("📂 *Foto Documenti per Polizia:*")
                f1, f2 = st.columns(2)
                if c.get("url_fronte"): f1.link_button("👁️ Vedi Fronte", c["url_fronte"])
                if c.get("url_retro"): f2.link_button("👁️ Vedi Retro", c["url_retro"])
