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

# --- DATI BATTAGLIA RENT ---
DITTA = "BATTAGLIA RENT"
TITOLARE = "BATTAGLIA MARIANNA"
PIVA = "10252601215"
SEDE = "Via Cognole n. 5 - 80075 Forio (NA)"

# Connessione Supabase
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

def s(v): return "" if v is None else str(v)
def safe(t): return s(t).encode("latin-1", "replace").decode("latin-1")

def get_prossimo_numero():
    try:
        res = supabase.table("contratti").select("numero_fattura").execute()
        nums = [int(r['numero_fattura']) for r in res.data if str(r['numero_fattura']).isdigit()]
        return max(nums) + 1 if nums else 1
    except: return 1

# --- MOTORE PDF CORRETTO ---
class PDF_Pro(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 8, DITTA, ln=True, align="L")
        self.set_font("Arial", "", 8)
        self.cell(0, 4, f"P.IVA: {PIVA} | Sede: {SEDE}", ln=True)
        self.ln(5)

def genera_contratto_legale(c):
    pdf = PDF_Pro()
    pdf.add_page()
    w_eff = pdf.epw # Calcola lo spazio esatto per evitare l'errore di "horizontal space"
    
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, safe(f"CONTRATTO DI NOLEGGIO N. {c['numero_fattura']}"), ln=True, align="C")
    
    # 1. Anagrafica
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", "B", 10); pdf.cell(0, 8, " 1. DATI DEL LOCATARIO", 1, ln=True, fill=True)
    pdf.set_font("Arial", "", 9)
    testo_cliente = (f"Cliente: {c['nome']} {c['cognome']} | Nazionalita': {c.get('nazionalita', 'N/D')}\n"
                     f"Nato a: {c.get('luogo_nascita', 'N/D')} il {c.get('data_nascita', 'N/D')}\n"
                     f"Residenza: {c.get('indirizzo_cliente', 'N/D')}\n"
                     f"C.F.: {c.get('codice_fiscale', 'N/D')} | Patente: {c.get('numero_patente', 'N/D')}")
    pdf.multi_cell(w_eff, 6, safe(testo_cliente), border=1)

    # 2. Veicolo e Pagamento
    pdf.ln(3)
    pdf.set_font("Arial", "B", 10); pdf.cell(0, 8, " 2. VEICOLO E PAGAMENTO", 1, ln=True, fill=True)
    pdf.set_font("Arial", "", 9)
    testo_noleggio = (f"Mezzo: {c['modello']} | Targa: {c['targa']}\n"
                      f"Inizio: {c.get('data_inizio')} ore {c.get('ora_inizio')}\n"
                      f"Prezzo: {c['prezzo']} EUR | Metodo: {c.get('metodo_pagamento', 'Cash')} | Pagato: {c.get('pagato', 'No')}")
    pdf.multi_cell(w_eff, 6, safe(testo_noleggio), border=1)

    # Firme
    pdf.ln(10); y_f = pdf.get_y()
    pdf.set_font("Arial", "B", 8)
    pdf.cell(w_eff/2 - 5, 30, "Firma Accettazione", border=1, align="L")
    pdf.set_xy(pdf.get_x() + 10, y_f)
    pdf.cell(w_eff/2 - 5, 30, "Firma Clausole 1341/1342 cc", border=1, align="L")
    
    try:
        if c.get("firma"):
            f1 = str(c["firma"]).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(f1)), x=20, y=y_f+5, w=35)
        if c.get("firma2"):
            f2 = str(c["firma2"]).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(f2)), x=115, y=y_f+5, w=35)
    except: pass

    # Pagina 2: Clausole
    pdf.add_page()
    pdf.set_font("Arial", "B", 11); pdf.cell(0, 10, "CONDIZIONI GENERALI DI CONTRATTO", ln=True, align="C")
    pdf.set_font("Arial", "", 7.5)
    clausole = [
        "1) Territorio: Il noleggio e' limitato esclusivamente all'Isola d'Ischia.",
        "2) Guida: Il veicolo puo' essere condotto solo dal firmatario.",
        "3) Danni: Il cliente e' responsabile di ogni danno, furto o incendio.",
        "4) Multe: Le sanzioni sono a carico del cliente + Euro 25,83 di gestione pratica.",
        "5) Sub-noleggio: Vietato assolutamente.",
        "6) Riconsegna: Ritardi oltre i 30 min comportano l'addebito di una giornata extra.",
        "7) Carburante: Il mezzo deve tornare con lo stesso livello di benzina.",
        "8) Foro: Per ogni controversia e' competente il Foro di Napoli.",
        "9) Chiavi: La perdita delle chiavi costa Euro 250,00.",
        "10) Casco: Obbligatorio. Il mancato uso esonera il locatore da ogni colpa.",
        "11) Stato Mezzo: Il cliente accetta il mezzo visionato senza riserve.",
        "12) Assicurazione: RCA inclusa come da legge.",
        "13) Divieti: Vietata la guida sotto l'effetto di alcool o droghe.",
        "14. Assistenza: In caso di guasto contattare subito il proprietario."
    ]
    for cl in clausole:
        pdf.multi_cell(w_eff, 5, safe(cl), border='B')
    
    return bytes(pdf.output(dest="S"))

