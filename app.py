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
DATI_FISCALI = "P.IVA: 10252601215 | C.F.: BTTMNN87A53Z112S"
NATO_A = "Berlino (Germania) il 13/01/1987"

# Connessione Database
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- UTILITY ---
def s(v): return "" if v is None else str(v)
def safe(t): return s(t).encode("latin-1", "replace").decode("latin-1")

def get_prossimo_numero():
    try:
        res = supabase.table("contratti").select("numero_fattura").execute()
        nums = [int(r['numero_fattura']) for r in res.data if str(r['numero_fattura']).isdigit()]
        return max(nums) + 1 if nums else 1
    except: return 1

def upload_foto(file, targa, tipo):
    if file is None: return None
    try:
        img = Image.open(file)
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
        img.thumbnail((800, 800))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=75)
        nome = f"{tipo}{targa}{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
        supabase.storage.from_("documenti").upload(nome, buf.getvalue(), {"content-type": "image/jpeg"})
        return supabase.storage.from_("documenti").get_public_url(nome)
    except: return None

# --- GENERATORE PDF PROFESSIONALE ---
class BusinessPDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 6, safe(DITTA), ln=True)
        self.set_font("Arial", "", 8)
        self.cell(0, 4, safe(f"{TITOLARE} - {INDIRIZZO}"), ln=True)
        self.cell(0, 4, safe(DATI_FISCALI), ln=True)
        self.ln(5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

def genera_contratto_legale(c):
    pdf = BusinessPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, safe(f"CONTRATTO DI NOLEGGIO SCOOTER N. {c['numero_fattura']}"), ln=True, align="C")
    pdf.ln(5)
    
    # --- ANAGRAFICA COMPLETA CLIENTE ---
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, " DATI ANAGRAFICI CLIENTE / CUSTOMER DETAILS", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "", 9)
    pdf.cell(95, 7, safe(f"Nome/Name: {c['nome']} {c['cognome']}"), border="LR")
    pdf.cell(95, 7, safe(f"Nazionalita/Nationality: {c.get('nazionalita','')}"), border="R", ln=True)
    pdf.cell(95, 7, safe(f"Nato il/Born on: {c.get('data_nascita','')} a: {c.get('luogo_nascita','')}"), border="LR")
    pdf.cell(95, 7, safe(f"C.F./Tax ID: {c['codice_fiscale']}"), border="R", ln=True)
    pdf.cell(190, 7, safe(f"Residenza/Address: {c.get('indirizzo_cliente','')}"), border="LRB", ln=True)
    pdf.cell(95, 7, safe(f"Tel: {c.get('telefono','')}"), border="LRB")
    pdf.cell(95, 7, safe(f"Email/PEC: {c.get('pec','')}"), border="RB", ln=True)
    
    pdf.ln(3)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, " DATI NOLEGGIO / RENTAL DATA", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "", 9)
    pdf.cell(63, 7, safe(f"Veicolo: {c['modello']}"), border=1)
    pdf.cell(63, 7, safe(f"Targa: {c['targa']}"), border=1)
    pdf.cell(64, 7, safe(f"Patente: {c['numero_patente']}"), border=1, ln=True)
    pdf.cell(95, 7, safe(f"Inizio: {c['inizio']}"), border=1)
    pdf.cell(95, 7, safe(f"Fine: {c['fine']}"), border=1, ln=True)
    pdf.cell(95, 7, safe(f"Prezzo: {c['prezzo']} EUR"), border=1)
    pdf.cell(95, 7, safe(f"Deposito: {c.get('deposito',0)} EUR"), border=1, ln=True)

    pdf.ln(5)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(0, 5, "CONDIZIONI GENERALI / TERMS AND CONDITIONS", ln=True)
    pdf.set_font("Arial", "", 7)
    testo_legale = (
        "Il conducente deve possedere patente valida. Il cliente e responsabile per danni, furto, incendio o smarrimento del veicolo. "
        "Tutte le contravvenzioni sono a carico del cliente. Il veicolo deve essere restituito con lo stesso livello di carburante. "
        "E vietato guidare sotto l'effetto di alcol o droghe. Il deposito cauzionale puo essere trattenuto in caso di danni.\n"
        "The driver must hold a valid driving license. The customer is responsible for damages, theft, fire or loss of the vehicle. "
        "All traffic fines are the responsibility of the customer. The vehicle must be returned with the same fuel level. "
        "Driving under the influence of alcohol or drugs is prohibited."
    )
    pdf.multi_cell(0, 4, safe(testo_legale), border=1)
    
    # --- SOLO FIRMA CLIENTE ---
    pdf.ln(5)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(0, 7, "Firma Digitale Cliente / Customer Digital Signature", ln=True)
    y_firma = pdf.get_y()
    pdf.cell(100, 25, "", border=1)
    pdf.cell(90, 25, safe(f"Data: {datetime.now().strftime('%d/%m/%Y')}"), border=1, ln=True)
    
    firma = c.get("firma")
    if firma and len(str(firma)) > 100:
        try:
            if "," in str(firma): firma = str(firma).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(firma)), x=15, y=y_firma+2, w=40)
        except: pass
    return bytes(pdf.output(dest="S"))

