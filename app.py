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
TITOLARE = "BATTAGLIA MARIANNA"
DETTAGLI_TITOLARE = "nata a Berlino (Germania) il 13/01/1987 e residente in Forio alla Via Cognole n. 5"
INDIRIZZO_FISCALE = "Via Cognole n. 5, Forio (NA)"
DATI_IVA = "P.IVA: 10252601215 | C.F.: BTTMNN87A53Z112S"

# --- CONNESSIONE SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# ------------------------------------------------
# UTILITY ANTI-ERRORE
# ------------------------------------------------
def s(dato):
    if dato is None: return ""
    return str(dato)

def safe_pdf_text(text):
    return s(text).encode("latin-1", "replace").decode("latin-1")

def prossimo_numero_fattura():
    try:
        res = supabase.table("contratti").select("numero_fattura").order("numero_fattura", desc=True).limit(1).execute()
        if res.data:
            ultimo = res.data[0].get("numero_fattura")
            return int(ultimo) + 1 if ultimo else 1
        return 1
    except: return 1

# ------------------------------------------------
# GENERAZIONE PDF (TESTI LEGALI BLINDATI)
# ------------------------------------------------
def genera_pdf_tipo(c, tipo):
    pdf = FPDF()
    pdf.add_page()
    oggi = datetime.now().strftime("%d/%m/%Y")
    
    # Intestazione Standard
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, safe_pdf_text(DITTA), ln=True)
    pdf.set_font("Arial", "", 8)
    pdf.cell(0, 4, safe_pdf_text(INDIRIZZO_FISCALE), ln=True)
    pdf.cell(0, 4, safe_pdf_text(DATI_IVA), ln=True)
    pdf.ln(5)

    nome_completo = f"{s(c.get('nome'))} {s(c.get('cognome'))}"
    targa = s(c.get('targa'))

    if tipo == "CONTRATTO":
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "CONTRATTO DI NOLEGGIO / RENTAL AGREEMENT", ln=True, align="C", border="B")
        pdf.ln(5)
        pdf.set_font("Arial", "", 10)
        
        testo = f"Cliente: {nome_completo} | CF/ID: {s(c.get('codice_fiscale'))}\n" \
                f"Residenza: {s(c.get('indirizzo_cliente'))}\n" \
                f"Targa: {targa} | Patente: {s(c.get('numero_patente'))}\n" \
                f"Periodo: dal {s(c.get('inizio'))} al {s(c.get('fine'))} | Prezzo: EUR {s(c.get('prezzo'))}\n\n" \
                f"CONDIZIONI DI NOLEGGIO:\n" \
                f"1. Il conducente dichiara di essere in possesso di regolare patente di guida in corso di validita.\n" \
                f"2. Il locatario e responsabile di ogni danno causato al veicolo, a se stesso o a terzi durante il noleggio.\n" \
                f"3. In caso di furto, il locatario risponde per l'intero valore commerciale del veicolo se non riconsegna le chiavi.\n" \
                f"4. Tutte le contravvenzioni (multe) prese durante il periodo sono a carico del locatario.\n" \
                f"5. Il veicolo deve essere riconsegnato con lo stesso livello di carburante iniziale.\n\n" \
                f"INFORMATIVA PRIVACY (GDPR):\n" \
                f"Il cliente autorizza il trattamento dei dati personali e la conservazione digitale dei documenti (foto patente/ID) " \
                f"per fini fiscali e di pubblica sicurezza (comunicazione dati conducente alle autorita).\n\n" \
                f"Ai sensi degli artt. 1341 e 1342 c.c. il cliente approva specificamente i punti 2, 3 e 4."
        
        pdf.multi_cell(0, 5, safe_pdf_text(testo))
        if c.get("firma"):
            try:
                firma_bytes = base64.b64decode(s(c["firma"]))
                pdf.image(io.BytesIO(firma_bytes), x=130, y=pdf.get_y()+5, w=50)
            except: pass
        pdf.ln(20)
        pdf.cell(0, 10, "Firma del Cliente per Accettazione", ln=True, align="R")

    elif tipo == "MULTE":
        pdf.set_font("Arial", "", 10)
        pdf.ln(10)
        pdf.cell(0, 5, "Spett. le", ln=True)
        pdf.cell(0, 5, "Polizia Locale di ________________", ln=True)
        pdf.ln(5)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 5, "OGGETTO: RIFERIMENTO VS. ACCERTAMENTO VIOLAZIONE N. ______________ PROT. ____", ln=True)
        pdf.cell(0, 5, "COMUNICAZIONE LOCAZIONE VEICOLO", ln=True)
        pdf.ln(5)
        pdf.set_font("Arial", "", 10)
        
        corpo = f"In riferimento al Verbale di accertamento di infrazione al Codice della strada di cui all'oggetto, con la presente, " \
                f"la sottoscritta {TITOLARE} {DETTAGLI_TITOLARE} in qualita di titolare dell'omonima ditta individuale, " \
                f"{DATI_IVA}\n\n" \
                f"DICHIARA\n" \
                f"Ai sensi della L. 445/2000 che il veicolo targato {targa} il giorno {s(c.get('inizio'))} era concesso in locazione senza conducente al signor:\n\n" \
                f"COGNOME E NOME: {nome_completo}\n" \
                f"LUOGO E DATA DI NASCITA: {s(c.get('luogo_nascita'))} il {s(c.get('data_nascita'))}\n" \
                f"RESIDENTE: {s(c.get('indirizzo_cliente'))}\n" \
                f"IDENTIFICATO A MEZZO PATENTE: {s(c.get('numero_patente'))}\n\n" \
                f"Si allega: Copia del contratto di locazione con documento del trasgressore.\n" \
                f"Ai sensi della L. 445/2000, si dichiara che la copia allegata e conforme all'originale.\n\n" \
                f"In fede,\nMarianna Battaglia"
        
        pdf.multi_cell(0, 5, safe_pdf_text(corpo))

    elif tipo == "FATTURA":
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "RICEVUTA DI PAGAMENTO", ln=True, align="C", border="B")
        pdf.ln(10)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, f"Ricevuta n: {s(c.get('numero_fattura'))}/A del {oggi}", ln=True)
        pdf.cell(0, 6, f"Cliente: {nome_completo}", ln=True)
        pdf.ln(10)
        pdf.cell(100, 10, safe_pdf_text(f"Noleggio Scooter targa {targa}"), 1)
        pdf.cell(40, 10, f"EUR {s(c.get('prezzo'))}", 1, 1, 'R')

    return pdf.output(dest="S").encode("latin-1")