def genera_vigili(c):
    pdf = PDF_Pro(); pdf.add_page()
    pdf.set_font("Arial", "B", 14); pdf.cell(0, 10, "NOTIFICA LOCAZIONE (Art. 196 CdS)", ln=True, align="C")
    pdf.ln(10); pdf.set_font("Arial", "", 11)
    corpo = (f"La ditta {DITTA} comunica che il veicolo targato {c['targa']}\n"
             f"modello {c['modello']} nel periodo {c.get('data_inizio')} - {c.get('data_fine')}\n"
             f"e' stato locato al Sig./Sig.ra:\n\n"
             f"NOME: {c['nome']}  COGNOME: {c['cognome']}\n"
             f"NATO A: {c.get('luogo_nascita')} IL: {c.get('data_nascita')}\n"
             f"NAZIONALITA': {c.get('nazionalita')}\n"
             f"C.F.: {c['codice_fiscale']}\n"
             f"PATENTE N.: {c.get('numero_patente')}\n\n"
             f"Il locatario si assume la piena responsabilita' per violazioni al Codice della Strada.")
    pdf.multi_cell(pdf.epw, 8, safe(corpo))
    return bytes(pdf.output(dest="S"))

# --- INTERFACCIA STREAMLIT ---
st.set_page_config(page_title="BATTAGLIA RENT", layout="wide")

if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Password", type="password") == "1234":
        if st.button("LOGIN"): st.session_state.auth = True; st.rerun()
    st.stop()

t1, t2 = st.tabs(["📝 NUOVO NOLEGGIO", "📂 ARCHIVIO"])

with t1:
    with st.form("main_form", clear_on_submit=True):
        st.subheader("🛵 MEZZO E PAGAMENTO")
        col1, col2, col3 = st.columns(3)
        mod = col1.text_input("Modello Mezzo")
        tg = col2.text_input("Targa").upper()
        prz = col3.number_input("Prezzo (€)", 0.0)
        
        col4, col5, col6 = st.columns(3)
        met = col4.selectbox("Metodo", ["Cash", "Carta", "Bonifico"])
        pag = col5.selectbox("Pagato", ["Sì", "No"])
        naz = col6.text_input("Nazionalità")

        st.subheader("👤 CLIENTE")
        c1, c2, c3 = st.columns(3)
        n, cg, wa = c1.text_input("Nome"), c2.text_input("Cognome"), c3.text_input("WhatsApp")
        c4, c5, c6 = st.columns(3)
        dn, ln, cf = c4.text_input("Data Nascita (GG/MM/AAAA)"), c5.text_input("Luogo Nascita"), c6.text_input("Codice Fiscale")
        c7, c8 = st.columns(2)
        ind, pat = c7.text_input("Indirizzo Residenza"), c8.text_input("Numero Patente")

        st.subheader("🖋️ FIRME")
        f1, f2 = st.columns(2)
        with f1: can1 = st_canvas(height=150, width=400, key="can1")
        with f2: can2 = st_canvas(height=150, width=400, key="can2")

        if st.form_submit_button("1. GENERA OTP"):
            if not wa: st.error("Inserisci il cellulare!")
            else:
                otp = str(random.randint(100000, 999999))
                st.session_state.otp = otp
                clean_wa = wa.replace(" ","").replace("+","")
                if not clean_wa.startswith("39"): clean_wa = "39" + clean_wa
                url = f"https://wa.me/{clean_wa}?text={urllib.parse.quote(f'Codice Battaglia Rent: {otp}')}"
                st.markdown(f"### [📲 INVIA WHATSAPP]({url})")

    if "otp" in st.session_state:
        check = st.text_input("Inserisci OTP ricevuto")
        if st.button("2. SALVA TUTTO"):
            if check == st.session_state.otp:
                # Trasformazione immagini
                def b64(c):
                    if c.image_data is not None:
                        img = Image.fromarray(c.image_data.astype("uint8"))
                        buf = io.BytesIO(); img.save(buf, format="PNG")
                        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
                    return ""
                
                dati = {
                    "nome": n, "cognome": cg, "targa": tg, "prezzo": prz, "metodo_pagamento": met, "pagato": pag,
                    "nazionalita": naz, "modello": mod, "data_nascita": dn, "luogo_nascita": ln,
                    "codice_fiscale": cf, "indirizzo_cliente": ind, "numero_patente": pat,
                    "pec": wa, "otp_code": st.session_state.otp, "timestamp_firma": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "firma": b64(can1), "firma2": b64(can2), "numero_fattura": get_prossimo_numero(),
                    "data_inizio": datetime.now().strftime("%d/%m/%Y"), "ora_inizio": datetime.now().strftime("%H:%M")
                }
                supabase.table("contratti").insert(dati).execute()
                st.success("CONTRATTO ARCHIVIATO!")
                del st.session_state.otp
            else: st.error("OTP sbagliato")

with t2:
    search = st.text_input("🔍 Cerca")
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    for r in res.data:
        if search.lower() in f"{s(r['cognome'])} {s(r['targa'])}".lower():
            with st.expander(f"📄 N. {r['numero_fattura']} - {r['cognome']} ({r['targa']})"):
                c_b1, c_b2 = st.columns(2)
                c_b1.download_button("📜 Contratto PDF", genera_contratto_legale(r), f"Contr_{r['id']}.pdf")
                c_b2.download_button("👮 Modulo Vigili", genera_vigili(r), f"Vigili_{r['id']}.pdf")
