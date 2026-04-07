import streamlit as st
import datetime
import pandas as pd
from supabase import create_client, Client
from fpdf import FPDF
import base64
from streamlit_drawable_canvas import st_canvas
import urllib.parse

# -------------------------
# CONFIGURAZIONE & CONNESSIONE
# -------------------------
st.set_page_config(page_title="Battaglia Rent - Ufficiale", layout="centered")

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
# FUNZIONI PDF PROFESSIONALI
# -------------------------

def genera_pdf_documento(d, tipo):
    pdf = FPDF()
    pdf.add_page()
    
    # Intestazione Aziendale
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "BATTAGLIA RENT", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 5, "Noleggio Scooter di Marianna Battaglia", ln=True, align="C")
    pdf.cell(0, 5, "P.IVA: IT12345678901 - Forio (NA)", ln=True, align="C") 
    pdf.ln(10)
    pdf.line(10, 35, 200, 35)
    pdf.ln(5)

    if tipo == "CONTRATTO":
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, f"CONTRATTO DI NOLEGGIO N. {d.get('numero_fattura')}", ln=True, align="C")
        pdf.ln(5)
        
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 7, "DATI DEL LOCATORE E DEL LOCATARIO", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 6, f"Ditta: Battaglia Rent di Marianna Battaglia\nCliente: {d.get('nome')} {d.get('cognome')}\n"
                             f"Nato a: {d.get('luogo_nascita')} il {d.get('data_nascita')} | Nazionalità: {d.get('nazionalita')}\n"
                             f"Cod. Fiscale: {d.get('codice_fiscale')} | Patente: {d.get('numero_patente')}")
        pdf.ln(3)
        
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 7, "DATI DEL NOLEGGIO", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 6, f"Veicolo: Scooter TARGA {d.get('targa')}\nPeriodo: dal {d.get('inizio')} al {d.get('fine')}\n"
                             f"Prezzo Totale: Euro {d.get('prezzo')} | Deposito Cauzionale: Euro {d.get('deposito')}")
        
        pdf.ln(5)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(0, 7, "CONDIZIONI GENERALI DI NOLEGGIO", ln=True)
        pdf.set_font("Arial", "", 8)
        condizioni = (
            "1. Il locatario dichiara di aver ricevuto il veicolo in ottimo stato di manutenzione.\n"
            "2. Il locatario è responsabile per le contravvenzioni al Codice della Strada occorse durante il noleggio.\n"
            "3. In caso di danni al veicolo, il locatario risponde per l'intero importo del ripristino.\n"
            "4. È vietato il sub-noleggio o l'uso del mezzo da parte di persone non indicate nel contratto.\n"
            "5. Privacy: I dati sono trattati secondo il GDPR 679/2016 per fini contrattuali."
        )
        pdf.multi_cell(0, 5, condizioni)
        
        pdf.ln(10)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(95, 10, "Firma Locatore", 0, 0, "C")
        pdf.cell(95, 10, "Firma Locatario", 0, 1, "C")
        pdf.ln(5)
        pdf.cell(95, 10, "__________________", 0, 0, "C")
        pdf.cell(95, 10, "__________________", 0, 1, "C")

    elif tipo == "MULTE":
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "COMUNICAZIONE DATI CONDUCENTE", ln=True, align="C")
        pdf.ln(5)
        pdf.set_font("Arial", "", 11)
        testo_multe = (
            f"La sottoscritta Marianna Battaglia, proprietaria del veicolo TARGA {d.get('targa')}, "
            f"dichiara che in data {d.get('inizio')} il suddetto veicolo era affidato al Sig./ra:\n\n"
            f"NOME: {d.get('nome')} {d.get('cognome')}\n"
            f"NATO A: {d.get('luogo_nascita')} IL: {d.get('data_nascita')}\n"
            f"NAZIONALITÀ: {d.get('nazionalita')}\n"
            f"CODICE FISCALE: {d.get('codice_fiscale')}\n"
            f"PATENTE N.: {d.get('numero_patente')}\n\n"
            f"Si allega copia del contratto e della patente di guida."
        )
        pdf.multi_cell(0, 7, testo_multe)

    elif tipo == "FATTURA":
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, f"RICEVUTA FISCALE N. {d.get('numero_fattura')}", ln=True, align="C")
        pdf.ln(5)
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, f"Data: {datetime.date.today()}", ln=True)
        pdf.cell(0, 10, f"Cliente: {d.get('nome')} {d.get('cognome')}", ln=True)
        pdf.ln(5)
        pdf.cell(150, 10, "Descrizione: Noleggio Scooter", 1)
        pdf.cell(40, 10, f"Euro {d.get('prezzo')}", 1, ln=True, align="C")

    return bytes(pdf.output())

# --- FUNZIONI SUPPORTO (Fattura e Foto) ---
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
    st.header("🛵 Registrazione Noleggio")
    with st.form("form_noleggio", clear_on_submit=True):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome")
        cognome = c2.text_input("Cognome")
        nazionalita = c1.text_input("Nazionalità", value="Italiana")
        cod_fisc = c2.text_input("Codice Fiscale")
        patente = c1.text_input("N. Patente")
        telefono = c2.text_input("Telefono")
        luogo_nas = c1.text_input("Luogo di Nascita")
        data_nas = c2.date_input("Data di Nascita", value=datetime.date(1990,1,1))
        
        targa = st.text_input("Targa Scooter").upper()
        c3, c4 = st.columns(2)
        prezzo = c3.number_input("Prezzo Totale (€)", min_value=0.0)
        deposito = c4.number_input("Deposito (€)", min_value=0.0)
        inizio = c3.date_input("Inizio")
        fine = c4.date_input("Fine")

        f_fronte = st.file_uploader("Patente Fronte", type=['jpg', 'png'])
        f_retro = st.file_uploader("Patente Retro", type=['jpg', 'png'])

        st.write("✍️ Firma Cliente (su schermo):")
        canvas = st_canvas(height=150, stroke_width=2, stroke_color="#000", background_color="#eee", key="canvas")
        
        submit = st.form_submit_button("SALVA E GENERA")

        if submit:
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

            # Aggiornamento Registro
            oggi = str(datetime.date.today())
            res_reg = supabase.table("registro_giornaliero").select("*").eq("data", oggi).execute()
            if res_reg.data:
                supabase.table("registro_giornaliero").update({"numero_noleggi": res_reg.data[0]["numero_noleggi"] + 1, "totale_incasso": float(res_reg.data[0]["totale_incasso"]) + float(prezzo)}).eq("data", oggi).execute()
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
                    col3.download_button("🚨 Modulo Vigilanza", genera_pdf_documento(c, "MULTE"), f"Modulo_Multe_{c['targa']}.pdf")
                    
                    st.divider()
                    if c.get("url_fronte"): st.link_button("👁️ Foto Patente Fronte", c["url_fronte"])
                    if c.get("url_retro"): st.link_button("👁️ Foto Patente Retro", c["url_retro"])
                    
                    # WhatsApp rapido
                    msg_wa = urllib.parse.quote(f"Ciao {c['nome']}, ecco i documenti del tuo noleggio scooter {c['targa']}. Grazie!")
                    st.link_button("🟢 Invia su WhatsApp", f"https://wa.me/{str(c['telefono']).replace(' ','')}?text={msg_wa}")

elif menu == "Registro Giornaliero":
    st.header("📊 Registro Fiscale")
    res = supabase.table("registro_giornaliero").select("*").order("data", desc=True).execute()
    if res.data:
        st.table(pd.DataFrame(res.data)[['data', 'numero_noleggi', 'totale_incasso']])
