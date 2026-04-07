import streamlit as st
import datetime
import pandas as pd
from supabase import create_client, Client
from fpdf import FPDF
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io

# --- CONNESSIONE ---
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- DATI AZIENDALI FISSI ---
TITOLARE = "BATTAGLIA MARIANNA"
SEDE = "Via Cognole, 5 - 80075 Forio (NA)"
PIVA = "10252601215"
CF = "BTTMNN87A53Z112S"

# --- FUNZIONI PDF ---

def genera_pdf_documento(d, tipo, firma_img=None):
    pdf = FPDF()
    pdf.add_page()
    
    if tipo == "CONTRATTO":
        # INTESTAZIONE
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 8, "BATTAGLIA RENT", ln=True)
        pdf.set_font("Arial", "", 8)
        pdf.cell(0, 4, f"di {TITOLARE} - {SEDE}", ln=True)
        pdf.cell(0, 4, f"P.IVA: {PIVA} - C.F.: {CF}", ln=True)
        pdf.ln(5)
        
        # TITOLO E DATI
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, f"CONTRATTO DI NOLEGGIO N. {d.get('numero_fattura')}", border="TB", ln=True, align="C")
        pdf.ln(3)
        
        pdf.set_font("Arial", "B", 9)
        pdf.cell(0, 6, "DATI DEL CLIENTE", ln=True, fill=False)
        pdf.set_font("Arial", "", 9)
        pdf.multi_cell(0, 5, f"Nome: {d.get('nome')} {d.get('cognome')} | C.F.: {d.get('codice_fiscale')}\n"
                             f"Nato a: {d.get('luogo_nascita')} il {d.get('data_nascita')} | Naz.: {d.get('nazionalita')}\n"
                             f"Residente: {d.get('residenza')}\n"
                             f"Documento: Patente N. {d.get('numero_patente')} | Tel: {d.get('telefono')}")
        
        pdf.ln(3)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(0, 6, "DETTAGLI NOLEGGIO", ln=True)
        pdf.set_font("Arial", "", 9)
        pdf.cell(95, 7, f"Veicolo: {d.get('modello')} Targa: {d.get('targa')}", border=1)
        pdf.cell(95, 7, f"Uscita: {d.get('inizio')} Rientro: {d.get('fine')}", border=1, ln=True)
        pdf.cell(95, 7, f"Benzina: {d.get('benzina')}", border=1)
        pdf.cell(95, 7, f"Deposito: Euro {d.get('deposito')}", border=1, ln=True)
        pdf.multi_cell(0, 5, f"Note Danni/Accessori: {d.get('note_danni')}", border=1)

        # CLAUSOLE E PRIVACY (Come da tua foto)
        pdf.ln(3)
        pdf.set_font("Arial", "B", 7)
        pdf.cell(0, 4, "CONDIZIONI GENERALI E PRIVACY", ln=True)
        pdf.set_font("Arial", "", 6)
        clausole = (
            "IL CLIENTE DICHIARA: di aver ricevuto il mezzo in ottimo stato; di impegnarsi a pagare contravvenzioni e pedaggi; "
            "di essere responsabile per danni a terzi o al mezzo. PRIVACY: Il cliente autorizza il trattamento dei dati (GDPR 679/2016) "
            "per la gestione del contratto e la notifica di eventuali violazioni al Codice della Strada."
        )
        pdf.multi_cell(0, 3, clausole)

        # FIRMA
        pdf.ln(5)
        y_firma = pdf.get_y()
        pdf.set_font("Arial", "B", 9)
        pdf.cell(95, 5, "Il Locatore", 0, 0, "C")
        pdf.cell(95, 5, "Il Cliente (Firma)", 0, 1, "C")
        if firma_img:
            img_io = io.BytesIO()
            firma_img.save(img_io, format='PNG')
            img_io.seek(0)
            pdf.image(img_io, x=135, y=y_firma+5, w=35)
        pdf.cell(95, 10, "______________", 0, 0, "C")
        pdf.cell(95, 10, "______________", 0, 1, "C")

    elif tipo == "MULTE":
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 10, "DICHIARAZIONE SOSTITUTIVA (L. 445/2000)", ln=True, align="C")
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 6, f"Io sottoscritta {TITOLARE}, titolare della ditta BATTAGLIA RENT, dichiaro che il veicolo "
                             f"targato {d.get('targa')} in data {d.get('inizio')} era locato al Sig. "
                             f"{d.get('nome')} {d.get('cognome')}, nato a {d.get('luogo_nascita')} il {d.get('data_nascita')}, "
                             f"residente a {d.get('residenza')}, Patente {d.get('numero_patente')}.")
        pdf.ln(10)
        pdf.cell(0, 5, "Firma del Titolare: ______________________", ln=True, align="R")

    elif tipo == "FATTURA":
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, f"RICEVUTA/FATTURA N. {d.get('numero_fattura')}", ln=True, align="C")
        pdf.ln(5)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, f"Emittente: {TITOLARE} - P.IVA {PIVA}", ln=True)
        pdf.cell(0, 6, f"Cliente: {d.get('nome')} {d.get('cognome')}", ln=True)
        pdf.ln(5)
        pdf.cell(140, 8, "Noleggio Veicolo", 1)
        pdf.cell(40, 8, f"Euro {d.get('prezzo')}", 1, ln=True, align="C")
        pdf.set_font("Arial", "I", 7)
        pdf.cell(0, 5, "Operazione in franchigia da IVA ai sensi della L. 190/2014.", ln=True)

    return bytes(pdf.output())

