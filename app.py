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
# NUMERO FATTURA
# -------------------------
def get_next_fattura():
    year = datetime.date.today().year
    try:
        res = supabase.table("contratti").select("numero_fattura").filter("numero_fattura", "ilike", f"{year}-%").order("numero_fattura", desc=True).limit(1).execute()
        if not res.data:
            return f"{year}-001"
        last_num = int(res.data[0]["numero_fattura"].split("-")[1])
        return f"{year}-{str(last_num + 1).zfill(3)}"
    except:
        return f"{year}-001"

# -------------------------
# REGISTRO GIORNALIERO
# -------------------------
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
    except:
        st.error("Errore aggiornamento registro")

# -------------------------
# GENERAZIONE PDF
# -------------------------
def genera_pdf(d, tipo):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)

    # Funzione per pulire il testo da caratteri speciali
    def clean(t):
        return str(t).encode("latin-1", "replace").decode("latin-1").replace("?", "-")

    if tipo == "MULTE":
        pdf.cell(200, 10, "DICHIARAZIONE DATI CONDUCENTE (L. 445/2000)", ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("Arial", "", 11)
        testo = (
            f"La sottoscritta Marianna Battaglia dichiara che in data {d.get('inizio')} "
            f"il veicolo targa {d.get('targa')} era affidato al Sig. "
            f"{d.get('nome')} {d.get('cognome')} nato a {d.get('luogo_nascita')} "
            f"il {d.get('data_nascita')} residente in {d.get('residenza')} "
            f"patente n. {d.get('numero_patente')}."
        )
        pdf.multi_cell(0, 10, clean(testo))

    elif tipo == "FATTURA":
        pdf.cell(200, 10, clean(f"RICEVUTA FISCALE N. {d.get('numero_fattura')}"), ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, clean(f"Cliente: {d.get('nome')} {d.get('cognome')}"), ln=True)
        pdf.cell(0, 10, clean(f"Codice Fiscale: {d.get('codice_fiscale', '---')}"), ln=True)
        pdf.cell(0, 10, clean(f"Importo: Euro {d.get('prezzo')}"), ln=True)

    else:
        pdf.cell(200, 10, "CONTRATTO DI NOLEGGIO VEICOLO", ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("Arial", "", 11)
        testo = (
            f"Locatario: {d.get('nome')} {d.get('cognome')}\n"
            f"Nato a: {d.get('luogo_nascita')} il {d.get('data_nascita')}\n"
            f"Targa: {d.get('targa')}\n"
            f"Dal: {d.get('inizio')} Al: {d.get('fine')}\n"
            f"Prezzo: Euro {d.get('prezzo')}\n"
            f"Deposito: Euro {d.get('deposito')}"
        )
        pdf.multi_cell(0, 10, clean(testo))
        
        # Aggiunta firma se presente
        if d.get("firma"):
            try:
                base64_str = d.get("firma").split(",")[-1]
                img_data = base64.b64decode(base64_str)
                pdf.image(io.BytesIO(img_data), x=130, y=pdf.get_y()+5, w=50)
            except: pass

    return pdf.output(dest="S")

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
        data_nas = col2.text_input("Data di Nascita (GG/MM/AAAA)")
        residenza = col1.text_input("Residenza")
        cod_fisc = col2.text_input("Codice Fiscale")
        patente = col1.text_input("N. Patente")
        telefono = col2.text_input("Telefono")
        targa = col1.text_input("Targa").upper()
        
        c_prezzo, c_dep = st.columns(2)
        prezzo = c_prezzo.number_input("Prezzo", min_value=0.0)
        deposito = c_dep.number_input("Deposito", min_value=0.0)
        
        inizio = st.date_input("Inizio")
        fine = st.date_input("Fine")

        st.write("Firma Cliente")
        canvas = st_canvas(
            height=150, 
            stroke_width=2, 
            stroke_color="#000", 
            background_color="#eee", 
            key="canvas"
        )

        submit = st.form_submit_button("SALVA")

        if submit:
            if not nome or not targa:
                st.error("Nome e Targa obbligatori")
            else:
                try:
                    # 1. Gestione Firma
                    firma_b64 = ""
                    if canvas.image_data is not None:
                        img = Image.fromarray(canvas.image_data.astype(np.uint8))
                        buffered = io.BytesIO()
                        img.save(buffered, format="PNG")
                        firma_b64 = "data:image/png;base64," + base64.b64encode(buffered.getvalue()).decode()

                    # 2. Numero Fattura
                    numero_fattura = get_next_fattura()

                    # 3. Preparazione Dati
                    dati = {
                        "nome": str(nome),
                        "cognome": str(cognome),
                        "luogo_nascita": str(luogo_nas),
                        "data_nascita": str(data_nas),
                        "residenza": str(residenza),
                        "codice_fiscale": str(cod_fisc),
                        "numero_patente": str(patente),
                        "telefono": str(telefono),
                        "targa": str(targa),
                        "inizio": inizio.isoformat(),
                        "fine": fine.isoformat(),
                        "prezzo": float(prezzo),
                        "deposito": float(deposito),
                        "numero_fattura": str(numero_fattura),
                        "firma": firma_b64
                    }

                    # 4. Salvataggio
                    supabase.table("contratti").insert(dati).execute()
                    
                    # 5. Registro
                    aggiorna_registro(prezzo)
                    
                    st.success(f"Noleggio salvato - Fattura {numero_fattura}")

                    if telefono:
                        tel_clean = ''.join(filter(str.isdigit, str(telefono)))
                        msg = urllib.parse.quote(f"Buongiorno {nome}, Battaglia Rent.\nScooter {targa}\nTotale €{prezzo}")
                        st.markdown(f"[📲 Invia WhatsApp](https://wa.me/{tel_clean}?text={msg})")
                
                except Exception as e:
                    st.error(f"Errore durante il salvataggio: {e}")
# -------------------------
# ARCHIVIO
# -------------------------
elif menu == "Archivio Storico":
    st.header("📂 Archivio")
    cerca = st.text_input("Cerca").lower()
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        testo = f"{c.get('targa')} {c.get('cognome')} {c.get('numero_fattura')}".lower()
        if cerca in testo:
            with st.expander(f"{c.get('numero_fattura')} - {c.get('targa')} - {c.get('cognome')}"):
                st.download_button("📜 Contratto", genera_pdf(c, "CONTRATTO"), file_name=f"contratto_{c['targa']}.pdf")
                st.download_button("💰 Ricevuta", genera_pdf(c, "FATTURA"), file_name=f"ricevuta_{c['numero_fattura']}.pdf")
                st.download_button("🚨 Multe", genera_pdf(c, "MULTE"), file_name=f"multe_{c['targa']}.pdf")

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
        df = pd.DataFrame(res.data)
        st.download_button("Scarica Backup", df.to_csv(index=False).encode("utf-8"), "backup.csv")
