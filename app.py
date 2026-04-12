import streamlit as st
from supabase import create_client, Client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from fpdf import FPDF
import io
import base64
from datetime import datetime
import urllib.parse

# --- CONFIGURAZIONE DATI DITTA ---
DITTA = "BATTAGLIA RENT"
INDIRIZZO_FISCALE = "Via Cognole n. 5, Forio (NA)"
DATI_IVA = "P.IVA: 10252601215 | C.F.: BTTMNN87A53Z112S"

# --- CONNESSIONE SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# ------------------------------------------------
# UTILITY
# ------------------------------------------------
def safe_text(text):
    if text is None: return ""
    return str(text).encode("latin-1", "replace").decode("latin-1")

def prossimo_numero_fattura():
    try:
        res = supabase.table("contratti").select("numero_fattura").order("numero_fattura", desc=True).limit(1).execute()
        if res.data:
            ultimo = res.data[0].get("numero_fattura")
            return int(ultimo) + 1 if ultimo else 1
        return 1
    except: return 1

def upload_to_supabase(file, targa, prefix):
    try:
        if file is None: return None
        estensione = file.name.split('.')[-1]
        nome_file = f"{prefix}{targa}{datetime.now().strftime('%Y%m%d_%H%M%S')}.{estensione}"
        supabase.storage.from_("documenti").upload(nome_file, file.getvalue(), {"content-type": f"image/{estensione}"})
        return supabase.storage.from_("documenti").get_public_url(nome_file)
    except Exception as e:
        st.error(f"Errore caricamento foto: {e}")
        return None

# ------------------------------------------------
# FUNZIONE PDF
# ------------------------------------------------
def genera_pdf_tipo(c, tipo):
    pdf = FPDF()
    pdf.add_page()
    oggi = datetime.now().date().strftime("%d/%m/%Y")
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, safe_text(DITTA), ln=True)
    pdf.set_font("Arial", "", 9)
    pdf.cell(0, 5, safe_text(INDIRIZZO_FISCALE), ln=True)
    pdf.cell(0, 5, safe_text(DATI_IVA), ln=True)
    pdf.ln(8)

    if tipo == "CONTRATTO":
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "CONTRATTO DI NOLEGGIO / RENTAL AGREEMENT", ln=True, align="C", border="B")
        pdf.ln(5)
        pdf.set_font("Arial", "", 9)
        testo = f"Cliente: {c.get('nome')} {c.get('cognome')} | CF/ID: {c.get('codice_fiscale', '---')}\n" \
                f"Residenza: {c.get('indirizzo_cliente', '---')}\n" \
                f"Targa: {c.get('targa')} | Patente: {c.get('numero_patente')}\n" \
                f"Periodo: dal {c.get('inizio')} al {c.get('fine')} | Prezzo: EUR {c.get('prezzo')}\n\n" \
                f"CONDIZIONI DI NOLEGGIO:\n1. Patente valida obbligatoria.\n2. Responsabilità danni e furto.\n3. Multe a carico del locatario.\n\n" \
                f"Autorizzo il trattamento dati (GDPR) e la conservazione dei documenti d'identità."
        pdf.multi_cell(0, 5, safe_text(testo))
        if c.get("firma"):
            try:
                firma_bytes = base64.b64decode(c["firma"])
                pdf.image(io.BytesIO(firma_bytes), x=130, y=pdf.get_y()+5, w=50)
            except: pass

    elif tipo == "FATTURA":
        pdf.set_font("Arial", "B", 15)
        pdf.cell(0, 10, "RICEVUTA DI PAGAMENTO / RECEIPT", ln=True, align="C", border="B")
        pdf.ln(10)
        testo = f"Ricevuta n: {c.get('numero_fattura')} del {oggi}\n\nCliente: {c.get('nome')} {c.get('cognome')}\nTarga: {c.get('targa')}\nTotale: EUR {c.get('prezzo')}"
        pdf.multi_cell(0, 6, safe_text(testo))

    elif tipo == "MULTE":
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "COMUNICAZIONE DATI CONDUCENTE", ln=True, align="C")
        corpo = f"Il veicolo {c.get('targa')} in data {c.get('inizio')} era locato a:\n\n" \
                f"SOGGETTO: {c.get('nome')} {c.get('cognome')}\nNATO A: {c.get('luogo_nascita')} il {c.get('data_nascita')}\n" \
                f"RESIDENTE: {c.get('indirizzo_cliente')}\nPATENTE: {c.get('numero_patente')}"
        pdf.multi_cell(0, 6, safe_text(corpo))

    pdf_out = pdf.output(dest="S")
    return bytes(pdf_out) if not isinstance(pdf_out, str) else pdf_out.encode("latin-1")

# ------------------------------------------------
# LOGICA APP
# ------------------------------------------------
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.title("🔐 Accesso Master Rent")
    password = st.text_input("Password", type="password")
    if st.button("Accedi"):
        if password == "1234":
            st.session_state.autenticato = True
            st.rerun()
