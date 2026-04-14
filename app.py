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

# --- MOTORE PDF PROFESSIONALE ---
class ProPDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.cell(0, 8, safe_text(DITTA), ln=True)
        self.set_font("Arial", "", 9)
        self.cell(0, 5, safe_text(f"{INDIRIZZO} | {DATI_IVA}"), ln=True)
        self.line(10, 28, 200, 28)
        self.ln(10)

def genera_pdf_professionale(c, tipo="CONTRATTO"):
    pdf = ProPDF()
    pdf.add_page()
    num_doc = s(c.get('numero_fattura'))
    anno = datetime.now().year
    
    # Titolo Documento e Numero Sequenziale
    pdf.set_font("Arial", "B", 16)
    titolo = f"{tipo} DI NOLEGGIO N. {num_doc} / {anno}"
    if tipo == "FATTURA": titolo = f"RICEVUTA FISCALE N. {num_doc} / {anno}"
    if tipo == "VIGILI": titolo = "DICHIARAZIONE CONDUCENTE PER SANZIONI"
    
    pdf.cell(0, 10, safe_text(titolo), ln=True, align="C")
    pdf.ln(5)

    # Tabella Dati Cliente
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 8, " DATI DEL CONDUTTORE (CLIENTE)", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "", 10)
    
    anagrafica = (
        f"Nome e Cognome: {s(c.get('nome'))} {s(c.get('cognome'))}\n"
        f"Luogo e Data di Nascita: {s(c.get('luogo_nascita'))}, {s(c.get('data_nascita'))}\n"
        f"Codice Fiscale: {s(c.get('codice_fiscale'))} | Nazionalita: {s(c.get('nazionalita'))}\n"
        f"Residenza: {s(c.get('indirizzo_cliente'))} | Tel: {s(c.get('telefono'))}"
    )
    pdf.multi_cell(0, 6, safe_text(anagrafica), border=1)
    pdf.ln(4)

    # Tabella Veicolo e Noleggio
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 8, " DETTAGLI NOLEGGIO E VEICOLO", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "", 10)
    
    dettagli = [
        ["Modello:", s(c.get('modello')), "Targa:", s(c.get('targa'))],
        ["Patente:", s(c.get('numero_patente')), "Benzina:", s(c.get('benzina'))],
        ["Inizio:", s(c.get('inizio')), "Fine:", s(c.get('fine'))],
        ["Prezzo:", f"EUR {s(c.get('prezzo'))}", "Deposito:", f"EUR {s(c.get('deposito'))}"]
    ]
    for row in dettagli:
        pdf.cell(45, 7, safe_text(row[0]), border=1)
        pdf.cell(50, 7, safe_text(row[1]), border=1)
        pdf.cell(45, 7, safe_text(row[2]), border=1)
        pdf.cell(50, 7, safe_text(row[3]), border=1, ln=True)
    
    pdf.ln(4)
    
    if tipo == "CONTRATTO":
        pdf.set_font("Arial", "B", 9)
        pdf.cell(0, 7, " NOTE E STATO D'USO:", ln=True)
        pdf.set_font("Arial", "I", 9)
        pdf.multi_cell(0, 5, safe_text(s(c.get('note_danni')) or "Nessun danno rilevato"), border=1)
        
        pdf.ln(5)
        pdf.set_font("Arial", "B", 8)
        pdf.cell(0, 5, "CONDIZIONI GENERALI E CLAUSOLE VESSATORIE:", ln=True)
        pdf.set_font("Arial", "", 7)
        clausole = (
            "1. Il locatario dichiara di essere responsabile per danni al veicolo, furto e incendio.\n"
            "2. Ai sensi dell'art. 126 bis C.d.S., il cliente e responsabile per tutte le sanzioni amministrative.\n"
            "3. Il cliente approva specificamente le clausole di cui agli artt. 1341 e 1342 del Codice Civile.\n"
            "4. Foro competente: Tribunale di Napoli."
        )
        pdf.multi_cell(0, 4, safe_text(clausole))
        
        # Firma posizionata meglio
        if c.get("firma") and len(str(c["firma"])) > 50:
            pdf.ln(5)
            curr_y = pdf.get_y()
            pdf.image(io.BytesIO(base64.b64decode(c["firma"])), x=140, y=curr_y, w=40)
            pdf.set_y(curr_y + 15)
            pdf.cell(0, 10, "Firma Legale del Cliente", align="R")

    elif tipo == "VIGILI":
        pdf.ln(10)
        testo_v = (
            f"La sottoscritta {TITOLARE}, in qualita di titolare della ditta {DITTA},\n"
            f"comunica che in data {s(c.get('inizio'))} il veicolo targato {s(c.get('targa'))}\n"
            f"era condotto dal Sig. {s(c.get('nome'))} {s(c.get('cognome'))}.\n"
            "Si richiede la notifica del verbale direttamente al trasgressore sopra indicato."
        )
        pdf.set_font("Arial", "", 12)
        pdf.multi_cell(0, 7, safe_text(testo_v))
        pdf.ln(20)
        pdf.cell(0, 10, "Timbro e Firma del Titolare", ln=True)

    output = pdf.output(dest="S")
    return bytes(output) if not isinstance(output, str) else output.encode("latin-1", "replace")

