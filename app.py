import streamlit as st
from supabase import create_client, Client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from fpdf import FPDF
import io
import base64
from datetime import datetime

# -------------------
# DATI AZIENDA
# -------------------
DITTA = "BATTAGLIA RENT"
TITOLARE = "BATTAGLIA MARIANNA"
INDIRIZZO = "Via Cognole n. 5, Forio (NA)"
DATI_IVA = "P.IVA: 10252601215 | C.F.: BTTMNN87A53Z112S"

# -------------------
# SUPABASE
# -------------------
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# -------------------
# UTILITY
# -------------------
def s(v): 
    return "" if v is None else str(v)

def safe_text(text):
    """Gestisce i caratteri speciali per il PDF"""
    return s(text).encode("latin-1", "replace").decode("latin-1")

def prossimo_numero_fattura():
    try:
        res = supabase.table("contratti").select("numero_fattura").order("numero_fattura", desc=True).limit(1).execute()
        if res.data and res.data[0].get("numero_fattura"):
            return int(res.data[0]["numero_fattura"]) + 1
        return 1
    except:
        return 1

def upload_foto(file, targa, tipo):
    if file is None:
        return None
    try:
        img = Image.open(file)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.thumbnail((1000, 1000))
        
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        
        nome = f"{tipo}{targa}{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
        
        # FIX: Rimosso dict extra che causava l'errore Header
        supabase.storage.from_("documenti").upload(
            nome, 
            buf.getvalue(), 
            {"content-type": "image/jpeg"}
        )
        return supabase.storage.from_("documenti").get_public_url(nome)
    except Exception as e:
        st.error(f"Errore caricamento foto: {e}")
        return None

def get_firma(canvas):
    if canvas.image_data is not None:
        img = Image.fromarray(canvas.image_data.astype("uint8"))
        if img.getbbox() is None: # Canvas vuoto
            return None
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    return None

# -------------------
# GENERAZIONE PDF
# -------------------
def genera_pdf(c):
    pdf = FPDF()
    pdf.add_page()
    
    # Intestazione
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, safe_text(DITTA), ln=True)
    pdf.set_font("Arial", "", 9)
    pdf.cell(0, 5, safe_text(INDIRIZZO), ln=True)
    pdf.cell(0, 5, safe_text(DATI_IVA), ln=True)
    pdf.ln(10)

    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "CONTRATTO DI NOLEGGIO SCOOTER", ln=True, align="C", border="B")
    pdf.ln(5)

    pdf.set_font("Arial", "", 10)
    
    # Corpo del testo con tutta l'anagrafica
    testo = f"""
DATI CLIENTE
Nome e Cognome: {s(c.get('nome'))} {s(c.get('cognome'))}
Nazionalità: {s(c.get('nazionalita'))}
Luogo e Data di Nascita: {s(c.get('luogo_nascita'))}, {s(c.get('data_nascita'))}
Codice Fiscale: {s(c.get('codice_fiscale'))}
Residenza: {s(c.get('indirizzo_cliente'))}
Patente N.: {s(c.get('numero_patente'))}

DATI NOLEGGIO
Veicolo Targa: {s(c.get('targa'))}
Periodo: Dal {s(c.get('inizio'))} Al {s(c.get('fine'))}
Corrispettivo: EUR {s(c.get('prezzo'))}

CONDIZIONI GENERALI:
1.⁠ ⁠Il cliente dichiara di essere in possesso di patente valida.
2.⁠ ⁠Responsabilità per ogni danno causato al veicolo o a terzi.
3.⁠ ⁠In caso di furto il cliente risponde dell'intero valore del veicolo.
4.⁠ ⁠Tutte le contravvenzioni stradali sono a carico del cliente.
5.⁠ ⁠Il cliente autorizza il trattamento dei dati personali (GDPR).

Approvazione specifica clausole ai sensi degli artt. 1341 e 1342 c.c.
"""
    pdf.multi_cell(0, 5, safe_text(testo))

    if c.get("firma"):
        try:
            pdf.image(io.BytesIO(base64.b64decode(c["firma"])), x=130, y=pdf.get_y() + 2, w=50)
        except: pass

    pdf.ln(20)
    pdf.cell(0, 10, "Firma del cliente", align="R", ln=True)

    out = pdf.output(dest="S")
    return bytes(out) if isinstance(out, bytearray) else out.encode("latin-1", "replace")

