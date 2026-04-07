import streamlit as st
import datetime
import pandas as pd
from supabase import create_client, Client
from fpdf import FPDF
from streamlit_drawable_canvas import st_canvas
import urllib.parse

# -------------------------
# CONFIGURAZIONE & CONNESSIONE
# -------------------------
st.set_page_config(page_title="Battaglia Rent - Sistema Gestionale", layout="centered")

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
# FUNZIONI PDF PROFESSIONALI (Tutte in una)
# -------------------------

def genera_pdf_documento(d, tipo):
    pdf = FPDF()
    pdf.add_page()
    
    # DATI FISCALI FISSI
    TITOLARE = "BATTAGLIA MARIANNA"
    SEDE = "Via Cognole, 5 - 80075 Forio (NA)"
    PIVA = "10252601215"
    CF = "BTTMNN87A53Z112S"
    DURATA = f"dal {d.get('inizio')} al {d.get('fine')}"

    if tipo == "MULTE":
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 5, "Spett. le Polizia Locale di ______________________", ln=True, align="R")
        pdf.ln(10)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 5, "OGGETTO: RIFERIMENTO VS. ACCERTAMENTO VIOLAZIONE N. _______________ PROT.", ln=True)
        pdf.cell(0, 5, f"          {d.get('targa')} - COMUNICAZIONE LOCAZIONE VEICOLO", ln=True)
        pdf.ln(8)
        pdf.set_font("Arial", "", 11)
        pdf.multi_cell(0, 6, f"In riferimento al Verbale in oggetto, la sottoscritta {TITOLARE} nata a Berlino (Germania) il 13/01/1987 e residente in Forio alla {SEDE} in qualità di titolare dell'omonima ditta individuale, C.F.: {CF} e P. IVA: {PIVA}")
        pdf.ln(5)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 10, "DICHIARA", ln=True, align="C")
        pdf.set_font("Arial", "", 11)
        pdf.cell(0, 7, f"Ai sensi della l. 445/2000 che il veicolo targato {d.get('targa')} il giorno {d.get('inizio')}", ln=True)
        pdf.cell(0, 7, "era concesso in locazione senza conducente al signor:", ln=True)
        pdf.ln(5)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, f"COGNOME E NOME: {str(d.get('cognome')).upper()} {str(d.get('nome')).upper()}", border="B", ln=True)
        pdf.cell(0, 8, f"NATO A: {d.get('luogo_nascita')} IL {d.get('data_nascita')}", border="B", ln=True)
        pdf.cell(0, 8, f"NAZIONALITA: {str(d.get('nazionalita')).upper()}", border="B", ln=True)
        pdf.cell(0, 8, f"IDENTIFICATO A MEZZO: PATENTE N. {d.get('numero_patente')}", border="B", ln=True)
        pdf.ln(10)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 5, "Si allega copia del contratto di locazione e del documento del trasgressore. Il sottoscritto dichiara che la copia allegata è conforme all'originale.")
        pdf.ln(10)
        pdf.cell(0, 5, "In fede, Marianna Battaglia", ln=True, align="R")

    elif tipo == "FATTURA":
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "BATTAGLIA RENT", ln=True, align="C")
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 5, f"{TITOLARE} - {SEDE}", ln=True, align="C")
        pdf.cell(0, 5, f"P.IVA: {PIVA} - C.F.: {CF}", ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, f"RICEVUTA FISCALE N. {d.get('numero_fattura')}", ln=True, border="B", align="C")
        pdf.ln(5)
        pdf.set_font("Arial", "", 11)
        pdf.cell(0, 8, f"Data emissione: {datetime.date.today()}", ln=True)
        pdf.cell(0, 8, f"Cliente: {d.get('nome')} {d.get('cognome')}", ln=True)
        pdf.cell(0, 8, f"C.F./ID: {d.get('codice_fiscale', 'N/D')}", ln=True)
        pdf.ln(5)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(140, 10, "DESCRIZIONE", 1)
        pdf.cell(50, 10, "TOTALE", 1, ln=True, align="C")
        pdf.set_font("Arial", "", 11)
        pdf.cell(140, 10, f"Noleggio Scooter {d.get('targa')} ({DURATA})", 1)
        pdf.cell(50, 10, f"Euro {d.get('prezzo')}", 1, ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("Arial", "I", 8)
        pdf.multi_cell(0, 5, "Operazione effettuata ai sensi dell'art. 1, commi da 54 a 89, Legge n. 190/2014. Regime forfettario.")

    elif tipo == "CONTRATTO":
        # Pagina 1: Fronte Contratto
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, f"CONTRATTO DI NOLEGGIO N. {d.get('numero_fattura')}", ln=True, align="C")
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 5, f"{TITOLARE} - {SEDE}", ln=True, align="C")
        pdf.ln(10)
        
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 7, "1. DATI DEL CLIENTE", ln=True, fill=False)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 6, f"Nome/Cognome: {d.get('nome')} {d.get('cognome')}\n"
                             f"Nato a: {d.get('luogo_nascita')} il {d.get('data_nascita')}\n"
                             f"Cod.Fiscale: {d.get('codice_fiscale')} | Patente: {d.get('numero_patente')}\n"
                             f"Tel: {d.get('telefono')} | Nazionalità: {d.get('nazionalita')}")
        pdf.ln(5)
        
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 7, "2. DATI VEICOLO E NOLEGGIO", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 6, f"Veicolo Targa: {d.get('targa')}\n"
                             f"Periodo: {DURATA}\n"
                             f"Prezzo: Euro {d.get('prezzo')} | Deposito: Euro {d.get('deposito')}")
        pdf.ln(5)
        
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 7, "3. CHECK-LIST VEICOLO", ln=True)
        pdf.set_font("Arial", "", 9)
        pdf.cell(0, 6, "- Benzina: [ ] 1/1  [ ] 1/2  [ ] Riserva", ln=True)
        pdf.cell(0, 6, "- Caschi: [ ] 1  [ ] 2 | Bauletto: [ ] SI  [ ] NO", ln=True)
        pdf.ln(10)
        
        pdf.cell(95, 10, "Firma Titolare", 0, 0, "C")
        pdf.cell(95, 10, "Firma Cliente", 0, 1, "C")
        pdf.cell(95, 10, "_______________", 0, 0, "C")
        pdf.cell(95, 10, "_______________", 0, 1, "C")

        # Pagina 2: Condizioni Generali (Retro)
        pdf.add_page()
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 10, "CONDIZIONI GENERALI DI NOLEGGIO", ln=True, align="C")
        pdf.set_font("Arial", "", 7)
        condizioni = (
            "1. REQUISITI: Il locatario deve avere l'età minima prevista per legge...\n"
            "2. STATO VEICOLO: Il veicolo viene consegnato in ottimo stato di manutenzione...\n"
            "3. RESPONSABILITÀ: Il cliente è responsabile per danni, furto e incendio...\n"
            "4. CONTRAVVENZIONI: Tutte le multe elevate durante il noleggio sono a carico del cliente...\n"
            "5. RICONSEGNA: Il veicolo deve essere riconsegnato entro l'orario stabilito...\n"
            "6. FORO COMPETENTE: Per ogni controversia il foro competente è quello di Ischia.\n"
            "\n[... QUI PUOI AGGIUNGERE TUTTI GLI ALTRI PUNTI DELLA TUA FOTO 3 ...]"
        )
        pdf.multi_cell(0, 4, condizioni)

    return bytes(pdf.output())

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

