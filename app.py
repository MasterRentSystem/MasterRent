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
CONTATTI = "Email: battagliarent@gmail.com | Tel: +39 XXX XXXXXXX"

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

# --- GENERATORE PDF BUSINESS ---
class BusinessPDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 6, safe(DITTA), ln=True, align="L")
        self.set_font("Arial", "", 8)
        self.cell(0, 4, safe(f"{TITOLARE} - {INDIRIZZO}"), ln=True)
        self.cell(0, 4, safe(DATI_FISCALI), ln=True)
        self.ln(5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Pagina {self.page_no()}", align="C")

def genera_contratto_legale(c):
    pdf = BusinessPDF()
    pdf.add_page()
    
    # Titolo
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, safe(f"CONTRATTO DI NOLEGGIO SCOOTER N. {c['numero_fattura']}"), ln=True, align="C")
    pdf.ln(5)

    # Condizioni Generali (Riprese dal tuo esempio)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 6, "CONDIZIONI GENERALI (ITALIANO)", ln=True)
    pdf.set_font("Arial", "", 8)
    condizioni_it = [
        "- Il conducente deve possedere patente valida.",
        "- Il cliente e responsabile per danni, furto, incendio o smarrimento del veicolo.",
        "- Tutte le contravvenzioni sono a carico del cliente.",
        "- Il veicolo deve essere restituito con lo stesso livello di carburante.",
        "- E vietato guidare sotto l'effetto di alcol o droghe.",
        "- Il deposito cauzionale puo essere trattenuto in caso di danni.",
        "- Il cliente autorizza il trattamento dei dati personali ai sensi del GDPR.",
        "- Approvazione specifica clausole ai sensi degli artt. 1341 e 1342 c.c."
    ]
    for riga in condizioni_it:
        pdf.cell(0, 4, safe(riga), ln=True)
    
    pdf.ln(3)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 6, "GENERAL TERMS AND CONDITIONS (ENGLISH)", ln=True)
    pdf.set_font("Arial", "", 8)
    condizioni_en = [
        "- The driver must hold a valid driving license.",
        "- The customer is responsible for damages, theft, fire or loss of the vehicle.",
        "- All traffic fines are the responsibility of the customer.",
        "- The vehicle must be returned with the same fuel level.",
        "- Driving under the influence of alcohol or drugs is prohibited.",
        "- The security deposit may be retained in case of damages.",
        "- The customer authorizes the processing of personal data in accordance with GDPR.",
        "- Specific approval of clauses pursuant to Articles 1341 and 1342 of the Italian Civil Code."
    ]
    for riga in condizioni_en:
        pdf.cell(0, 4, safe(riga), ln=True)

    # Dati Noleggio
    pdf.ln(5)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, " DETTAGLI NOLEGGIO / RENTAL DETAILS", ln=True, fill=True, border=1)
    pdf.set_font("Arial", "", 9)
    pdf.cell(95, 7, safe(f"Cliente/Client: {c['nome']} {c['cognome']}"), border=1)
    pdf.cell(95, 7, safe(f"C.F./Tax ID: {c['codice_fiscale']}"), border=1, ln=True)
    pdf.cell(95, 7, safe(f"Veicolo/Vehicle: {c['modello']} ({c['targa']})"), border=1)
    pdf.cell(95, 7, safe(f"Patente/License: {c['numero_patente']}"), border=1, ln=True)
    pdf.cell(95, 7, safe(f"Dal/From: {c['inizio']}  Al/To: {c['fine']}"), border=1)
    pdf.cell(95, 7, safe(f"Prezzo/Price: {c['prezzo']} EUR"), border=1, ln=True)

    # Firme
    pdf.ln(10)
    y_firme = pdf.get_y()
    pdf.set_font("Arial", "B", 8)
    pdf.cell(95, 20, safe("Firma Cliente / Customer Signature"), border=1)
    pdf.cell(95, 20, safe("Firma Noleggiatore / Rental Company Signature"), border=1, ln=True)
    
    # Inserimento Firma Digitale se presente
    firma_base64 = c.get("firma")
    if firma_base64 and len(str(firma_base64)) > 100:
        try:
            if "," in str(firma_base64): firma_base64 = str(firma_base64).split(",")[1]
            pdf.image(io.BytesIO(base64.b64decode(firma_base64)), x=15, y=y_firme+5, w=40)
        except: pass

    return bytes(pdf.output(dest="S"))