else:
    st.title("🛵 Gestione Noleggio")
    
    menu = st.sidebar.radio("Menu", ["Nuovo Noleggio", "Archivio"])

    if menu == "Nuovo Noleggio":
        with st.form("nuovo_noleggio", clear_on_submit=True):
            col1, col2 = st.columns(2)
            nome = col1.text_input("Nome")
            cognome = col1.text_input("Cognome")
            telefono = col1.text_input("Telefono (es. 393331234567)")
            cf = col1.text_input("Codice Fiscale / ID")
            ind = col1.text_area("Indirizzo")
            
            targa = col2.text_input("Targa").upper()
            pat = col2.text_input("Patente")
            l_nas = col2.text_input("Luogo nascita")
            d_nas = col2.text_input("Data nascita")
            prezzo = col2.number_input("Prezzo (€)", min_value=0.0)
            
            d1, d2 = st.columns(2)
            inizio, fine = d1.date_input("Inizio"), d2.date_input("Fine")

            f1, f2 = st.columns(2)
            fronte = f1.file_uploader("Fronte Patente", type=["jpg", "png", "jpeg"])
            retro = f2.file_uploader("Retro Patente", type=["jpg", "png", "jpeg"])

            check = st.checkbox("Accetto Condizioni e Privacy")
            canvas = st_canvas(stroke_width=3, stroke_color="#000", background_color="#eee", height=150, width=400, key="firma")

            if st.form_submit_button("💾 SALVA"):
                if check and nome and targa:
                    try:
                        firma_b64 = ""
                        if canvas.image_data is not None:
                            img = Image.fromarray(canvas.image_data.astype("uint8"))
                            buf = io.BytesIO()
                            img.save(buf, format="PNG")
                            firma_b64 = base64.b64encode(buf.getvalue()).decode()

                        u_f = upload_to_supabase(fronte, targa, "fronte")
                        u_r = upload_to_supabase(retro, targa, "retro")
                        n_f = prossimo_numero_fattura()

                        dati = {
                            "nome": nome, "cognome": cognome, "telefono": telefono, "targa": targa, 
                            "prezzo": prezzo, "inizio": str(inizio), "fine": str(fine),
                            "firma": firma_b64, "numero_fattura": n_f, "luogo_nascita": l_nas, 
                            "data_nascita": d_nas, "numero_patente": pat, "url_fronte": u_f, 
                            "url_retro": u_r, "codice_fiscale": cf, "indirizzo_cliente": ind
                        }
                        supabase.table("contratti").insert(dati).execute()
                        st.success("Salvato!")
                        st.rerun()
                    except Exception as e: st.error(f"Errore: {e}")

    else:
        st.subheader("📂 Archivio")
        res = supabase.table("contratti").select("*").order("id", desc=True).execute()
        if res.data:
            cerca = st.text_input("Cerca Targa o Cognome").lower()
            for c in res.data:
                if cerca in f"{c['targa']} {c['cognome']}".lower():
                    with st.expander(f"📝 {c['targa']} - {c['cognome'].upper()}"):
                        # --- SEZIONE DOWNLOAD PDF ---
                        st.write("### 📄 Documenti PDF")
                        col_p1, col_p2, col_p3 = st.columns(3)
                        p1 = genera_pdf_tipo(c, "CONTRATTO")
                        p2 = genera_pdf_tipo(c, "FATTURA")
                        p3 = genera_pdf_tipo(c, "MULTE")
                        col_p1.download_button("📜 Contratto", p1, f"Cont_{c['id']}.pdf")
                        col_p2.download_button("💰 Ricevuta", p2, f"Ric_{c['id']}.pdf")
                        col_p3.download_button("🚨 Modulo Multe", p3, f"Multe_{c['id']}.pdf")

                        # --- SEZIONE FOTO PATENTE ---
                        st.write("### 📸 Foto Patente (per Vigili)")
                        col_f1, col_f2 = st.columns(2)
                        if c.get("url_fronte"): col_f1.image(c["url_fronte"], caption="Fronte")
                        else: col_f1.warning("Fronte mancante")
                        if c.get("url_retro"): col_f2.image(c["url_retro"], caption="Retro")
                        else: col_f2.warning("Retro mancante")

                        # --- SEZIONE INVIO (WhatsApp / Email) ---
                        st.write("### 📲 Invia al Cliente")
                        tel = c.get('telefono', '')
                        msg = urllib.parse.quote(f"Ciao {c['nome']}, ecco il tuo contratto per lo scooter {c['targa']}. Grazie!")
                        
                        col_i1, col_i2 = st.columns(2)
                        if tel:
                            col_i1.markdown(f"[💬 WhatsApp](https://wa.me/{tel}?text={msg})")
                        
                        mail_sub = urllib.parse.quote(f"Contratto Noleggio {c['targa']}")
                        col_i2.markdown(f"[📧 Email](mailto:?subject={mail_sub}&body={msg})")
