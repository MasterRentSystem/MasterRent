import streamlit as st
import datetime
from fpdf import FPDF
from supabase import create_client

# Connessione Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def clean(t):
    if not t: return ""
    repl = {"à":"a","è":"e","é":"e","ì":"i","ò":"o","ù":"u","€":"Euro","’":"'"}
    for k,v in repl.items(): t = str(t).replace(k,v)
    return t.encode('latin-1', 'ignore').decode('latin-1')

# --- FUNZIONE GENERAZIONE CONTRATTO COMPLETO ---
def get_contratto_pdf(c):
    pdf = FPDF()
    pdf.add_page()
    # Intestazione
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "CONTRATTO DI NOLEGGIO SCOOTER - MASTERRENT", ln=True, align="C")
    pdf.ln(5)
    
    # Dati Anagrafici
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "DATI DEL CONDUCENTE E DEL VEICOLO", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 7, clean(f"Nome e Cognome: {c['cliente']}\nCodice Fiscale: {c.get('cf','')}\nTarga Veicolo: {c['targa']}\nData Inizio: {c['data_inizio']}"))
    pdf.ln(5)

    # Clausole Legali
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 10, "CONDIZIONI GENERALI DI NOLEGGIO", ln=True)
    pdf.set_font("Arial", size=9)
    clausole = (
        "1. Il locatario dichiara di ricevere il veicolo in ottimo stato di manutenzione.\n"
        "2. Il carburante e le forature sono a carico del locatario.\n"
        "3. Il locatario si assume la piena responsabilita per contravvenzioni e danni a terzi.\n"
        "4. E vietato il trasporto di piu persone di quanto consentito dal libretto.\n"
        "5. In caso di furto, il locatario e tenuto a risarcire il valore di mercato del veicolo.\n"
        "6. PRIVACY: Il cliente acconsente al trattamento dei dati ai sensi del GDPR 679/2016."
    )
    pdf.multi_cell(0, 5, clean(clausole))
    pdf.ln(10)

    # Spazi per Foto e Firma
    pdf.set_font("Arial", "B", 10)
    pdf.cell(90, 40, "SPAZIO FOTO DOCUMENTO", border=1, align='C')
    pdf.cell(10)
    pdf.cell(0, 10, "FIRMA PER ACCETTAZIONE:", ln=True)
    pdf.ln(20)
    pdf.cell(100)
    pdf.cell(0, 10, "________________________", ln=True)
    
    return bytes(pdf.output())

# --- FUNZIONE GENERAZIONE RICEVUTA ---
def get_ricevuta_pdf(c):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 20, "RICEVUTA DI PAGAMENTO", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", size=14)
    pdf.cell(0, 10, clean(f"Cliente: {c['cliente']}"), ln=True)
    pdf.cell(0, 10, clean(f"Veicolo Targa: {c['targa']}"), ln=True)
    pdf.cell(0, 10, clean(f"Data: {c['data_inizio']}"), ln=True)
    pdf.ln(20)
    pdf.set_font("Arial", "B", 20)
    pdf.cell(0, 20, clean(f"TOTALE PAGATO: {c['prezzo']} Euro"), border=1, align="C")
    return bytes(pdf.output())

# --- INTERFACCIA STREAMLIT ---
st.set_page_config(layout="wide")
tab1, tab2 = st.tabs(["📝 Nuovo Noleggio", "🗄️ Archivio"])

with tab1:
    with st.form("main_form"):
        c1, c2 = st.columns(2)
        n = c1.text_input("Nome e Cognome")
        t = c1.text_input("Targa").upper()
        p = c2.number_input("Prezzo (€)", min_value=0.0)
        cf = c2.text_input("Codice Fiscale")
        if st.form_submit_button("💾 SALVA"):
            if n and t:
                supabase.table("contratti").insert({"cliente":n,"targa":t,"prezzo":p,"cf":cf,"data_inizio":str(datetime.date.today())}).execute()
                st.success("Dati salvati!")

with tab2:
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for row in res.data:
        with st.expander(f"📄 {row['cliente']} - {row['targa']}"):
            col_con, col_ric = st.columns(2)
            
            # Generazione on-demand per evitare scambi di file
            col_con.download_button(
                "📜 SCARICA CONTRATTO COMPLETO",
                get_contratto_pdf(row),
                f"Contratto_{row['id']}.pdf",
                "application/pdf",
                key=f"c_{row['id']}"
            )
            
            col_ric.download_button(
                "💰 SCARICA RICEVUTA",
                get_ricevuta_pdf(row),
                f"Ricevuta_{row['id']}.pdf",
                "application/pdf",
                key=f"r_{row['id']}"
            )
