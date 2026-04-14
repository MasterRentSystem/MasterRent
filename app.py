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
NATO_A = "Berlino (Germania) il 13/01/1987"

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

# --- MOTORE PDF PERSONALIZZATO ---
class BRPDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 6, safe(DITTA), ln=True, align="L")
        self.set_font("Arial", "", 8)
        self.cell(0, 4, safe(f"{TITOLARE} - {INDIRIZZO}"), ln=True)
        self.cell(0, 4, safe(DATI_IVA), ln=True)
        self.ln(5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

def genera_contratto(c):
    pdf = BRPDF()
    pdf.add_page()
    
    # Intestazione Documento
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, safe(f"CONTRATTO DI NOLEGGIO SCOOTER N. {c['numero_fattura']}"), ln=True, align="C")
    
    # Testo bilingue come da tua foto
    pdf.set_font("Arial", "", 8)
    pdf.multi_cell(0, 4, safe("Italiano: Il presente contratto disciplina il noleggio dello scooter tra la societa di noleggio e il cliente. Il cliente dichiara di aver letto, compreso e accettato tutte le condizioni sotto indicate."))
    pdf.ln(2)
    pdf.multi_cell(0, 4, safe("English: This agreement governs the rental of the scooter between the rental company and the customer. The customer declares to have read, understood and accepted all the conditions listed below."))
    
    # Condizioni Generali
    pdf.ln(5)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, "CONDIZIONI GENERALI (ITALIANO)", ln=True)
    pdf.set_font("Arial", "", 9)
    condizioni = [
        "- Il conducente deve possedere patente valida.",
        "- Il cliente e responsabile per danni, furto, incendio o smarrimento del veicolo.",
        "- Tutte le contravvenzioni sono a carico del cliente.",
        "- Il veicolo deve essere restituito con lo stesso livello di carburante.",
        "- E vietato guidare sotto l'effetto di alcol o droghe.",
        "- Il deposito cauzionale puo essere trattenuto in caso di danni.",
        "- Il cliente autorizza il trattamento dei dati personali ai sensi del GDPR.",
        "- Approvazione specifica clausole ai sensi degli artt. 1341 e 1342 c.c."
    ]
    for riga in condizioni: pdf.cell(0, 5, safe(riga), ln=True)
    
    # Box Firme
    pdf.ln(10)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(95, 10, safe("Firma Digitale Cliente / Customer Signature"), border=1)
    x_firma = pdf.get_x()
    y_firma = pdf.get_y()
    pdf.cell(95, 25, "", border=1, ln=True) # Spazio per immagine firma
    
    if c.get("firma") and len(str(c["firma"])) > 100:
        pdf.image(io.BytesIO(base64.b64decode(c["firma"])), x=135, y=y_firma+2, w=40)

    pdf.ln(5)
    pdf.cell(95, 10, safe("Data / Date"), border=1)
    pdf.cell(95, 10, safe(s(c.get('data_creazione'))[:10]), border=1, ln=True)
    
    return pdf.output(dest="S").encode("latin-1")

def genera_vigili(c):
    pdf = BRPDF()
    pdf.add_page()
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 10, "Spett. le Polizia Locale di ______________________", ln=True, align="R")
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 10, safe("OGGETTO: RIFERIMENTO VS. ACCERTAMENTO VIOLAZIONE N. __________ PROT. ______"), ln=True)
    pdf.cell(0, 10, safe("COMUNICAZIONE LOCAZIONE VEICOLO"), ln=True, align="C")
    
    pdf.set_font("Arial", "", 11)
    testo = (f"In riferimento al Verbale di accertamento di infrazione al Codice della strada di cui all'oggetto, "
             f"con la presente, la sottoscritta BATTAGLIA MARIANNA nata a {NATO_A} e residente in Forio "
             f"alla Via Cognole n. 5 in qualita di titolare dell'omonima ditta individuale, C.F.: BTTMNN87A53Z112S e P. IVA: 10252601215")
    pdf.multi_cell(0, 6, safe(testo))
    pdf.ln(5)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 10, "DICHIARA", ln=True, align="C")
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, safe(f"Ai sensi della L. 445/2000 che il veicolo modello {c['modello']} targato {c['targa']} il giorno {c['inizio']} era concesso in locazione senza conducente al signor:"))
    
    pdf.ln(5)
    pdf.cell(0, 8, safe(f"COGNOME E NOME: {c['nome']} {c['cognome']}"), ln=True, border="B")
    pdf.cell(0, 8, safe(f"LUOGO E DATA DI NASCITA: {c['luogo_nascita']} - {c['data_nascita']}"), ln=True, border="B")
    pdf.cell(0, 8, safe(f"RESIDENZA: {c['indirizzo_cliente']}"), ln=True, border="B")
    pdf.cell(0, 8, safe(f"IDENTIFICATO A MEZZO: Patente N. {c['numero_patente']}"), ln=True, border="B")
    
    pdf.ln(10)
    pdf.multi_cell(0, 6, safe("La presente al fine di procedere alla rinotifica nei confronti del locatario sopra indicato.\nSi allega: Copia del contratto di locazione con documento del trasgressore."))
    
    pdf.ln(10)
    pdf.cell(0, 10, "In fede", ln=True, align="R")
    pdf.cell(0, 10, "Marianna Battaglia", ln=True, align="R")
    
    return pdf.output(dest="S").encode("latin-1")

