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
    
    if tipo == "MULTE":
        # Struttura identica alla foto inviata
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 5, "Spett. le", ln=True, align="R")
        pdf.cell(0, 5, "Polizia Locale di ______________________", ln=True, align="R")
        pdf.ln(15)

        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 5, "OGGETTO:   RIFERIMENTO VS. ACCERTAMENTO VIOLAZIONE N. _______________ PROT.", ln=True)
        pdf.cell(0, 5, "           _______________ - COMUNICAZIONE LOCAZIONE VEICOLO", ln=True)
        pdf.ln(10)

        pdf.set_font("Arial", "", 11)
        testo_inizio = (
            "In riferimento al Verbale di accertamento di infrazione al Codice della strada di cui all'oggetto, "
            "con la presente, la sottoscritta BATTAGLIA MARIANNA nata a Berlino (Germania) il 13/01/1987 e "
            "residente in Forio alla Via Cognole n. 5 in qualità di titolare dell'omonima ditta individuale, "
            "C.F.: BTTMNN87A53Z112S e P. IVA: 10252601215"
        )
        pdf.multi_cell(0, 6, testo_inizio)
        pdf.ln(5)

        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 10, "DICHIARA", ln=True, align="C")
        pdf.ln(2)

        pdf.set_font("Arial", "", 11)
        pdf.cell(0, 7, f"Ai sensi della l. 445/2000 che il veicolo modello _______________ targato {d.get('targa')} il", ln=True)
        pdf.cell(0, 7, f"giorno {d.get('inizio')} era concesso in locazione senza conducente al signor:", ln=True)
        pdf.ln(5)

        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 7, f"COGNOME E NOME: {d.get('cognome').upper()} {d.get('nome').upper()}", ln=True)
        pdf.line(pdf.get_x(), pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)

        pdf.cell(0, 7, f"LUOGO E DATA DI NASCITA: {d.get('luogo_nascita')} IL {d.get('data_nascita')}", ln=True)
        pdf.line(pdf.get_x(), pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)

        pdf.cell(0, 7, f"RESIDENZA: ________________________________________________________________", ln=True)
        pdf.line(pdf.get_x(), pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)

        pdf.cell(0, 7, f"IDENTIFICATO A MEZZO: PATENTE N. {d.get('numero_patente')}", ln=True)
        pdf.line(pdf.get_x(), pdf.get_y(), 200, pdf.get_y())
        pdf.ln(8)

        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 5, "La presente al fine di procedere alla rinotifica nei confronti del locatario sopra indicato.", ln=True)
        pdf.ln(5)
        pdf.cell(0, 5, "Si allega", ln=True)
        pdf.cell(0, 5, "   * Copia del contratto di locazione con documento del trasgressore", ln=True)
        pdf.ln(5)
        
        testo_fede = (
            "Ai sensi della L. 445/2000, il sottoscritto dichiara che la copia del contratto che si allega è "
            "conforme all'originale agli atti della ditta."
        )
        pdf.multi_cell(0, 5, testo_fede)
        
        pdf.ln(15)
        pdf.cell(0, 5, "In fede", ln=True, align="R")
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 5, "Marianna Battaglia", ln=True, align="R")

    elif tipo == "FATTURA":
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "BATTAGLIA RENT", ln=True, align="C")
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 5, "di Marianna Battaglia - P.IVA: 10252601215", ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, f"RICEVUTA N. {d.get('numero_fattura')}", ln=True, align="C")
        pdf.set_font("Arial", "", 12)
        pdf.ln(5)
        pdf.cell(0, 10, f"Cliente: {d.get('nome')} {d.get('cognome')}", ln=True)
        pdf.cell(0, 10, f"Veicolo: {d.get('targa')} | Importo: Euro {d.get('prezzo')}", ln=True)

    else: # CONTRATTO
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "CONTRATTO DI NOLEGGIO SCOOTER", ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("Arial", "", 11)
        pdf.multi_cell(0, 7, f"Locatario: {d.get('nome')} {d.get('cognome')}\n"
                             f"Targa: {d.get('targa')} | Inizio: {d.get('inizio')} | Fine: {d.get('fine')}\n"
                             f"Prezzo: Euro {d.get('prezzo')} | Deposito: Euro {d.get('deposito')}")

    return bytes(pdf.output())

# --- RESTO DEL CODICE (FUNZIONI SUPPORTO E INTERFACCIA) ---
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
            # Registro
            oggi = str(datetime.date.today())
            res_reg = supabase.table("registro_giornaliero").select("*").eq("data", oggi).execute()
            if res_reg.data:
                supabase.table("registro_giornaliero").update({"numero_noleggi": res_reg.data[0]["numero_noleggi"] + 1, "totale_incasso": float(res_reg.data[0]["totale_incasso"]) + float(prezzo)}).eq("data", oggi).execute()
            else:
                supabase.table("registro_giornaliero").insert({"data": oggi, "numero_noleggi": 1, "totale_incasso": prezzo}).execute()
            st.success(f"Noleggio Registrato! Fattura: {n_fatt}")

elif menu == "Archivio Storico":
    st.header("📂 Archivio Contratti")
    cerca = st.text_input("🔍 Cerca").lower()
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    if res.data:
        for c in res.data:
            if cerca in f"{c['targa']} {c['cognome']}".lower():
                with st.expander(f"📝 {c['numero_fattura']} | {c['targa']} | {c['cognome']}"):
                    col1, col2, col3 = st.columns(3)
                    col1.download_button("📜 Contratto", genera_pdf_documento(c, "CONTRATTO"), f"Contratto_{c['targa']}.pdf")
                    col2.download_button("💰 Fattura", genera_pdf_documento(c, "FATTURA"), f"Fattura_{c['numero_fattura']}.pdf")
                    col3.download_button("🚨 Modulo Multe", genera_pdf_documento(c, "MULTE"), f"Multe_{c['targa']}.pdf")
                    st.divider()
                    if c.get("url_fronte"): st.link_button("👁️ Foto Patente", c["url_fronte"])
                    msg_wa = urllib.parse.quote(f"Ciao {c['nome']}, ecco i documenti del tuo noleggio scooter {c['targa']}.")
                    st.link_button("🟢 Invia su WhatsApp", f"https://wa.me/{str(c['telefono']).replace(' ','')}?text={msg_wa}")

elif menu == "Registro Giornaliero":
    st.header("📊 Registro Fiscale")
    res = supabase.table("registro_giornaliero").select("*").order("data", desc=True).execute()
    if res.data: st.table(pd.DataFrame(res.data)[['data', 'numero_noleggi', 'totale_incasso']])
