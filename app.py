import streamlit as st
from supabase import create_client, Client
import base64
from datetime import datetime
from fpdf import FPDF
import io
import urllib.parse

# --- DATI BATTAGLIA RENT (DAI TUOI DOCUMENTI) ---
DITTA = "BATTAGLIA RENT"
TITOLARE = "BATTAGLIA MARIANNA"
SEDE = "Via Cognole n. 5 - 80075 Forio (NA)"
PIVA = "10252601215"
CF = "BTTMNN87A53Z112S"

# Connessione Database
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# Funzioni di utilità
def safe(t): return str(t).encode("latin-1", "replace").decode("latin-1")

def get_num():
    try:
        res = supabase.table("contratti").select("numero_fattura").execute()
        nums = [int(r['numero_fattura']) for r in res.data if str(r['numero_fattura']).isdigit()]
        return max(nums) + 1 if nums else 1
    except: return 1

# --- GENERATORE MODULO VIGILI (COPIA IDENTICA DELLA TUA FOTO) ---
def genera_rinotifica_pdf(c, info_v):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Times", "", 11)
    
    # Destinatario (in alto a dx)
    pdf.set_xy(120, 20)
    pdf.cell(0, 5, "Spett. le", ln=True)
    pdf.set_x(120)
    pdf.set_font("Times", "B", 11)
    pdf.cell(0, 5, f"Polizia Locale di {info_v['comune']}", ln=True)
    
    pdf.ln(15)
    pdf.set_font("Times", "B", 10)
    pdf.cell(20, 5, "OGGETTO:")
    pdf.set_font("Times", "", 10)
    pdf.cell(0, 5, f"RIFERIMENTO VS. ACCERTAMENTO VIOLAZIONE N. {info_v['num']} PROT. {info_v['prot']}")
    pdf.ln(5)
    pdf.cell(0, 5, "                       - COMUNICAZIONE LOCAZIONE VEICOLO")
    
    pdf.ln(10)
    testo = f"""In riferimento al Verbale... la sottoscritta BATTAGLIA MARIANNA nata a Berlino (Germania) il 13/01/1987 e residente in Forio alla Via Cognole n. 5 in qualita' di titolare dell'omonima ditta individuale, C.F.: {CF} e P.IVA: {PIVA}
    
    DICHIARA
Ai sensi della L. 445/2000 che il veicolo modello {c['modello']} targato {c['targa']} il giorno {info_v['data']} era concesso in locazione senza conducente al signor:

COGNOME E NOME: {c['cognome'].upper()} {c['nome'].upper()}
LUOGO E DATA DI NASCITA: {c.get('luogo_nascita', '-').upper()} {c.get('data_nascita', '-')}
RESIDENZA: {c.get('indirizzo', '-').upper()}
IDENTIFICATO A MEZZO: Patente di Guida"""
    
    pdf.multi_cell(0, 6, safe(testo))
    pdf.ln(20)
    pdf.cell(130)
    pdf.cell(0, 5, "In fede", ln=True)
    pdf.cell(130)
    pdf.cell(0, 5, "Marianna Battaglia", ln=True)
    return bytes(pdf.output(dest="S"))

# --- INTERFACCIA APP ---
st.set_page_config(page_title="Battaglia Rent App", layout="centered")

tab1, tab2, tab3 = st.tabs(["📝 NUOVO NOLEGGIO", "📂 ARCHIVIO", "🚨 GESTIONE MULTE"])

with tab1:
    with st.form("registrazione"):
        st.subheader("Dati Cliente")
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome")
        cognome = c2.text_input("Cognome")
        cf_cliente = st.text_input("Codice Fiscale")
        wa = st.text_input("WhatsApp (es: 39333...)")
        
        st.subheader("Dati Mezzo")
        m1, m2, m3 = st.columns(3)
        modello = m1.text_input("Modello Scooter")
        targa = m2.text_input("Targa").upper()
        prezzo = m3.number_input("Prezzo €", 0.0)
        
        st.subheader("Foto Obbligatorie")
        f_patente = st.camera_input("FOTO PATENTE")
        f_contratto = st.camera_input("FOTO CONTRATTO FIRMATO")
        
        if st.form_submit_button("SALVA TUTTO"):
            def b64(f): return "data:image/png;base64," + base64.b64encode(f.getvalue()).decode() if f else ""
            nuovo_id = get_num()
            dati = {
                "nome": nome, "cognome": cognome, "codice_fiscale": cf_cliente,
                "pec": wa, "modello": modello, "targa": targa, "prezzo": prezzo,
                "data_inizio": datetime.now().strftime("%d/%m/%Y"),
                "numero_fattura": nuovo_id,
                "foto_patente": b64(f_patente), "firma": b64(f_contratto)
            }
            supabase.table("contratti").insert(dati).execute()
            st.success(f"Salvato! Fattura N. {nuovo_id}")

with tab2:
    search = st.text_input("Cerca Targa o Cognome")
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for r in res.data:
        if search.lower() in f"{r['targa']} {r['cognome']}".lower():
            with st.expander(f"📄 {r['targa']} - {r['cognome']}"):
                # Tasto WhatsApp
                msg = f"Ciao {r['nome']}, ecco il tuo contratto con Battaglia Rent."
                wa_link = f"https://wa.me/{r['pec']}?text={urllib.parse.quote(msg)}"
                st.link_button("📲 INVIA SU WHATSAPP", wa_link)
                
                # Visualizza Foto
                st.image(r['firma'], caption="Contratto Firmato")

with tab3:
    st.subheader("🚨 Crea Modulo Rinotifica per i Vigili")
    targa_multa = st.text_input("Targa del motorino multato").upper()
    
    c1, c2 = st.columns(2)
    comune = c1.text_input("Polizia Locale di...")
    data_infraz = c2.text_input("Data Infrazione (GG/MM/AAAA)")
    
    c3, c4 = st.columns(2)
    n_verb = c3.text_input("Verbale N.")
    p_verb = c4.text_input("Prot.")
    
    if st.button("GENERA MODULO COMPILATO"):
        # Cerca il cliente nel database
        db_res = supabase.table("contratti").select("*").eq("targa", targa_multa).execute()
        if db_res.data:
            cliente = db_res.data[0]
            info_v = {"comune": comune, "data": data_infraz, "num": n_verb, "prot": p_verb}
            pdf_vigili = genera_rinotifica_pdf(cliente, info_v)
            st.download_button("📩 SCARICA MODULO PRONTO", pdf_vigili, f"Rinotifica_{targa_multa}.pdf")
        else:
            st.error("Targa non trovata in archivio!")
