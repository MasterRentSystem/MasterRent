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

# -------------------------
# CONNESSIONE SUPABASE
# -------------------------
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
        elif pwd != "":
            st.error("Password errata")
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
                 f"Residente in: {d.get('residenza')}\n"
                 f"CF: {d.get('codice_fiscale')}\n"
                 f"Patente: {d.get('numero_patente')}\n\n"
                 f"Veicolo: {d.get('targa')}\n"
                 f"Periodo: {d.get('inizio')} - {d.get('fine')}\n"
                 f"Prezzo: Euro {d.get('prezzo')}")
        pdf.multi_cell(0, 8, clean(testo))
    elif tipo == "FATTURA":
        pdf.cell(0, 10, clean(f"Ricevuta N. {d.get('numero_fattura')}"), ln=True, align="C")
        pdf.ln(10)
        pdf.cell(0, 10, clean(f"Cliente: {d.get('nome')} {d.get('cognome')} - Euro {d.get('prezzo')}"), ln=True)
    elif tipo == "MULTE":
        pdf.cell(0, 10, "DICHIARAZIONE DATI CONDUCENTE", ln=True, align="C")
        pdf.ln(10)
        testo = f"Veicolo: {d.get('targa')}\nData: {d.get('inizio')}\nConducente: {d.get('nome')} {d.get('cognome')}\nPatente: {d.get('numero_patente')}"
        pdf.multi_cell(0, 8, clean(testo))

    res_pdf = pdf.output(dest="S")
    return res_pdf.encode("latin-1", "ignore") if isinstance(res_pdf, str) else res_pdf

# -------------------------
# INTERFACCIA
# -------------------------
menu = st.sidebar.radio("Menu", ["Nuovo Noleggio", "Archivio"])

if menu == "Nuovo Noleggio":
    st.header("🛵 Nuovo Noleggio")
    
    with st.form("form_principale", clear_on_submit=True):
        st.subheader("Anagrafica Cliente")
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome")
        cognome = c2.text_input("Cognome")
        luogo_nas = c1.text_input("Luogo di Nascita")
        data_nas = c2.text_input("Data di Nascita (GG/MM/AAAA)")
        residenza = c1.text_input("Residenza")
        cf = c2.text_input("Codice Fiscale")
        patente = c1.text_input("Numero Patente")
        telefono = c2.text_input("Telefono")
        
        st.subheader("Dati Noleggio")
        c3, c4 = st.columns(2)
        targa = c3.text_input("Targa").upper()
        prezzo = c4.number_input("Prezzo Totale (€)", min_value=0.0)
        deposito = c3.number_input("Deposito (€)", min_value=0.0)
        inizio = c3.date_input("Data Inizio")
        fine = c4.date_input("Data Fine")
        
        st.divider()
        st.subheader("Documenti (Foto)")
        foto_fronte = st.file_uploader("📸 FOTO PATENTE FRONTE", type=['png', 'jpg', 'jpeg'])
        foto_retro = st.file_uploader("📸 FOTO PATENTE RETRO", type=['png', 'jpg', 'jpeg'])
        foto_privacy = st.file_uploader("📄 PRIVACY FIRMATA", type=['png', 'jpg', 'jpeg', 'pdf'])
        
        st.divider()
        st.subheader("Firma")
        canvas = st_canvas(height=180, stroke_width=3, stroke_color="#000", background_color="#fff", key="canvas_firma")

        submit = st.form_submit_button("💾 SALVA TUTTO")

        if submit:
            if not nome or not targa:
                st.error("⚠️ Nome e Targa obbligatori!")
            else:
                with st.spinner("Salvataggio..."):
                    # Caricamento file
                    url_f = upload_file(foto_fronte, targa, "fronte")
                    url_r = upload_file(foto_retro, targa, "retro")
                    url_p = upload_file(foto_privacy, targa, "privacy")

                    # Firma
                    firma_b64 = ""
                    if canvas.image_data is not None:
                        img_firma = Image.fromarray(canvas.image_data.astype("uint8"))
                        buffered = io.BytesIO()
                        img_firma.save(buffered, format="PNG")
                        firma_b64 = "data:image/png;base64," + base64.b64encode(buffered.getvalue()).decode()

                    # Preparazione Dati
                    dati = {
                        "nome": nome, "cognome": cognome, "luogo_nascita": luogo_nas, "data_nascita": data_nas,
                        "residenza": residenza, "codice_fiscale": cf, "numero_patente": patente,
                        "telefono": telefono, "targa": targa, "prezzo": prezzo, "deposito": deposito,
                        "numero_fattura": get_next_fattura(), "inizio": inizio.isoformat(), "fine": fine.isoformat(),
                        "firma": firma_b64, "url_fronte": url_f, "url_retro": url_r, "url_privacy": url_p
                    }
                    
                    try:
                        supabase.table("contratti").insert(dati).execute()
                        st.success(f"✅ Salvato! Fattura: {dati['numero_fattura']}")
                    except Exception as e:
                        # Se l'errore riguarda le colonne mancanti, riprova senza quelle colonne
                        if "url_privacy" in str(e) or "column" in str(e):
                            st.warning("Nota: Le foto sono state caricate nello Storage ma non collegate al database (colonne mancanti). Salvo i dati anagrafici...")
                            dati_ridotti = {k: v for k, v in dati.items() if not k.startswith("url_")}
                            supabase.table("contratti").insert(dati_ridotti).execute()
                            st.success(f"✅ Dati anagrafici salvati! Fattura: {dati['numero_fattura']}")
                        else:
                            st.error(f"❌ Errore: {e}")

elif menu == "Archivio":
    st.header("📂 Archivio")
    cerca = st.text_input("🔍 Cerca per Cognome o Targa").lower()
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    if res.data:
        for c in res.data:
            if cerca in f"{c.get('targa','')} {c.get('cognome','')}".lower():
                with st.expander(f"{c.get('numero_fattura')} - {c.get('targa')} - {c.get('cognome')}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.download_button("📜 Contratto", genera_pdf(c, "CONTRATTO"), f"Contratto_{c['targa']}.pdf", "application/pdf")
                        st.download_button("🚨 Multe", genera_pdf(c, "MULTE"), f"Multe_{c['targa']}.pdf", "application/pdf")
                    with col2:
                        st.download_button("💰 Ricevuta", genera_pdf(c, "FATTURA"), f"Ricevuta_{c['numero_fattura']}.pdf", "application/pdf")
                        if c.get('url_fronte'): st.link_button("🖼️ Foto Fronte", c['url_fronte'])
                        if c.get('url_retro'): st.link_button("🖼️ Foto Retro", c['url_retro'])
