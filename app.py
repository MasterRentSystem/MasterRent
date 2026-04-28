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
import xml.etree.ElementTree as ET

# --- DATI FISSI ---
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

# --- FUNZIONE PER CONVERTIRE FOTO IN BASE64 ---
def img_to_b64(img_file):
    if img_file is not None:
        return "data:image/png;base64," + base64.b64encode(img_file.getvalue()).decode()
    return ""

# --- MOTORE PDF (UNICA PAGINA OTTIMIZZATA) ---
class PDF_Contratto(FPDF):
    def header(self):
        self.set_font("Arial", "B", 9)
        self.cell(0, 5, DITTA, ln=True, align="L")
        self.set_font("Arial", "", 6)
        self.cell(0, 3, f"{SEDE} | P.IVA: {PIVA}", ln=True)
        self.ln(1)

def genera_pdf_unificato(c):
    pdf = PDF_Contratto()
    pdf.add_page()
    w = pdf.epw

    # Titolo Compatto
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 7, safe(f"CONTRATTO DI LOCAZIONE E FATTURA N. {c['numero_fattura']}"), ln=True, align="C")

    # Sezione Dati (Grid)
    pdf.set_font("Arial", "B", 7); pdf.set_fill_color(240, 240, 240)
    pdf.cell(w/2, 5, " DATI CLIENTE", 1, 0, fill=True)
    pdf.cell(w/2, 5, " DETTAGLI NOLEGGIO", 1, 1, fill=True)
    
    pdf.set_font("Arial", "", 6.5)
    y_start = pdf.get_y()
    info_c = f"Nome: {c['nome']} {c['cognome']} ({c.get('nazionalita')})\nC.F: {c.get('codice_fiscale')}\nPatente: {c.get('numero_patente')}\nRes: {c.get('indirizzo_cliente')}"
    pdf.multi_cell(w/2, 3.5, safe(info_c), border=1)
    
    pdf.set_xy(w/2 + 10, y_start)
    info_n = f"Mezzo: {c['modello']} - {c['targa']}\nPeriodo: {c.get('data_inizio')} {c.get('ora_inizio')} > {c.get('data_fine')} {c.get('ora_fine')}\nPagamento: {c.get('prezzo')} EUR ({c.get('metodo_pagamento')}) - Pagato: {c.get('pagato')}"
    pdf.multi_cell(w/2, 3.5, safe(info_n), border=1)

    # Clausole su due colonne (Font molto piccolo per far stare tutto)
    pdf.ln(1)
    pdf.set_font("Arial", "B", 7)
    pdf.cell(0, 4, "CONDIZIONI GENERALI / TERMS AND CONDITIONS", ln=True)
    pdf.set_font("Arial", "", 5)
    clausole = [
        "1. Isola d'Ischia: uso limitato all'isola.", "1. Limited to Ischia island only.",
        "2. Guida: solo il firmatario puo' guidare.", "2. Only the signer can drive.",
        "3. Danni/Furto: responsabilita' del cliente.", "3. Customer liable for damage/theft.",
        "4. Multe: a carico cliente + 25,83 Euro fee.", "4. Fines + 25.83 Euro fee to customer.",
        "5. Sub-noleggio: severamente vietato.", "5. Sub-rental is strictly forbidden.",
        "6. Riconsegna: >30 min ritardo = 1gg extra.", "6. Delay >30 min = 1 extra day fee.",
        "7. Carburante: riconsegna stesso livello.", "7. Return with same fuel level.",
        "8. Foro: competenza esclusiva Napoli.", "8. Jurisdiction: Court of Naples.",
        "9. Chiavi: smarrimento Euro 250,00.", "9. Lost keys penalty: Euro 250.00.",
        "10. Casco: obbligatorio per legge.", "10. Helmet is mandatory by law.",
        "11. Stato: mezzo ricevuto in perfetto stato.", "11. Vehicle received in perfect condition.",
        "12. Assicurazione: RCA inclusa.", "12. RCA Insurance included.",
        "13. Divieti: no alcool o droghe alla guida.", "13. No driving under influence.",
        "14. Sinistro: obbligo denuncia immediata.", "14. Immediate accident report required."
    ]
    for i in range(0, len(clausole), 2):
        pdf.cell(w/2, 3, safe(clausole[i]), border='B')
        pdf.cell(w/2, 3, safe(clausole[i+1]), border='B', ln=1)

    # Privacy e Foto
    pdf.ln(1)
    pdf.set_font("Arial", "B", 7); pdf.cell(0, 4, "FOTO DOCUMENTO E STATO MEZZO", ln=True)
    y_foto = pdf.get_y()
    pdf.rect(10, y_foto, 40, 25) # Box per foto patente
    pdf.rect(55, y_foto, 40, 25) # Box per foto mezzo
    
    try:
        if c.get("foto_patente"):
            p_img = str(c["foto_patente"]).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(p_img)), x=11, y=y_foto+1, w=38, h=23)
        if c.get("foto_mezzo"):
            m_img = str(c["foto_mezzo"]).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(m_img)), x=56, y=y_foto+1, w=38, h=23)
    except: pass

    # Firme
    pdf.set_xy(100, y_foto)
    pdf.set_font("Arial", "B", 6)
    pdf.cell(45, 25, "Firma Cliente", border=1, align="T")
    pdf.set_xy(150, y_foto)
    pdf.cell(45, 25, "Approvazione 1341-1342 cc", border=1, align="T")

    try:
        if c.get("firma"):
            f1 = str(c["firma"]).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(f1)), x=105, y=y_foto+5, w=35)
        if c.get("firma2"):
            f2 = str(c["firma2"]).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(f2)), x=155, y=y_foto+5, w=35)
    except: pass

    return bytes(pdf.output(dest="S"))

