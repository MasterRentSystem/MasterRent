import streamlit as st
import datetime
import pandas as pd
from supabase import create_client, Client
from fpdf import FPDF
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Battaglia Rent - Gestionale", layout="wide")
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- LOGIN ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Accesso Riservato Battaglia Rent")
    pwd = st.text_input("Password", type="password")
    if st.button("Entra"):
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state.auth = True
            st.rerun()
    st.stop()

# --- DATI FISSI ---
TITOLARE = "BATTAGLIA MARIANNA"
SEDE = "Via Cognole, 5 - 80075 Forio (NA)"
PIVA = "10252601215"
CF = "BTTMNN87A53Z112S"

# --- LOGICA PDF ---
def genera_pdf_professionale(d, tipo, firma_img=None):
    pdf = FPDF()
    pdf.add_page()
    
    # Intestazione per tutti i documenti
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "BATTAGLIA RENT", ln=True, align="L")
    pdf.set_font("Arial", "", 8)
    pdf.cell(0, 4, f"di {TITOLARE} - {SEDE}", ln=True)
    pdf.cell(0, 4, f"P.IVA: {PIVA} - C.F.: {CF}", ln=True)
    pdf.ln(5)

    if tipo == "CONTRATTO":
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, f"CONTRATTO DI LOCAZIONE SCOOTER N. {d.get('numero_fattura')}", border="TB", ln=True, align="C")
        
        # Dati Cliente e Veicolo
        pdf.ln(3)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(0, 6, "DATI DEL LOCATARIO", ln=True)
        pdf.set_font("Arial", "", 9)
        pdf.multi_cell(0, 5, f"Cliente: {d.get('nome')} {d.get('cognome')} | CF: {d.get('codice_fiscale')}\n"
                             f"Nato a: {d.get('luogo_nascita')} il {d.get('data_nascita')} | Residente: {d.get('residenza')}\n"
                             f"Patente: {d.get('numero_patente')} | Tel: {d.get('telefono')}")
        
        pdf.ln(2)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(95, 7, f"Veicolo: {d.get('modello')} Targa: {d.get('targa')}", border=1)
        pdf.cell(95, 7, f"Periodo: {d.get('inizio')} / {d.get('fine')}", border=1, ln=True)
        pdf.cell(95, 7, f"Benzina: {d.get('benzina')} | Deposito: {d.get('deposito')}€", border=1)
        pdf.cell(95, 7, f"Prezzo Totale: {d.get('prezzo')}€", border=1, ln=True)
        
        # CLAUSOLE DETTAGLIATE (Box Clausole)
        pdf.ln(3)
        pdf.set_font("Arial", "B", 8)
        pdf.cell(0, 5, "CONDIZIONI GENERALI DI NOLEGGIO E PRIVACY (GDPR 2016/679)", ln=True)
        pdf.set_font("Arial", "", 6)
        clausole = (
            "1. CONSEGNA: Il cliente riceve il mezzo in ottimo stato. 2. DANNI: Ogni danno al veicolo è a carico del cliente. "
            "3. FURTO: In caso di furto il cliente risponde del valore commerciale del mezzo. 4. MULTE: Il cliente è l'unico responsabile "
            "delle violazioni al C.d.S. 5. PRIVACY: I dati sono trattati per finalità contrattuali e di pubblica sicurezza. "
            "6. RICONSEGNA: Il mezzo va riconsegnato entro l'orario stabilito, pena l'addebito di una giornata extra."
        )
        pdf.multi_cell(0, 3, clausole, border=1)

        # FIRMA
        pdf.ln(10)
        y_f = pdf.get_y()
        pdf.set_font("Arial", "B", 9)
        pdf.cell(95, 5, "Il Locatore", 0, 0, "C")
        pdf.cell(95, 5, "Il Cliente (Firma Digitale)", 0, 1, "C")
        if firma_img:
            buf = io.BytesIO()
            firma_img.save(buf, format='PNG')
            buf.seek(0)
            pdf.image(buf, x=135, y=y_f+5, w=35)
        pdf.cell(95, 10, "______________", 0, 0, "C")
        pdf.cell(95, 10, "______________", 0, 1, "C")

    elif tipo == "MULTE":
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "DICHIARAZIONE DATI CONDUCENTE (VIPALAZIONE)", ln=True, align="C")
        pdf.set_font("Arial", "", 11)
        pdf.ln(10)
        testo = (
            f"La sottoscritta {TITOLARE}, titolare della ditta BATTAGLIA RENT, proprietaria del veicolo "
            f"targato {d.get('targa')}, dichiara ai sensi della L. 445/2000 che il giorno dell'infrazione "
            f"il mezzo era affidato al Sig. {d.get('nome')} {d.get('cognome')}, nato a {d.get('luogo_nascita')} "
            f"il {d.get('data_nascita')}, residente a {d.get('residenza')}, titolare di patente {d.get('numero_patente')}."
        )
        pdf.multi_cell(0, 7, testo)
        pdf.ln(20)
        pdf.cell(0, 10, "Firma Titolare: ______________________", ln=True, align="R")

    return bytes(pdf.output())

