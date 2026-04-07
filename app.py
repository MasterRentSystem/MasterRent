import streamlit as st
import datetime
import pandas as pd
from supabase import create_client, Client
from fpdf import FPDF
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io

# 1. CONNESSIONE & CONFIGURAZIONE
st.set_page_config(page_title="Battaglia Rent - Gestionale Ufficiale", layout="wide")
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# 2. PROTEZIONE CON PASSWORD
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Accesso Battaglia Rent")
    pwd = st.text_input("Inserisci Password", type="password")
    if st.button("Accedi"):
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Password Errata")
    st.stop()

# 3. DATI AZIENDALI FISSI
TITOLARE = "BATTAGLIA MARIANNA"
SEDE = "Via Cognole, 5 - 80075 Forio (NA)"
PIVA = "10252601215"
CF = "BTTMNN87A53Z112S"

# -------------------------
# FUNZIONI PDF (3 MODELLI DISTINTI)
# -------------------------

def genera_pdf(d, tipo, firma_img=None):
    pdf = FPDF()
    pdf.add_page()
    
    # --- MODELLO 1: CONTRATTO COMPLETO CON CLAUSE E PRIVACY ---
    if tipo == "CONTRATTO":
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "BATTAGLIA RENT - CONTRATTO DI LOCAZIONE", ln=True, align="C")
        pdf.set_font("Arial", "", 8)
        pdf.cell(0, 4, f"di {TITOLARE} - {SEDE} - P.IVA: {PIVA} - C.F.: {CF}", ln=True, align="C")
        pdf.ln(5)
        
        # Box Dati Cliente
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 8, "DATI DEL LOCATARIO", border="B", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 6, f"Nome/Cognome: {d.get('nome')} {d.get('cognome')}\n"
                             f"Nato a: {d.get('luogo_nascita')} il {d.get('data_nascita')} | Naz.: {d.get('nazionalita')}\n"
                             f"Residente: {d.get('residenza')} | C.F.: {d.get('codice_fiscale')}\n"
                             f"Patente N: {d.get('numero_patente')} | Tel: {d.get('telefono')}")
        
        # Box Veicolo e Stato
        pdf.ln(3)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 8, "DETTAGLI VEICOLO E CONSEGNA", border="B", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.cell(95, 8, f"Veicolo/Modello: {d.get('modello')}", border=1)
        pdf.cell(95, 8, f"Targa: {d.get('targa')}", border=1, ln=True)
        pdf.cell(95, 8, f"Uscita: {d.get('inizio')}", border=1)
        pdf.cell(95, 8, f"Rientro: {d.get('fine')}", border=1, ln=True)
        pdf.cell(95, 8, f"Benzina: {d.get('benzina')}", border=1)
        pdf.cell(95, 8, f"Deposito: Euro {d.get('deposito')}", border=1, ln=True)
        pdf.multi_cell(0, 6, f"Note Danni/Caschi: {d.get('note_danni')}", border=1)

        # CLAUSOLE PRIVACY E RESPONSABILITA (Box Clausole)
        pdf.ln(4)
        pdf.set_font("Arial", "B", 7)
        pdf.cell(0, 5, "INFORMATIVA PRIVACY E CONDIZIONI GENERALI", ln=True)
        pdf.set_font("Arial", "", 6)
        clausole = (
            "1. Il locatario dichiara di aver visionato il mezzo e di trovarlo in perfetto stato. 2. Responsabilità: Il cliente è responsabile di ogni danno, "
            "furto o incendio. 3. Multe: Le sanzioni elevate durante il noleggio sono a carico del cliente. 4. Privacy: Ai sensi del GDPR 2016/679, "
            "il cliente autorizza il trattamento dei dati personali per fini contrattuali e per la notifica di violazioni al codice della strada."
        )
        pdf.multi_cell(0, 3, clausole)

        # Firma Digitale
        pdf.ln(8)
        y_firma = pdf.get_y()
        pdf.set_font("Arial", "B", 9)
        pdf.cell(95, 5, "Firma Locatore", 0, 0, "C")
        pdf.cell(95, 5, "Firma Locatario (Cliente)", 0, 1, "C")
        if firma_img:
            img_io = io.BytesIO()
            firma_img.save(img_io, format='PNG')
            img_io.seek(0)
            pdf.image(img_io, x=130, y=y_firma+5, w=40)
        pdf.cell(95, 10, "______________", 0, 0, "C")
        pdf.cell(95, 10, "______________", 0, 1, "C")

    # --- MODELLO 2: DICHIARAZIONE PER MULTE (Vipalazione/Accertamento) ---
    elif tipo == "MULTE":
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "COMUNICAZIONE DATI CONDUCENTE (L. 445/2000)", ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("Arial", "", 11)
        testo_multa = (
            f"La sottoscritta {TITOLARE}, in qualità di titolare della ditta BATTAGLIA RENT, "
            f"proprietaria del veicolo targa {d.get('targa')}, comunica che in data {d.get('inizio')} "
            f"il suddetto mezzo era concesso in locazione al Sig./Sig.ra:\n\n"
            f"COGNOME E NOME: {str(d.get('cognome')).upper()} {str(d.get('nome')).upper()}\n"
            f"NATO A: {d.get('luogo_nascita')} IL {d.get('data_nascita')}\n"
            f"RESIDENTE IN: {d.get('residenza')}\n"
            f"PATENTE N: {d.get('numero_patente')}\n"
            f"CODICE FISCALE: {d.get('codice_fiscale')}\n\n"
            "Si allega copia del contratto di noleggio e del documento di identità."
        )
        pdf.multi_cell(0, 7, testo_multa)
        pdf.ln(20)
        pdf.cell(0, 10, f"Forio, {datetime.date.today()}", 0, 0)
        pdf.cell(0, 10, "Firma del Titolare: __________________", 0, 1, "R")

    # --- MODELLO 3: FATTURA / RICEVUTA FISCALE ---
    elif tipo == "FATTURA":
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, f"RICEVUTA FISCALE N. {d.get('numero_fattura', '2026-X')}", ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 5, f"EMITTENTE: {TITOLARE}", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 5, f"P.IVA: {PIVA} - C.F.: {CF} - {SEDE}", ln=True)
        pdf.ln(10)
        pdf.cell(0, 5, f"CLIENTE: {d.get('nome')} {d.get('cognome')}", ln=True)
        pdf.ln(10)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(140, 10, "DESCRIZIONE PRESTAZIONE", 1, 0, "L", True)
        pdf.cell(50, 10, "TOTALE", 1, 1, "C", True)
        pdf.cell(140, 15, f"Noleggio Scooter Targa {d.get('targa')} dal {d.get('inizio')} al {d.get('fine')}", 1)
        pdf.cell(50, 15, f"Euro {d.get('prezzo')}", 1, 1, "C")
        pdf.ln(10)
        pdf.set_font("Arial", "I", 8)
        pdf.cell(0, 5, "Operazione in franchigia da IVA ai sensi della L. 190/2014 regime forfettario.", ln=True)

    return bytes(pdf.output())

