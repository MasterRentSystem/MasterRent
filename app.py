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

# --- DATI AZIENDALI ---
DITTA = "BATTAGLIA RENT"
TITOLARE = "BATTAGLIA MARIANNA"
PIVA = "10252601215"
CF_DITTA = "BTTMNN87A53Z112S"
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

# --- MOTORE PDF ---
class PDF_Battaglia(FPDF):
    def header(self):
        self.set_font("Arial", "B", 10)
        self.cell(0, 5, DITTA, ln=True)
        self.set_font("Arial", "", 8)
        self.cell(0, 4, f"{SEDE} | P.IVA: {PIVA}", ln=True)
        self.ln(5)

def genera_documento_completo(c):
    pdf = PDF_Battaglia()
    pdf.add_page()
    w = pdf.epw

    # FRONTESPIZIO
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, safe(f"CONTRATTO DI NOLEGGIO N. {c['numero_fattura']}"), ln=True, align="C")
    
    # DATI CLIENTE
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", "B", 10); pdf.cell(0, 7, " DATI CLIENTE / CUSTOMER DATA", 1, ln=True, fill=True)
    pdf.set_font("Arial", "", 9)
    info_c = (f"Nome/Name: {c['nome']} {c['cognome']} | Nazionalita: {c.get('nazionalita')}\n"
              f"Nato a/Born in: {c.get('luogo_nascita')} il {c.get('data_nascita')}\n"
              f"Codice Fiscale: {c.get('codice_fiscale')} | Patente: {c.get('numero_patente')}\n"
              f"Indirizzo/Address: {c.get('indirizzo_cliente')}")
    pdf.multi_cell(0, 6, safe(info_c), border=1)

    # DATI NOLEGGIO
    pdf.ln(2)
    pdf.set_font("Arial", "B", 10); pdf.cell(0, 7, " DETTAGLI NOLEGGIO / RENTAL DETAILS", 1, ln=True, fill=True)
    pdf.set_font("Arial", "", 9)
    info_n = (f"Veicolo: {c['modello']} | Targa: {c['targa']}\n"
              f"DALLE ore: {c.get('ora_inizio')} del {c.get('data_inizio')} | ALLE ore: {c.get('ora_fine')} del {c.get('data_fine')}\n"
              f"Prezzo: {c['prezzo']} EUR | Pagamento: {c.get('metodo_pagamento')} | Pagato: {c.get('pagato')}")
    pdf.multi_cell(0, 6, safe(info_n), border=1)

    # FIRME (SOTTILE)
    pdf.ln(5); y_f = pdf.get_y()
    pdf.set_font("Arial", "B", 8)
    pdf.cell(w/2 - 2, 35, "Firma Cliente / Customer Signature", border=1, align="L")
    pdf.set_xy(w/2 + 17, y_f)
    pdf.cell(w/2 - 2, 35, "Firma Clausole (1341-1342 cc)", border=1, align="L")
    try:
        if c.get("firma"):
            f1 = str(c["firma"]).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(f1)), x=20, y=y_f+10, w=35)
        if c.get("firma2"):
            f2 = str(c["firma2"]).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(f2)), x=120, y=y_f+10, w=35)
    except: pass

    # PAGINA 2: LE 14 CLAUSOLE (IT + EN)
    pdf.add_page()
    pdf.set_font("Arial", "B", 9); pdf.cell(w/2, 8, "CONDIZIONI GENERALI", 0, 0); pdf.cell(w/2, 8, "GENERAL CONDITIONS", 0, 1)
    pdf.set_font("Arial", "", 6)
    
    clausole_it = [
        "1) Noleggio limitato all'isola d'Ischia.", "2) Solo il firmatario puo' guidare.", 
        "3) Responsabilita' totale per danni/furto.", "4) Multe a carico cliente + 25.83 Euro gestione.",
        "5) Vietato sub-noleggio.", "6) Riconsegna entro l'orario (ritardo >30min = 1gg extra).",
        "7) Mezzo consegnato in ottimo stato.", "8) Carburante a carico cliente.",
        "9) Foro competente: Napoli.", "10) Onere di segnalare danni alla partenza.",
        "11) Smarrimento chiavi: Euro 250,00.", "12) Casco obbligatorio (fermo 90gg per violazione).",
        "13) Copertura RCA inclusa.", "14) In caso di furto cliente responsabile."
    ]
    clausole_en = [
        "1) Rental limited to Ischia island.", "2) Only the signer may drive.",
        "3) Full liability for damage/theft.", "4) Fines paid by customer + 25.83 Euro fee.",
        "5) Sub-rental forbidden.", "6) Return on time (delay >30min = 1 extra day).",
        "7) Vehicle delivered in perfect condition.", "8) Fuel at customer's expense.",
        "9) Jurisdiction: Naples.", "10) Duty to report damages at start.",
        "11) Lost keys: Euro 250.00.", "12) Helmet mandatory (90 days impound for breach).",
        "13) RCA Insurance included.", "14) Customer responsible for theft."
    ]
    
    y_start = pdf.get_y()
    for i in range(14):
        pdf.set_xy(10, pdf.get_y())
        pdf.multi_cell(w/2 - 2, 4, safe(clausole_it[i]), border='B')
        curr_y = pdf.get_y()
        pdf.set_xy(w/2 + 12, curr_y - 4)
        pdf.multi_cell(w/2 - 2, 4, safe(clausole_en[i]), border='B')
        pdf.set_y(curr_y)

    # INFORMATIVA PRIVACY
    pdf.ln(5)
    pdf.set_font("Arial", "B", 8); pdf.cell(0, 5, "INFORMATIVA PRIVACY (D.Lgs 196/2003)", ln=True)
    pdf.set_font("Arial", "", 6)
    priv_it = "I dati personali sono raccolti per l'esecuzione del contratto. Il trattamento avviene con modalita' manuali e informatiche. Il conferimento e' obbligatorio per concludere il noleggio."
    priv_en = "Personal data is collected for contract execution. Processing is manual and digital. Providing data is mandatory for the rental agreement."
    pdf.multi_cell(0, 4, safe(f"IT: {priv_it}\nEN: {priv_en}"), border=1)

    return bytes(pdf.output(dest="S"))

