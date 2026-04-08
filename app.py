import streamlit as st
import datetime
import pandas as pd
from supabase import create_client, Client
from fpdf import FPDF
import base64
from streamlit_drawable_canvas import st_canvas
import urllib.parse
from PIL import Image
import io

# -------------------------
# CONFIGURAZIONE
# -------------------------
st.set_page_config(page_title="Battaglia Rent", layout="centered")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# -------------------------
# LOGIN
# -------------------------
def check_password():
    if "auth" not in st.session_state:
        st.session_state.auth = False
    if not st.session_state.auth:
        st.title("🔒 Accesso Riservato")
        pwd = st.text_input("Password", type="password")
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state.auth = True
            st.rerun()
        return False
    return True

if not check_password():
    st.stop()

# -------------------------
# UTILITY
# -------------------------
def get_next_fattura():
    year = datetime.date.today().year
    try:
        res = supabase.table("contratti").select("numero_fattura").filter("numero_fattura", "ilike", f"{year}-%").order("numero_fattura", desc=True).limit(1).execute()
        if not res.data: return f"{year}-001"
        last_num = int(res.data[0]["numero_fattura"].split("-")[1])
        return f"{year}-{str(last_num + 1).zfill(3)}"
    except: return f"{year}-001"

def upload_file(file, targa, tipo):
    if file is None: return None
    try:
        ext = file.name.split(".")[-1]
        nome = f"{tipo}{targa}{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
        supabase.storage.from_("documenti").upload(nome, file.getvalue())
        return supabase.storage.from_("documenti").get_public_url(nome)
    except: return None

def genera_pdf(d, tipo):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    def clean(text):
        return str(text).encode('latin-1', 'replace').decode('latin-1').replace('?', '-')

    if tipo == "CONTRATTO":
        pdf.cell(0, 10, "CONTRATTO DI NOLEGGIO SCOOTER", ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("Arial", "", 11)
        testo = (f"Locatario: {d.get('nome')} {d.get('cognome')}\n"
                 f"Nato a: {d.get('luogo_nascita')} il {d.get('data_nascita')}\n"
                 f"CF: {d.get('codice_fiscale')}\n"
                 f"Patente: {d.get('numero_patente')}\n\n"
                 f"Veicolo: {d.get('targa')}\n"
                 f"Dal: {d.get('inizio')} Al: {d.get('fine')}\n"
                 f"Prezzo: Euro {d.get('prezzo')}\n\n"
                 f"Privacy e Clausole: ACCETTATE")
        pdf.multi_cell(0, 8, clean(testo))
    elif tipo == "FATTURA":
        pdf.cell(0, 10, clean(f"Ricevuta N. {d.get('numero_fattura')}"), ln=True, align="C")
        pdf.ln(10)
        pdf.cell(0, 10, clean(f"Cliente: {d.get('nome')} {d.get('cognome')} - Euro {d.get('prezzo')}"), ln=True)
    
    return pdf.output(dest="S").encode("latin-1", "ignore") if isinstance(pdf.output(dest="S"), str) else pdf.output(dest="S")

# -------------------------
# MENU
# -------------------------
menu = st.sidebar.radio("Menu", ["Nuovo Noleggio", "Archivio"])

if menu == "Nuovo Noleggio":
    st.header("🛵 Nuovo Noleggio")
    
    with st.form("form_principale"):
        st.subheader("Dati Cliente")
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome")
        cognome = c2.text_input("Cognome")
        luogo_nascita = c1.text_input("Luogo di Nascita")
        data_nascita = c2.text_input("Data di Nascita (GG/MM/AAAA)")
        residenza = c1.text_input("Residenza")
        codice_fiscale = c2.text_input("Codice Fiscale")
        numero_patente = c1.text_input("Numero Patente")
        telefono = c2.text_input("Telefono")
        
        st.subheader("Dati Noleggio")
        c3, c4 = st.columns(2)
        targa = c3.text_input("Targa").upper()
        prezzo = c4.number_input("Prezzo (€)", min_value=0.0)
        deposito = c3.number_input("Deposito (€)", min_value=0.0)
        inizio = c3.date_input("Inizio")
        fine = c4.date_input("Fine")
        
        st.divider()
        st.subheader("Foto Documenti")
        patente_fronte = st.file_uploader("📸 Foto Patente Fronte", type=['png', 'jpg', 'jpeg'])
        patente_retro = st.file_uploader("📸 Foto Patente Retro", type=['png', 'jpg', 'jpeg'])
        
        st.divider()
        st.subheader("Consensi e Firma")
        # CHECKBOX RICHIESTI
        check_privacy = st.checkbox("Accetto Informativa Privacy")
        check_clausole = st.checkbox("Accetto Condizioni Contrattuali e Responsabilità")
        
        canvas = st_canvas(height=180, stroke_width=3, stroke_color="#000", background_color="#fff", key="canvas_firma")

        submit = st.form_submit_button("💾 SALVA NOLEGGIO")

        if submit:
            if not nome or not targa:
                st.error("⚠️ Nome e Targa obbligatori!")
            elif not check_privacy or not check_clausole:
                st.error("⚠️ Devi accettare Privacy e Condizioni!")
            else:
                with st.spinner("Salvataggio..."):
                    # Caricamento foto (usando i tuoi nomi di funzione)
                    url_fronte = upload_file(patente_fronte, targa, "fronte")
                    url_retro = upload_file(patente_retro, targa, "retro")
                    
                    # Firma
                    firma_b64 = ""
                    if canvas.image_data is not None:
                        img_f = Image.fromarray(canvas.image_data.astype("uint8"))
                        buf = io.BytesIO()
                        img_f.save(buf, format="PNG")
                        firma_b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

                    # DATI CON I NOMI COLONNA ORIGINALI
                    dati = {
                        "nome": nome,
                        "cognome": cognome,
                        "luogo_nascita": luogo_nascita,
                        "data_nascita": data_nascita,
                        "residenza": residenza,
                        "codice_fiscale": codice_fiscale,
                        "numero_patente": numero_patente,
                        "telefono": telefono,
                        "targa": targa,
                        "prezzo": prezzo,
                        "deposito": deposito,
                        "numero_fattura": get_next_fattura(),
                        "inizio": inizio.isoformat(),
                        "fine": fine.isoformat(),
                        "firma": firma_b64,
                        "url_fronte": url_fronte,
                        "url_retro": url_retro
                    }
                    
                    try:
                        supabase.table("contratti").insert(dati).execute()
                        st.success(f"✅ Noleggio salvato! Fattura: {dati['numero_fattura']}")
                    except Exception as e:
                        st.error(f"❌ Errore Database: {e}")

elif menu == "Archivio":
    st.header("📂 Archivio")
    cerca = st.text_input("🔍 Cerca Targa o Cognome").lower()
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    if res.data:
        for c in res.data:
            if cerca in f"{c.get('targa','')} {c.get('cognome','')}".lower():
                with st.expander(f"{c.get('numero_fattura')} - {c.get('targa')} - {c.get('cognome')}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.download_button("📜 Contratto", genera_pdf(c, "CONTRATTO"), f"Cont_{c['targa']}.pdf", "application/pdf")
                        st.download_button("💰 Ricevuta", genera_pdf(c, "FATTURA"), f"Ric_{c['numero_fattura']}.pdf", "application/pdf")
                    with col2:
                        if c.get('url_fronte'): st.link_button("🖼️ Patente Fronte", c['url_fronte'])
                        if c.get('url_retro'): st.link_button("🖼️ Patente Retro", c['url_retro'])