# -------------------------
# INTERFACCIA APP
# -------------------------
menu = st.sidebar.radio("MENU BATTAGLIA RENT", ["Nuovo Noleggio", "Archivio Contratti", "Report Giornaliero"])

if menu == "Nuovo Noleggio":
    st.header("📝 Registrazione Nuovo Cliente")
    
    # Sezione 1: Anagrafica
    c1, c2 = st.columns(2)
    nome = c1.text_input("Nome")
    cognome = c2.text_input("Cognome")
    residenza = st.text_input("Indirizzo Residenza (Via, Città)")
    c3, c4 = st.columns(2)
    cod_fisc = c3.text_input("Codice Fiscale")
    patente = c4.text_input("N. Patente")
    nazionalita = c3.text_input("Nazionalità", "Italiana")
    telefono = c4.text_input("Telefono WhatsApp")
    luogo_nas = c3.text_input("Luogo di Nascita")
    data_nas = c4.date_input("Data di Nascita", value=datetime.date(1990,1,1))
    
    st.divider()
    
    # Sezione 2: Scooter
    targa = st.text_input("TARGA SCOOTER").upper()
    modello = st.text_input("Modello (es. Piaggio Liberty 125)")
    c5, c6 = st.columns(2)
    prezzo = c5.number_input("Prezzo Totale (€)", 0.0)
    deposito = c6.number_input("Deposito (€)", 0.0)
    inizio = c5.date_input("Inizio Noleggio")
    fine = c6.date_input("Fine Noleggio")
    benzina = st.selectbox("Livello Benzina", ["Pieno", "1/2", "Riserva"])
    note_danni = st.text_area("Note Danni/Caschi/Accessori")

    st.subheader("✍️ Firma Digitale Cliente")
    canvas_result = st_canvas(stroke_width=3, stroke_color="#000", background_color="#eee", height=150, key="firma_finale")

    if st.button("💾 SALVA NOLEGGIO E GENERA DOCUMENTI"):
        if nome and targa:
            # Creazione numero fattura univoco
            n_fatt = f"2026-{datetime.datetime.now().strftime('%H%M%S')}"
            
            firma_pil = None
            if canvas_result.image_data is not None:
                firma_pil = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')

            dati = {
                "nome": nome, "cognome": cognome, "targa": targa, "modello": modello,
                "prezzo": prezzo, "deposito": deposito, "inizio": str(inizio), "fine": str(fine),
                "codice_fiscale": cod_fisc, "numero_patente": patente, "residenza": residenza,
                "nazionalita": nazionalita, "luogo_nascita": luogo_nas, "data_nascita": str(data_nas),
                "benzina": benzina, "note_danni": note_danni, "numero_fattura": n_fatt, "telefono": telefono
            }
            
            supabase.table("contratti").insert(dati).execute()
            st.success(f"Noleggio registrato correttamente per {cognome}!")
            
            # Generazione PDF istantanea
            st.download_button("📥 Scarica Contratto", genera_pdf(dati, "CONTRATTO", firma_pil), f"Contratto_{targa}.pdf")
            st.download_button("💰 Scarica Fattura", genera_pdf(dati, "FATTURA"), f"Fattura_{n_fatt}.pdf")
        else:
            st.error("Inserisci almeno Nome e Targa!")

