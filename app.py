import streamlit as st
import datetime
import base64
from fpdf import FPDF
from supabase import create_client
from streamlit_drawable_canvas import st_canvas

st.set_page_config(layout="wide", page_title="MasterRent Pro")

# --- DATI FISCALI FISSI ---
INTESTAZIONE = "BATTAGLIA MARIANNA\nVia Cognole, 5 - 80075 Forio (NA)\nC.F. BTTMNN87A53Z112S - P. IVA 10252601215"

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def clean(t):
    if not t: return ""
    repl = {"à":"a","è":"e","é":"e","ì":"i","ò":"o","ù":"u","€":"Euro"}
    for k,v in repl.items(): t = str(t).replace(k,v)
    return t.encode("latin-1", "ignore").decode("latin-1")

def prossimo_numero():
    anno = datetime.date.today().year
    res = supabase.table("contatore_fatture").select("*").eq("anno", anno).execute()
    if not res.data:
        supabase.table("contatore_fatture").insert({"anno": anno, "ultimo_numero": 1}).execute()
        return 1
    numero = res.data[0]["ultimo_numero"] + 1
    supabase.table("contatore_fatture").update({"ultimo_numero": numero}).eq("anno", anno).execute()
    return numero

# --- PDF GENERATOR ---
def genera_pdf_tipo(c, tipo="CONTRATTO"):
    pdf = FPDF()
    pdf.add_page()
    
    # --- INTESTAZIONE ---
    try:
        # Se carichi un file chiamato logo.png su GitHub apparirà qui
        pdf.image("logo.png", 10, 8, 33) 
    except:
        pdf.set_font("Arial", "B", 20)
        pdf.cell(0, 10, "BATTAGLIA RENT", ln=True, align="C")
        pdf.set_font("Arial", "I", 10)
        pdf.cell(0, 10, "Noleggio Veicoli - Ischia", ln=True, align="C")
    
    pdf.ln(15)
    pdf.set_font("Arial", "B", 12)
    
    # --- TITOLO DEL DOCUMENTO ---
    titoli = {
        "CONTRATTO": "CONTRATTO DI NOLEGGIO", 
        "FATTURA": "RICEVUTA DI PAGAMENTO", 
        "MULTE": "COMUNICAZIONE DATI CONDUCENTE (VERBALI)"
    }
    pdf.cell(0, 10, titoli.get(tipo, "DOCUMENTO"), ln=True, align="C")
    pdf.ln(5)
    
    # --- DATI ANAGRAFICI ---
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 10, "DATI DEL CONDUCENTE:", ln=True)
    pdf.set_font("Arial", "", 10)
    
    dati_cliente = (
        f"Nome e Cognome: {c.get('nome', '')} {c.get('cognome', '')}\n"
        f"Nato a: {c.get('luogo_nascita', '________')} il {c.get('data_nascita', '________')}\n"
        f"Residenza: {c.get('indirizzo', '________')}\n"
        f"Codice Fiscale: {c.get('codice_fiscale', '________')}\n"
        f"Patente n.: {c.get('numero_patente', '________')}\n"
        f"Veicolo Targa: {c.get('targa', '________')}"
    )
    pdf.multi_cell(0, 6, dati_cliente)
    pdf.ln(5)

    # --- CONTENUTO SPECIFICO ---
    if tipo == "CONTRATTO":
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 8, "CONDIZIONI GENERALI E CLAUSOLE:", ln=True)
        pdf.set_font("Arial", "", 8)
        clausole = (
            "1. Il locatario dichiara di ricevere il veicolo in ottimo stato di manutenzione.\n"
            "2. È vietato il trasporto di persone o merci a fini commerciali.\n"
            "3. Il cliente è responsabile per eventuali danni, furti o contravvenzioni stradali.\n"
            "4. Il veicolo deve essere riconsegnato entro l'orario stabilito; il ritardo comporta penali.\n"
            "5. Carburante: il veicolo va riconsegnato con lo stesso livello di uscita."
        )
        pdf.multi_cell(0, 4, clausole)
        pdf.ln(5)
        
        pdf.set_font("Arial", "B", 9)
        pdf.cell(0, 8, "INFORMATIVA SULLA PRIVACY (GDPR):", ln=True)
        pdf.set_font("Arial", "", 7)
        privacy = "I dati personali raccolti sono trattati per l'esecuzione del contratto di noleggio e per gli adempimenti di legge (Art. 13 Reg. UE 2016/679). Il titolare del trattamento è Battaglia Rent."
        pdf.multi_cell(0, 4, privacy)

    elif tipo == "FATTURA":
        pdf.ln(5)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 10, f"IMPORTO NOLEGGIO: Euro {c.get('prezzo', '0.00')}", ln=True)
        pdf.cell(0, 10, f"DEPOSITO CAUZIONALE: Euro {c.get('deposito', '0.00')}", ln=True)
        pdf.ln(5)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 10, "Pagamento ricevuto. Documento valido come ricevuta fiscale.", ln=True)

    elif tipo == "MULTE":
        pdf.ln(5)
        pdf.multi_cell(0, 6, "In relazione alla violazione del Codice della Strada accertata, si comunica che il veicolo era affidato al conducente sopra indicato, che ne assume ogni responsabilità legale.")

    # --- SPAZIO PER LA FIRMA ---
    pdf.ln(15)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(100, 10, "Firma del Titolare (Battaglia Rent)", 0, 0)
    pdf.cell(0, 10, "Firma del Cliente", 0, 1, "R")
    pdf.ln(5)
    pdf.cell(100, 10, "________________________", 0, 0)
    pdf.cell(0, 10, "________________________", 0, 1, "R")
    
    return bytes(pdf.output())
