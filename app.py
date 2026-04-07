import streamlit as st
import datetime
import pandas as pd
from supabase import create_client, Client
from fpdf import FPDF
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io

# -------------------------
# CONFIGURAZIONE & CONNESSIONE
# -------------------------
st.set_page_config(page_title="Battaglia Rent - Sistema Definitivo", layout="wide")

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
# FUNZIONI PDF
# -------------------------
def genera_pdf_documento(d, tipo, firma_img=None):
    pdf = FPDF()
    pdf.add_page()
    
    TITOLARE = "BATTAGLIA MARIANNA"
    SEDE = "Via Cognole, 5 - 80075 Forio (NA)"
    PIVA = "10252601215"
    CF = "BTTMNN87A53Z112S"

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
        pdf.cell(0, 7, f"Benzina: {d.get('benzina')} | Deposito: Euro {d.get('deposito')}", ln=True)
        pdf.multi_cell(0, 6, f"Note Danni: {d.get('note_danni')}")
        
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

    # [Le altre sezioni Multe/Fattura rimangono uguali]
    return bytes(pdf.output())

# -------------------------
# INTERFACCIA
# -------------------------
menu = st.sidebar.radio("Navigazione", ["Nuovo Noleggio", "Archivio Storico"])

if menu == "Nuovo Noleggio":
    st.header("📝 Registrazione Noleggio")
    
    # Rimosso st.form per evitare errori di invio
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
        height=150, update_statusbar=False, key="canvas_firma_libera"
    )

    if st.button("💾 SALVA E GENERA CONTRATTO"):
        if not nome or not targa:
            st.error("Inserisci Nome e Targa!")
        else:
            # Recupero firma
            firma_pil = None
            if canvas_result.image_data is not None:
                firma_pil = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')

            # Genera numero fattura (logica semplificata per velocità)
            n_fatt = f"{datetime.date.today().year}-{datetime.datetime.now().strftime('%H%M%S')}"
            
            dati = {
                "nome": nome, "cognome": cognome, "targa": targa, "modello": modello,
                "prezzo": prezzo, "deposito": deposito, "inizio": str(inizio), "fine": str(fine),
                "codice_fiscale": cod_fisc, "numero_patente": patente, "residenza": residenza,
                "nazionalita": nazionalita, "luogo_nascita": luogo_nas, "data_nascita": str(data_nas),
                "benzina": benzina, "note_danni": note_danni, "numero_fattura": n_fatt
            }
            
            try:
                supabase.table("contratti").insert(dati).execute()
                st.success("Dati salvati con successo!")
                
                pdf_firmato = genera_pdf_documento(dati, "CONTRATTO", firma_pil)
                st.download_button("📥 Scarica Contratto Firmato", pdf_firmato, f"Contratto_{targa}.pdf")
            except Exception as e:
                st.error(f"Errore database: {e}")

elif menu == "Archivio Storico":
    st.header("📂 Archivio")
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    if res.data:
        for c in res.data:
            with st.expander(f"{c['targa']} - {c['cognome']}"):
                st.write(f"Fattura: {c['numero_fattura']}")
                st.download_button("📜 Scarica Contratto", genera_pdf_documento(c, "CONTRATTO"), f"Contratto_{c['targa']}.pdf", key=c['id'])
