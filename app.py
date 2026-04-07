import streamlit as st
import datetime
import pandas as pd
from supabase import create_client, Client
from fpdf import FPDF
from streamlit_drawable_canvas import st_canvas
import urllib.parse
import PIL.Image
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
    pwd = st.text_input("Password Accesso", type="password")
    if pwd == st.secrets["APP_PASSWORD"]:
        st.session_state.auth = True
        st.rerun()
    st.stop()

# -------------------------
# FUNZIONE PDF CON FIRMA
# -------------------------

def genera_pdf_documento(d, tipo, firma_img=None):
    pdf = FPDF()
    pdf.add_page()
    
    TITOLARE = "BATTAGLIA MARIANNA"
    SEDE = "Via Cognole, 5 - 80075 Forio (NA)"
    PIVA = "10252601215"
    CF = "BTTMNN87A53Z112S"

    if tipo == "CONTRATTO":
        # INTESTAZIONE
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "BATTAGLIA RENT", ln=True, align="L")
        pdf.set_font("Arial", "", 9)
        pdf.cell(0, 4, f"di {TITOLARE}", ln=True)
        pdf.cell(0, 4, f"Sede Legale: {SEDE}", ln=True)
        pdf.cell(0, 4, f"P.IVA: {PIVA} | C.F.: {CF}", ln=True)
        pdf.cell(0, 4, "Tel: +39 333 1234567", ln=True) # Aggiungi tuo tel reale
        
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, f"CONTRATTO DI LOCAZIONE N. {d.get('numero_fattura')}", border="TB", ln=True, align="C")
        pdf.ln(5)

        # DATI CLIENTE
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 7, "DATI DEL LOCATARIO (CLIENTE)", ln=True, fill=False)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 6, f"Nome e Cognome: {d.get('nome')} {d.get('cognome')}\n"
                             f"Nato a: {d.get('luogo_nascita')} il {d.get('data_nascita')} | Nazionalità: {d.get('nazionalita')}\n"
                             f"Cod. Fiscale: {d.get('codice_fiscale')} | Patente N.: {d.get('numero_patente')}\n"
                             f"Residente in: {d.get('residenza', '_______________________________')}\n"
                             f"Telefono: {d.get('telefono')}")
        pdf.ln(5)

        # DATI VEICOLO
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 7, "OGGETTO DELLA LOCAZIONE", ln=True)
        pdf.set_font("Arial", "", 10)
        col_w = 95
        pdf.cell(col_w, 7, f"Veicolo Targa: {d.get('targa')}", border=1)
        pdf.cell(col_w, 7, f"Modello: {d.get('modello', 'Scooter')}", border=1, ln=True)
        pdf.cell(col_w, 7, f"Uscita: {d.get('inizio')}", border=1)
        pdf.cell(col_w, 7, f"Rientro previsto: {d.get('fine')}", border=1, ln=True)
        pdf.ln(5)

        # STATO VEICOLO (Checklist come tua foto)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 7, "STATO DEL VEICOLO E ACCESSORI", ln=True)
        pdf.set_font("Arial", "", 9)
        pdf.cell(60, 6, f"Benzina: {d.get('benzina', '_')}", border=0)
        pdf.cell(60, 6, f"Caschi consegnati: {d.get('caschi', '2')}", border=0)
        pdf.cell(60, 6, f"Bauletto: {d.get('bauletto', 'SI')}", border=0, ln=True)
        pdf.multi_cell(0, 6, f"Danni riscontrati alla consegna: {d.get('note_danni', 'Nessuno')}")
        pdf.ln(5)

        # CLAUSOLE SINTETICHE
        pdf.set_font("Arial", "B", 8)
        pdf.cell(0, 5, "DICHIARAZIONE DI RESPONSABILITA", ln=True)
        pdf.set_font("Arial", "", 7)
        clausole = (
            "Il cliente dichiara di aver visionato il mezzo e di riceverlo in perfetto stato. Si impegna a riconsegnarlo nelle stesse condizioni. "
            "Il cliente è l'unico responsabile per multe e infrazioni al codice della strada. In caso di furto o danni, il cliente risponde secondo le "
            "condizioni generali riportate sul retro del presente contratto."
        )
        pdf.multi_cell(0, 4, clausole)
        
        # --- SEZIONE FIRMA ---
        pdf.ln(10)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(95, 10, "Firma del Locatore", 0, 0, "C")
        pdf.cell(95, 10, "Firma del Locatario (Cliente)", 0, 1, "C")
        
        # Inserimento firma digitale se presente
        if firma_img:
            # Salviamo la firma temporaneamente per il PDF
            temp_path = "temp_signature.png"
            firma_img.save(temp_path)
            # Posizioniamo la firma sopra la riga (x, y, w)
            pdf.image(temp_path, x=135, y=pdf.get_y()-5, w=40)
            
        pdf.cell(95, 10, "__________________", 0, 0, "C")
        pdf.cell(95, 10, "__________________", 0, 1, "C")

    # [Multe e Fattura restano invariate come prima]
    return bytes(pdf.output())