# ------------------------------------------------
# LOGICA APP STREAMLIT (RIMANE QUELLA STABILE)
# ------------------------------------------------
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.title("🔐 Accesso Battaglia Rent")
    if st.text_input("Password", type="password") == "1234":
        if st.button("Entra"): 
            st.session_state.autenticato = True
            st.rerun()
else:
    menu = st.sidebar.radio("Menu", ["Nuovo Noleggio", "Archivio"])

    if menu == "Nuovo Noleggio":
        st.title("🛵 Registra Noleggio")
        with st.form("main_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            n = c1.text_input("Nome")
            c = c1.text_input("Cognome")
            t = c2.text_input("Targa").upper()
            p = c2.number_input("Prezzo (€)", min_value=0.0)
            
            c3, c4 = st.columns(2)
            pat = c3.text_input("Patente")
            cf = c4.text_input("Codice Fiscale")
            ln = c3.text_input("Luogo Nascita")
            dn = c4.text_input("Data Nascita (es: 13/01/1987)")
            
            ind = st.text_area("Indirizzo Residenza Completo")
            ini = st.date_input("Data Inizio")
            fin = st.date_input("Data Fine")
            
            st.subheader("🖋️ Firma per Accettazione")
            canvas = st_canvas(stroke_width=3, height=150, width=400, key="f_sig")
            accetta = st.checkbox("Il cliente approva le clausole contrattuali e il GDPR")

            if st.form_submit_button("💾 SALVA"):
                if accetta and n and t:
                    try:
                        f_b64 = ""
                        if canvas.image_data is not None:
                            img = Image.fromarray(canvas.image_data.astype("uint8"))
                            buf = io.BytesIO()
                            img.save(buf, format="PNG")
                            f_b64 = base64.b64encode(buf.getvalue()).decode()

                        nf = prossimo_numero_fattura()
                        dati = {
                            "nome": n, "cognome": c, "targa": t, "prezzo": p,
                            "inizio": str(ini), "fine": str(fin), "firma": f_b64,
                            "numero_fattura": nf, "luogo_nascita": ln, "data_nascita": dn,
                            "numero_patente": pat, "codice_fiscale": cf, "indirizzo_cliente": ind
                        }
                        supabase.table("contratti").insert(dati).execute()
                        st.success("Salvato!")
                        st.rerun()
                    except Exception as e: st.error(f"Errore: {e}")

    else:
        st.title("📂 Archivio")
        res = supabase.table("contratti").select("*").order("id", desc=True).execute()
        for r in res.data:
            with st.expander(f"📄 {r['targa']} - {r['cognome']}"):
                col1, col2, col3 = st.columns(3)
                col1.download_button("📜 Contratto", genera_pdf_tipo(r, "CONTRATTO"), f"Contr_{r['targa']}.pdf")
                col2.download_button("💰 Ricevuta", genera_pdf_tipo(r, "FATTURA"), f"Ric_{r['id']}.pdf")
                col3.download_button("🚨 Modulo Vigili", genera_pdf_tipo(r, "MULTE"), f"Multe_{r['targa']}.pdf")
