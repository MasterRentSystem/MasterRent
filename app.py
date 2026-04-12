import streamlit as st
from supabase import create_client, Client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from fpdf import FPDF
import io
import base64
from datetime import datetime
import urllib.parse

# --- CONFIGURAZIONE ---
DITTA = "BATTAGLIA RENT"
INDIRIZZO_FISCALE = "Via Cognole n. 5, Forio (NA)"
DATI_IVA = "P.IVA: 10252601215 | C.F.: BTTMNN87A53Z112S"

URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# ------------------------------------------------
# IL FILTRO TOTALE
# ------------------------------------------------
def S(valore):
    """Trasforma QUALSIASI cosa in stringa. Se è None, diventa stringa vuota."""
    if valore is None: return ""
    return str(valore)

def PDF_T(testo):
    """Pulisce il testo per il PDF"""
    return S(testo).encode('latin-1', 'replace').decode('latin-1')

# ------------------------------------------------
# GENERAZIONE PDF INTEGRALE
# ------------------------------------------------
def crea_documento(dati, tipo):
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, PDF_T(DITTA), ln=True)
    pdf.set_font("Arial", "", 8)
    pdf.cell(0, 4, PDF_T(INDIRIZZO_FISCALE), ln=True)
    pdf.cell(0, 4, PDF_T(DATI_IVA), ln=True)
    pdf.ln(5)

    # Variabili pulite
    nome = S(dati.get('nome'))
    cognome = S(dati.get('cognome'))
    targa = S(dati.get('targa'))
    prezzo = S(dati.get('prezzo'))
    inizio = S(dati.get('inizio'))
    fine = S(dati.get('fine'))
    patente = S(dati.get('numero_patente'))
    cf = S(dati.get('codice_fiscale'))

    if tipo == "CONTRATTO":
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "CONTRATTO DI NOLEGGIO", ln=True, align="C", border="B")
        pdf.set_font("Arial", "", 9)
        testo_completo = f"""
CLIENTE: {nome} {cognome} | CF: {cf}
VEICOLO: {targa} | PATENTE: {patente}
PERIODO: dal {inizio} al {fine} | CORRISPETTIVO: EUR {prezzo}

CONDIZIONI GENERALI (Art. 1341-1342 c.c.):
1.⁠ ⁠Il cliente dichiara di ricevere il veicolo in ottimo stato e con il pieno.
2.⁠ ⁠Responsabilità: Il cliente risponde di ogni danno, del furto (se non consegna chiavi) e di tutte le sanzioni amministrative.
3.⁠ ⁠Assicurazione: Copertura RCA standard. Esclusi danni al conducente o per guida impropria.
4.⁠ ⁠Multe: Il cliente autorizza la ditta a fornire i propri dati alle autorità per la notifica dei verbali.
"""
        pdf.multi_cell(0, 5, PDF_T(testo_completo))
        
        firma = dati.get("firma")
        if firma:
            try:
                fb = base64.b64decode(S(firma))
                pdf.image(io.BytesIO(fb), x=130, y=pdf.get_y()+5, w=50)
            except: pass
        pdf.ln(20)
        pdf.cell(0, 10, "Firma per accettazione clausole 2-3", ln=True, align="R")

    elif tipo == "FATTURA":
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "RICEVUTA DI PAGAMENTO", ln=True, align="C", border="B")
        pdf.ln(10)
        pdf.set_font("Arial", "", 11)
        pdf.cell(0, 10, f"Ricevuta n. {S(dati.get('numero_fattura'))} del {datetime.now().strftime('%d/%m/%Y')}", ln=True)
        pdf.cell(0, 10, f"Spett.le {nome} {cognome}", ln=True)
        pdf.ln(5)
        pdf.cell(100, 10, f"Servizio noleggio scooter {targa}", 1)
        pdf.cell(40, 10, f"EUR {prezzo}", 1, 1, 'R')

    elif tipo == "MULTE":
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "DICHIARAZIONE DATI CONDUCENTE", ln=True, align="C")
        pdf.ln(10)
        multe = f"Il veicolo {targa} in data {inizio} era guidato da {nome} {cognome}, nato a {S(dati.get('luogo_nascita'))} il {S(dati.get('data_nascita'))}, residente in {S(dati.get('indirizzo_cliente'))}, patente {patente}."
        pdf.multi_cell(0, 8, PDF_T(multe))

    return pdf.output(dest="S").encode("latin-1")

