import streamlit as st
from supabase import create_client, Client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from fpdf import FPDF
import io
import base64
import random
from datetime import datetime
import xml.etree.ElementTree as ET

# --- CONFIGURAZIONE ---
DITTA = "BATTAGLIA RENT"
PIVA = "10252601215"
CF_DITTA = "BTTMNN87A53Z112S"
SEDE = "Via Cognole n. 5 - 80075 Forio (NA)"

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

# --- PDF MASTER ---
class PDF_Master(FPDF):
    def header(self):
        self.set_font("Arial", "B", 10)
        self.cell(0, 5, DITTA, ln=True)
        self.set_font("Arial", "", 7)
        self.cell(0, 4, f"{SEDE} | P.IVA: {PIVA}", ln=True)
        self.ln(2)

def genera_pdf_completo(c):
    pdf = PDF_Master()
    pdf.add_page()
    w = pdf.epw
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 7, safe(f"CONTRATTO DI LOCAZIONE N. {c.get('numero_fattura')}"), ln=True, align="C")

    # SEZIONE ANAGRAFICA
    pdf.set_font("Arial", "B", 8); pdf.set_fill_color(230, 230, 230)
    pdf.cell(w, 5, " DATI CLIENTE", 1, 1, fill=True)
    pdf.set_font("Arial", "", 7)
    pdf.cell(w/2, 5, safe(f"Nome e Cognome: {c.get('nome')} {c.get('cognome')}"), 1)
    pdf.cell(w/2, 5, safe(f"Codice Fiscale: {c.get('codice_fiscale')}"), 1, 1)
    pdf.cell(w/3, 5, safe(f"Nato a: {c.get('luogo_nascita')}"), 1)
    pdf.cell(w/3, 5, safe(f"Data Nascita: {c.get('data_nascita')}"), 1)
    pdf.cell(w/3, 5, safe(f"Nazionalita: {c.get('nazionalita')}"), 1, 1)
    pdf.cell(w, 5, safe(f"Indirizzo: {c.get('indirizzo')}"), 1, 1)
    pdf.cell(w/2, 5, safe(f"Email: {c.get('email')}"), 1)
    pdf.cell(w/2, 5, safe(f"WhatsApp: {c.get('pec')}"), 1, 1)

    # SEZIONE NOLEGGIO
    pdf.ln(1)
    pdf.set_font("Arial", "B", 8); pdf.cell(w, 5, " DETTAGLI MEZZO E NOLEGGIO", 1, 1, fill=True)
    pdf.set_font("Arial", "", 7)
    pdf.cell(w/3, 5, safe(f"Modello: {c.get('modello')}"), 1)
    pdf.cell(w/3, 5, safe(f"Targa: {c.get('targa')}"), 1)
    pdf.cell(w/3, 5, safe(f"Patente: {c.get('numero_patente')}"), 1, 1)
    pdf.cell(w/2, 5, safe(f"Inizio: {c.get('data_inizio')} ore {c.get('ora_inizio')}"), 1)
    pdf.cell(w/2, 5, safe(f"Fine: {c.get('data_fine')} ore {c.get('ora_fine')}"), 1, 1)
    
    # PAGAMENTO E FISCALE
    pdf.cell(w/4, 5, safe(f"Prezzo: {c.get('prezzo')} EUR"), 1)
    pdf.cell(w/4, 5, safe(f"Metodo: {c.get('metodo_pagamento')}"), 1)
    pdf.cell(w/4, 5, safe(f"Stato: {c.get('stato_pagamento')}"), 1)
    pdf.cell(w/4, 5, safe(f"SDI: {c.get('codice_sdi', '0000000')}"), 1, 1)
    pdf.cell(w, 5, safe(f"Riferimento Multa: {c.get('riferimento_multa')}"), 1, 1)

    # CLAUSOLE (FISSE A 14 PER EVITARE INDEXERROR)
    pdf.ln(1); pdf.set_font("Arial", "B", 7); pdf.cell(0, 4, "CONDIZIONI GENERALI", ln=True)
    pdf.set_font("Arial", "", 5)
    cl = [
        "1. Isola d'Ischia: uso limitato all'isola.", "2. Guida: solo il firmatario.",
        "3. Danni: cliente responsabile.", "4. Multe: cliente + 25.83 Euro fee.",
        "5. Sub-noleggio: vietato.", "6. Ritardo: >30 min = 1gg extra.",
        "7. Carburante: stesso livello.", "8. Chiavi: perso = Euro 250,00.",
        "9. Casco: obbligatorio.", "10. Stato: ricevuto perfetto.",
        "11. Foro: Napoli.", "12. Assicurazione: RCA inclusa.",
        "13. Alcool/Droga: divieto.", "14. Furto: responsabile cliente."
    ]
    # Scriviamo in due colonne
    for i in range(0, 7):
        pdf.cell(w/2, 3, safe(cl[i]), border='B')
        pdf.cell(w/2, 3, safe(cl[i+7]), border='B', ln=1)

    # FOTO E FIRME
    pdf.ln(2); y_foto = pdf.get_y()
    try:
        if c.get("foto_patente"):
            p_img = str(c["foto_patente"]).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(p_img)), x=10, y=y_foto, w=35, h=22)
        if c.get("foto_mezzo"):
            m_img = str(c["foto_mezzo"]).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(m_img)), x=50, y=y_foto, w=35, h=22)
    except: pass

    pdf.set_xy(95, y_foto)
    pdf.set_font("Arial", "B", 6)
    pdf.cell(50, 22, "Firma Cliente", border=1, align="L")
    pdf.set_xy(148, y_foto)
    pdf.cell(50, 22, "Approvazione 1341-1342 cc", border=1, align="L")
    
    try:
        if c.get("firma"):
            f1 = str(c["firma"]).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(f1)), x=100, y=y_foto+5, w=35)
        if c.get("firma2"):
            f2 = str(c["firma2"]).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(f2)), x=153, y=y_foto+5, w=35)
    except: pass
    return bytes(pdf.output(dest="S"))

