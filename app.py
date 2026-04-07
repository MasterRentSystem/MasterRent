import streamlit as st
import datetime
import pandas as pd
from supabase import create_client, Client
from fpdf import FPDF
import base64
from streamlit_drawable_canvas import st_canvas
import urllib.parse
import numpy as np
from PIL import Image
import io

# -------------------------
# CONFIGURAZIONE PAGINA
# -------------------------
st.set_page_config(
    page_title="Battaglia Rent - Sistema Ufficiale",
    layout="centered"
)

# -------------------------
# CONNESSIONE SUPABASE
# -------------------------
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# -------------------------
# LOGIN
# -------------------------
def check_password():
    if "auth" not in st.session_state:
        st.session_state.auth = False
    if not st.session_state.auth:
        st.title("🔒 Accesso Riservato")
        pwd = st.text_input("Inserisci Password", type="password")
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state.auth = True
            st.rerun()
        elif pwd != "":
            st.error("Password errata")
        return False
    return True

if not check_password():
    st.stop()

# -------------------------
# UTILITY PDF
# -------------------------
def genera_pdf(d, tipo):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)

    def clean(t):
        return str(t).encode("latin-1", "replace").decode("latin-1").replace("?", "-")

    if tipo == "MULTE":
        pdf.cell(200, 10, "DICHIARAZIONE DATI CONDUCENTE", ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("Arial", "", 11)
        testo = (
            f"In data {d.get('inizio')} il veicolo targa {d.get('targa')} "
            f"era affidato a: {d.get('nome')} {d.get('cognome')}, nato a {d.get('luogo_nascita')} "
            f"il {d.get('data_nascita')}, residente in {d.get('residenza')}, "
            f"patente n. {d.get('numero_patente')}."
        )
        pdf.multi_cell(0, 10, clean(testo))

    elif tipo == "FATTURA":
        pdf.cell(200, 10, clean(f"RICEVUTA N. {d.get('numero_fattura')}"), ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, clean(f"Cliente: {d.get('nome')} {d.get('cognome')}"), ln=True)
        pdf.cell(0, 10, clean(f"Importo: Euro {d.get('prezzo')}"), ln=True)

    else: # CONTRATTO
        pdf.cell(200, 10, "CONTRATTO DI NOLEGGIO", ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("Arial", "", 11)
        testo = (
            f"Locatario: {d.get('nome')} {d.get('cognome')}\n"
            f"Targa: {d.get('targa')}\n"
            f"Dal: {d.get('inizio')} Al: {d.get('fine')}\n"
            f"Prezzo: Euro {d.get('prezzo')}\n"
            f"Deposito: Euro {d.get('deposito')}"
        )
        pdf.multi_cell(0, 10, clean(testo))
        
        if d.get("firma"):
            try:
                base64_str = d.get("firma").split(",")[-1]
                img_data = base64.b64decode(base64_str)
                pdf.image(io.BytesIO(img_data), x=130, y=pdf.get_y()+5, w=50)
            except: pass

    return bytes(pdf.output(dest='S'), encoding='latin-1', errors='ignore')

def get_next_fattura():
    year = datetime.date.today().year
    try:
        res = supabase.table("contratti").select("numero_fattura").filter("numero_fattura", "ilike", f"{year}-%").order("numero_fattura", desc=True).limit(1).execute()
        if not res.data: return f"{year}-001"
        last_num = int(res.data[0]["numero_fattura"].split("-")[1])
        return f"{year}-{str(last_num + 1).zfill(3)}"
    except: return f"{year}-001"

def aggiorna_registro(prezzo):
    oggi = str(datetime.date.today())
    try:
        res = supabase.table("registro_giornaliero").select("*").eq("data", oggi).execute()
        if res.data:
            nuovo_n = res.data[0]["numero_noleggi"] + 1
            nuovo_t = float(res.data[0]["totale_incasso"]) + float(prezzo)
            supabase.table("registro_giornaliero").update({"numero_noleggi": nuovo_n, "totale_incasso": nuovo_t}).eq("data", oggi).execute()
        else:
            supabase.table("registro_giornaliero").insert({"data": oggi, "numero_noleggi": 1, "totale_incasso": prezzo}).execute()
    except: pass

# -------------------------
# MENU
# -------------------------
menu = st.sidebar.radio("Menu", ["Nuovo Noleggio", "Archivio Storico", "Registro Giornaliero", "Backup"])

# -------------------------
# NUOVO NOLEGGIO
# -------------------------
if menu == "Nuovo Noleggio":
    st.header("🛵 Nuovo Noleggio")
    with st.form("form_noleggio", clear_on_submit=True):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Nome")
        cognome = col2.text_input("Cognome")
        luogo_nas = col1.text_input("Luogo di Nascita")
        data_nas = col2.text_input("Data di Nascita")
        residenza = col1.text_input("Residenza")
        cod_fisc = col2.text_input("Codice Fiscale")
        patente = col1.text_input("N. Patente")
        telefono = col2.text_input("Telefono")
        targa = col1.text_input("Targa").upper()
        prezzo = col2.number_input("Prezzo", min_value=0.0)
        deposito = col1.number_input("Deposito", min_value=0.0)
        inizio = col1.date_input("Inizio")
        fine = col2.date_input("Fine")
        st.write("Firma Cliente")
        canvas = st_canvas(height=150, stroke_width=2, stroke_color="#000", background_color="#eee", key="canvas")
        submit = st.form_submit_button("SALVA")

        if submit:
            if not nome or not targa:
                st.error("Nome e Targa obbligatori")
            else:
                try:
                    firma_b64 = ""
                    if canvas.image_data is not None:
                        img = Image.fromarray(canvas.image_data.astype(np.uint8))
                        buffered = io.BytesIO()
                        img.save(buffered, format="PNG")
                        firma_b64 = "data:image/png;base64," + base64.b64encode(buffered.getvalue()).decode()
                    
                    n_fatt = get_next_fattura()
                    dati = {
                        "nome": nome, "cognome": cognome, "luogo_nascita": luogo_nas,
                        "data_nascita": data_nas, "residenza": residenza, "codice_fiscale": cod_fisc,
                        "numero_patente": patente, "telefono": telefono, "targa": targa,
                        "inizio": inizio.isoformat(), "fine": fine.isoformat(), "prezzo": prezzo,
                        "deposito": deposito, "numero_fattura": n_fatt, "firma": firma_b64
                    }
                    supabase.table("contratti").insert(dati).execute()
                    aggiorna_registro(prezzo)
                    st.success(f"Salvato! Fattura {n_fatt}")
                except Exception as e:
                    st.error(f"Errore: {e}")

# -------------------------
# ARCHIVIO
# -------------------------
elif menu == "Archivio Storico":
    st.header("📂 Archivio")
    cerca = st.text_input("Cerca").lower()
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    if res.data:
        for c in res.data:
            if cerca in f"{c['targa']} {c['cognome']}".lower():
                with st.expander(f"{c['numero_fattura']} - {c['targa']} - {c['cognome']}"):
                    col1, col2, col3 = st.columns(3)
                    col1.download_button("📜 Contratto", genera_pdf(c, "CONTRATTO"), f"Cont_{c['id']}.pdf", "application/pdf")
                    col2.download_button("💰 Ricevuta", genera_pdf(c, "FATTURA"), f"Ric_{c['id']}.pdf", "application/pdf")
                    col3.download_button("🚨 Multe", genera_pdf(c, "MULTE"), f"Multe_{c['id']}.pdf", "application/pdf")

# -------------------------
# REGISTRO
# -------------------------
elif menu == "Registro Giornaliero":
    st.header("📊 Registro")
    res = supabase.table("registro_giornaliero").select("*").order("data", desc=True).execute()
    if res.data:
        st.table(pd.DataFrame(res.data))

# -------------------------
# BACKUP
# -------------------------
elif menu == "Backup":
    st.header("💾 Backup")
    if st.button("Genera Backup CSV"):
        res = supabase.table("contratti").select("*").execute()
        st.download_button("Scarica CSV", pd.DataFrame(res.data).to_csv(index=False).encode("utf-8"), "backup.csv", "text/csv")
        
