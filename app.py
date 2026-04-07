import streamlit as st
import datetime
import pandas as pd
from supabase import create_client, Client
from fpdf import FPDF
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io

# -------------------------
# CONFIGURAZIONE & CONNESSIONE
# -------------------------
st.set_page_config(page_title="Battaglia Rent - Ufficiale", layout="wide")

url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- LOGIN ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Accesso Riservato")
    pwd = st.text_input("Password Accesso", type="password")
    if st.button("Entra"):
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Password errata")
    st.stop()

# -------------------------
# FUNZIONI SUPPORTO
# -------------------------
def genera_numero_fattura():
    anno = datetime.date.today().year
    try:
        res = supabase.table("contratti").select("numero_fattura").filter("numero_fattura", "ilike", f"{anno}-%").order("numero_fattura", desc=True).limit(1).execute()
        if not res.data: return f"{anno}-001"
        ultimo = int(res.data[0]["numero_fattura"].split("-")[1])
        return f"{anno}-{str(ultimo + 1).zfill(3)}"
    except: return f"{anno}-001"

def upload_documento(file, targa, lato):
    if file is None: return None
    try:
        nome_file = f"{targa}{lato}{datetime.datetime.now().strftime('%H%M%S')}.png"
        supabase.storage.from_("documenti").upload(nome_file, file.getvalue())
        return supabase.storage.from_("documenti").get_public_url(nome_file)
    except: return None

# -------------------------
# GENERAZIONE PDF PROFESSIONALI
# -------------------------
def genera_pdf_documento(d, tipo, firma_img=None):
    pdf = FPDF()
    pdf.add_page()
    
    TITOLARE = "BATTAGLIA MARIANNA"
    SEDE = "Via Cognole, 5 - 80075 Forio (NA)"
    PIVA = "10252601215"
    CF = "BTTMNN87A53Z112S"

    if tipo == "CONTRATTO":
        # INTESTAZIONE
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "BATTAGLIA RENT", ln=True)
        pdf.set_font("Arial", "", 9)
        pdf.cell(0, 4, f"di {TITOLARE} | P.IVA: {PIVA} | C.F.: {CF}", ln=True)
        pdf.cell(0, 4, f"Sede Legale: {SEDE}", ln=True)
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, f"CONTRATTO DI LOCAZIONE N. {d.get('numero_fattura')}", border="TB", ln=True, align="C")
        
        # DATI LOCATARIO
        pdf.ln(5)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 7, "DATI DEL LOCATARIO (CLIENTE)", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 6, f"Nome e Cognome: {d.get('nome')} {d.get('cognome')}\n"
                             f"Nato a: {d.get('luogo_nascita')} il {d.get('data_nascita')} | Nazionalità: {d.get('nazionalita')}\n"
                             f"Residente in: {d.get('residenza')}\n"
                             f"Codice Fiscale: {d.get('codice_fiscale')} | Patente N.: {d.get('numero_patente')}\n"
                             f"Telefono: {d.get('telefono')}")
        
        # DATI VEICOLO E STATO
        pdf.ln(5)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 7, "DETTAGLI VEICOLO E CONSEGNA", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.cell(95, 8, f"Veicolo: {d.get('modello')} Targa: {d.get('targa')}", border=1)
        pdf.cell(95, 8, f"Uscita: {d.get('inizio')} Rientro: {d.get('fine')}", border=1, ln=True)
        pdf.cell(0, 8, f"Benzina alla consegna: {d.get('benzina')} | Deposito: Euro {d.get('deposito')}", border=1, ln=True)
        pdf.multi_cell(0, 6, f"Note Danni/Accessori: {d.get('note_danni')}", border=1)

        # CLAUSOLE PRIVACY E RESPONSABILITÀ
        pdf.ln(5)
        pdf.set_font("Arial", "B", 8)
        pdf.cell(0, 5, "PRIVACY E CONDIZIONI", ln=True)
        pdf.set_font("Arial", "", 7)
        testo_legale = (
            "1. Il locatario dichiara di aver ricevuto il veicolo in ottimo stato. 2. Il locatario è responsabile per danni e multe. "
            "3. Il locatario autorizza il trattamento dei dati personali ai sensi del GDPR 2016/679 per scopi contrattuali. "
            "4. In caso di sosta vietata o infrazioni, il locatario autorizza la rinotifica dei verbali."
        )
        pdf.multi_cell(0, 4, testo_legale)
        
        # FIRMA
        pdf.ln(10)
        y_firma = pdf.get_y()
        pdf.set_font("Arial", "B", 10)
        pdf.cell(95, 10, "Il Locatore", 0, 0, "C")
        pdf.cell(95, 10, "Il Locatario (Firma Digitale)", 0, 1, "C")
        
        if firma_img:
            img_io = io.BytesIO()
            firma_img.save(img_io, format='PNG')
            img_io.seek(0)
            pdf.image(img_io, x=135, y=y_firma+8, w=40)
        
        pdf.cell(95, 10, "__________________", 0, 0, "C")
        pdf.cell(95, 10, "__________________", 0, 1, "C")

    elif tipo == "MULTE":
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 5, "Spett. le Polizia Locale di ______________________", ln=True, align="R")
        pdf.ln(10)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 5, "OGGETTO: RIFERIMENTO VS. ACCERTAMENTO VIOLAZIONE N. _______________ PROT.", ln=True)
        pdf.cell(0, 5, f"          {d.get('targa')} - COMUNICAZIONE LOCAZIONE VEICOLO", ln=True)
        pdf.ln(8)
        pdf.set_font("Arial", "", 11)
        pdf.multi_cell(0, 6, f"In riferimento al Verbale in oggetto, la sottoscritta {TITOLARE} nata a Berlino (Germania) il 13/01/1987 e residente in Forio alla {SEDE} in qualità di titolare dell'omonima ditta individuale, C.F.: {CF} e P. IVA: {PIVA}")
        pdf.ln(5)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 10, "DICHIARA", ln=True, align="C")
        pdf.set_font("Arial", "", 11)
        pdf.cell(0, 7, f"Ai sensi della l. 445/2000 che il veicolo targato {d.get('targa')} il giorno {d.get('inizio')}", ln=True)
        pdf.cell(0, 7, "era concesso in locazione senza conducente al signor:", ln=True)
        pdf.ln(5)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, f"COGNOME E NOME: {str(d.get('cognome')).upper()} {str(d.get('nome')).upper()}", border="B", ln=True)
        pdf.cell(0, 8, f"NATO A: {d.get('luogo_nascita')} IL {d.get('data_nascita')}", border="B", ln=True)
        pdf.cell(0, 8, f"IDENTIFICATO A MEZZO: PATENTE N. {d.get('numero_patente')}", border="B", ln=True)
        pdf.ln(10)
        pdf.cell(0, 5, "In fede, Marianna Battaglia", ln=True, align="R")

    return bytes(pdf.output())