def genera_modulo_vigili_legale(c):
    pdf = BusinessPDF()
    pdf.add_page()
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 10, safe("Spett. le"), ln=True, align="R")
    pdf.cell(0, 10, safe("Polizia Locale di ______________________"), ln=True, align="R")
    pdf.ln(5)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, safe("OGGETTO: RIFERIMENTO VS. ACCERTAMENTO VIOLAZIONE N. ______________ PROT. _______"), ln=True)
    pdf.cell(0, 7, safe("- COMUNICAZIONE LOCAZIONE VEICOLO"), ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", "", 10)
    corpo = (f"In riferimento al Verbale di accertamento di infrazione al Codice della strada di cui all'oggetto, con la presente, la "
             f"sottoscritta BATTAGLIA MARIANNA nata a Berlino (Germania) il 13/01/1987 e residente in Forio alla Via Cognole "
             f"n. 5 in qualita di titolare dell'omonima ditta individuale, C.F.: BTTMNN87A53Z112S e P. IVA: 10252601215")
    pdf.multi_cell(0, 6, safe(corpo))
    pdf.ln(5)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 10, "DICHIARA", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 6, safe(f"Ai sensi della l. 445/2000 che il veicolo modello {c['modello']} targato {c['targa']} il "
                              f"giorno {c['inizio']} era concesso in locazione senza conducente al signor:"))
    pdf.ln(5)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 8, safe(f"COGNOME E NOME: {c['nome']} {c['cognome']}"), ln=True)
    pdf.cell(0, 8, safe(f"LUOGO E DATA DI NASCITA: {c.get('luogo_nascita','')} - {c.get('data_nascita','')}"), ln=True)
    pdf.cell(0, 8, safe(f"RESIDENZA: {c.get('indirizzo_cliente','')}"), ln=True)
    pdf.cell(0, 8, safe(f"IDENTIFICATO A MEZZO PATENTE: {c['numero_patente']}"), ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 6, safe("La presente al fine di procedere alla rinotifica nei confronti del locatario sopra indicato.\nSi allega:\n- Copia del contratto di locazione con documento del trasgressore"))
    pdf.ln(5)
    pdf.multi_cell(0, 6, safe("Ai sensi della L. 445/2000, il sottoscritto dichiara che la copia del contratto che si allega e conforme all'originale agli atti della ditta."))
    pdf.ln(10)
    pdf.cell(0, 10, "In fede,", align="R", ln=True)
    pdf.cell(0, 10, "Marianna Battaglia", align="R", ln=True)
    return bytes(pdf.output(dest="S"))

