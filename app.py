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

# --- DATI AZIENDALI FISSI ---
DITTA = "BATTAGLIA RENT"
TITOLARE = "BATTAGLIA MARIANNA"
PIVA = "10252601215"
CF_DITTA = "BTTMNN87A53Z112S"
SEDE = "Via Cognole n. 5 - 80075 Forio (NA)"

# Connessione Supabase
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- UTILS ---
def s(v): return "" if v is None else str(v)
def safe(t): return s(t).encode("latin-1", "replace").decode("latin-1")

def get_prossimo_numero():
    try:
        res = supabase.table("contratti").select("numero_fattura").execute()
        nums = [int(r['numero_fattura']) for r in res.data if str(r['numero_fattura']).isdigit()]
        return max(nums) + 1 if nums else 1
    except: return 1

# --- GENERAZIONE PDF CONTRATTO + 14 CLAUSOLE ---
class PDF_Contratto(FPDF):
    def header(self):
        self.set_font("Arial", "B", 11)
        self.cell(0, 5, DITTA, ln=True)
        self.set_font("Arial", "", 8)
        self.cell(0, 4, f"Sede Legale: {SEDE} | P.IVA: {PIVA}", ln=True)
        self.ln(10)

def genera_contratto(c):
    pdf = PDF_Contratto(); pdf.add_page()
    pdf.set_font("Arial", "B", 14); pdf.cell(0, 10, safe(f"CONTRATTO DI NOLEGGIO N. {c['numero_fattura']}"), ln=True, align="C")
    
    # BOX DATI CLIENTE
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", "B", 10); pdf.cell(0, 8, " 1. DATI DEL LOCATARIO (CLIENTE)", 1, ln=True, fill=True)
    pdf.set_font("Arial", "", 9)
    dati_cliente = (f"Nome e Cognome: {c['nome']} {c['cognome']}\n"
                    f"Nato a: {c.get('luogo_nascita', 'N/D')} il {c.get('data_nascita', 'N/D')}\n"
                    f"Residente in: {c.get('indirizzo_cliente', 'N/D')}\n"
                    f"Codice Fiscale: {c.get('codice_fiscale', 'N/D')} | Patente: {c.get('numero_patente', 'N/D')}")
    pdf.multi_cell(0, 6, safe(dati_cliente), border=1)

    # BOX DATI VEICOLO E NOLEGGIO
    pdf.ln(2)
    pdf.set_font("Arial", "B", 10); pdf.cell(0, 8, " 2. OGGETTO DEL NOLEGGIO E DURATA", 1, ln=True, fill=True)
    pdf.set_font("Arial", "", 9)
    dati_veicolo = (f"Veicolo: {c['modello']} | Targa: {c['targa']}\n"
                    f"Inizio: {c.get('data_inizio')} ore {c.get('ora_inizio')} | Fine: {c.get('data_fine')}\n"
                    f"Prezzo Pattuito: EUR {c['prezzo']}")
    pdf.multi_cell(0, 6, safe(dati_veicolo), border=1)

    # CERTIFICAZIONE OTP
    pdf.ln(2); pdf.set_font("Arial", "I", 7)
    pdf.multi_cell(0, 4, safe(f"Documento sottoscritto elettronicamente tramite validazione OTP inviata al numero {c.get('pec')} in data {c.get('timestamp_firma')}. Codice Univoco: {c.get('otp_code')}"))

    # FIRME
    pdf.ln(5); y_firma = pdf.get_y()
    pdf.set_font("Arial", "B", 8)
    pdf.cell(95, 35, "Firma Locatario (Accettazione)", border=1, align="L")
    pdf.cell(95, 35, "Firma Locatario (Clausole 1341-1342 cc)", border=1, align="L")
    try:
        if c.get("firma"):
            f1 = str(c["firma"]).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(f1)), x=15, y=y_firma+10, w=45)
        if c.get("firma2"):
            f2 = str(c["firma2"]).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(f2)), x=110, y=y_firma+10, w=45)
    except: pass

    # PAGINA 2: LE 14 CLAUSOLE LEGALI
    pdf.add_page()
    pdf.set_font("Arial", "B", 11); pdf.cell(0, 10, "CONDIZIONI GENERALI DI CONTRATTO", ln=True, align="C")
    pdf.set_font("Arial", "", 7)
    
    clausole = [
        "1. UTILIZZO: Il noleggio e' consentito esclusivamente nell'ambito del territorio dell'Isola d'Ischia.",
        "2. GUIDA: Il veicolo puo' essere condotto solo dal firmatario del presente contratto, munito di patente valida.",
        "3. RESPONSABILITA': Il locatario e' responsabile per danni, furto, incendio e atti vandalici occorsi durante il noleggio.",
        "4. INFRAZIONI: Ogni multa e' a carico del cliente. Per ogni notifica verra' addebitato un costo di gestione di Euro 25,83.",
        "5. DIVIETI: E' severamente vietato il sub-noleggio o la cessione del veicolo a terzi.",
        "6. RICONSEGNA: Il veicolo deve essere riconsegnato entro l'orario stabilito. Ritardi oltre i 30 min comportano l'addebito di un giorno extra.",
        "7. STATO MEZZO: Il cliente dichiara di ricevere il veicolo in ottimo stato e senza vizi palesi.",
        "8. CARBURANTE: Il veicolo deve essere riconsegnato con lo stesso livello di carburante iniziale.",
        "9. FORO COMPETENTE: Per ogni controversia il foro competente esclusivo e' quello di Napoli.",
        "10. ISPEZIONE: Il cliente ha l'onere di segnalare graffi o danni prima della partenza; in mancanza, si presumono causati dal cliente.",
        "11. CHIAVI: Lo smarrimento delle chiavi comporta una penale fissa di Euro 250,00.",
        "12. CASCO: E' obbligatorio l'uso del casco protettivo. Il locatore declina ogni responsabilita' per il mancato uso dello stesso.",
        "13. ASSICURAZIONE: Il veicolo e' coperto da polizza RCA verso terzi secondo i massimali di legge.",
        "14. ALCOOL/DROGA: E' vietata la guida in stato di alterazione. In tal caso l'assicurazione non copre i danni."
    ]
    for cl in clausole:
        pdf.multi_cell(0, 5, safe(cl), border='B')
    
    return bytes(pdf.output(dest="S"))

