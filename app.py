import streamlit as st
import datetime
import pandas as pd
from supabase import create_client, Client
from fpdf import FPDF
from streamlit_drawable_canvas import st_canvas
import urllib.parse
from PIL import Image
import io

# -------------------------
# CONFIGURAZIONE & CONNESSIONE
# -------------------------
st.set_page_config(page_title="Battaglia Rent - Ufficiale", layout="wide")

url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- LOGIN ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Accesso Riservato")
    pwd = st.text_input("Inserisci la Password", type="password")
    if st.button("Entra"):
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Password errata")
    st.stop()

# -------------------------
# FUNZIONI SUPPORTO
# -------------------------
def genera_numero_fattura():
    anno = datetime.date.today().year
    try:
        res = supabase.table("contratti").select("numero_fattura").filter("numero_fattura", "ilike", f"{anno}-%").order("numero_fattura", desc=True).limit(1).execute()
        if not res.data: return f"{anno}-001"
        ultimo = int(res.data[0]["numero_fattura"].split("-")[1])
        return f"{anno}-{str(ultimo + 1).zfill(3)}"
    except: return f"{anno}-001"

# -------------------------
# GENERAZIONE PDF PROFESSIONALI
# -------------------------
def genera_pdf_documento(d, tipo, firma_img=None):
    pdf = FPDF()
    pdf.add_page()
    
    TITOLARE = "BATTAGLIA MARIANNA"
    SEDE = "Via Cognole, 5 - 80075 Forio (NA)"
    PIVA = "10252601215"
    CF = "BTTMNN87A53Z112S"
    DURATA = f"dal {d.get('inizio')} al {d.get('fine')}"

    if tipo == "CONTRATTO":
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "BATTAGLIA RENT", ln=True)
        pdf.set_font("Arial", "", 9)
        pdf.cell(0, 4, f"di {TITOLARE} | P.IVA: {PIVA} | C.F.: {CF}", ln=True)
        pdf.cell(0, 4, f"Sede: {SEDE}", ln=True)
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, f"CONTRATTO DI LOCAZIONE N. {d.get('numero_fattura')}", border="TB", ln=True, align="C")
        
        pdf.ln(5)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 7, "DATI DEL LOCATARIO", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 6, f"Nome/Cognome: {d.get('nome')} {d.get('cognome')}\n"
                             f"Nato a: {d.get('luogo_nascita')} il {d.get('data_nascita')}\n"
                             f"Residente: {d.get('residenza')} | C.F.: {d.get('codice_fiscale')}\n"
                             f"Patente: {d.get('numero_patente')} | Tel: {d.get('telefono')}")
        
        pdf.ln(5)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 7, "OGGETTO DEL NOLEGGIO", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.cell(95, 8, f"Veicolo: {d.get('modello')} Targa: {d.get('targa')}", border=1)
        pdf.cell(95, 8, f"Uscita: {d.get('inizio')} Rientro: {d.get('fine')}", border=1, ln=True)
        
        pdf.ln(5)
        pdf.cell(0, 7, f"Benzina alla consegna: {d.get('benzina')} | Deposito: Euro {d.get('deposito')}", ln=True)
        pdf.multi_cell(0, 6, f"Note Danni/Accessori: {d.get('note_danni')}")
        
        pdf.ln(15)
        curr_y = pdf.get_y()
        pdf.cell(95, 10, "Firma Titolare", 0, 0, "C")
        pdf.cell(95, 10, "Firma Cliente", 0, 1, "C")
        
        if firma_img:
            img_io = io.BytesIO()
            firma_img.save(img_io, format='PNG')
            img_io.seek(0)
            pdf.image(img_io, x=135, y=curr_y+10, w=40)
        
        pdf.cell(95, 10, "__________________", 0, 0, "C")
        pdf.cell(95, 10, "__________________", 0, 1, "C")

    elif tipo == "MULTE":
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 5, "Spett. le Polizia Locale di ______________________", ln=True, align="R")
        pdf.ln(10)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 10, "DICHIARAZIONE DATI CONDUCENTE", ln=True, align="C")
        pdf.set_font("Arial", "", 11)
        pdf.multi_cell(0, 6, f"La sottoscritta {TITOLARE}, titolare di Battaglia Rent, proprietaria del veicolo {d.get('targa')}, dichiara che in data {d.get('inizio')} il mezzo era affidato a:")
        pdf.ln(5)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, f"NOME/COGNOME: {str(d.get('nome')).upper()} {str(d.get('cognome')).upper()}", border="B", ln=True)
        pdf.cell(0, 8, f"NATO A: {d.get('luogo_nascita')} IL {d.get('data_nascita')}", border="B", ln=True)
        pdf.cell(0, 8, f"PATENTE N: {d.get('numero_patente')}", border="B", ln=True)
        pdf.ln(10)
        pdf.cell(0, 5, "In fede, Marianna Battaglia", ln=True, align="R")

    elif tipo == "FATTURA":
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, f"RICEVUTA FISCALE N. {d.get('numero_fattura')}", ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("Arial", "", 11)
        pdf.cell(0, 7, f"Emittente: {TITOLARE} - P.IVA {PIVA}", ln=True)
        pdf.cell(0, 7, f"Cliente: {d.get('nome')} {d.get('cognome')}", ln=True)
        pdf.ln(10)
        pdf.cell(140, 10, "Descrizione: Noleggio Scooter", 1)
        pdf.cell(40, 10, f"Euro {d.get('prezzo')}", 1, ln=True, align="C")

    return bytes(pdf.output())