# --- MODULO POLIZIA LOCALE (MODELLO FOTO) ---
def genera_modulo_polizia(c):
    pdf = FPDF(); pdf.add_page()
    pdf.set_font("Arial", "B", 11); pdf.cell(0, 10, "Spett.le Polizia Locale", ln=True, align="R")
    pdf.ln(5)
    pdf.set_font("Arial", "B", 10); pdf.cell(0, 10, safe(f"OGGETTO: COMUNICAZIONE LOCAZIONE VEICOLO - Targa {c['targa']}"), ln=True)
    pdf.set_font("Arial", "", 10)
    testo = (f"La sottoscritta {TITOLARE}, nata a Berlino (Germania) il 13/01/1987 e residente in Forio,\n"
             f"P.IVA {PIVA}, in qualita' di titolare della ditta individuale,\n\nDICHIARA\n\n"
             f"Ai sensi della L. 445/2000 che il veicolo modello {c['modello']} targa {c['targa']}\n"
             f"dal giorno {c.get('data_inizio')} al {c.get('data_fine')} era concesso in locazione a:\n\n"
             f"COGNOME E NOME: {c['nome']} {c['cognome']}\n"
             f"LUOGO E DATA DI NASCITA: {c.get('luogo_nascita')} il {c.get('data_nascita')}\n"
             f"RESIDENZA: {c.get('indirizzo_cliente')}\n"
             f"IDENTIFICATO A MEZZO: Patente di Guida n. {c.get('numero_patente')}\n\n"
             f"Si allega copia del contratto di locazione conforme all'originale.")
    pdf.multi_cell(0, 7, safe(testo))
    pdf.ln(20); pdf.cell(0, 10, "In fede, Marianna Battaglia", align="R")
    return bytes(pdf.output(dest="S"))

# --- INTERFACCIA ---
st.set_page_config(page_title="BATTAGLIA RENT ADMIN", layout="wide")

if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Password", type="password") == "1234":
        if st.button("ACCEDI"): st.session_state.auth = True; st.rerun()
    st.stop()

tab1, tab2 = st.tabs(["📝 NUOVO CONTRATTO", "📂 ARCHIVIO"])