def upload_foto(file, targa, tipo):
    if file is None: return None
    try:
        ext = file.name.split(".")[-1]
        nome_file = f"{tipo}{targa}{datetime.datetime.now().strftime('%H%M%S')}.{ext}"
        supabase.storage.from_("documenti").upload(nome_file, file.getvalue())
        return supabase.storage.from_("documenti").get_public_url(nome_file)
    except: return None

# -------------------------
# INTERFACCIA STREAMLIT
# -------------------------

menu = st.sidebar.radio("Navigazione", ["Nuovo Noleggio", "Archivio Storico", "Registro Giornaliero"])

if menu == "Nuovo Noleggio":
    st.header("🛵 Registrazione Noleggio Professionale")
    with st.form("form_noleggio", clear_on_submit=True):
        st.subheader("👤 Dati Anagrafici")
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome")
        cognome = c2.text_input("Cognome")
        nazionalita = c1.text_input("Nazionalità", value="Italiana")
        cod_fisc = c2.text_input("Codice Fiscale / ID")
        patente = c1.text_input("N. Patente")
        telefono = c2.text_input("Telefono (WhatsApp)")
        luogo_nas = c1.text_input("Luogo di Nascita")
        data_nas = c2.date_input("Data di Nascita", value=datetime.date(1990,1,1))
        
        st.subheader("🚲 Dati Veicolo")
        targa = st.text_input("Targa Scooter").upper()
        c3, c4 = st.columns(2)
        prezzo = c3.number_input("Prezzo Totale (€)", min_value=0.0)
        deposito = c4.number_input("Deposito Cauzionale (€)", min_value=0.0)
        inizio = c3.date_input("Inizio Noleggio")
        fine = c4.date_input("Fine Noleggio")

        st.subheader("📸 Documenti e Firma")
        f_fronte = st.file_uploader("Patente Fronte", type=['jpg', 'png'])
        f_retro = st.file_uploader("Patente Retro", type=['jpg', 'png'])
        canvas = st_canvas(height=150, stroke_width=2, stroke_color="#000", background_color="#eee", key="canvas")
        
        submit = st.form_submit_button("💾 SALVA TUTTO")

        if submit:
            if not nome or not targa:
                st.error("Nome e Targa sono obbligatori!")
            else:
                n_fatt = genera_numero_fattura()
                u_f = upload_foto(f_fronte, targa, "F")
                u_r = upload_foto(f_retro, targa, "R")
                
                dati = {
                    "nome": nome, "cognome": cognome, "telefono": telefono, "targa": targa,
                    "inizio": str(inizio), "fine": str(fine), "prezzo": prezzo, "deposito": deposito,
                    "numero_fattura": n_fatt, "codice_fiscale": cod_fisc, "numero_patente": patente,
                    "luogo_nascita": luogo_nas, "data_nascita": str(data_nas), "nazionalita": nazionalita,
                    "url_fronte": u_f, "url_retro": u_r
                }
                
                supabase.table("contratti").insert(dati).execute()

                # Registro Fiscale
                oggi = str(datetime.date.today())
                res_reg = supabase.table("registro_giornaliero").select("*").eq("data", oggi).execute()
                if res_reg.data:
                    n = res_reg.data[0]["numero_noleggi"] + 1
                    t = float(res_reg.data[0]["totale_incasso"]) + float(prezzo)
                    supabase.table("registro_giornaliero").update({"numero_noleggi": n, "totale_incasso": t}).eq("data", oggi).execute()
                else:
                    supabase.table("registro_giornaliero").insert({"data": oggi, "numero_noleggi": 1, "totale_incasso": prezzo}).execute()

                st.success(f"Noleggio Registrato! Fattura: {n_fatt}")