# ------------------------------------------------
# APP
# ------------------------------------------------
if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    pw = st.text_input("Password", type="password")
    if st.button("Accedi"):
        if pw == "1234": 
            st.session_state.auth = True
            st.rerun()
else:
    m = st.sidebar.radio("Menu", ["Nuovo", "Archivio"])

    if m == "Nuovo":
        st.title("🛵 Nuovo Contratto")
        with st.form("f"):
            c1, c2 = st.columns(2)
            n = c1.text_input("Nome")
            c = c1.text_input("Cognome")
            t = c2.text_input("Targa").upper()
            p = c2.number_input("Prezzo", min_value=0.0)
            pat = c2.text_input("Patente")
            cf = c1.text_input("CF")
            ln = c1.text_input("Luogo Nascita")
            dn = c1.text_input("Data Nascita")
            ind = st.text_area("Indirizzo")
            ini = st.date_input("Inizio")
            fin = st.date_input("Fine")
            f1 = st.file_uploader("Fronte")
            f2 = st.file_uploader("Retro")
            canvas = st_canvas(stroke_width=2, height=100, width=300, key="sig")
            
            if st.form_submit_button("SALVA"):
                try:
                    sig_b64 = ""
                    if canvas.image_data is not None:
                        im = Image.fromarray(canvas.image_data.astype("uint8"))
                        bb = io.BytesIO()
                        im.save(bb, format="PNG")
                        sig_b64 = base64.b64encode(bb.getvalue()).decode()
                    
                    # Caricamento ultra-semplificato
                    u1, u2 = "", ""
                    if f1:
                        n1 = f"F_{t}_{datetime.now().strftime('%M%S')}.jpg"
                        supabase.storage.from_("documenti").upload(n1, f1.getvalue())
                        u1 = supabase.storage.from_("documenti").get_public_url(n1)
                    if f2:
                        n2 = f"R_{t}_{datetime.now().strftime('%M%S')}.jpg"
                        supabase.storage.from_("documenti").upload(n2, f2.getvalue())
                        u2 = supabase.storage.from_("documenti").get_public_url(n2)

                    last = supabase.table("contratti").select("numero_fattura").order("id", desc=True).limit(1).execute()
                    nf = (last.data[0]['numero_fattura'] + 1) if last.data else 1

                    # Salvataggio: tutto convertito in stringa esplicita
                    supabase.table("contratti").insert({
                        "nome": str(n), "cognome": str(c), "targa": str(t), "prezzo": float(p),
                        "inizio": str(ini), "fine": str(fin), "firma": str(sig_b64),
                        "numero_fattura": int(nf), "luogo_nascita": str(ln),
                        "data_nascita": str(dn), "numero_patente": str(pat),
                        "url_fronte": str(u1), "url_retro": str(u2),
                        "codice_fiscale": str(cf), "indirizzo_cliente": str(ind)
                    }).execute()
                    st.success("Fatto!")
                    st.rerun()
                except Exception as ex: st.error(f"Errore: {ex}")

    else:
        st.title("📂 Archivio")
        res = supabase.table("contratti").select("*").order("id", desc=True).execute()
        for r in res.data:
            # Qui è dove avviene il crash: forziamo il titolo
            titolo = f"{S(r.get('targa'))} - {S(r.get('cognome')).upper()}"
            with st.expander(titolo):
                col1, col2, col3 = st.columns(3)
                # Generazione PDF
                col1.download_button("📜 Contratto", crea_documento(r, "CONTRATTO"), f"C_{S(r.get('id'))}.pdf")
                col2.download_button("💰 Fattura", crea_documento(r, "FATTURA"), f"F_{S(r.get('id'))}.pdf")
                col3.download_button("🚨 Multe", crea_documento(r, "MULTE"), f"M_{S(r.get('id'))}.pdf")