# --- MODULO VIGILI (ART. 196 CdS) ---
def genera_vigili(c):
    pdf = FPDF(); pdf.add_page()
    pdf.set_font("Arial", "B", 12); pdf.cell(0, 10, "COMUNICAZIONE AI SENSI DELL'ART. 196 C.d.S.", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", "", 11)
    corpo = (f"La sottoscritta {TITOLARE}, titolare della ditta {DITTA},\n"
             f"con sede in {SEDE}, P.IVA {PIVA},\n\n"
             f"DICHIARA\n\n"
             f"che il veicolo targato {c['targa']}, modello {c['modello']},\n"
             f"nel periodo dal {c.get('data_inizio')} al {c.get('data_fine')}\n"
             f"e' stato locato al Sig./Sig.ra:\n\n"
             f"NOME: {c['nome']}  COGNOME: {c['cognome']}\n"
             f"NATO A: {c.get('luogo_nascita')} IL: {c.get('data_nascita')}\n"
             f"RESIDENTE: {c.get('indirizzo_cliente')}\n"
             f"C.F.: {c['codice_fiscale']}\n"
             f"PATENTE N.: {c.get('numero_patente')}\n\n"
             f"Il suddetto locatario e' responsabile in solido per eventuali violazioni al Codice della Strada.")
    pdf.multi_cell(0, 8, safe(corpo))
    pdf.ln(20); pdf.cell(0, 10, "Firma del Titolare _________________________", align="R")
    return bytes(pdf.output(dest="S"))

# --- INTERFACCIA STREAMLIT ---
st.set_page_config(page_title="BATTAGLIA RENT PRO", layout="wide")

# Login Semplice
if "autenticato" not in st.session_state: st.session_state.autenticato = False
if not st.session_state.autenticato:
    password = st.text_input("Inserisci Password di Gestione", type="password")
    if st.button("ACCEDI"):
        if password == "1234": st.session_state.autenticato = True; st.rerun()
    st.stop()

tab_nuovo, tab_archivio = st.tabs(["📝 NUOVO CONTRATTO", "📂 ARCHIVIO DOCUMENTI"])

with tab_nuovo:
    with st.form("form_contratto", clear_on_submit=True):
        st.subheader("🏁 DATI NOLEGGIO")
        col_m1, col_m2, col_m3 = st.columns(3)
        modello = col_m1.text_input("Modello Veicolo")
        targa = col_m2.text_input("Targa").upper()
        prezzo = col_m3.number_input("Prezzo Totale (€)", min_value=0.0)
        
        col_t1, col_t2, col_t3 = st.columns(3)
        data_inizio = col_t1.date_input("Data Inizio").strftime("%d/%m/%Y")
        ora_inizio = col_t2.time_input("Ora Inizio").strftime("%H:%M")
        data_fine = col_t3.date_input("Data Fine previsto").strftime("%d/%m/%Y")

        st.subheader("👤 ANAGRAFICA CLIENTE")
        c1, c2, c3 = st.columns(3)
        nome = c1.text_input("Nome")
        cognome = c2.text_input("Cognome")
        cellulare = c3.text_input("Cellulare per OTP (es. 3331234567)")
        
        c4, c5, c6 = st.columns(3)
        dn = c4.text_input("Data di Nascita (GG/MM/AAAA)")
        ln = c5.text_input("Luogo di Nascita")
        cf = c6.text_input("Codice Fiscale").upper()
        
        c7, c8 = st.columns(2)
        indirizzo = c7.text_input("Indirizzo Residenza Completo")
        patente = c8.text_input("Numero Patente")

        st.write("---")
        st.subheader("🖋️ FIRME DIGITALI")
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            st.caption("Firma per Accettazione")
            canvas1 = st_canvas(height=150, width=400, stroke_width=2, key="can1")
        with f_col2:
            st.caption("Firma Clausole Vessatorie")
            canvas2 = st_canvas(height=150, width=400, stroke_width=2, key="can2")

        invia_otp = st.form_submit_button("1. GENERA E INVIA OTP WHATSAPP")
        
        if invia_otp:
            if not (nome and cellulare and targa):
                st.error("Dati obbligatori mancanti!")
            else:
                otp = str(random.randint(100000, 999999))
                st.session_state.current_otp = otp
                msg = f"BATTAGLIA RENT: Il tuo codice OTP per firmare il contratto della targa {targa} e': {otp}"
                p_wa = cellulare.replace(" ", "").replace("+", "")
                if not p_wa.startswith("39"): p_wa = "39" + p_wa
                link = f"https://wa.me/{p_wa}?text={urllib.parse.quote(msg)}"
                st.markdown(f"### [📲 CLICCA QUI PER INVIARE IL CODICE]({link})")

    # Verifica OTP e Salvataggio
    if "current_otp" in st.session_state:
        st.warning("⚠️ Inserisci il codice che hai appena inviato per salvare il contratto.")
        inserito = st.text_input("Codice OTP")
        if st.button("2. SALVA E ARCHIVIA CONTRATTO"):
            if inserito == st.session_state.current_otp:
                # Conversione Firme
                def get_b64(canvas):
                    if canvas.image_data is not None:
                        img = Image.fromarray(canvas.image_data.astype("uint8"))
                        buf = io.BytesIO(); img.save(buf, format="PNG")
                        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
                    return ""
                
                dati = {
                    "nome": nome, "cognome": cognome, "targa": targa, "prezzo": prezzo, "modello": modello,
                    "data_inizio": data_inizio, "ora_inizio": ora_inizio, "data_fine": data_fine,
                    "data_nascita": dn, "luogo_nascita": ln, "codice_fiscale": cf, "indirizzo_cliente": indirizzo,
                    "numero_patente": patente, "pec": cellulare, "otp_code": st.session_state.current_otp,
                    "firma": get_b64(canvas1), "firma2": get_b64(canvas2),
                    "timestamp_firma": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "numero_fattura": get_prossimo_numero()
                }
                supabase.table("contratti").insert(dati).execute()
                st.success("✅ CONTRATTO SALVATO CON SUCCESSO!")
                del st.session_state.current_otp
            else:
                st.error("Codice OTP Errato!")

with tab_archivio:
    cerca = st.text_input("🔍 Cerca per Cognome o Targa")
    risultati = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    
    for r in risultati.data:
        if cerca.lower() in f"{s(r['cognome'])} {s(r['targa'])}".lower():
            with st.expander(f"📄 Contr. {r['numero_fattura']} - {r['cognome']} ({r['targa']})"):
                col_b1, col_b2 = st.columns(2)
                col_b1.download_button("📜 Scarica Contratto + Clausole", genera_contratto(r), f"Contratto_{r['id']}.pdf")
                col_b2.download_button("👮 Scarica Modulo Vigili", genera_vigili(r), f"Modulo_Vigili_{r['id']}.pdf")
