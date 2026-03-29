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

# DATI AZIENDA MARIANNA
TITOLARE_INFO = "BATTAGLIA MARIANNA, nata a Berlino (Germania) il 13/01/1987\nResidente a Forio in Via Cognole n. 5\nC.F.: BTTMNN87A53Z112S | P.IVA: 10252601215"

# TESTI LEGALI
PRIVACY_TEXT = "INFORMATIVA PRIVACY: I dati personali sono trattati ai sensi del Reg. UE 2016/679 (GDPR). Il cliente presta il consenso."
CLAUSOLE_VESSATORIE = "Ai sensi degli artt. 1341 e 1342 c.c. il Cliente approva le clausole: 3 (Multe), 4 (Spese), 5 (Danni), 13 (Foro)."

def genera_moduli(c):
    # --- 1. CONTRATTO (PULITO) ---
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
    p2.multi_cell(0, 6, txt=clean_t(f"Si comunica che il veicolo {c['targa']} era in locazione a:\n\nNome: {c['cliente']}\nCF: {c['cf']}\nNato a: {c.get('luogo_nascita','')}\nResidenza: {c.get('residenza','')}\nDoc: {c.get('num_doc','')}"))
    p2.ln(10); p2.cell(0, 10, "In fede, Marianna Battaglia", align='R')
    b2 = p2.output(dest='S').encode('latin-1')

    # --- 3. DATI FATTURA ---
    p3 = fpdf.FPDF()
    p3.add_page()
    p3.set_font("Arial", 'B', 14); p3.cell(0, 10, "DATI FATTURAZIONE", ln=1, align='C')
    p3.set_font("Arial", size=11)
    p3.multi_cell(0, 8, txt=clean_t(f"Cliente: {c['cliente']}\nP.IVA: {c.get('p_iva','')}\nSDI: {c.get('sdi','')}\nTarga: {c['targa']}\nImporto: {c.get('prezzo', 0)} Euro"))
    b3 = p3.output(dest='S').encode('latin-1')
    
    return b1, b2, b3

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
    
    with st.expander("💰 Dati Fattura"):
        p_iva = st.text_input("Partita IVA")
        sdi = st.text_input("Codice SDI / PEC")

    foto_p = st.camera_input("📸 Foto Patente")
    canvas = st_canvas(fill_color="white", stroke_width=2, height=150, key="sig_v_final")

    if st.button("💾 SALVA TUTTO"):
        if cliente and targa:
            dat = {"cliente": cliente, "cf": cf_cliente, "targa": targa, "data_inizio": str(datetime.date.today()), "telefono": telefono, "p_iva": p_iva, "sdi": sdi, "luogo_nascita": nascita, "residenza": residenza, "num_doc": num_doc, "prezzo": prezzo}
            supabase.table("contratti").insert(dat).execute()
            st.success(f"Archiviato con successo! Cerca la targa {targa} in Archivio.")
        else:
            st.error("Inserisci almeno Nome e Targa!")

elif menu == "🗄️ Archivio Documenti":
    st.header("🔎 Ricerca per Targa")
    t_search = st.text_input("Inserisci TARGA").upper()
    
    if t_search:
        res = supabase.table("contratti").select("*").eq("targa", t_search).execute()
        if res.data:
            for c in res.data:
                # Creiamo un ID unico per i pulsanti di questo specifico noleggio
                unique_id = f"{c['id']}_{c['targa']}"
                
                with st.expander(f"📂 Noleggio del {c['data_inizio']} - {c['cliente']}"):
                    b1, b2, b3 = genera_moduli(c)
                    
                    st.write(f"*Cliente:* {c['cliente']} | *Targa:* {c['targa']}")
                    
                    col1, col2, col3 = st.columns(3)
                    # Aggiunto 'key' unico per evitare l'errore DuplicateElementId
                    col1.download_button("📄 Contratto", b1, f"Contratto_{c['targa']}.pdf", key=f"btn_con_{unique_id}")
                    col2.download_button("🚨 Modulo Vigili", b2, f"Multe_{c['targa']}.pdf", key=f"btn_mul_{unique_id}")
                    col3.download_button("💰 Fattura", b3, f"Fattura_{c['cliente']}.pdf", key=f"btn_fat_{unique_id}")
                    
                    # WhatsApp con link diretto
                    if c['telefono']:
                        msg = urllib.parse.quote(f"Ciao {c['cliente']}, ecco i documenti MasterRent per la targa {c['targa']}.")
                        st.link_button("📲 WhatsApp", f"https://wa.me/{c['telefono']}?text={msg}")
        else:
            st.warning("Nessun noleggio trovato per questa targa.")