# --- INSERIMENTO DATI ---
    st.subheader("Dati Cliente e Veicolo")
    nome = st.text_input("Nome")
    cognome = st.text_input("Cognome")
    indirizzo = st.text_input("Indirizzo Residenza")
    luogo_n = st.text_input("Luogo di Nascita")
    data_n = st.date_input("Data di Nascita", value=None)
    tel = st.text_input("Telefono")
    cf = st.text_input("Codice Fiscale")
    pat = st.text_input("Numero Patente")
    targa = st.text_input("Targa Veicolo")
    prezzo = st.number_input("Prezzo Noleggio (€)", min_value=0.0)
    deposito = st.number_input("Deposito Cauzionale (€)", min_value=0.0)

    # --- TASTO SALVA ---
    if st.button("💾 Salva Contratto e Genera Documenti"):
        try:
            dati = {
                "nome": nome,
                "cognome": cognome,
                "telefono": tel,
                "numero_patente": pat,
                "targa": targa,
                "prezzo": prezzo,
                "indirizzo": indirizzo,
                "luogo_nascita": luogo_n,
                "data_nascita": str(data_n) if data_n else None,
                "privacy_accettata": True
            }
            supabase.table("contratti").insert(dati).execute()
            st.success(f"✅ Contratto di {nome} salvato!")
            st.rerun() # Ricarica l'app per mostrare il nuovo contratto nell'archivio
        except Exception as e:
            st.error(f"Errore database: {e}")

# --- ARCHIVIO ---
st.divider()
st.header("📋 Archivio Contratti")
try:
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        id_c = c.get('id', '0')
        n = c.get('nome', '')
        cog = c.get('cognome', '')
        t = c.get('targa', '')
        
        with st.expander(f"ID: {id_c} - {n} {cog} ({t})"):
            col1, col2, col3 = st.columns(3)
            col1.download_button("📜 Contratto", genera_pdf_tipo(c, "CONTRATTO"), f"C_{id_c}.pdf")
            col2.download_button("💰 Fattura", genera_pdf_tipo(c, "FATTURA"), f"F_{id_c}.pdf")
            col3.download_button("🚨 Modulo Multe", genera_pdf_tipo(c, "MULTE"), f"M_{t}.pdf")
except Exception as e:
    st.info("Inizia a inserire il primo contratto per vedere l'archivio!")
