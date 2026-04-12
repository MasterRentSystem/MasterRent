import streamlit as st
from supabase import create_client, Client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from fpdf import FPDF
import io
import base64
from datetime import datetime

# --- 1. SOSTITUISCI DA QUI ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(URL, KEY)
# --- A QUI ---

# ------------------------------------------------
# FUNZIONI UTILITY (il resto del codice continua qui...)
# ------------------------------------------------
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
        # Genera un nome unico per il file
        estensione = file.name.split('.')[-1]
        nome_file = f"{prefix}{targa}{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.{estensione}"
        
        # Carica il file su Supabase
        supabase.storage.from_("documenti").upload(nome_file, file.getvalue(), {"content-type": f"image/{estensione}"})
        
        # Recupera l'URL pubblico
        url_pubblico = supabase.storage.from_("documenti").get_public_url(nome_file)
        return url_pubblico
    except Exception as e:
        st.error(f"Errore caricamento foto: {e}")
        return None
# ------------------------------------------------
# FUNZIONE PDF
# ------------------------------------------------
def genera_pdf_tipo(c, tipo):
    pdf = FPDF()
    pdf.add_page()
    oggi = datetime.date.today().strftime("%d/%m/%Y")
    
    # Intestazione Ditta
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
                f"CONDIZIONI DI NOLEGGIO:\n" \
                f"1. Il conducente dichiara di essere in possesso di regolare patente.\n" \
                f"2. Il locatario e responsabile di ogni danno causato al veicolo o a terzi.\n" \
                f"3. In caso di furto, il locatario risponde per l'intero valore del veicolo.\n" \
                f"4. Tutte le contravvenzioni (multe) prese durante il periodo sono a carico del locatario.\n" \
                f"5. Il veicolo deve essere riconsegnato con lo stesso livello di carburante.\n\n" \
                f"INFORMATIVA PRIVACY (GDPR):\n" \
                f"Il cliente autorizza il trattamento dei dati personali e la conservazione digitale dei documenti " \
                f"(foto patente/ID) per fini fiscali e di pubblica sicurezza (comunicazione dati conducente alle autorita)."
        pdf.multi_cell(0, 5, safe_text(testo))
        if c.get("firma"):
            try:
                firma_bytes = base64.b64decode(c["firma"])
                pdf.image(io.BytesIO(firma_bytes), x=130, y=pdf.get_y()+10, w=50)
            except: pass
        pdf.ln(25)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 10, "Firma del Cliente per Accettazione", ln=True, align="R")

    elif tipo == "FATTURA":
        pdf.set_font("Arial", "B", 15)
        pdf.cell(0, 10, "RICEVUTA DI PAGAMENTO / RECEIPT", ln=True, align="C", border="B")
        pdf.ln(10)
        pdf.set_font("Arial", "", 10)
        testo = f"Ricevuta n: {c.get('numero_fattura')} del {oggi}\n\n" \
                f"Cliente: {c.get('nome')} {c.get('cognome')}\n" \
                f"Codice Fiscale / ID: {c.get('codice_fiscale', '---')}\n" \
                f"Targa: {c.get('targa')}\n" \
                f"Totale Incassato: EUR {c.get('prezzo')}"
        pdf.multi_cell(0, 6, safe_text(testo))

    elif tipo == "MULTE":
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 5, "Spett. le", ln=True, align="R")
        pdf.cell(0, 5, "Polizia Locale di ____________________", ln=True, align="R")
        pdf.ln(8)
        pdf.set_font("Arial", "B", 10)
        pdf.multi_cell(0, 5, safe_text("OGGETTO:  RIFERIMENTO VS. ACCERTAMENTO VIOLAZIONE N. __________________ PROT. ________ - COMUNICAZIONE LOCAZIONE VEICOLO"))
        pdf.ln(6)
        pdf.set_font("Arial", "", 10)
        corpo = f"In riferimento al Verbale di accertamento di infrazione al Codice della strada di cui all'oggetto, con la presente, la sottoscritta BATTAGLIA MARIANNA nata a Berlino (Germania) il 13/01/1987 e residente in Forio alla Via Cognole n. 5 in qualita di titolare dell'omonima ditta individuale, C.F.: BTTMNN87A53Z112S e P. IVA: 10252601215\n\n" \
                f"DICHIARA\n\n" \
                f"Ai sensi della L. 445/2000 che il veicolo targato {c.get('targa')} il giorno {c.get('inizio')} era concesso in locazione senza conducente al signor:\n\n" \
                f"COGNOME E NOME: {c.get('nome')} {c.get('cognome')}\n" \
                f"LUOGO E DATA DI NASCITA: {c.get('luogo_nascita')} il {c.get('data_nascita')}\n" \
                f"RESIDENZA: {c.get('indirizzo_cliente', '---')}\n" \
                f"IDENTIFICATO A MEZZO PATENTE: {c.get('numero_patente')}\n\n" \
                f"Si allega: Copia del contratto di locazione con documento del trasgressore.\n" \
                f"Ai sensi della L. 445/2000, si dichiara che la copia allegata e conforme all'originale.\n\n"
        pdf.multi_cell(0, 5, safe_text(corpo))
        pdf.ln(10)
        pdf.set_font("Arial", "I", 10)
        pdf.cell(0, 5, "In fede,", ln=True, align="R")
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 5, "Marianna Battaglia", ln=True, align="R")

    pdf_out = pdf.output(dest="S")
    return bytes(pdf_out) if not isinstance(pdf_out, str) else pdf_out.encode("latin-1")