# --- INTERFACCIA ---
st.set_page_config(page_title="BATTAGLIA RENT", layout="wide")

if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Password", type="password") == "1234":
        if st.button("ACCEDI"): st.session_state.auth = True; st.rerun()
    st.stop()

tab1, tab2 = st.tabs(["📝 NUOVO", "📂 ARCHIVIO"])

with tab1:
    with st.form("f"):
        c1, c2, c3 = st.columns(3)
        n, cg, cf = c1.text_input("Nome"), c2.text_input("Cognome"), c3.text_input("Codice Fiscale")
        
        c4, c5, c6 = st.columns(3)
        ln, dn, nz = c4.text_input("Luogo Nascita"), c5.text_input("Data Nascita"), c6.text_input("Nazionalità")
        
        c7, c8, c9 = st.columns(3)
        ind, eml, sdi = c7.text_input("Indirizzo"), c8.text_input("Email"), c9.text_input("SDI", "0000000")
        
        m1, m2, m3, m4 = st.columns(4)
        mod, tg, pat, wa = m1.text_input("Modello"), m2.text_input("Targa").upper(), m3.text_input("N. Patente"), m4.text_input("WhatsApp")
        
        o1, o2, o3, o4 = st.columns(4)
        di, oi = o1.date_input("Data Inizio"), o2.time_input("Ora Inizio")
        df, of = o3.date_input("Data Fine"), o4.time_input("Ora Fine")
        
        p1, p2, p3, p4 = st.columns(4)
        prz, met, sta, rif = p1.number_input("Prezzo"), p2.selectbox("Metodo", ["Cash", "Carta"]), p3.selectbox("Stato", ["Pagato", "Da Pagare"]), p4.text_input("Rif Multa")
        
        vid = st.text_input("URL Video")
        
        f1, f2 = st.columns(2)
        fp, fm = f1.camera_input("Patente"), f2.camera_input("Mezzo")
        
        s1, s2 = st.columns(2)
        with s1: can1 = st_canvas(height=100, width=380, stroke_width=1, key="c1")
        with s2: can2 = st_canvas(height=100, width=380, stroke_width=1, key="c2")

        if st.form_submit_button("INVIA OTP"):
            def b64(f): return "data:image/png;base64," + base64.b64encode(f.getvalue()).decode() if f else ""
            def cnv(c):
                if c.image_data is not None:
                    img = Image.fromarray(c.image_data.astype("uint8"))
                    buf = io.BytesIO(); img.save(buf, format="PNG")
                    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
                return ""
            otp = str(random.randint(100000, 999999))
            st.session_state.temp = {
                "nome":n, "cognome":cg, "codice_fiscale":cf, "luogo_nascita":ln, "data_nascita":dn, "nazionalita":nz,
                "indirizzo":ind, "email":eml, "codice_sdi":sdi, "modello":mod, "targa":tg, "numero_patente":pat,
                "pec":wa, "data_inizio":di.strftime("%d/%m/%Y"), "ora_inizio":oi.strftime("%H:%M"),
                "data_fine":df.strftime("%d/%m/%Y"), "ora_fine":of.strftime("%H:%M"),
                "prezzo":prz, "metodo_pagamento":met, "stato_pagamento":sta, "riferimento_multa":rif,
                "video_url":vid, "otp_code":otp, "foto_patente":b64(fp), "foto_mezzo":b64(fm), "firma":cnv(can1), "firma2":cnv(can2)
            }
            st.success(f"Invia questo OTP: {otp}")

    if "temp" in st.session_state:
        v = st.text_input("Codice OTP")
        if st.button("SALVA"):
            if v == st.session_state.temp["otp_code"]:
                st.session_state.temp["numero_fattura"] = get_prossimo_numero()
                supabase.table("contratti").insert(st.session_state.temp).execute()
                st.success("Archiviato!")
                del st.session_state.temp
            else: st.error("OTP Errato")

with tab2:
    q = st.text_input("Cerca")
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    for r in res.data:
        if q.lower() in f"{s(r['cognome'])} {s(r['targa'])}".lower():
            with st.expander(f"Contratto {r['numero_fattura']} - {r['cognome']}"):
                st.download_button("📜 PDF", genera_pdf_completo(r), f"N.pdf", key=f"k_{r['id']}")