elif menu == "Archivio Contratti":
    st.header("📂 Archivio Storico")
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    if res.data:
        for c in res.data:
            with st.expander(f"📌 {c['targa']} - {c['cognome']} ({c['inizio']})"):
                st.write(f"Fattura: {c['numero_fattura']} | Totale: {c['prezzo']} €")
                colA, colB, colC = st.columns(3)
                colA.download_button("📜 Contratto", genera_pdf(c, "CONTRATTO"), f"Contr_{c['id']}.pdf", key=f"c{c['id']}")
                colB.download_button("🚨 Modulo Multe", genera_pdf(c, "MULTE"), f"Mult_{c['id']}.pdf", key=f"m{c['id']}")
                colC.download_button("💰 Fattura", genera_pdf(c, "FATTURA"), f"Fatt_{c['id']}.pdf", key=f"f{c['id']}")

elif menu == "Report Giornaliero":
    st.header("📊 Report Incassi")
    res = supabase.table("contratti").select("inizio, prezzo").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        df['prezzo'] = df['prezzo'].astype(float)
        totale = df['prezzo'].sum()
        st.metric("INCASSO TOTALE 2026", f"{totale} €")
        st.subheader("Incassi per Giorno")
        st.bar_chart(df.groupby('inizio')['prezzo'].sum())
