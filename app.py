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

# Connessione
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# -------------------------
# UTILITY PDF & TESTO
# -------------------------
def safe_text(text):
    """Sostituisce caratteri non compatibili con FPDF (Arial/Latin-1)"""
    if text is None: return ""
    # Sostituisce l'euro e gestisce accenti comuni
    text = str(text).replace("€", "EUR").replace("’", "'").replace("“", '"').replace("”", '"')
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
    except: st.error("Errore aggiornamento registro incassi")

# -------------------------
# GENERAZIONE PDF
# -------------------------
def genera_pdf(d, tipo):
    pdf = FPDF()
    pdf.add_page()
    
    # Intestazione Ditta
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
                f"Socio/Conducente: {d.get('nome')} {d.get('cognome')}\n" \
                f"Nato a: {d.get('luogo_nascita', '---')} il {d.get('data_nascita', '---')}\n" \
                f"Patente n.: {d.get('numero_patente', '---')}\n" \
                f"Residenza: {d.get('residenza', '---')}"
        pdf.multi_cell(0, 8, safe_text(testo))

    elif tipo == "FATTURA":
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, f"RICEVUTA DI PAGAMENTO N. {d.get('numero_fattura')}", ln=True, align="C", border=1)
        pdf.ln(10)
        pdf.set_font("Arial", "", 11)
        testo = f"Cliente: {d.get('nome')} {d.get('cognome')}\n" \
                f"Targa veicolo: {d.get('targa')}\n" \
                f"Periodo: dal {d.get('inizio')} al {d.get('fine')}\n\n" \
                f"TOTALE INCASSATO: EUR {d.get('prezzo')}"
        pdf.multi_cell(0, 8, safe_text(testo))

    else: # CONTRATTO
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "CONTRATTO DI NOLEGGIO SCOOTER", ln=True, align="C", border="B")
        pdf.ln(5)
        pdf.set_font("Arial", "", 10)
        testo = f"LOCATARIO: {d.get('nome')} {d.get('cognome')}\n" \
                f"VEICOLO TARGA: {d.get('targa')}\n" \
                f"PERIODO: dal {d.get('inizio')} al {d.get('fine')}\n" \
                f"PREZZO: EUR {d.get('prezzo')} | DEPOSITO: EUR {d.get('deposito')}\n\n" \
                f"CONDIZIONI: Il cliente dichiara di ricevere il mezzo in ottimo stato e si assume " \
                f"ogni responsabilita per danni, furto o infrazioni al codice della strada."
        pdf.multi_cell(0, 6, safe_text(testo))
        
        # Inserimento Firma se presente
        if d.get("firma") and len(str(d.get("firma"))) > 100:
            try:
                # Rimuove l'header data:image/png;base64, se presente
                base64_str = d.get("firma").split(",")[-1]
                img_data = base64.b64decode(base64_str)
                pdf.image(io.BytesIO(img_data), x=130, y=pdf.get_y()+5, w=50)
            except: pass
        
        pdf.ln(25)
        pdf.cell(0, 10, "Firma del Cliente _________________________", ln=True, align="R")

    return pdf.output(dest="S")

# -------------------------
# ACCESSO
# -------------------------
if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔒 Battaglia Rent - Login")
    pwd = st.text_input("Inserisci Password", type="password")
    if st.button("Entra"):
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state.auth = True
            st.rerun()
    st.stop()

# -------------------------
# MENU & NAVIGAZIONE
# -------------------------
menu = st.sidebar.radio("Menu principale", ["Nuovo Noleggio", "Archivio Storico", "Registro Giornaliero", "Backup"])

if menu == "Nuovo Noleggio":
    st.header("🛵 Registra Nuovo Contratto")
    with st.form("noleggio_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome")
        cognome = c2.text_input("Cognome")
        telefono = c1.text_input("Telefono (es. 393331234567)")
        targa = c2.text_input("Targa").upper()
        
        c3, c4 = st.columns(2)
        inizio = c3.date_input("Inizio Noleggio")
        fine = c4.date_input("Fine Noleggio")
        
        c5, c6 = st.columns(2)
        prezzo = c5.number_input("Prezzo Totale (€)", min_value=0.0)
        deposito = c6.number_input("Deposito (€)", min_value=0.0)

        st.subheader("✍️ Firma del Cliente")
        canvas = st_canvas(stroke_width=3, stroke_color="#000", background_color="#eee", height=150, width=500, key="canvas")

        if st.form_submit_button("💾 SALVA E GENERA"):
            if nome and targa:
                # Gestione Firma senza OpenCV
                firma_b64 = ""
                if canvas.image_data is not None:
                    img = Image.fromarray(canvas.image_data.astype(np.uint8))
                    buffered = io.BytesIO()
                    img.save(buffered, format="PNG")
                    firma_b64 = base64.b64encode(buffered.getvalue()).decode()

                n_fatt = get_next_fattura()
                
                dati = {
                    "nome": nome, "cognome": cognome, "telefono": telefono, "targa": targa,
                    "inizio": str(inizio), "fine": str(fine), "prezzo": prezzo,
                    "deposito": deposito, "numero_fattura": n_fatt, "firma": firma_b64
                }
                
                try:
                    supabase.table("contratti").insert(dati).execute()
                    aggiorna_registro(prezzo)
                    st.success(f"✅ Contratto n° {n_fatt} salvato!")
                    
                    # Tasto WhatsApp Rapido
                    if telefono:
                        msg = urllib.parse.quote(f"Ciao {nome}, Battaglia Rent! Ti confermiamo il noleggio per lo scooter {targa}. Totale: {prezzo}€. A presto!")
                        st.markdown(f"*[📲 Clicca qui per inviare WhatsApp al cliente](https://wa.me/{telefono}?text={msg})*")
                except Exception as e:
                    st.error(f"Errore database: {e}")
            else:
                st.error("Nome e Targa sono obbligatori!")

elif menu == "Archivio Storico":
    st.header("📂 Archivio Contratti")
    cerca = st.text_input("🔍 Cerca per Targa o Cognome").lower()
    
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    if res.data:
        for c in res.data:
            identificativo = f"{c.get('targa', '')} {c.get('cognome', '')} {c.get('numero_fattura', '')}".lower()
            if cerca in identificativo:
                with st.expander(f"📝 {c['numero_fattura']} - {c['targa']} - {c['cognome']}"):
                    col1, col2, col3 = st.columns(3)
                    col1.download_button("📜 Contratto", genera_pdf(c, "CONTRATTO"), f"Contratto_{c['id']}.pdf")
                    col2.download_button("💰 Ricevuta", genera_pdf(c, "FATTURA"), f"Ricevuta_{c['id']}.pdf")
                    col3.download_button("🚨 Multe", genera_pdf(c, "MULTE"), f"Multe_{c['id']}.pdf")

elif menu == "Registro Giornaliero":
    st.header("📊 Registro Incassi")
    res = supabase.table("registro_giornaliero").select("*").order("data", desc=True).execute()
    if res.data:
        st.table(pd.DataFrame(res.data))
    else:
        st.info("Nessun dato nel registro.")

elif menu == "Backup":
    st.header("💾 Backup Dati")
    if st.button("Genera Backup CSV"):
        res = supabase.table("contratti").select("*").execute()
        df = pd.DataFrame(res.data)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Scarica Backup", csv, "backup_battaglia_rent.csv", "text/csv")
