import streamlit as st
import datetime
import pandas as pd
from supabase import create_client, Client
from fpdf import FPDF
import base64
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io

# -------------------------
# CONFIGURAZIONE & CONNESSIONE
# -------------------------
st.set_page_config(page_title="Battaglia Rent", layout="centered")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

def check_password():
    if "auth" not in st.session_state: st.session_state.auth = False
    if not st.session_state.auth:
        st.title("🔒 Accesso Riservato")
        pwd = st.text_input("Password", type="password")
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state.auth = True
            st.rerun()
        return False
    return True

if not check_password(): st.stop()

# -------------------------
# FUNZIONI UTILITY
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
    
    def clean(text):
        return str(text if text else "").encode('latin-1', 'replace').decode('latin-1').replace('?', '-')

    if tipo == "CONTRATTO":
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "CONTRATTO DI NOLEGGIO SCOOTER", ln=True, align="C")
        pdf.ln(5)
        pdf.set_font("Arial", "", 10)
        
        testo = (
            f"Fattura N: {d.get('numero_fattura')}\n"
            f"CLIENTE: {d.get('nome')} {d.get('cognome')}\n"
            f"Nazionalita: {d.get('nazionalita')}\n"
            f"Nato a: {d.get('luogo_nascita')} il {d.get('data_nascita')}\n"
            f"Residenza: {d.get('residenza')}\n"
            f"Codice Fiscale: {d.get('codice_fiscale')}\n"
            f"Patente: {d.get('numero_patente')}\n"
            f"Telefono: {d.get('telefono')}\n\n"
            f"VEICOLO: {d.get('targa')}\n"
            f"Periodo: Dal {d.get('inizio')} Al {d.get('fine')}\n"
            f"Prezzo: Euro {d.get('prezzo')} | Deposito: Euro {d.get('deposito')}\n\n"
            "CONDIZIONI:\n"
            "Il cliente dichiara di ricevere il veicolo in ottimo stato. Si assume la responsabilita "
            "per danni, furto e sanzioni amministrative. Autorizza il trattamento dati GDPR."
        )
        pdf.multi_cell(0, 7, clean(testo))

    elif tipo == "MULTE":
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "DICHIARAZIONE SOSTITUTIVA (L. 445/2000)", ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("Arial", "", 11)
        testo_m = (
            f"Io sottoscritta BATTAGLIA MARIANNA, titolare della ditta BATTAGLIA RENT, "
            f"dichiaro che il veicolo targato {d.get('targa')}\n"
            f"in data {d.get('inizio')} era locato al Sig. {d.get('nome')} {d.get('cognome')}, "
            f"nato a {d.get('luogo_nascita')} il {d.get('data_nascita')}, "
            f"residente a {d.get('residenza')}, Patente {d.get('numero_patente')}.\n\n"
            f"Firma del titolare: _________________________"
        )
        pdf.multi_cell(0, 8, clean(testo_m))
    
    return bytes(pdf.output(dest="S"))

# -------------------------
# INTERFACCIA
# -------------------------
menu = st.sidebar.radio("Menu", ["Nuovo Noleggio", "Archivio"])

if menu == "Nuovo Noleggio":
    st.header("🛵 Nuovo Noleggio - Battaglia Rent")
    
    with st.form("form_noleggio"):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Nome")
        cognome = col2.text_input("Cognome")
        nazionalita = col1.text_input("Nazionalità")
        luogo_nascita = col2.text_input("Luogo di Nascita")
        data_nascita = col1.date_input("Data di Nascita", min_value=datetime.date(1930, 1, 1))
        residenza = col2.text_input("Residenza")
        codice_fiscale = col1.text_input("Codice Fiscale")
        numero_patente = col2.text_input("Numero Patente")
        telefono = col1.text_input("Telefono")
        targa = col2.text_input("Targa Scooter").upper()
        prezzo = col1.number_input("Prezzo (€)", min_value=0.0)
        deposito = col2.number_input("Deposito (€)", min_value=0.0)
        inizio = col1.date_input("Inizio Noleggio")
        fine = col2.date_input("Fine Noleggio")
        
        st.subheader("Documentazione")
        f_p = st.file_uploader("Foto Patente Fronte", type=['png', 'jpg', 'jpeg'])
        r_p = st.file_uploader("Foto Patente Retro", type=['png', 'jpg', 'jpeg'])
        
        st.subheader("Firma")
        canvas = st_canvas(height=150, stroke_width=3, stroke_color="#000", background_color="#f0f0f0", key="canvas_firma")
        
        c_priv = st.checkbox("Accetto Privacy e Condizioni Contrattuali")
        submit = st.form_submit_button("💾 SALVA E GENERA")

        if submit:
            if not nome or not targa or not c_priv:
                st.error("⚠️ Compila i campi obbligatori e accetta la privacy!")
            else:
                with st.spinner("Salvataggio in corso..."):
                    u_f = upload_file(f_p, targa, "fronte")
                    u_r = upload_file(r_p, targa, "retro")
                    
                    f_b64 = ""
                    if canvas.image_data is not None:
                        img = Image.fromarray(canvas.image_data.astype("uint8"))
                        buf = io.BytesIO()
                        img.save(buf, format="PNG")
                        f_b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

                    dati = {
                        "nome": nome, "cognome": cognome, "nazionalita": nazionalita, 
                        "luogo_nascita": luogo_nascita, "data_nascita": str(data_nascita),
                        "residenza": residenza, "codice_fiscale": codice_fiscale, "numero_patente": numero_patente,
                        "telefono": telefono, "targa": targa, "prezzo": prezzo, "deposito": deposito,
                        "numero_fattura": get_next_fattura(), "inizio": str(inizio), "fine": str(fine),
                        "firma": f_b64, "url_fronte": u_f, "url_retro": u_r
                    }

                    try:
                        # Rilevamento automatico delle colonne per evitare crash
                        check = supabase.table("contratti").select("*").limit(1).execute()
                        col_db = check.data[0].keys() if check.data else dati.keys()
                        dati_ok = {k: v for k, v in dati.items() if k in col_db}
                        
                        supabase.table("contratti").insert(dati_ok).execute()
                        st.success("✅ Noleggio registrato con successo!")
                    except Exception as e:
                        st.error(f"❌ Errore: {e}")

elif menu == "Archivio":
    st.header("📂 Archivio Contratti")
    cerca = st.text_input("Cerca Targa o Cognome").lower()
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    
    if res.data:
        for c in res.data:
            if cerca in f"{c.get('targa','')} {c.get('cognome','')}".lower():
                with st.expander(f"📄 {c.get('numero_fattura')} - {c.get('targa')} - {c.get('cognome')}"):
                    col1, col2 = st.columns(2)
                    col1.download_button("📜 Contratto", genera_pdf(c, "CONTRATTO"), f"Contratto_{c['targa']}.pdf", "application/pdf")
                    col2.download_button("🚨 Modulo Multe", genera_pdf(c, "MULTE"), f"Multe_{c['targa']}.pdf", "application/pdf")
                    
                    st.divider()
                    if c.get('url_fronte'): st.link_button("🖼️ Patente Fronte", c['url_fronte'])
                    if c.get('url_retro'): st.link_button("🖼️ Patente Retro", c['url_retro'])
                    if c.get('firma'): st.image(c.get('firma'), caption="Firma", width=200)