def genera_modulo_vigili_legale(c):
    pdf = BusinessPDF()
    pdf.add_page()
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, safe("Spett. le Polizia Locale di ______________________"), ln=True, align="R")
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 10)
    pdf.multi_cell(0, 5, safe("OGGETTO: RIFERIMENTO VS. ACCERTAMENTO VIOLAZIONE N. ______________ PROT. _______\n- COMUNICAZIONE LOCAZIONE VEICOLO"))
    pdf.ln(10)
    
    pdf.set_font("Arial", "", 10)
    corpo = (f"In riferimento al Verbale di accertamento di infrazione al Codice della strada di cui all'oggetto, "
             f"con la presente, la sottoscritta BATTAGLIA MARIANNA nata a Berlino (Germania) il 13/01/1987 "
             f"e residente in Forio alla Via Cognole n. 5 in qualità di titolare dell'omonima ditta individuale, "
             f"C.F.: BTTMNN87A53Z112S e P. IVA: 10252601215")
    pdf.multi_cell(0, 6, safe(corpo))
    pdf.ln(5)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 10, "DICHIARA", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 6, safe(f"Ai sensi della l. 445/2000 che il veicolo modello {c['modello']} targato {c['targa']} "
                              f"il giorno {c['inizio']} era concesso in locazione senza conducente al signor:"))
    
    pdf.ln(5)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 8, safe(f"COGNOME E NOME: {c['nome']} {c['cognome']}"), ln=True)
    pdf.cell(0, 8, safe(f"LUOGO E DATA DI NASCITA: {c.get('luogo_nascita','')} - {c.get('data_nascita','')}"), ln=True)
    pdf.cell(0, 8, safe(f"RESIDENZA: {c.get('indirizzo_cliente','')}"), ln=True)
    pdf.cell(0, 8, safe(f"IDENTIFICATO A MEZZO PATENTE: {c['numero_patente']}"), ln=True)
    
    pdf.ln(10)
    pdf.multi_cell(0, 6, safe("La presente al fine di procedere alla rinotifica nei confronti del locatario sopra indicato.\nSi allega:\n- Copia del contratto di locazione con documento del trasgressore"))
    pdf.ln(10)
    pdf.cell(0, 10, "In fede, Marianna Battaglia", align="R", ln=True)
    
    return bytes(pdf.output(dest="S"))

def genera_fattura_completa(c):
    pdf = BusinessPDF()
    pdf.add_page()
    
    # Intestazione Fattura
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, safe(f"FATTURA ELETTRONICA N. {c['numero_fattura']}"), ln=True, align="C", border="B")
    pdf.ln(10)

    # Box Fornitore e Cliente
    y_box = pdf.get_y()
    pdf.set_font("Arial", "B", 9)
    pdf.cell(95, 7, "CEDENTE (FORNITORE)", border=1, fill=True)
    pdf.cell(95, 7, "CESSIONARIO (CLIENTE)", border=1, fill=True, ln=True)
    
    pdf.set_font("Arial", "", 9)
    # Colonna Sinistra (Tu)
    pdf.set_xy(10, y_box + 7)
    pdf.multi_cell(95, 5, safe(f"{DITTA}\n{TITOLARE}\n{INDIRIZZO}\n{DATI_FISCALI}"), border="LRB")
    
    # Colonna Destra (Cliente)
    pdf.set_xy(105, y_box + 7)
    info_cliente = f"{c['nome']} {c['cognome']}\n{c.get('indirizzo_cliente','')}\nC.F.: {c['codice_fiscale']}\nPEC: {c.get('pec','')}\nSDI: {c.get('codice_univoco','0000000')}"
    pdf.multi_cell(95, 5, safe(info_cliente), border="LRB")
    
    pdf.ln(10)

    # Tabella Prezzi
    pdf.set_font("Arial", "B", 10)
    pdf.cell(110, 8, "DESCRIZIONE SERVIZIO", border=1, fill=True)
    pdf.cell(25, 8, "IMPONIBILE", border=1, fill=True, align="C")
    pdf.cell(20, 8, "IVA", border=1, fill=True, align="C")
    pdf.cell(35, 8, "TOTALE", border=1, fill=True, align="C", ln=True)

    pdf.set_font("Arial", "", 10)
    prezzo_totale = float(c['prezzo'])
    imponibile = prezzo_totale / 1.22
    iva = prezzo_totale - imponibile

    pdf.cell(110, 10, safe(f"Noleggio Scooter {c['modello']} Targa {c['targa']}"), border=1)
    pdf.cell(25, 10, f"{imponibile:.2f}", border=1, align="C")
    pdf.cell(20, 10, "22%", border=1, align="C")
    pdf.cell(35, 10, f"{prezzo_totale:.2f} EUR", border=1, align="C", ln=True)

    # Riepilogo Finale
    pdf.ln(5)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(155, 8, "TOTALE DA PAGARE", align="R")
    pdf.cell(35, 8, f"{prezzo_totale:.2f} EUR", border=1, align="C")

    return bytes(pdf.output(dest="S"))

# --- L'INTERFACCIA STREAMLIT RIMANE SIMILE MA CON I NUOVI PDF ---
# ... (Codice Streamlit come prima, ma chiama queste nuove funzioni)