# --- INTERFACCIA STREAMLIT ---
st.set_page_config(page_title="BATTAGLIA RENT APP", layout="wide")

if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Password", type="password") == "1234":
        if st.button("ACCEDI"): st.session_state.auth = True; st.rerun()
    st.stop()

t1, t2 = st.tabs(["📝 NUOVO NOLEGGIO", "📂 ARCHIVIO"])

with t1:
    with st.form("main_form"):
        col1, col2, col3 = st.columns(3)
        mod = col1.text_input("Modello")
        tg = col2.text_input("Targa").upper()
        prz = col3.number_input("Prezzo (€)", 0.0)
        
        c1, c2, c3 = st.columns(3)
        nome = c1.text_input("Nome")
        cognome = c2.text_input("Cognome")
        wa = c3.text_input("WhatsApp")
        
        c4, c5, c6 = st.columns(3)
        cf = c4.text_input("Codice Fiscale")
        pat = c5.text_input("Numero Patente")
        naz = c6.text_input("Nazionalità")

        # Orari e Pagamento
        o1, o2, o3 = st.columns(3)
        d_in = o1.date_input("Inizio")
        d_fi = o2.date_input("Fine")
        met = o3.selectbox("Metodo", ["Cash", "Carta"])
        pag = o3.selectbox("Pagato", ["Sì", "No"])

        # --- SEZIONE FOTO ---
        st.subheader("📸 ACQUISIZIONE FOTO")
        f_col1, f_col2 = st.columns(2)
        foto_p = f_col1.camera_input("Foto Patente")
        foto_m = f_col2.camera_input("Foto Stato Motorino")

        st.subheader("🖋️ FIRME")
        s_col1, s_col2 = st.columns(2)
        with s_col1: can1 = st_canvas(height=100, width=350, stroke_width=1, key="c1")
        with s_col2: can2 = st_canvas(height=100, width=350, stroke_width=1, key="c2")

        if st.form_submit_button("SALVA E GENERA OTP"):
            otp = str(random.randint(100000, 999999))
            def b64_canvas(c):
                if c.image_data is not None:
                    img = Image.fromarray(c.image_data.astype("uint8"))
                    buf = io.BytesIO(); img.save(buf, format="PNG")
                    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
                return ""

            st.session_state.temp = {
                "nome": nome, "cognome": cognome, "targa": tg, "prezzo": prz, "modello": mod,
                "data_inizio": d_in.strftime("%d/%m/%Y"), "data_fine": d_fi.strftime("%d/%m/%Y"),
                "codice_fiscale": cf, "numero_patente": pat, "nazionalita": naz, "pec": wa,
                "metodo_pagamento": met, "pagato": pag, "otp_code": otp,
                "firma": b64_canvas(can1), "firma2": b64_canvas(can2),
                "foto_patente": img_to_b64(foto_p), "foto_mezzo": img_to_b64(foto_m)
            }
            st.markdown(f"### [📲 INVIA OTP](https://wa.me/{wa}?text=Codice+Firma:+{otp})")

    if "temp" in st.session_state:
        val = st.text_input("Codice OTP")
        if st.button("CONFERMA NOLEGGIO"):
            if val == st.session_state.temp["otp_code"]:
                st.session_state.temp["numero_fattura"] = get_prossimo_numero()
                supabase.table("contratti").insert(st.session_state.temp).execute()
                st.success("CONTRATTO E FOTO SALVATI!")
                del st.session_state.temp
            else: st.error("OTP Errato")

with t2:
    q = st.text_input("🔍 Cerca per Cognome o Targa")
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    for r in res.data:
        if q.lower() in f"{s(r['cognome'])} {s(r['targa'])}".lower():
            with st.expander(f"📄 {r['numero_fattura']} - {r['cognome']} ({r['targa']})"):
                st.download_button("📜 Scarica Contratto + Foto", genera_pdf_unificato(r), f"Noleggio_{r['id']}.pdf")