# -------------------------
# INTERFACCIA PRINCIPALE
# -------------------------
menu = st.sidebar.radio("Menu", ["Nuovo Noleggio", "Archivio Storico"])

if menu == "Nuovo Noleggio":
    st.header("🛵 Registrazione Completa Noleggio")
    
    # DATI ANAGRAFICI
    with st.expander("1. Dati Anagrafici Cliente", expanded=True):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome")
        cognome = c2.text_input("Cognome")
        residenza = st.text_input("Indirizzo di Residenza Completo")
        c3, c4 = st.columns(2)
        cod_fisc = c3.text_input("Codice Fiscale")
        patente = c4.text_input("N. Patente")
        luogo_nas = c3.text_input("Luogo di Nascita")
        data_nas = c4.date_input("Data di Nascita", value=datetime.date(1990,1,1))
        nazionalita = st.text_input("Nazionalità", value="Italiana")
        telefono = st.text_input("Telefono / WhatsApp")

    # DATI VEICOLO
    with st.expander("2. Dati Veicolo e Noleggio", expanded=True):
        targa = st.text_input("Targa").upper()
        modello = st.text_input("Modello Veicolo (es. Liberty 125)")
        c5, c6 = st.columns(2)
        prezzo = c5.number_input("Prezzo Totale (€)", min_value=0.0)
        deposito = c6.number_input("Deposito (€)", min_value=0.0)
        inizio = c5.date_input("Inizio Noleggio")
        fine = c6.date_input("Fine Noleggio")
        benzina = st.selectbox("Livello Benzina", ["Pieno", "1/2", "Riserva"])
        note_danni = st.text_area("Stato del veicolo (danni, caschi, accessori)")

    # FOTO E FIRMA
    with st.expander("3. Foto Documenti e Firma Digitale", expanded=True):
        f_fronte = st.file_uploader("Carica Foto Patente Fronte", type=['png', 'jpg', 'jpeg'])
        f_retro = st.file_uploader("Carica Foto Patente Retro", type=['png', 'jpg', 'jpeg'])
        st.write("✍️ Firma qui sotto:")
        canvas_result = st_canvas(
            stroke_width=3, stroke_color="#000", background_color="#eee",
            height=150, width=400, key="canvas_firma_completa"
        )

    if st.button("💾 SALVA TUTTO E GENERA DOCUMENTI"):
        if not nome or not targa:
            st.error("Nome e Targa sono obbligatori!")
        else:
            # Upload Foto
            url_f = upload_documento(f_fronte, targa, "FRONTE")
            url_r = upload_documento(f_retro, targa, "RETRO")
            
            # Recupero Firma
            firma_pil = None
            if canvas_result.image_data is not None:
                firma_pil = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')

            n_fatt = genera_numero_fattura()
            dati = {
                "nome": nome, "cognome": cognome, "targa": targa, "modello": modello,
                "prezzo": prezzo, "deposito": deposito, "inizio": str(inizio), "fine": str(fine),
                "codice_fiscale": cod_fisc, "numero_patente": patente, "residenza": residenza,
                "nazionalita": nazionalita, "luogo_nascita": luogo_nas, "data_nascita": str(data_nas),
                "benzina": benzina, "note_danni": note_danni, "numero_fattura": n_fatt,
                "telefono": telefono, "url_fronte": url_f, "url_retro": url_r
            }
            
            supabase.table("contratti").insert(dati).execute()
            st.success("Noleggio Registrato!")
            
            pdf_con = genera_pdf_documento(dati, "CONTRATTO", firma_pil)
            st.download_button("📥 Scarica Contratto Firmato", pdf_con, f"Contratto_{targa}.pdf")

elif menu == "Archivio Storico":
    st.header("📂 Archivio Contratti")
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    if res.data:
        for c in res.data:
            with st.expander(f"{c['targa']} - {c['cognome']}"):
                col1, col2 = st.columns(2)
                col1.download_button("📜 Contratto", genera_pdf_documento(c, "CONTRATTO"), f"Contratto_{c['targa']}.pdf", key=f"c_{c['id']}")
                col2.download_button("🚨 Modulo Multe", genera_pdf_documento(c, "MULTE"), f"Multe_{c['targa']}.pdf", key=f"m_{c['id']}")
                if c.get("url_fronte"): st.link_button("👁️ Vedi Foto Patente", c["url_fronte"])
