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

# Connessione Database
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- UTILITY ---
def s(v): return "" if v is None else str(v)

def safe_text(text):
    """Gestisce i caratteri speciali per il PDF"""
    return s(text).encode("latin-1", "replace").decode("latin-1")

def get_prossimo_numero():
    """Recupera l'ultimo numero fattura e incrementa"""
    try:
        res = supabase.table("contratti").select("numero_fattura").order("numero_fattura", desc=True).limit(1).execute()
        if res.data and res.data[0].get("numero_fattura"):
            return int(res.data[0]["numero_fattura"]) + 1
        return 1
    except: return 1

# --- MOTORE PDF PROFESSIONALE ---
class ProPDF(FPDF):
    def header(self):
        # Intestazione con Logo Testuale
        self.set_font("Arial", "B", 16)
        self.set_text_color(0, 51, 102) # Blu scuro
        self.cell(0, 8, safe_text(DITTA), ln=True, align="L")
        self.set_font("Arial", "", 8)
        self.set_text_color(0, 0, 0)
        self.cell(0, 4, safe_text(f"{INDIRIZZO}"), ln=True)
        self.cell(0, 4, safe_text(f"{DATI_IVA}"), ln=True)
        self.line(10, 28, 200, 28)
        self.ln(12)

def genera_documento(c, tipo="CONTRATTO"):
    pdf = ProPDF()
    pdf.add_page()
    
    n_doc = s(c.get('numero_fattura'))
    data_doc = s(c.get('data_creazione'))[:10] if c.get('data_creazione') else datetime.now().strftime("%Y-%m-%d")

    # Titolo Documento
    pdf.set_font("Arial", "B", 14)
    if tipo == "CONTRATTO": 
        titolo = f"CONTRATTO DI NOLEGGIO N. {n_doc}"
    elif tipo == "FATTURA": 
        titolo = f"RICEVUTA / FATTURA N. {n_doc}"
    else: 
        titolo = "COMUNICAZIONE DATI CONDUCENTE (VIGILI)"
    
    pdf.cell(0, 10, safe_text(titolo), ln=True, align="C")
    pdf.set_font("Arial", "I", 10)
    pdf.cell(0, 8, f"Data: {data_doc}", ln=True, align="R")
    pdf.ln(5)

    # 1. Box Anagrafica
    pdf.set_fill_color(230, 240, 255)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 8, " 1. DATI DEL CLIENTE (CONDUTTORE)", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "", 10)
    info = (
        f"Nome e Cognome: {s(c.get('nome'))} {s(c.get('cognome'))} | Nazionalita: {s(c.get('nazionalita'))}\n"
        f"Luogo e Data Nascita: {s(c.get('luogo_nascita'))}, {s(c.get('data_nascita'))}\n"
        f"Codice Fiscale: {s(c.get('codice_fiscale'))} | Patente: {s(c.get('numero_patente'))}\n"
        f"Residenza: {s(c.get('indirizzo_cliente'))} | Telefono: {s(c.get('telefono'))}"
    )
    pdf.multi_cell(0, 6, safe_text(info), border=1)
    pdf.ln(4)

    # 2. Box Veicolo
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 8, " 2. DETTAGLI VEICOLO E NOLEGGIO", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "", 10)
    
    # Griglia Tecnica
    pdf.cell(45, 8, "Modello Scooter:", border=1); pdf.cell(50, 8, safe_text(c.get('modello')), border=1)
    pdf.cell(45, 8, "Targa:", border=1); pdf.cell(50, 8, safe_text(c.get('targa')), border=1, ln=True)
    pdf.cell(45, 8, "Inizio Noleggio:", border=1); pdf.cell(50, 8, safe_text(c.get('inizio')), border=1)
    pdf.cell(45, 8, "Fine Noleggio:", border=1); pdf.cell(50, 8, safe_text(c.get('fine')), border=1, ln=True)
    pdf.cell(45, 8, "Livello Benzina:", border=1); pdf.cell(50, 8, safe_text(c.get('benzina')), border=1)
    pdf.cell(45, 8, "Prezzo Totale:", border=1); pdf.cell(50, 8, f"EUR {s(c.get('prezzo'))}", border=1, ln=True)
    pdf.cell(45, 8, "Deposito/Cauzione:", border=1); pdf.cell(145, 8, f"EUR {s(c.get('deposito'))}", border=1, ln=True)
    
    pdf.ln(4)

    # 3. Note Danni
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 8, " 3. STATO DEL MEZZO / NOTE DANNI", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "I", 10)
    pdf.multi_cell(0, 6, safe_text(s(c.get('note_danni')) or "Il veicolo non presenta danni visibili."), border=1)
    
    if tipo == "CONTRATTO":
        pdf.ln(5)
        pdf.set_font("Arial", "B", 8)
        pdf.cell(0, 5, "CONDIZIONI GENERALI (Artt. 1341-1342 C.C.):", ln=True)
        pdf.set_font("Arial", "", 7)
        legal = (
            "- Il cliente e costituito custode del veicolo ed e responsabile di ogni danno, furto o incendio.\n"
            "- Il cliente dichiara che i dati della patente sono corretti e in corso di validita.\n"
            "- Le sanzioni amministrative (multe) elevate durante il noleggio sono a carico esclusivo del cliente.\n"
            "- Foro competente: Tribunale di Napoli."
        )
        pdf.multi_cell(0, 4, safe_text(legal))
        
        # Firma
        firma_b64 = c.get("firma")
        if firma_b64 and len(str(firma_b64)) > 100:
            try:
                pdf.ln(5)
                y_firma = pdf.get_y()
                pdf.image(io.BytesIO(base64.b64decode(firma_b64)), x=140, y=y_firma, w=45)
                pdf.set_y(y_firma + 15)
                pdf.set_font("Arial", "B", 10)
                pdf.cell(0, 10, "Firma del Cliente per accettazione", align="R")
            except: pass

    elif tipo == "VIGILI":
        pdf.ln(15)
        pdf.set_font("Arial", "", 12)
        testo = (
            f"La sottoscritta {TITOLARE}, titolare della ditta {DITTA}, dichiara che il veicolo "
            f"targato {s(c.get('targa'))} era in locazione al cliente sopra indicato al momento "
            f"dell'eventuale infrazione. Si richiede la rinotifica del verbale al trasgressore."
        )
        pdf.multi_cell(0, 8, safe_text(testo))

    out = pdf.output(dest="S")
    return bytes(out) if not isinstance(out, str) else out.encode("latin-1", "replace")