def genera_fattura_completa(c):
    pdf = BusinessPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, safe(f"FATTURA N. {c['numero_fattura']}"), ln=True, align="C", border="B")
    pdf.ln(5)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(95, 7, "CEDENTE (BATTAGLIA RENT)", border=1, fill=True)
    pdf.cell(95, 7, "CESSIONARIO (CLIENTE)", border=1, fill=True, ln=True)
    pdf.set_font("Arial", "", 9)
    pdf.multi_cell(95, 5, safe(f"{DITTA}\n{TITOLARE}\n{INDIRIZZO}\n{DATI_FISCALI}"), border=1)
    pdf.set_xy(105, pdf.get_y()-20)
    pdf.multi_cell(95, 5, safe(f"{c['nome']} {c['cognome']}\n{c.get('indirizzo_cliente','')}\nCF: {c['codice_fiscale']}\nSDI: {c.get('codice_univoco','0000000')}\nPEC/Email: {c.get('pec','')}"), border=1)
    pdf.ln(10)
    
    prezzo = float(c['prezzo'])
    imponibile = prezzo / 1.22
    iva = prezzo - imponibile
    
    pdf.set_font("Arial", "B", 10)
    pdf.cell(110, 8, "DESCRIZIONE", border=1, fill=True); pdf.cell(40, 8, "IVA", border=1, fill=True); pdf.cell(40, 8, "TOTALE", border=1, fill=True, ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(110, 10, safe(f"Noleggio Scooter {c['modello']} ({c['targa']})"), border=1)
    pdf.cell(40, 10, "22%", border=1)
    pdf.cell(40, 10, f"{prezzo:.2f} EUR", border=1, ln=True)
    pdf.ln(5)
    pdf.cell(150, 8, "IMPONIBILE:", align="R"); pdf.cell(40, 8, f"{imponibile:.2f} EUR", border=1, ln=True)
    pdf.cell(150, 8, "IVA 22%:", align="R"); pdf.cell(40, 8, f"{iva:.2f} EUR", border=1, ln=True)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(150, 8, "TOTALE FATTURA:", align="R"); pdf.cell(40, 8, f"{prezzo:.2f} EUR", border=1, ln=True)
    return bytes(pdf.output(dest="S"))

# --- INTERFACCIA STREAMLIT ---
st.set_page_config(page_title="Battaglia Rent Pro", layout="wide")

if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Password", type="password") == "1234":
        if st.button("Accedi"): st.session_state.auth = True; st.rerun()
    st.stop()

t1, t2 = st.tabs(["📝 Nuovo Noleggio", "📂 Archivio"])

with t1:
    with st.form("form_v21"):
        st.subheader("👤 Anagrafica Cliente")
        c1, c2, c3 = st.columns(3)
        nome = c1.text_input("Nome")
        cognome = c2.text_input("Cognome")
        naz = c3.text_input("Nazionalita")
        
        c4, c5, c6 = st.columns(3)
        cf = c4.text_input("C.F. / ID")
        tel = c5.text_input("Telefono")
        pec = c6.text_input("Email / PEC")
        
        c7, c8, c9 = st.columns(3)
        dat_n = c7.text_input("Data Nascita (GG/MM/AAAA)")
        luo_n = c8.text_input("Luogo Nascita")
        ind = c9.text_input("Indirizzo Residenza Completo")
        
        st.subheader("🛵 Dati Mezzo")
        m1, m2, m3 = st.columns(3)
        mod = m1.text_input("Modello")
        tar = m2.text_input("Targa").upper()
        pat = m3.text_input("N. Patente")
        
        d1, d2, d3 = st.columns(3)
        prezzo = d1.number_input("Prezzo Totale (€)")
        deposito = d2.number_input("Deposito (€)")
        sdi = d3.text_input("Codice SDI", value="0000000")
        
        ini, fin = st.columns(2)
        d_ini = ini.date_input("Inizio Noleggio")
        d_fin = fin.date_input("Fine Noleggio")
        
        f1, f2 = st.columns(2)
        front = f1.file_uploader("Fronte Patente")
        back = f2.file_uploader("Retro Patente")
        
        st.write("Firma Cliente")
        canvas = st_canvas(height=150, width=400, stroke_width=3, key="sig_v21")

        if st.form_submit_button("SALVA E GENERA"):
            try:
                img = Image.fromarray(canvas.image_data.astype("uint8"))
                buf = io.BytesIO(); img.save(buf, format="PNG")
                firma = base64.b64encode(buf.getvalue()).decode()
                u_f = upload_foto(front, tar, "F")
                u_r = upload_foto(back, tar, "R")
                num = get_prossimo_numero()
                
                dati = {
                    "nome": nome, "cognome": cognome, "codice_fiscale": cf, "modello": mod, "targa": tar,
                    "prezzo": prezzo, "deposito": deposito, "numero_fattura": num, "firma": firma,
                    "url_fronte": u_f, "url_retro": u_r, "pec": pec, "codice_univoco": sdi,
                    "data_nascita": dat_n, "luogo_nascita": luo_n, "indirizzo_cliente": ind,
                    "inizio": str(d_ini), "fine": str(d_fin), "numero_patente": pat,
                    "nazionalita": naz, "telefono": tel
                }
                supabase.table("contratti").insert(dati).execute()
                st.success(f"Registrato con successo! Numero: {num}")
            except Exception as e:
                st.error(f"Errore: {e}")

with t2:
    search = st.text_input("🔍 Cerca per Cognome o Targa")
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    for r in res.data:
        if search.lower() in f"{s(r['cognome'])} {s(r['targa'])}".lower():
            with st.expander(f"N. {r['numero_fattura']} - {r['cognome']} ({r['targa']})"):
                c_pdf, f_pdf, v_pdf = genera_contratto_legale(r), genera_fattura_completa(r), genera_modulo_vigili_legale(r)
                ca, cb, cc = st.columns(3)
                ca.download_button("📜 Contratto", c_pdf, f"C_{r['id']}.pdf", key=f"c_{r['id']}")
                cb.download_button("🧾 Fattura", f_pdf, f"F_{r['id']}.pdf", key=f"f_{r['id']}")
                cc.download_button("🚨 Vigili", v_pdf, f"V_{r['id']}.pdf", key=f"v_{r['id']}")
                if r.get("url_fronte"): st.image(r["url_fronte"], width=300)