# ------------------------------------------------
# LOGICA APP
# ------------------------------------------------
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False

# --- LOGICA DI ACCESSO ---
if not st.session_state.get("autenticato", False):
    st.title("🔐 Accesso Master Rent")
    password = st.text_input("Inserisci la password", type="password")
    if st.button("Accedi"):
        if password == "1234": # Sostituisci con la tua password
            st.session_state.autenticato = True
            st.rerun()
        else:
            st.error("Password errata")
else:
    # --- SE AUTENTICATO, MOSTRA IL RESTO ---
    st.title("🛵 Nuovo Noleggio Scooter")
    
    with st.form("nuovo_noleggio", clear_on_submit=True):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Nome")
        cognome = col1.text_input("Cognome")
        naz = col1.selectbox("Nazionalità", ["Italiana", "Straniera"])
        cf = col1.text_input("Codice Fiscale / ID Passaporto")
        ind = col1.text_area("Indirizzo Residenza Completo")
        
        targa = col2.text_input("Targa").upper()
        pat = col2.text_input("Numero Patente")
        l_nas = col2.text_input("Luogo nascita")
        d_nas = col2.text_input("Data nascita (GG/MM/AAAA)")
        prezzo = col2.number_input("Prezzo Totale (€)", min_value=0.0)
        deposito = col2.number_input("Deposito (€)", min_value=0.0)
        
        d1, d2 = st.columns(2)
        inizio = d1.date_input("Inizio Noleggio")
        fine = d2.date_input("Fine Noleggio")

        st.subheader("📸 Documenti")
        f1, f2 = st.columns(2)
        fronte = f1.file_uploader("Fronte Patente", type=["jpg", "png", "jpeg"])
        retro = f2.file_uploader("Retro Patente", type=["jpg", "png", "jpeg"])

        st.subheader("⚖️ Note Legali e Privacy")
        st.info("Dichiaro di aver preso visione delle condizioni di noleggio...")
        check_condizioni = st.checkbox("Accetto le Condizioni di Noleggio")
        check_privacy = st.checkbox("Accetto l'Informativa Privacy")

        st.subheader("✍️ Firma")
        canvas = st_canvas(stroke_width=3, stroke_color="#000", background_color="#eee", height=150, width=400, key="firma")

        if st.form_submit_button("💾 SALVA E GENERA"):
            if not check_condizioni or not check_privacy:
                st.error("Devi accettare le condizioni e la privacy per procedere!")
            elif nome and cognome and targa:
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
                        "nome": nome, "cognome": cognome, "targa": targa, "prezzo": prezzo, 
                        "deposito": deposito, "inizio": str(inizio), "fine": str(fine),
                        "firma": firma_b64, "numero_fattura": n_f, "luogo_nascita": l_nas, 
                        "data_nascita": d_nas, "numero_patente": pat, "url_fronte": u_f, 
                        "url_retro": u_r, "codice_fiscale": cf, "indirizzo_cliente": ind, "nazionalita": naz
                    }
                    
                    supabase.table("contratti").insert(dati).execute()
                    st.success(f"Contratto n° {n_f} salvato con successo!")
                    st.rerun()
                except Exception as e:
                    # QUESTO CI DIRÀ IL VERO ERRORE DI SUPABASE
                    st.error(f"⚠️ ERRORE DA SUPABASE: {str(e)}")
            else:
                st.error("Compila i campi obbligatori (Nome, Cognome, Targa)")

    # --- ARCHIVIO ---
    st.divider()
    st.subheader("📂 Archivio Contratti")
    try:
        res = supabase.table("contratti").select("*").order("id", desc=True).execute()
        if res.data:
            search_query = st.text_input("🔍 Cerca per Targa o Cognome", "").lower()
            for c in res.data:
                testo = f"{c.get('targa', '')} {c.get('cognome', '')}".lower()
                if search_query in testo:
                    with st.expander(f"📝 {c.get('targa')} - {c.get('cognome', '').upper()}"):
                        col_a, col_b, col_c = st.columns(3)
                        col_a.download_button("📜 Contratto", genera_pdf_tipo(c, "CONTRATTO"), f"Cont_{c['id']}.pdf")
                        col_b.download_button("💰 Ricevuta", genera_pdf_tipo(c, "FATTURA"), f"Ric_{c['id']}.pdf")
                        col_c.download_button("🚨 Multe", genera_pdf_tipo(c, "MULTE"), f"Multe_{c['id']}.pdf")
    except Exception as e:
        st.error(f"Errore caricamento archivio: {e}")
