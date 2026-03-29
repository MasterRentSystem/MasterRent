import streamlit as st
import pandas as pd
import datetime
import fpdf
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io
import urllib.parse

# 1. CONNESSIONE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def clean_t(text):
    if not text: return ""
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in repls.items(): text = text.replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

# DATI AZIENDA MARIANNA (Per Modulo Multe)
TITOLARE_INFO = "BATTAGLIA MARIANNA, nata a Berlino (Germania) il 13/01/1987\nResidente a Forio in Via Cognole n. 5\nC.F.: BTTMNN87A53Z112S | P.IVA: 10252601215"

# TESTI LEGALI
PRIVACY_TEXT = "INFORMATIVA PRIVACY: I dati personali sono trattati ai sensi del Reg. UE 2016/679 (GDPR). Il cliente presta il consenso."
CLAUSOLE_VESSATORIE = "Ai sensi degli artt. 1341 e 1342 c.c. il Cliente approva le clausole: 3 (Multe), 4 (Spese), 5 (Danni), 13 (Foro)."

def genera_moduli(c):
    # --- 1. CONTRATTO (PULITO + PRIVACY) ---
    p1 = fpdf.FPDF()
    p1.add_page()
    p1.set_font("Arial", 'B', 16); p1.cell(0, 10, clean_t("CONTRATTO DI NOLEGGIO"), ln=1, align='C')
    p1.set_font("Arial", size=10)
    p1.multi_cell(0, 6, txt=clean_t(f"Cliente: {c['cliente']}\nNato a: {c.get('luogo_nascita','')}\nResidenza: {c.get('residenza','')}\nPatente: {c.get('num_doc','')}\n\nVeicolo: {c['targa']} | Data: {c['data_inizio']}"))
    p1.ln(5); p1.set_font("Arial", size=7); p1.multi_cell(0, 4, txt=clean_t(f"{PRIVACY_TEXT}\n{CLAUSOLE_VESSATORIE}"))
    b1 = p1.output(dest='S').encode('latin-1')

    # --- 2. MODULO MULTE (VIGILI) ---
    p2 = fpdf.FPDF()
    p2.add_page()
    p2.set_font("Arial", size=10); p2.multi_cell(0, 5, txt=clean_t(TITOLARE_INFO))
    p2.ln(10); p2.set_font("Arial", 'B', 12); p2.cell(0, 7, clean_t("COMUNICAZIONE LOCAZIONE VEICOLO"), ln=1, align='C')
    p2.ln(5); p2.set_font("Arial", size=10)
    p2.multi_cell(0, 6, txt=clean_t(f"Si dichiara che il veicolo {c['targa']} era in uso a:\n\nNome: {c['cliente']}\nCF: {c['cf']}\nNato a: {c.get('luogo_nascita','')}\nResidenza: {c.get('residenza','')}\nDoc: {c.get('num_doc','')}"))
    p2.ln(10); p2.cell(0, 10, "In fede, Marianna Battaglia", align='R')
    b2 = p2.output(dest='S').encode('latin-1')
    
    return b1, b2

st.sidebar.title("🚀 MasterRent Ischia")
menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Noleggio", "🗄️ Archivio Documenti"])

if menu == "📝 Nuovo Noleggio":
    st.header("Nuovo Noleggio")
    c1, c2 = st.columns(2)
    cliente = c1.text_input("Nome e Cognome")
    cf_cliente = c2.text_input("Codice Fiscale")
    nascita = c1.text_input("Luogo/Data Nascita")
    residenza = c2.text_input("Indirizzo Residenza")
    num_doc = c1.text_input("Numero Patente")
    telefono = c2.text_input("Cellulare")
    targa = c1.text_input("TARGA").upper()
    prezzo = c2.number_input("Prezzo (€)", min_value=0)
    
    # RIMOSSO IL BLOCCO DATI FATTURA DA QUI

    foto_p = st.camera_input("📸 Foto Patente")
    canvas = st_canvas(fill_color="white", stroke_width=2, height=150, key="sig_v_clean")

    if st.button("💾 SALVA NOLEGGIO"):
        if cliente and targa:
            dat = {"cliente": cliente, "cf": cf_cliente, "targa": targa, "data_inizio": str(datetime.date.today()), "telefono": telefono, "luogo_nascita": nascita, "residenza": residenza, "num_doc": num_doc, "prezzo": prezzo}
            supabase.table("contratti").insert(dat).execute()
            st.success(f"Noleggio di {cliente} salvato! Vai in Archivio per i documenti.")
        else:
            st.warning("Compila i campi obbligatori!")

elif menu == "🗄️ Archivio Documenti":
    st.header("🔎 Ricerca per Targa")
    t_search = st.text_input("Inserisci TARGA").upper()
    
    if t_search:
        res = supabase.table("contratti").select("*").eq("targa", t_search).execute()
        if res.data:
            for c in res.data:
                # Chiave unica per evitare l'errore DuplicateElementId
                unique_key = f"{c['id']}_{c['targa']}"
                with st.expander(f"📂 {c['cliente']} - {c['data_inizio']}"):
                    b1, b2 = genera_moduli(c)
                    st.write(f"Targa: {c['targa']}")
                    
                    col1, col2 = st.columns(2)
                    col1.download_button("📄 Scarica Contratto", b1, f"Contratto_{c['targa']}.pdf", key=f"dl_c_{unique_key}")
                    col2.download_button("🚨 Modulo Vigili", b2, f"Multe_{c['targa']}.pdf", key=f"dl_m_{unique_key}")
                    
                    msg = urllib.parse.quote(f"Ciao {c['cliente']}, ecco il contratto MasterRent.")
                    st.link_button("📲 Invia su WhatsApp", f"https://wa.me/{c['telefono']}?text={msg}")
        else:
            st.warning("Nessun noleggio trovato per questa targa.")