# -------------------------
# INTERFACCIA NUOVO NOLEGGIO
# -------------------------

if menu == "Nuovo Noleggio":
    st.header("📝 Nuovo Contratto Professionale")
    
    with st.form("form_noleggio"):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome")
            cognome = st.text_input("Cognome")
            residenza = st.text_input("Indirizzo Residenza")
            nazionalita = st.text_input("Nazionalità", value="Italiana")
        with col2:
            cod_fisc = st.text_input("Codice Fiscale / ID")
            patente = st.text_input("N. Patente")
            luogo_nas = st.text_input("Luogo di Nascita")
            data_nas = st.date_input("Data di Nascita", value=datetime.date(1990,1,1))
        
        st.divider()
        col3, col4 = st.columns(2)
        with col3:
            targa = st.text_input("Targa").upper()
            prezzo = st.number_input("Prezzo Totale (€)", min_value=0.0)
            inizio = st.date_input("Data Inizio")
        with col4:
            benzina = st.selectbox("Livello Benzina", ["1/1 (Pieno)", "1/2", "Riserva"])
            deposito = st.number_input("Deposito Cauzionale (€)", min_value=0.0)
            fine = st.date_input("Data Fine")
            
        note_danni = st.text_area("Note Danni/Accessori (es: graffio scocca destra, 2 caschi)")

        st.subheader("✍️ Firma Digitale Cliente")
        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 255, 0)", 
            stroke_width=3,
            stroke_color="#000000",
            background_color="#eee",
            height=150,
            key="canvas",
        )

        submit = st.form_submit_button("SALVA E GENERA CONTRATTO")

        if submit:
            # Processiamo la firma
            firma_img = None
            if canvas_result.image_data is not None:
                firma_img = PIL.Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
            
            # Creazione dizionario dati
            n_fatt = genera_numero_fattura()
            dati = {
                "nome": nome, "cognome": cognome, "targa": targa, "prezzo": prezzo,
                "inizio": str(inizio), "fine": str(fine), "numero_fattura": n_fatt,
                "codice_fiscale": cod_fisc, "numero_patente": patente, "nazionalita": nazionalita,
                "luogo_nascita": luogo_nas, "data_nascita": str(data_nas), "residenza": residenza,
                "benzina": benzina, "note_danni": note_danni, "deposito": deposito
            }
            
            # Salvataggio su Supabase
            supabase.table("contratti").insert(dati).execute()
            
            # Generazione PDF con Firma
            pdf_noleggio = genera_pdf_documento(dati, "CONTRATTO", firma_img)
            
            st.success(f"Contratto N. {n_fatt} salvato con successo!")
            st.download_button("📥 Scarica Contratto Firmato", pdf_noleggio, f"Contratto_{targa}.pdf")