# --- INTERFACCIA ---
st.sidebar.title("MENU GESTIONALE")
scelta = st.sidebar.selectbox("Vai a:", ["Nuovo Noleggio", "Archivio e Multe", "Report Incassi"])

if scelta == "Nuovo Noleggio":
    st.header("📝 Registrazione Noleggio")
    
    with st.expander("Anagrafica e Documenti", expanded=True):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome")
        cognome = c2.text_input("Cognome")
        residenza = st.text_input("Indirizzo Residenza")
        cod_fisc = c1.text_input("Codice Fiscale")
        patente = c2.text_input("Numero Patente")
        telefono = c1.text_input("Telefono")
        nazion = c2.text_input("Nazionalità", "Italiana")
        luogo_nas = c1.text_input("Luogo Nascita")
        data_nas = c2.date_input("Data Nascita", value=datetime.date(1990,1,1))
        f_fronte = st.file_uploader("Foto Patente", type=['jpg','png'])

    with st.expander("Veicolo e Check-in", expanded=True):
        targa = st.text_input("Targa").upper()
        modello = st.text_input("Modello (es. Liberty 125)")
        c3, c4 = st.columns(2)
        prezzo = c3.number_input("Prezzo (€)", 0.0)
        deposito = c4.number_input("Deposito (€)", 0.0)
        inizio = c3.date_input("Inizio")
        fine = c4.date_input("Fine")
        benzina = st.selectbox("Benzina", ["Pieno", "1/2", "Riserva"])
        note = st.text_area("Note Danni/Caschi")

    st.subheader("✍️ Firma Cliente")
    canvas_result = st_canvas(stroke_width=3, stroke_color="#000", background_color="#eee", height=150, key="firma_noleggio")

    if st.button("💾 SALVA E GENERA"):
        if nome and targa:
            n_fatt = f"{datetime.date.today().year}-{datetime.datetime.now().strftime('%H%M%S')}"
            
            # Recupero Firma
            firma_pil = None
            if canvas_result.image_data is not None:
                firma_pil = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')

            dati = {
                "nome": nome, "cognome": cognome, "targa": targa, "modello": modello,
                "prezzo": prezzo, "deposito": deposito, "inizio": str(inizio), "fine": str(fine),
                "codice_fiscale": cod_fisc, "numero_patente": patente, "residenza": residenza,
                "nazionalita": nazion, "luogo_nascita": luogo_nas, "data_nascita": str(data_nas),
                "benzina": benzina, "note_danni": note, "numero_fattura": n_fatt, "telefono": telefono
            }
            
            supabase.table("contratti").insert(dati).execute()
            st.success("Registrato con successo!")
            
            pdf = genera_pdf_documento(dati, "CONTRATTO", firma_pil)
            st.download_button("📥 Scarica Contratto", pdf, f"Contratto_{targa}.pdf")
        else:
            st.error("Mancano Nome o Targa!")

elif scelta == "Archivio e Multe":
    st.header("📂 Storico Contratti")
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    if res.data:
        for c in res.data:
            with st.expander(f"{c['targa']} - {c['cognome']}"):
                col1, col2, col3 = st.columns(3)
                col1.download_button("📜 Contratto", genera_pdf_documento(c, "CONTRATTO"), f"C_{c['id']}.pdf", key=f"c_{c['id']}")
                col2.download_button("🚨 Modulo Multe", genera_pdf_documento(c, "MULTE"), f"M_{c['id']}.pdf", key=f"m_{c['id']}")
                col3.download_button("💰 Fattura", genera_pdf_documento(c, "FATTURA"), f"F_{c['id']}.pdf", key=f"f_{c['id']}")

elif scelta == "Report Incassi":
    st.header("📊 Report Giornaliero")
    res = supabase.table("contratti").select("inizio, prezzo").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        df['prezzo'] = df['prezzo'].astype(float)
        incasso_tot = df['prezzo'].sum()
        st.metric("Incasso Totale Registrato", f"{incasso_tot} €")
        st.write("Dettaglio per data:")
        st.bar_chart(df.groupby('inizio')['prezzo'].sum())
        