with tab1:
    with st.form("main_form"):
        st.subheader("🛵 DETTAGLI MEZZO")
        col1, col2, col3 = st.columns(3)
        mod = col1.text_input("Modello")
        tg = col2.text_input("Targa").upper()
        prz = col3.number_input("Prezzo Totale (€)", 0.0)
        
        col4, col5 = st.columns(2)
        d_in = col4.date_input("Data Inizio")
        t_in = col4.time_input("Ora Inizio")
        d_fi = col5.date_input("Data Fine")
        t_fi = col5.time_input("Ora Fine")

        st.subheader("👤 ANAGRAFICA")
        c1, c2, c3 = st.columns(3)
        nome, cognome, wa = c1.text_input("Nome"), c2.text_input("Cognome"), c3.text_input("WhatsApp")
        
        c4, c5, c6 = st.columns(3)
        naz = c4.text_input("Nazionalita")
        dn, ln = c5.text_input("Data Nascita"), c6.text_input("Luogo Nascita")
        
        c7, c8, c9 = st.columns(3)
        cf, ind, pat = c7.text_input("Codice Fiscale"), c8.text_input("Indirizzo"), c9.text_input("Patente")

        st.subheader("💳 PAGAMENTO")
        p1, p2 = st.columns(2)
        met = p1.selectbox("Metodo", ["Cash", "Carta", "Bonifico"])
        pag = p2.selectbox("Pagato", ["Sì", "No"])

        st.subheader("🖋️ FIRME (Tratto Sottile)")
        f1, f2 = st.columns(2)
        with f1: can1 = st_canvas(height=150, width=400, stroke_width=1, stroke_color="#000", key="c1")
        with f2: can2 = st_canvas(height=150, width=400, stroke_width=1, stroke_color="#000", key="c2")

        if st.form_submit_button("GENERA OTP E SALVA"):
            otp = str(random.randint(100000, 999999))
            st.session_state.temp_dati = {
                "nome": nome, "cognome": cognome, "targa": tg, "prezzo": prz, "modello": mod,
                "data_inizio": d_in.strftime("%d/%m/%Y"), "ora_inizio": t_in.strftime("%H:%M"),
                "data_fine": d_fi.strftime("%d/%m/%Y"), "ora_fine": t_fi.strftime("%H:%M"),
                "nazionalita": naz, "data_nascita": dn, "luogo_nascita": ln, "codice_fiscale": cf,
                "indirizzo_cliente": ind, "numero_patente": pat, "metodo_pagamento": met, "pagato": pag,
                "pec": wa, "otp_code": otp, "timestamp_firma": datetime.now().strftime("%d/%m/%Y %H:%M")
            }
            # Cattura Firme
            def get_b64(c):
                if c.image_data is not None:
                    img = Image.fromarray(c.image_data.astype("uint8"))
                    buf = io.BytesIO(); img.save(buf, format="PNG")
                    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
                return ""
            st.session_state.temp_dati["firma"] = get_b64(can1)
            st.session_state.temp_dati["firma2"] = get_b64(can2)
            
            clean_wa = wa.replace(" ","").replace("+","")
            if not clean_wa.startswith("39"): clean_wa = "39" + clean_wa
            url = f"https://wa.me/{clean_wa}?text=Codice+Firma+Battaglia+Rent:+{otp}"
            st.markdown(f"### [📲 INVIA CODICE WHATSAPP]({url})")

    if "temp_dati" in st.session_state:
        v_otp = st.text_input("Inserisci OTP per confermare")
        if st.button("CONFERMA E ARCHIVIA"):
            if v_otp == st.session_state.temp_dati["otp_code"]:
                st.session_state.temp_dati["numero_fattura"] = get_prossimo_numero()
                supabase.table("contratti").insert(st.session_state.temp_dati).execute()
                st.success("✅ SALVATO!")
                del st.session_state.temp_dati
            else: st.error("OTP Errato")

with tab2:
    q = st.text_input("🔍 Cerca")
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    for r in res.data:
        if q.lower() in f"{s(r['cognome'])} {s(r['targa'])}".lower():
            with st.expander(f"📄 N. {r['numero_fattura']} - {r['cognome']}"):
                b1, b2 = st.columns(2)
                b1.download_button("📜 Contratto + Clausole + Privacy", genera_documento_completo(r), f"Contr_{r['id']}.pdf")
                b2.download_button("👮 Modulo Polizia Locale", genera_modulo_polizia(r), f"Polizia_{r['id']}.pdf")
