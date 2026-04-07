import streamlit as st
import datetime
import pandas as pd
from supabase import create_client, Client
from fpdf import FPDF
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io
import base64

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Battaglia Rent Pro", layout="wide")

url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- LOGIN ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Accesso Riservato Battaglia Rent")
    pwd = st.text_input("Password", type="password")
    if st.button("Entra"):
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state.auth = True
            st.rerun()
    st.stop()

# --- FUNZIONI DI SUPPORTO ---
def safe_text(text):
    return str(text).encode("latin-1", "replace").decode("latin-1").replace("€", "EUR")

def upload_foto(file, targa, prefix):
    if file is None: return None
    try:
        ext = file.name.split('.')[-1]
        nome_file = f"{prefix}{targa}{datetime.datetime.now().strftime('%H%M%S')}.{ext}"
        supabase.storage.from_("documenti").upload(nome_file, file.getvalue())
        return supabase.storage.from_("documenti").get_public_url(nome_file)
    except: return None

def genera_pdf_tipo(d, tipo, firma_img_b64=None):
    pdf = FPDF()
    pdf.add_page()
    
    # Intestazione Standard
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, "BATTAGLIA MARIANNA", ln=True)
    pdf.set_font("Arial", "", 9)
    pdf.cell(0, 5, "Via Cognole, 5 - 80075 Forio (NA)", ln=True)
    pdf.cell(0, 5, "P.IVA: 10252601215 - C.F.: BTTMNN87A53Z112S", ln=True)
    pdf.ln(10)

    if tipo == "CONTRATTO":
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, safe_text(f"CONTRATTO DI NOLEGGIO N. {d.get('numero_fattura')}"), border="B", ln=True, align="C")
        pdf.ln(5)
        pdf.set_font("Arial", "", 10)
        corpo = f"Cliente: {d['nome']} {d['cognome']} | CF: {d['codice_fiscale']}\n" \
                f"Nato a: {d['luogo_nascita']} il {d['data_nascita']}\n" \
                f"Targa: {d['targa']} | Modello: {d.get('modello', 'Scooter')}\n" \
                f"Periodo: dal {d['inizio']} al {d['fine']} | Prezzo: EUR {d['prezzo']}\n\n" \
                f"CONDIZIONI: Il cliente e responsabile di ogni danno o furto. " \
                f"Le multe sono a carico del locatario. Il mezzo va reso con stessa benzina.\n\n" \
                f"PRIVACY: Autorizzo il trattamento dati e conservazione foto documenti."
        pdf.multi_cell(0, 6, safe_text(corpo))
        
        if firma_img_b64:
            try:
                img_data = base64.b64decode(firma_img_b64)
                pdf.image(io.BytesIO(img_data), x=130, y=pdf.get_y()+5, w=45)
            except: pass
        pdf.ln(20)
        pdf.cell(0, 10, "Firma Cliente _________________________", ln=True, align="R")

    elif tipo == "MULTE":
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "COMUNICAZIONE DATI CONDUCENTE", ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("Arial", "", 11)
        testo = f"Il veicolo targa {d['targa']} in data {d['inizio']} era affidato a:\n\n" \
                f"Conducente: {d['nome']} {d['cognome']}\n" \
                f"Nato a: {d['luogo_nascita']} il {d['data_nascita']}\n" \
                f"Patente: {d['numero_patente']}\n" \
                f"Residenza: {d.get('residenza', '---')}"
        pdf.multi_cell(0, 7, safe_text(testo))

    return bytes(pdf.output(dest="S"))

# --- NAVIGAZIONE ---
menu = st.sidebar.radio("Menu", ["Nuovo Noleggio", "Archivio"])

if menu == "Nuovo Noleggio":
    st.header("🛵 Registrazione Noleggio")
    with st.form("form_noleggio", clear_on_submit=True):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome")
        cognome = c2.text_input("Cognome")
        targa = c1.text_input("Targa").upper()
        patente = c2.text_input("N. Patente")
        prezzo = c1.number_input("Prezzo (€)", 0.0)
        deposito = c2.number_input("Deposito (€)", 0.0)
        
        inizio = c1.date_input("Inizio")
        fine = c2.date_input("Fine")
        
        st.subheader("📸 Documenti")
        f_fronte = st.file_uploader("Fronte Patente", type=["jpg","png"])
        f_retro = st.file_uploader("Retro Patente", type=["jpg","png"])
        
        st.subheader("✍️ Firma")
        canvas = st_canvas(stroke_width=3, stroke_color="#000", background_color="#eee", height=150, width=400, key="firma")
        
        # Campi nascosti o extra per il DB
        l_nas = st.text_input("Luogo Nascita")
        d_nas = st.text_input("Data Nascita (GG/MM/AAAA)")
        cf = st.text_input("Codice Fiscale")
        
        submit = st.form_submit_button("💾 SALVA TUTTO")

        if submit:
            if nome and targa:
                # Gestione Firma
                firma_b64 = ""
                if canvas.image_data is not None:
                    img = Image.fromarray(canvas.image_data.astype("uint8"))
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    firma_b64 = base64.b64encode(buf.getvalue()).decode()

                # Upload Foto
                url_f = upload_foto(f_fronte, targa, "F")
                url_r = upload_foto(f_retro, targa, "R")
                
                n_fatt = f"{datetime.date.today().year}-{datetime.datetime.now().strftime('%H%M%S')}"

                dati = {
                    "nome": nome, "cognome": cognome, "targa": targa, "prezzo": prezzo,
                    "deposito": deposito, "inizio": str(inizio), "fine": str(fine),
                    "numero_patente": patente, "firma": firma_b64, "numero_fattura": n_fatt,
                    "url_fronte": url_f, "url_retro": url_r, "luogo_nascita": l_nas,
                    "data_nascita": d_nas, "codice_fiscale": cf
                }
                
                supabase.table("contratti").insert(dati).execute()
                st.success("✅ Noleggio salvato correttamente!")
                st.rerun()

elif menu == "Archivio":
    st.header("📂 Archivio Storico")
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    if res.data:
        for c in res.data:
            with st.expander(f"📝 {c['targa']} - {c['cognome']}"):
                col1, col2, col3 = st.columns(3)
                col1.download_button("📜 Contratto", genera_pdf_tipo(c, "CONTRATTO", c.get("firma")), f"Contr_{c['targa']}.pdf")
                col2.download_button("🚨 Multe", genera_pdf_tipo(c, "MULTE"), f"Multe_{c['targa']}.pdf")
                
                if c.get("url_fronte"):
                    col3.link_button("👁️ Vedi Patente", c["url_fronte"])
                    
