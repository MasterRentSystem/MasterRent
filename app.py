import streamlit as st
from supabase import create_client, Client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from fpdf import FPDF
import io
import base64
from datetime import datetime

# --- CONFIGURAZIONE AZIENDALE ---
DITTA = "BATTAGLIA RENT"
TITOLARE = "BATTAGLIA MARIANNA"
INDIRIZZO = "Via Cognole n. 5, Forio (NA)"
DATI_IVA = "P.IVA: 10252601215 | C.F.: BTTMNN87A53Z112S"

URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- UTILITY ---
def s(v): return "" if v is None else str(v)

def safe_text(text):
    return s(text).encode("latin-1", "replace").decode("latin-1")

def get_prossimo_numero():
    try:
        res = supabase.table("contratti").select("numero_fattura").order("numero_fattura", desc=True).limit(1).execute()
        if res.data and res.data[0].get("numero_fattura"):
            return int(res.data[0]["numero_fattura"]) + 1
        return 1
    except: return 1

# --- CLASSE PDF PROFESSIONALE ---
class ProPDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 6, safe_text(DITTA), ln=True)
        self.set_font("Arial", "", 8)
        self.cell(0, 4, safe_text(f"{INDIRIZZO} | {DATI_IVA}"), ln=True)
        self.line(10, 25, 200, 25)
        self.ln(10)

def genera_pdf_professionale(c, tipo="CONTRATTO"):
    pdf = ProPDF()
    pdf.add_page()
    
    # Recupero numero sequenziale
    n_doc = s(c.get('numero_fattura'))
    data_doc = s(c.get('data_creazione'))[:10] if c.get('data_creazione') else datetime.now().strftime("%d/%m/%Y")

    # Titolo del Documento
    pdf.set_font("Arial", "B", 14)
    if tipo == "CONTRATTO": titolo = f"CONTRATTO DI NOLEGGIO N. {n_doc}"
    elif tipo == "FATTURA": titolo = f"RICEVUTA FISCALE N. {n_doc}"
    else: titolo = "DICHIARAZIONE DATI CONDUCENTE (VIGILI)"
    
    pdf.cell(0, 10, safe_text(titolo), ln=True, align="C", border="B")
    pdf.set_font("Arial", "I", 9)
    pdf.cell(0, 8, f"Data emissione: {data_doc}", ln=True, align="R")
    pdf.ln(5)

    # Tabella Cliente
    pdf.set_fill_color(245, 245, 245)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, " DATI DEL CLIENTE", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "", 10)
    info_cliente = (
        f"Nome: {s(c.get('nome'))} {s(c.get('cognome'))} | C.F.: {s(c.get('codice_fiscale'))}\n"
        f"Nato a: {s(c.get('luogo_nascita'))} ({s(c.get('data_nascita'))}) | Nazionalità: {s(c.get('nazionalita'))}\n"
        f"Residenza: {s(c.get('indirizzo_cliente'))} | Tel: {s(c.get('telefono'))}"
    )
    pdf.multi_cell(0, 6, safe_text(info_cliente), border=1)
    pdf.ln(5)

    # Tabella Noleggio
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, " DETTAGLI VEICOLO E NOLEGGIO", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "", 10)
    
    # Griglia dati
    col_w = 47.5
    pdf.cell(col_w, 7, "Modello:", border=1); pdf.cell(col_w, 7, safe_text(c.get('modello')), border=1)
    pdf.cell(col_w, 7, "Targa:", border=1); pdf.cell(col_w, 7, safe_text(c.get('targa')), border=1, ln=True)
    pdf.cell(col_w, 7, "Inizio:", border=1); pdf.cell(col_w, 7, safe_text(c.get('inizio')), border=1)
    pdf.cell(col_w, 7, "Fine:", border=1); pdf.cell(col_w, 7, safe_text(c.get('fine')), border=1, ln=True)
    pdf.cell(col_w, 7, "Benzina:", border=1); pdf.cell(col_w, 7, safe_text(c.get('benzina')), border=1)
    pdf.cell(col_w, 7, "Prezzo:", border=1); pdf.cell(col_w, 7, f"EUR {s(c.get('prezzo'))}", border=1, ln=True)
    
    pdf.ln(5)
    
    # Note Danni
    pdf.set_font("Arial", "B", 9)
    pdf.cell(0, 6, "STATO DEL MEZZO / NOTE DANNI:", ln=True)
    pdf.set_font("Arial", "I", 9)
    pdf.multi_cell(0, 5, safe_text(s(c.get('note_danni')) or "Nessun danno rilevato al momento della consegna."), border=1)

    if tipo == "CONTRATTO":
        pdf.ln(5)
        pdf.set_font("Arial", "B", 8)
        pdf.cell(0, 5, "INFORMATIVA LEGALE E PRIVACY:", ln=True)
        pdf.set_font("Arial", "", 7)
        legal = (
            "Il cliente si assume la piena responsabilita del veicolo. In caso di sanzioni amministrative, il locatario autorizza fin d'ora "
            "la comunicazione dei propri dati alle autorità competenti (Art. 126 bis CdS). Il veicolo deve essere restituito nelle stesse condizioni.\n"
            "Ai sensi degli artt. 1341-1342 c.c. il cliente approva specificamente le clausole relative a danni, furto e multe."
        )
        pdf.multi_cell(0, 4, safe_text(legal))
        
        # --- FIX BINASCII ERROR ---
        firma_b64 = c.get("firma")
        if firma_b64 and len(str(firma_b64)) > 50:
            try:
                # Verifichiamo che sia base64 valido prima di procedere
                firma_data = base64.b64decode(firma_b64)
                curr_y = pdf.get_y() + 5
                pdf.image(io.BytesIO(firma_data), x=140, y=curr_y, w=40)
                pdf.set_y(curr_y + 15)
                pdf.set_font("Arial", "B", 10)
                pdf.cell(0, 10, "Firma del Cliente", align="R")
            except Exception:
                pass # Se la firma è vecchia o corrotta, il PDF non crasha più

    elif tipo == "VIGILI":
        pdf.ln(10)
        pdf.set_font("Arial", "", 12)
        testo_vigili = (
            f"Io sottoscritta {TITOLARE}, responsabile della ditta {DITTA},\n"
            f"dichiaro che il veicolo targato {s(c.get('targa'))} era noleggiato al Sig. {s(c.get('nome'))} {s(c.get('cognome'))}\n"
            f"nel periodo indicato nel contratto N. {n_doc}. Si richiede l'invio del verbale al trasgressore."
        )
        pdf.multi_cell(0, 7, safe_text(testo_vigili))

    # Output sicuro in byte
    out = pdf.output(dest="S")
    return bytes(out) if not isinstance(out, str) else out.encode("latin-1", "replace")