elif menu == "Archivio Storico":
    st.header("📂 Archivio Contratti")
    cerca = st.text_input("🔍 Cerca per Targa o Cognome").lower()
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    
    if res.data:
        for c in res.data:
            if cerca in f"{c['targa']} {c['cognome']}".lower():
                with st.expander(f"📝 {c['numero_fattura']} | {c['targa']} | {c['cognome']}"):
                    col1, col2, col3 = st.columns(3)
                    col1.download_button("📜 Contratto Cliente", genera_pdf_documento(c, "CONTRATTO"), f"Contratto_{c['targa']}.pdf")
                    col2.download_button("💰 Fattura/Ricevuta", genera_pdf_documento(c, "FATTURA"), f"Fattura_{c['numero_fattura']}.pdf")
                    col3.download_button("🚨 Modulo Multe", genera_pdf_documento(c, "MULTE"), f"Multe_{c['targa']}.pdf")
                    
                    st.divider()
                    if c.get("url_fronte"): st.link_button("👁️ Foto Patente", c["url_fronte"])
                    
                    msg_wa = urllib.parse.quote(f"Ciao {c['nome']}, ecco i documenti del tuo noleggio scooter {c['targa']}. Grazie da Battaglia Rent!")
                    st.link_button("🟢 Invia su WhatsApp", f"https://wa.me/{str(c['telefono']).replace(' ','')}?text={msg_wa}")

elif menu == "Registro Giornaliero":
    st.header("📊 Registro Incassi")
    res = supabase.table("registro_giornaliero").select("*").order("data", desc=True).execute()
    if res.data:
        st.table(pd.DataFrame(res.data)[['data', 'numero_noleggi', 'totale_incasso']])