# --- LOGIN ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Accesso Riservato", type="password") == "1234":
        if st.button("Entra"): st.session_state.auth = True; st.rerun()
    st.stop()

# --- APP ---
t1, t2 = st.tabs(["🆕 Emissione Contratto", "📂 Registro Storico"])

with t1:
    with st.form("form_noleggio_v3"):
        st.subheader("📋 Anagrafica Cliente")
        c1, c2, c3 = st.columns(3)
        nome = c1.text_input("Nome")
        cognome = c2.text_input("Cognome")
        telefono = c3.text_input("Cellulare")
        
        c4, c5, c6 = st.columns(3)
        nazion = c4.text_input("Nazionalita")
        cf = c5.text_input("Codice Fiscale")
        luogo_n = c6.text_input("Luogo Nascita")
        
        c4b, c5b = st.columns(2)
        data_n = c4b.text_input("Data Nascita (GG/MM/AAAA)")
        indirizzo = c5b.text_input("Indirizzo Residenza")
        
        st.subheader("🛵 Dettagli Scooter")
        c7, c8, c9 = st.columns(3)
        modello = c7.text_input("Modello")
        targa = c8.text_input("Targa").upper()
        benzina = c9.selectbox("Benzina", ["1/8", "1/4", "1/2", "3/4", "PIENO"])
        
        patente = st.text_input("Numero Patente")
        note_danni = st.text_area("Note Danni / Stato Mezzo")
        
        st.subheader("💰 Condizioni Economiche")
        c10, c11, c12, c13 = st.columns(4)
        prezzo = c10.number_input("Prezzo (€)", min_value=0.0)
        deposito = c11.number_input("Deposito (€)", min_value=0.0)
        inizio = c12.date_input("Data Inizio")
        fine = c13.date_input("Data Fine")
        
        f_p = st.file_uploader("Fronte Patente")
        r_p = st.file_uploader("Retro Patente")
        
        st.write("✒️ *Firma del Cliente per accettazione termini legali:*")
        canvas = st_canvas(height=120, width=400, stroke_width=3, key="sig_v3")
        conferma = st.checkbox("Dichiaro che il cliente ha visionato e accettato le condizioni legali")

        if st.form_submit_button("CONFERMA E REGISTRA"):
            if not nome or not targa or not conferma:
                st.error("Dati obbligatori mancanti o termini non accettati!")
            else:
                with st.spinner("Generazione documenti..."):
                    img_f = Image.fromarray(canvas.image_data.astype("uint8"))
                    buf_f = io.BytesIO()
                    img_f.save(buf_f, format="PNG")
                    firma_b64 = base64.b64encode(buf_f.getvalue()).decode()
                    
                    num_f = get_prossimo_numero()
                    
                    nuovo = {
                        "nome": nome, "cognome": cognome, "telefono": telefono,
                        "nazionalita": nazion, "codice_fiscale": cf, "luogo_nascita": luogo_n,
                        "data_nascita": data_n, "indirizzo_cliente": indirizzo,
                        "modello": modello, "targa": targa, "numero_patente": patente,
                        "benzina": benzina, "note_danni": note_danni, "prezzo": prezzo,
                        "deposito": deposito, "inizio": str(inizio), "fine": str(fine),
                        "firma": firma_b64, "numero_fattura": num_f,
                        "data_creazione": datetime.now().isoformat()
                    }
                    
                    res = supabase.table("contratti").insert(nuovo).execute()
                    st.success(f"OPERAZIONE COMPLETATA! DOCUMENTO N. {num_f}")

with t2:
    st.subheader("🔍 Ricerca nel Registro Storico")
    cerca = st.text_input("Filtra per Targa o Cognome").lower()
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    
    for r in res.data:
        if cerca in f"{r['cognome']} {r['targa']}".lower():
            with st.expander(f"DOC N. {r['numero_fattura']} | {r['targa']} - {r['cognome'].upper()}"):
                col_a, col_b, col_c = st.columns(3)
                col_a.download_button("📜 CONTRATTO", genera_pdf_professionale(r, "CONTRATTO"), f"Contratto_{r['numero_fattura']}.pdf")
                col_b.download_button("💰 RICEVUTA", genera_pdf_professionale(r, "FATTURA"), f"Ricevuta_{r['numero_fattura']}.pdf")
                col_c.download_button("🚨 MODULO VIGILI", genera_pdf_professionale(r, "VIGILI"), f"Vigili_{r['numero_fattura']}.pdf")
