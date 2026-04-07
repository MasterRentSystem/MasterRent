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
st.set_page_config(page_title="Battaglia Rent - Sistema Ufficiale", layout="wide")

url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

def safe_text(text):
    if text is None: return ""
    text = str(text).replace("€", "EUR").replace("’", "'")
    return text.encode("latin-1", "replace").decode("latin-1")

# -------------------------
# LOGICA DATABASE
# -------------------------
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
# GENERAZIONE PDF
# -------------------------
def genera_pdf(d, tipo):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 8, "BATTAGLIA MARIANNA - BATTAGLIA RENT", ln=True)
    pdf.set_font("Arial", "", 9)
    pdf.cell(0, 5, "Via Cognole, 5 - 80075 Forio (NA) | P.IVA 10252601215", ln=True)
    pdf.ln(10)

    if tipo == "MULTE":
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "DICHIARAZIONE DATI CONDUCENTE (L. 445/2000)", ln=True, align="C", border="B")
        pdf.ln(10)
        pdf.set_font("Arial", "", 11)
        testo = f"La sottoscritta Marianna Battaglia dichiara che in data {d.get('inizio')} il veicolo targa {d.get('targa')} era affidato a:\n\n" \
                f"Conducente: {d.get('nome')} {d.get('cognome')}\n" \
                f"Nato a: {d.get('luogo_nascita')} il {d.get('data_nascita')}\n" \
                f"Patente n.: {d.get('numero_patente')}\n" \
                f"Codice Fiscale: {d.get('codice_fiscale')}\n" \
                f"Residenza: {d.get('residenza')}"
        pdf.multi_cell(0, 8, safe_text(testo))

    elif tipo == "FATTURA":
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, f"RICEVUTA DI PAGAMENTO N. {d.get('numero_fattura')}", ln=True, align="C", border=1)
        pdf.ln(10)
        pdf.multi_cell(0, 8, safe_text(f"Cliente: {d.get('nome')} {d.get('cognome')}\nTarga: {d.get('targa')}\nImporto: EUR {d.get('prezzo')}"))

    else: # CONTRATTO
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "CONTRATTO DI NOLEGGIO SCOOTER", ln=True, align="C", border="B")
        pdf.ln(5)
        pdf.set_font("Arial", "", 10)
        testo = f"LOCATARIO: {d.get('nome')} {d.get('cognome')}\n" \
                f"NATO A: {d.get('luogo_nascita')} IL {d.get('data_nascita')}\n" \
                f"RESIDENZA: {d.get('residenza')}\n" \
                f"TARGA: {d.get('targa')} | PATENTE: {d.get('numero_patente')}\n" \
                f"PERIODO: dal {d.get('inizio')} al {d.get('fine')}\n" \
                f"PREZZO: EUR {d.get('prezzo')} | DEPOSITO: EUR {d.get('deposito')}\n\n" \
                f"CONDIZIONI: Il cliente si assume ogni responsabilita civile e penale."
        pdf.multi_cell(0, 6, safe_text(testo))
        if d.get("firma"):
            try:
                base64_str = d.get("firma").split(",")[-1]
                pdf.image(io.BytesIO(base64.b64decode(base64_str)), x=130, y=pdf.get_y()+5, w=50)
            except: pass
        pdf.ln(25)
        pdf.cell(0, 10, "Firma del Cliente _________________________", ln=True, align="R")

    return pdf.output(dest="S")

# -------------------------
# LOGIN E MENU
# -------------------------
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    pwd = st.sidebar.text_input("Password", type="password")
    if pwd == st.secrets["APP_PASSWORD"]: st.session_state.auth = True
    else: st.stop()

menu = st.sidebar.radio("Menu", ["Nuovo Noleggio", "Archivio", "Registro", "Backup"])

if menu == "Nuovo Noleggio":
    st.header("📝 Nuovo Contratto")
    with st.form("noleggio_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Nome")
        cognome = col2.text_input("Cognome")
        luogo_nas = col1.text_input("Luogo Nascita")
        data_nas = col2.text_input("Data Nascita (GG/MM/AAAA)")
        residenza = col1.text_input("Residenza Completa")
        cf = col2.text_input("Codice Fiscale")
        patente = col1.text_input("N. Patente")
        telefono = col2.text_input("Telefono (WhatsApp)")
        targa = col1.text_input("Targa").upper()
        prezzo = col2.number_input("Prezzo (€)", min_value=0.0)
        deposito = col1.number_input("Deposito (€)", min_value=0.0)
        inizio = col1.date_input("Inizio")
        fine = col2.date_input("Fine")
        
        st.write("Firma Cliente")
        canvas = st_canvas(stroke_width=3, stroke_color="#000", background_color="#eee", height=150, width=500, key="canvas")

        if st.form_submit_button("💾 SALVA"):
            if nome and targa:
                firma_b64 = ""
                if canvas.image_data is not None:
                    img = Image.fromarray(canvas.image_data.astype(np.uint8))
                    buffered = io.BytesIO()
                    img.save(buffered, format="PNG")
                    firma_b64 = base64.b64encode(buffered.getvalue()).decode()

                n_fatt = get_next_fattura()
                dati = {
                    "nome": nome, "cognome": cognome, "luogo_nascita": luogo_nas, "data_nascita": data_nas,
                    "residenza": residenza, "codice_fiscale": cf, "numero_patente": patente,
                    "telefono": telefono, "targa": targa, "inizio": str(inizio), "fine": str(fine),
                    "prezzo": prezzo, "deposito": deposito, "numero_fattura": n_fatt, "firma": firma_b64
                }
                supabase.table("contratti").insert(dati).execute()
                aggiorna_registro(prezzo)
                st.success(f"Salvato! Fattura {n_fatt}")
            else: st.error("Nome e Targa obbligatori")

elif menu == "Archivio":
    st.header("📂 Archivio")
    cerca = st.text_input("Cerca...").lower()
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        if cerca in f"{c['targa']} {c['cognome']}".lower():
            with st.expander(f"{c['numero_fattura']} - {c['targa']} - {c['cognome']}"):
                col1, col2, col3 = st.columns(3)
                col1.download_button("📜 Contratto", genera_pdf(c, "CONTRATTO"), f"Contr_{c['id']}.pdf")
                col2.download_button("💰 Ricevuta", genera_pdf(c, "FATTURA"), f"Ric_{c['id']}.pdf")
                col3.download_button("🚨 Multe", genera_pdf(c, "MULTE"), f"Multe_{c['id']}.pdf")

elif menu == "Registro":
    st.header("📊 Registro")
    res = supabase.table("registro_giornaliero").select("*").order("data", desc=True).execute()
    st.table(pd.DataFrame(res.data))

elif menu == "Backup":
    st.header("💾 Backup")
    res = supabase.table("contratti").select("*").execute()
    st.download_button("Scarica Backup CSV", pd.DataFrame(res.data).to_csv(index=False).encode('utf-8'), "backup.csv")