def genera_fattura_aruba(c):
    pdf = BRPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, safe(f"FATTURA ELETTRONICA N. {c['numero_fattura']}"), ln=True, border="B", align="C")
    
    pdf.ln(5)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(100, 7, "CEDENTE (TU)", border=1); pdf.cell(90, 7, "CESSIONARIO (CLIENTE)", border=1, ln=True)
    pdf.set_font("Arial", "", 9)
    pdf.cell(100, 5, safe(DITTA), border="LR"); pdf.cell(90, 5, safe(f"{c['nome']} {c['cognome']}"), border="LR", ln=True)
    pdf.cell(100, 5, safe(DATI_IVA), border="LR"); pdf.cell(90, 5, safe(f"C.F./P.IVA: {c['codice_fiscale']}"), border="LR", ln=True)
    pdf.cell(100, 5, safe(INDIRIZZO), border="LR"); pdf.cell(90, 5, safe(f"Cod. Destinatario: {c.get('codice_univoco', '0000000')}"), border="LR", ln=True)
    pdf.cell(100, 5, "", border="LRB"); pdf.cell(90, 5, safe(f"PEC: {c.get('pec', 'N/A')}"), border="LRB", ln=True)
    
    pdf.ln(10)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(130, 8, "DESCRIZIONE PRESTAZIONE", border=1, fill=True); pdf.cell(30, 8, "IVA", border=1, fill=True); pdf.cell(30, 8, "TOTALE", border=1, fill=True, ln=True)
    pdf.set_font("Arial", "", 10)
    desc = f"Noleggio scooter {c['modello']} (Targa {c['targa']}) dal {c['inizio']} al {c['fine']}"
    pdf.cell(130, 15, safe(desc), border=1); pdf.cell(30, 15, "22%", border=1); pdf.cell(30, 15, f"{c['prezzo']} EUR", border=1, ln=True)
    
    return pdf.output(dest="S").encode("latin-1")

# --- INTERFACCIA ---
st.title("🚀 Battaglia Rent - Gestione Integrata")

tab1, tab2 = st.tabs(["📝 Nuovo Noleggio", "📁 Archivio & Aruba"])

with tab1:
    with st.form("form_noleggio"):
        c1, c2, c3 = st.columns(3)
        nome = c1.text_input("Nome")
        cognome = c2.text_input("Cognome")
        cf = c3.text_input("Codice Fiscale / P.IVA")
        
        c4, c5 = st.columns(2)
        pec = c4.text_input("PEC Cliente (per Aruba)")
        sdi = c5.text_input("Codice Univoco (SDI)", value="0000000")
        
        c6, c7, c8 = st.columns(3)
        mod = c6.text_input("Modello Scooter")
        tar = c7.text_input("Targa").upper()
        pat = c8.text_input("N. Patente")
        
        c9, c10, c11 = st.columns(3)
        prz = c9.number_input("Totale Fattura (€)", min_value=0.0)
        ini = c10.date_input("Data Inizio")
        fin = c11.date_input("Data Fine")
        
        dat_n = st.text_input("Data Nascita Cliente")
        luo_n = st.text_input("Luogo Nascita Cliente")
        ind = st.text_input("Indirizzo Residenza Cliente")
        
        st.write("Firma Cliente")
        canvas = st_canvas(height=150, width=400, key="f_v10")
        
        if st.form_submit_button("REGISTRA"):
            img = Image.fromarray(canvas.image_data.astype("uint8"))
            buf = io.BytesIO(); img.save(buf, format="PNG")
            f_b64 = base64.b64encode(buf.getvalue()).decode()
            
            num = get_prossimo_numero()
            dati = {
                "nome": nome, "cognome": cognome, "codice_fiscale": cf, "modello": mod, "targa": tar,
                "prezzo": prz, "inizio": str(ini), "fine": str(fin), "numero_fattura": num,
                "firma": f_b64, "data_nascita": dat_n, "luogo_nascita": luo_n, "indirizzo_cliente": ind,
                "numero_patente": pat, "pec": pec, "codice_univoco": sdi, "data_creazione": datetime.now().isoformat()
            }
            supabase.table("contratti").insert(dati).execute()
            st.success(f"Registrato! N. {num}")

with tab2:
    search = st.text_input("🔍 Cerca Targa o Cognome")
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    for r in res.data:
        if search.lower() in f"{r['cognome']} {r['targa']}".lower():
            with st.expander(f"Doc N. {r['numero_fattura']} - {r['cognome']}"):
                col1, col2, col3 = st.columns(3)
                col1.download_button("📜 Contratto (Bilingue)", genera_contratto(r), f"Contratto_{r['id']}.pdf")
                col2.download_button("🚨 Modulo Vigili", genera_vigili(r), f"Vigili_{r['id']}.pdf")
                col3.download_button("🧾 Fattura Aruba/AdE", genera_fattura_aruba(r), f"Fattura_{r['id']}.pdf")