# --- INTERFACCIA APP ---
st.set_page_config(page_title="Battaglia Rent Pro", layout="wide")

if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Inserisci Password Gestionale", type="password") == "1234":
        if st.button("ACCEDI"): st.session_state.auth = True; st.rerun()
    st.stop()

menu = st.sidebar.radio("MENU", ["🆕 Nuovo Noleggio", "📂 Archivio Contratti"])

if menu == "🆕 Nuovo Noleggio":
    with st.form("form_noleggio", clear_on_submit=True):
        st.title("📄 Nuovo Contratto di Noleggio")
        
        col1, col2, col3 = st.columns(3)
        nome = col1.text_input("Nome")
        cognome = col2.text_input("Cognome")
        telefono = col3.text_input("Telefono/WhatsApp")
        
        col4, col5, col6 = st.columns(3)
        nazion = col4.text_input("Nazionalità")
        cf = col5.text_input("Codice Fiscale")
        luogo_n = col6.text_input("Luogo di Nascita")
        
        col7, col8 = st.columns(2)
        data_n = col7.text_input("Data Nascita (GG/MM/AAAA)")
        indirizzo = col8.text_input("Indirizzo di Residenza")
        
        st.divider()
        st.subheader("🛵 Dati Veicolo e Condizioni")
        
        col9, col10, col11 = st.columns(3)
        modello = col9.text_input("Modello Scooter (es. SH 125)")
        targa = col10.text_input("Targa").upper()
        benzina = col11.selectbox("Livello Benzina", ["1/8", "1/4", "1/2", "3/4", "Pieno"])
        
        patente = st.text_input("Numero Patente")
        note_danni = st.text_area("Note Danni / Segni precostituiti")
        
        col12, col13, col14, col15 = st.columns(4)
        prezzo = col12.number_input("Prezzo (€)", min_value=0.0)
        deposito = col13.number_input("Deposito/Cauzione (€)", min_value=0.0)
        inizio = col14.date_input("Inizio Noleggio")
        fine = col15.date_input("Fine Noleggio")
        
        st.write("✍️ *Firma del Cliente:*")
        canvas = st_canvas(height=150, width=450, stroke_width=3, key="firma_v5")
        accetto = st.checkbox("Il cliente accetta le condizioni generali e la responsabilità per le multe.")

        if st.form_submit_button("REGISTRA E GENERA DOCUMENTI"):
            if not nome or not targa or not accetto:
                st.error("ERRORE: Compila Nome, Targa e accetta i termini.")
            else:
                with st.spinner("Salvataggio in corso..."):
                    # Trasforma firma in base64
                    img_f = Image.fromarray(canvas.image_data.astype("uint8"))
                    buf_f = io.BytesIO()
                    img_f.save(buf_f, format="PNG")
                    firma_b64 = base64.b64encode(buf_f.getvalue()).decode()
                    
                    num_sequenziale = get_prossimo_numero()
                    
                    dati_db = {
                        "nome": nome, "cognome": cognome, "telefono": telefono,
                        "nazionalita": nazion, "codice_fiscale": cf, "luogo_nascita": luogo_n,
                        "data_nascita": data_n, "indirizzo_cliente": indirizzo,
                        "modello": modello, "targa": targa, "numero_patente": patente,
                        "benzina": benzina, "note_danni": note_danni, "prezzo": prezzo,
                        "deposito": deposito, "inizio": str(inizio), "fine": str(fine),
                        "firma": firma_b64, "numero_fattura": num_sequenziale,
                        "data_creazione": datetime.now().isoformat()
                    }
                    
                    supabase.table("contratti").insert(dati_db).execute()
                    st.success(f"CONTRATTO N. {num_sequenziale} REGISTRATO CON SUCCESSO!")

else:
    st.title("📂 Archivio Storico Contratti")
    cerca = st.text_input("Cerca per Cognome o Targa").lower()
    
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    
    for r in res.data:
        if cerca in f"{r['cognome']} {r['targa']}".lower():
            with st.expander(f"📄 N. {r['numero_fattura']} - {r['targa']} ({r['cognome'].upper()})"):
                c1, c2, c3 = st.columns(3)
                
                # Usiamo chiavi uniche per evitare errori Streamlit
                c1.download_button("📜 Scarica Contratto", genera_documento(r, "CONTRATTO"), 
                                   f"Contratto_{r['numero_fattura']}.pdf", key=f"c_{r['id']}")
                
                c2.download_button("💰 Scarica Ricevuta", genera_documento(r, "FATTURA"), 
                                   f"Ricevuta_{r['numero_fattura']}.pdf", key=f"f_{r['id']}")
                
                c3.download_button("🚨 Modulo Vigili", genera_documento(r, "VIGILI"), 
                                   f"Vigili_{r['numero_fattura']}.pdf", key=f"v_{r['id']}")
                
                st.info(f"Creato il: {r.get('data_creazione')}")