# --- MENU ---
menu = st.sidebar.radio("NAVIGAZIONE", ["Nuovo Noleggio", "Archivio e Multe", "Incassi"])

if menu == "Nuovo Noleggio":
    st.header("📝 Registrazione Contratto Professionale")
    
    with st.expander("DATI CLIENTE", expanded=True):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome")
        cognome = c2.text_input("Cognome")
        residenza = st.text_input("Indirizzo Residenza")
        patente = c1.text_input("N. Patente")
        codfisc = c2.text_input("Codice Fiscale")
        tel = c1.text_input("Telefono")
        nascita = c2.date_input("Data Nascita", value=datetime.date(1990,1,1))
        luogo = c1.text_input("Luogo Nascita")
        f_patente = st.file_uploader("FOTO PATENTE (Fronte/Retro)", type=['jpg','png'])

    with st.expander("DATI VEICOLO", expanded=True):
        targa = st.text_input("TARGA").upper()
        modello = st.text_input("Modello Scooter")
        c3, c4 = st.columns(2)
        prezzo = c3.number_input("Prezzo (€)", 0.0)
        deposito = c4.number_input("Deposito (€)", 0.0)
        inizio = c3.date_input("Data Inizio")
        fine = c4.date_input("Data Fine")
        benzina = st.selectbox("Livello Benzina", ["Pieno", "1/2", "Riserva"])
        note = st.text_area("Note Danni / Caschi consegnati")

    st.subheader("✍️ Firma Digitale")
    canvas = st_canvas(stroke_width=3, stroke_color="#000", background_color="#eee", height=150, key="f_digitale")

    if st.button("💾 SALVA E GENERA"):
        if nome and targa:
            n_f = f"2026-{datetime.datetime.now().strftime('%H%M%S')}"
            
            # Gestione Firma
            img_firma = None
            if canvas.image_data is not None:
                img_firma = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA')

            dati = {
                "nome": nome, "cognome": cognome, "targa": targa, "modello": modello,
                "prezzo": prezzo, "deposito": deposito, "inizio": str(inizio), "fine": str(fine),
                "codice_fiscale": codfisc, "numero_patente": patente, "residenza": residenza,
                "luogo_nascita": luogo, "data_nascita": str(nascita), "benzina": benzina,
                "note_danni": note, "numero_fattura": n_f, "telefono": tel
            }
            
            supabase.table("contratti").insert(dati).execute()
            st.success("✅ Noleggio Salvato!")
            
            st.download_button("📥 Scarica Contratto Firmato", genera_pdf_professionale(dati, "CONTRATTO", img_firma), f"Contratto_{targa}.pdf")
        else:
            st.error("Inserisci Nome e Targa!")

elif menu == "Archivio e Multe":
    st.header("📂 Archivio Contratti")
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"📌 {c['targa']} - {c['cognome']}"):
            col1, col2 = st.columns(2)
            col1.download_button("📜 Contratto", genera_pdf_professionale(c, "CONTRATTO"), f"C_{c['id']}.pdf", key=f"c_{c['id']}")
            col2.download_button("🚨 Modulo Multe", genera_pdf_professionale(c, "MULTE"), f"M_{c['id']}.pdf", key=f"m_{c['id']}")

elif menu == "Incassi":
    st.header("📊 Report Giornaliero")
    res = supabase.table("contratti").select("prezzo, inizio").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.metric("INCASSO TOTALE", f"{df['prezzo'].sum()} €")
        st.write("Dettaglio Noleggi:")
        st.table(df)
