import streamlit as st
from supabase import create_client, Client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from fpdf import FPDF
import io
import base64
import random
from datetime import datetime
import urllib.parse

# --- CONFIGURAZIONE AZIENDALE ---
DITTA = "BATTAGLIA RENT"
TITOLARE = "BATTAGLIA MARIANNA"
PIVA = "10252601215"
CF_DITTA = "BTTMNN87A53Z112S"
SEDE = "Via Cognole n. 5 - 80075 Forio (NA)"

# Connessione Supabase
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- FUNZIONI DI SUPPORTO ---
def s(v): return "" if v is None else str(v)
def safe(t): return s(t).encode("latin-1", "replace").decode("latin-1")

def get_prossimo_numero():
    try:
        res = supabase.table("contratti").select("numero_fattura").execute()
        nums = [int(r['numero_fattura']) for r in res.data if str(r['numero_fattura']).isdigit()]
        return max(nums) + 1 if nums else 1
    except: return 1

# --- MOTORE PDF PROFESSIONALE ---
class PDF_Master(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 8, DITTA, ln=True)
        self.set_font("Arial", "", 8)
        self.cell(0, 4, f"Proprietario: {TITOLARE} | P.IVA: {PIVA}", ln=True)
        self.cell(0, 4, f"Sede: {SEDE}", ln=True)
        self.ln(5)

def genera_contratto_legale(c):
    pdf = PDF_Master(); pdf.add_page()
    pdf.set_margins(15, 15, 15)
    
    # Titolo
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, safe(f"CONTRATTO DI LOCAZIONE N. {c['numero_fattura']}"), ln=True, align="C")
    
    # Sezione 1: Cliente
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", "B", 10); pdf.cell(0, 7, " 1. DATI DEL CLIENTE", 1, ln=True, fill=True)
    pdf.set_font("Arial", "", 9)
    testo_c = (f"Nome: {c['nome']} {c['cognome']} | Nazionalita: {c.get('nazionalita', 'N/D')}\n"
               f"Nato a: {c.get('luogo_nascita')} il {c.get('data_nascita')}\n"
               f"Residenza: {c.get('indirizzo_cliente')}\n"
               f"C.F.: {c.get('codice_fiscale')} | Patente: {c.get('numero_patente')}")
    pdf.multi_cell(0, 6, safe(testo_c), border=1)

    # Sezione 2: Veicolo e Pagamento
    pdf.ln(3)
    pdf.set_font("Arial", "B", 10); pdf.cell(0, 7, " 2. DETTAGLI NOLEGGIO E PAGAMENTO", 1, ln=True, fill=True)
    pdf.set_font("Arial", "", 9)
    testo_v = (f"Mezzo: {c['modello']} | Targa: {c['targa']}\n"
               f"Periodo: dal {c.get('data_inizio')} ore {c.get('ora_inizio')} al {c.get('data_fine')}\n"
               f"Prezzo: {c['prezzo']} EUR | Metodo: {c.get('metodo_pagamento')} | Pagato: {c.get('pagato')}")
    pdf.multi_cell(0, 6, safe(testo_v), border=1)

    # Firme
    pdf.ln(5); y_f = pdf.get_y()
    pdf.set_font("Arial", "B", 8)
    pdf.cell(90, 35, "Firma Accettazione", border=1, align="L")
    pdf.set_xy(105, y_f)
    pdf.cell(90, 35, "Firma Art. 1341-1342 cc", border=1, align="L")
    
    try:
        if c.get("firma"):
            f1 = str(c["firma"]).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(f1)), x=18, y=y_f+8, w=40)
        if c.get("firma2"):
            f2 = str(c["firma2"]).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(f2)), x=110, y=y_f+8, w=40)
    except: pass

    # Pagina 2: Clausole
    pdf.add_page()
    pdf.set_font("Arial", "B", 10); pdf.cell(0, 10, "CONDIZIONI GENERALI DI CONTRATTO", ln=True, align="C")
    pdf.set_font("Arial", "", 7.5)
    
    clausole = [
        "1) Territorio: Il noleggio e' valido solo per l'Isola d'Ischia.",
        "2) Conducente: Solo il firmatario puo' guidare il mezzo.",
        "3) Responsabilita': Il cliente risponde di ogni danno, furto o incendio.",
        "4) Multe: A carico del cliente + Euro 25,83 di spese gestione per ogni verbale.",
        "5) Sub-noleggio: Vietato.",
        "6) Riconsegna: Oltre i 30 minuti di ritardo verra' addebitato un giorno extra.",
        "7) Carburante: Il mezzo va riconsegnato con lo stesso livello ricevuto.",
        "8) Foro: Competenza esclusiva del Foro di Napoli.",
        "9) Chiavi: Lo smarrimento delle chiavi costa Euro 250,00.",
        "10) Casco: Obbligatorio. Il mancato uso esonera il locatore da ogni colpa.",
        "11) Stato: Il cliente accetta il mezzo nello stato in cui si trova.",
        "12) Assicurazione: Inclusa RCA base come da massimali di legge.",
        "13) Guida: Vietata sotto effetto di alcool o stupefacenti.",
        "14) Meccanica: In caso di guasto avvisare subito il locatore."
    ]
    for cl in clausole:
        pdf.multi_cell(0, 5, safe(cl), border='B')
    
    return bytes(pdf.output(dest="S"))

