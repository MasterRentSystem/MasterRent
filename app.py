import streamlit as st
from supabase import create_client, Client
import base64
from datetime import datetime
from fpdf import FPDF
import io
import urllib.parse
from PIL import Image, ImageOps

# --- CONFIGURAZIONE BATTAGLIA RENT ---
DITTA = "BATTAGLIA RENT"
TITOLARE = "BATTAGLIA MARIANNA"
SEDE = "Via Cognole n. 5 - 80075 Forio (NA)"
PIVA = "10252601215"
CF_TITOLARE = "BTTMNN87A53Z112S"

URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- FUNZIONI DI UTILITÀ ---
def safe(t): return str(t).encode("latin-1", "replace").decode("latin-1")

def correggi_e_converti_foto(image_file):
    if image_file is not None:
        img = Image.open(image_file)
        # Raddrizza la foto automaticamente (se scattata di traverso)
        img = ImageOps.exif_transpose(img)
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=70) # JPEG occupa meno spazio
        return "data:image/jpeg;base64," + base64.b64encode(buffered.getvalue()).decode()
    return None

def get_prossimo_numero():
    try:
        res = supabase.table("contratti").select("numero_fattura").execute()
        nums = [int(r['numero_fattura']) for r in res.data if str(r['numero_fattura']).isdigit()]
        return max(nums) + 1 if nums else 1
    except: return 1

# --- GENERATORI PDF E XML (Identici a prima) ---
# ... (Qui restano le funzioni genera_rinotifica_pdf, genera_xml_sdi e genera_cortesia_pdf)

# --- INTERFACCIA APP ---
st.set_page_config(page_title="BATTAGLIA RENT", layout="centered")

if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    pwd = st.text_input("Password", type="password")
    if st.button("ENTRA"):
        if pwd == "1234": st.session_state.auth = True; st.rerun()
    st.stop()

tab1, tab2, tab3 = st.tabs(["📝 NUOVO NOLEGGIO", "📂 ARCHIVIO", "🚨 GESTIONE MULTE"])

with tab1:
    with st.form("registrazione"):
        st.subheader("👤 Dati per Contratto e Fattura")
        c1, c2 = st.columns(2)
        n = c1.text_input("Nome")
        cg = c2.text_input("Cognome")
        cf = st.text_input("Codice Fiscale")
        ind = st.text_input("Indirizzo Residenza")
        wa = st.text_input("Cellulare (WhatsApp)")
        
        st.subheader("🛵 Dati Mezzo")
        m1, m2 = st.columns(2)
        mod = m1.text_input("Modello Scooter")
        tg = m2.text_input("Targa").upper()
        prz = st.number_input("Prezzo Totale €", 0.0)

        st.subheader("📸 Foto Documenti")
        st.info("Clicca sotto e scegli 'Scatta Foto' per usare la fotocamera posteriore.")
        # Usiamo file_uploader invece di camera_input per forzare l'uso della fotocamera del telefono
        f1_file = st.file_uploader("FOTO PATENTE", type=['jpg', 'jpeg', 'png'])
        f2_file = st.file_uploader("FOTO CONTRATTO FIRMATO", type=['jpg', 'jpeg', 'png'])

        if st.form_submit_button("💾 SALVA E ARCHIVIA"):
            if not n or not tg or not f2_file:
                st.error("Inserisci almeno Nome, Targa e Foto Contratto!")
            else:
                with st.spinner("Salvataggio e raddrizzamento foto in corso..."):
                    f1_ready = correggi_e_converti_foto(f1_file)
                    f2_ready = correggi_e_converti_foto(f2_file)
                    
                    num_f = get_prossimo_numero()
                    dati = {
                        "nome": n, "cognome": cg, "codice_fiscale": cf, "indirizzo": ind,
                        "pec": wa, "modello": mod, "targa": tg, "prezzo": prz,
                        "data_inizio": datetime.now().strftime("%d/%m/%Y"),
                        "numero_fattura": num_f, 
                        "foto_patente": f1_ready, 
                        "firma": f2_ready
                    }
                    supabase.table("contratti").insert(dati).execute()
                    st.success(f"Noleggio registrato con successo! Fattura N. {num_f}")

# ... (Tab 2 e 3 con la visualizzazione immagini corretta)