# --- LOGIN ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Password", type="password") == "1234":
        if st.button("Accedi"): st.session_state.auth = True; st.rerun()
    st.stop()

# --- APP ---
t1, t2 = st.tabs(["🆕 Nuovo Contratto", "📂 Archivio"])

with t1:
    with st.form("form_v4", clear_on_submit=True):
        st.subheader("Anagrafica Cliente")
        c1, c2, c3 = st.columns(3)
        n = c1.text_input("Nome")
        cog = c2.text_input("Cognome")
        tel = c3.text_input("Telefono")
        naz = c1.text_input("Nazionalità")
        cf = c2.text_input("Codice Fiscale")
        luo = c3.text_input("Luogo Nascita")
        dat_n = c1.text_input("Data Nascita")
        ind = st.text_input("Indirizzo Residenza")
        
        st.subheader("Dati Scooter")
        c4, c5, c6 = st.columns(3)
        mod = c4.text_input("Modello")
        tar = c5.text_input("Targa").upper()
        ben = c6.selectbox("Livello Benzina", ["1/8", "2/8", "3/8", "4/8", "5/8", "6/8", "7/8", "PIENO"])
        pat = st.text_input("N. Patente")
        danni = st.text_area("Note Danni")
        
        c7, c8, c9, c10 = st.columns(4)
        prz = c7.number_input("Prezzo (€)", min_value=0.0)
        dep = c8.number_input("Deposito (€)", min_value=0.0)
        ini = c9.date_input("Inizio")
        fin = c10.date_input("Fine")
        
        st.write("Firma Cliente:")
        canvas = st_canvas(height=120, width=400, stroke_width=3, key="canvas_v4")
        accetto = st.checkbox("Accetto termini legali e clausole multe")

        if st.form_submit_button("REGISTRA"):
            if not n or not tar or not accetto:
                st.error("Dati obbligatori mancanti!")
            else:
                with st.spinner("Salvataggio..."):
                    img_f = Image.fromarray(canvas.image_data.astype("uint8"))
                    buf_f = io.BytesIO()
                    img_f.save(buf_f, format="PNG")
                    firma_b64 = base64.b64encode(buf_f.getvalue()).decode()
                    
                    nuovo_n = get_prossimo_numero()
                    data_save = {
                        "nome": n, "cognome": cog, "telefono": tel, "nazionalita": naz,
                        "codice_fiscale": cf, "luogo_nascita": luo, "data_nascita": dat_n,
                        "indirizzo_cliente": ind, "modello": mod, "targa": tar,
                        "numero_patente": pat, "benzina": ben, "note_danni": danni,
                        "prezzo": prz, "deposito": dep, "inizio": str(ini), "fine": str(fin),
                        "firma": firma_b64, "numero_fattura": nuovo_n, "data_creazione": datetime.now().isoformat()
                    }
                    supabase.table("contratti").insert(data_save).execute()
                    st.success(f"Registrato! N. {nuovo_n}")

with t2:
    search = st.text_input("🔍 Cerca...").lower()
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    for r in res.data:
        if search in f"{r['cognome']} {r['targa']}".lower():
            with st.expander(f"DOC N. {r['numero_fattura']} | {r['targa']} - {r['cognome']}"):
                c1, c2, c3 = st.columns(3)
                c1.download_button("📜 Contratto", genera_pdf_professionale(r, "CONTRATTO"), f"Contr_{r['numero_fattura']}.pdf")
                c2.download_button("💰 Ricevuta", genera_pdf_professionale(r, "FATTURA"), f"Ricevuta_{r['numero_fattura']}.pdf")
                c3.download_button("🚨 Vigili", genera_pdf_professionale(r, "VIGILI"), f"Vigili_{r['numero_fattura']}.pdf")