# --- INTERFACCIA STREAMLIT ---
st.set_page_config(page_title="BATTAGLIA RENT ADMIN", layout="wide")

if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Password", type="password") == "1234":
        if st.button("LOGIN"): st.session_state.auth = True; st.rerun()
    st.stop()

tab_n, tab_a = st.tabs(["📝 NUOVO NOLEGGIO", "📂 ARCHIVIO"])

with tab_n:
    with st.form("main_form", clear_on_submit=True):
        st.subheader("🛵 DATI MEZZO E PAGAMENTO")
        col1, col2, col3 = st.columns(3)
        modello = col1.text_input("Modello")
        targa = col2.text_input("Targa").upper()
        prezzo = col3.number_input("Prezzo Totale (€)", min_value=0.0)
        
        col4, col5, col6 = st.columns(3)
        metodo = col4.selectbox("Metodo di Pagamento", ["Contanti", "Carta/POS", "Bonifico"])
        pagato = col5.selectbox("Pagato?", ["Sì", "No"])
        nazionalita = col6.text_input("Nazionalità Cliente")

        st.subheader("👤 ANAGRAFICA CLIENTE")
        c1, c2, c3 = st.columns(3)
        nome, cognome, wa = c1.text_input("Nome"), c2.text_input("Cognome"), c3.text_input("WhatsApp (es. 3331234567)")
        
        c4, c5, c6 = st.columns(3)
        dn, ln, cf = c4.text_input("Data Nascita"), c5.text_input("Luogo Nascita"), c6.text_input("Codice Fiscale").upper()
        
        c7, c8 = st.columns(2)
        indirizzo, patente = c7.text_input("Indirizzo Residenza"), c8.text_input("N. Patente")

        st.subheader("🖋️ FIRME")
        f1, f2 = st.columns(2)
        with f1: can1 = st_canvas(height=150, width=380, stroke_width=2, key="c1")
        with f2: can2 = st_canvas(height=150, width=380, stroke_width=2, key="c2")

        if st.form_submit_button("1. GENERA OTP E INVIA"):
            if not (wa and targa): st.error("Mancano dati!")
            else:
                otp = str(random.randint(100000, 999999))
                st.session_state.otp_code = otp
                clean_wa = wa.replace(" ","").replace("+","")
                if not clean_wa.startswith("39"): clean_wa = "39" + clean_wa
                msg = f"BATTAGLIA RENT: Codice OTP per targa {targa}: {otp}"
                link = f"https://wa.me/{clean_wa}?text={urllib.parse.quote(msg)}"
                st.markdown(f"### [📲 INVIA CODICE WHATSAPP]({link})")

    if "otp_code" in st.session_state:
        check = st.text_input("Codice OTP ricevuto")
        if st.button("2. SALVA TUTTO"):
            if check == st.session_state.otp_code:
                # Trasformazione firme
                def get_b64(c):
                    if c.image_data is not None:
                        img = Image.fromarray(c.image_data.astype("uint8"))
                        buf = io.BytesIO(); img.save(buf, format="PNG")
                        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
                    return ""

                dati = {
                    "nome": nome, "cognome": cognome, "targa": targa, "prezzo": prezzo,
                    "metodo_pagamento": metodo, "pagato": pagato, "nazionalita": nazionalita,
                    "modello": modello, "data_nascita": dn, "luogo_nascita": ln,
                    "codice_fiscale": cf, "indirizzo_cliente": indirizzo, "numero_patente": patente,
                    "pec": wa, "otp_code": st.session_state.otp_code, "timestamp_firma": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "firma": get_b64(can1), "firma2": get_b64(can2),
                    "numero_fattura": get_prossimo_numero(), "data_inizio": datetime.now().strftime("%d/%m/%Y"), "ora_inizio": datetime.now().strftime("%H:%M")
                }
                supabase.table("contratti").insert(dati).execute()
                st.success("CONTRATTO SALVATO!")
                del st.session_state.otp_code
            else: st.error("Codice errato")

with tab_a:
    q = st.text_input("🔍 Cerca")
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    for r in res.data:
        if q.lower() in f"{s(r['cognome'])} {s(r['targa'])}".lower():
            with st.expander(f"📄 N. {r['numero_fattura']} - {r['cognome']} ({r['targa']})"):
                st.download_button("📜 Scarica Contratto PDF", genera_contratto_legale(r), f"C_{r['id']}.pdf")