# -------------------------
# NAVIGAZIONE & INTERFACCIA
# -------------------------
menu = st.sidebar.radio("Navigazione", ["Nuovo Noleggio", "Archivio Storico", "Registro Giornaliero"])

if menu == "Nuovo Noleggio":
    st.header("📝 Registrazione Noleggio Professionale")
    
    # TUTTO DEVE STARE DENTRO IL FORM
    with st.form("noleggio_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome")
        cognome = c2.text_input("Cognome")
        residenza = c1.text_input("Indirizzo Residenza")
        nazionalita = c2.text_input("Nazionalità", value="Italiana")
        
        c3, c4 = st.columns(2)
        cod_fisc = c3.text_input("Codice Fiscale")
        patente = c4.text_input("N. Patente")
        luogo_nas = c3.text_input("Luogo di Nascita")
        data_nas = c4.date_input("Data di Nascita", value=datetime.date(1990,1,1))
        
        st.divider()
        targa = st.text_input("Targa").upper()
        modello = st.text_input("Modello Scooter")
        
        c5, c6 = st.columns(2)
        prezzo = c5.number_input("Prezzo Totale (€)", min_value=0.0)
        deposito = c6.number_input("Deposito (€)", min_value=0.0)
        inizio = c5.date_input("Inizio Noleggio")
        fine = c6.date_input("Fine Noleggio")
        
        benzina = st.selectbox("Livello Benzina", ["Pieno", "1/2", "Riserva"])
        note_danni = st.text_area("Note Danni e Accessori")

        st.subheader("✍️ Firma Digitale Cliente")
        canvas_result = st_canvas(
            stroke_width=3, stroke_color="#000", background_color="#eee",
            height=150, update_statusbar=False, key="canvas_firma"
        )

        # IL PULSANTE DI INVIO DEVE ESSERE L'ULTIMO DENTRO IL FORM
        submit = st.form_submit_button("💾 SALVA E GENERA CONTRATTO")

    # LOGICA DOPO L'INVIO (FUORI DAL FORM)
    if submit:
        if not nome or not targa:
            st.error("Nome e Targa sono obbligatori!")
        else:
            n_fatt = genera_numero_fattura()
            
            # Recupero immagine firma
            firma_pil = None
            if canvas_result.image_data is not None:
                firma_pil = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')

            dati = {
                "nome": nome, "cognome": cognome, "targa": targa, "modello": modello,
                "prezzo": prezzo, "deposito": deposito, "inizio": str(inizio), "fine": str(fine),
                "codice_fiscale": cod_fisc, "numero_patente": patente, "residenza": residenza,
                "nazionalita": nazionalita, "luogo_nascita": luogo_nas, "data_nascita": str(data_nas),
                "benzina": benzina, "note_danni": note_danni, "numero_fattura": n_fatt
            }
            
            # Salvataggio Database
            supabase.table("contratti").insert(dati).execute()
            
            st.success(f"Noleggio registrato! Fattura: {n_fatt}")
            
            # Download immediato
            pdf_firmato = genera_pdf_documento(dati, "CONTRATTO", firma_pil)
            st.download_button("📥 Scarica Contratto Firmato", pdf_firmato, f"Contratto_{targa}.pdf")

elif menu == "Archivio Storico":
    st.header("📂 Archivio Noleggi")
    cerca = st.text_input("Cerca per targa o cognome").lower()
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    
    if res.data:
        for c in res.data:
            if cerca in f"{c['targa']} {c['cognome']}".lower():
                with st.expander(f"📝 {c['numero_fattura']} | {c['targa']} | {c['cognome']}"):
                    col1, col2, col3 = st.columns(3)
                    col1.download_button("📜 Contratto", genera_pdf_documento(c, "CONTRATTO"), f"Contratto_{c['targa']}.pdf")
                    col2.download_button("💰 Fattura", genera_pdf_documento(c, "FATTURA"), f"Fattura_{c['numero_fattura']}.pdf")
                    col3.download_button("🚨 Modulo Multe", genera_pdf_documento(c, "MULTE"), f"Multe_{c['targa']}.pdf")

elif menu == "Registro Giornaliero":
    st.header("📊 Registro Incassi")
    res = supabase.table("contratti").select("inizio, prezzo").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.write("Totale incassi registrati:")
        st.dataframe(df)