# -------------------
# LOGIN
# -------------------
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🛵 BATTAGLIA RENT")
    password = st.text_input("Password", type="password")
    if st.button("Accedi"):
        if password == "1234":
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Accesso negato")
    st.stop()

# -------------------
# INTERFACCIA
# -------------------
tab1, tab2 = st.tabs(["🆕 Nuovo Contratto", "📂 Archivio"])

with tab1:
    with st.form("form_noleggio", clear_on_submit=True):
        st.subheader("Anagrafica Cliente")
        col1, col2 = st.columns(2)
        nome = col1.text_input("Nome")
        cognome = col1.text_input("Cognome")
        nazion = col2.text_input("Nazionalità")
        cf = col2.text_input("Codice Fiscale")
        
        col3, col4 = st.columns(2)
        luogo_n = col3.text_input("Luogo di Nascita")
        data_n = col4.text_input("Data di Nascita (GG/MM/AAAA)")
        
        indirizzo = st.text_area("Indirizzo di Residenza")
        
        st.subheader("Dati Noleggio")
        col5, col6 = st.columns(2)
        targa = col5.text_input("Targa Veicolo").upper()
        n_patente = col6.text_input("Numero Patente")
        
        col7, col8, col9 = st.columns(3)
        prezzo = col7.number_input("Prezzo (€)", min_value=0.0)
        inizio = col8.date_input("Inizio Noleggio")
        fine = col9.date_input("Fine Noleggio")
        
        st.write("---")
        f_doc = st.file_uploader("Foto Fronte Patente", type=['jpg','jpeg','png'])
        r_doc = st.file_uploader("Foto Retro Patente", type=['jpg','jpeg','png'])
        
        st.write("Firma del cliente")
        canvas = st_canvas(height=150, width=400, stroke_width=3, key="firma_c")

        if st.form_submit_button("💾 SALVA CONTRATTO"):
            firma_b64 = get_firma(canvas)
            if not nome or not cognome or not targa or firma_b64 is None:
                st.error("Compila i campi obbligatori (Nome, Cognome, Targa e Firma)")
            else:
                with st.spinner("Salvataggio..."):
                    u_f = upload_foto(f_doc, targa, "F")
                    u_r = upload_foto(r_doc, targa, "R")
                    
                    supabase.table("contratti").insert({
                        "nome": nome, "cognome": cognome, "nazionalita": nazion,
                        "luogo_nascita": luogo_n, "data_nascita": data_n,
                        "codice_fiscale": cf, "indirizzo_cliente": indirizzo,
                        "targa": targa, "numero_patente": n_patente,
                        "prezzo": prezzo, "inizio": str(inizio), "fine": str(fine),
                        "firma": firma_b64, "url_fronte": u_f, "url_retro": u_r,
                        "numero_fattura": prossimo_numero_fattura()
                    }).execute()
                    st.success("Contratto registrato con successo!")

with tab2:
    st.subheader("Ricerca in Archivio")
    cerca = st.text_input("Cerca per Targa o Cognome").lower()
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    
    for r in res.data:
        if cerca in f"{r['targa']} {r['cognome']}".lower():
            with st.expander(f"📄 {r['targa']} - {r['cognome'].upper()}"):
                st.download_button("📥 Scarica PDF", genera_pdf(r), f"Contratto_{r['targa']}.pdf", key=f"btn_{r['id']}")
                col_img1, col_img2 = st.columns(2)
                if r.get("url_fronte"): col_img1.image(r["url_fronte"], caption="Fronte")
                if r.get("url_retro"): col_img2.image(r["url_retro"], caption="Retro")
