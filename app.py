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
st.set_page_config(page_title="Battaglia Rent - Gestione Completa", layout="centered")

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
# FUNZIONI SUPPORTO
# -------------------------

def genera_numero_fattura():
    anno = datetime.date.today().year
    try:
        res = supabase.table("contratti").select("numero_fattura").filter("numero_fattura", "ilike", f"{anno}-%").order("numero_fattura", desc=True).limit(1).execute()
        if not res.data: return f"{anno}-001"
        last_val = res.data[0]["numero_fattura"]
        ultimo = int(last_val.split("-")[1])
        return f"{anno}-{str(ultimo + 1).zfill(3)}"
    except:
        return f"{anno}-001"

def upload_foto(file, targa, tipo):
    if file is None: return None
    try:
        ext = file.name.split(".")[-1]
        nome_file = f"{tipo}{targa}{datetime.datetime.now().strftime('%H%M%S')}.{ext}"
        supabase.storage.from_("documenti").upload(nome_file, file.getvalue())
        return supabase.storage.from_("documenti").get_public_url(nome_file)
    except:
        return None

# -------------------------
# MENU
# -------------------------
menu = st.sidebar.radio("Navigazione", ["Nuovo Noleggio", "Archivio Storico", "Registro Giornaliero"])

# -------------------------
# 1. NUOVO NOLEGGIO (AGGIORNATO CON NAZIONALITÀ)
# -------------------------
if menu == "Nuovo Noleggio":
    st.header("🛵 Nuovo Noleggio Professionale")
    
    with st.form("form_noleggio", clear_on_submit=True):
        st.subheader("👤 Dati Anagrafici")
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome")
        cognome = c2.text_input("Cognome")
        
        # --- AGGIUNTA NAZIONALITÀ ---
        c_naz, c_cf = st.columns(2)
        nazionalita = c_naz.text_input("Nazionalità", value="Italiana")
        cod_fisc = c_cf.text_input("Codice Fiscale / ID")
        
        patente = c1.text_input("N. Patente")
        telefono = c2.text_input("Telefono (per WhatsApp)")
        
        luogo_nas = c1.text_input("Luogo di Nascita")
        data_nas = c2.date_input("Data di Nascita", value=datetime.date(1990,1,1))

        st.subheader("🚲 Dati Veicolo e Noleggio")
        c3, c4 = st.columns(2)
        targa = c3.text_input("Targa Scooter").upper()
        prezzo = c4.number_input("Prezzo Totale (€)", min_value=0.0)
        inizio = c3.date_input("Inizio Noleggio")
        fine = c4.date_input("Fine Noleggio")
        deposito = st.number_input("Deposito Cauzionale (€)", min_value=0.0)

        st.subheader("📸 Documenti")
        f_fronte = st.file_uploader("Foto Patente Fronte", type=['jpg', 'png'])
        f_retro = st.file_uploader("Foto Patente Retro", type=['jpg', 'png'])

        st.subheader("⚖️ Clausole e Privacy")
        check_privacy = st.checkbox("Accetto il trattamento dei dati (GDPR 679/2016)")
        check_condizioni = st.checkbox("Il cliente dichiara di aver visionato lo stato del veicolo e accetta le condizioni di noleggio.")

        st.write("✍️ Firma Cliente:")
        canvas = st_canvas(height=150, stroke_width=2, stroke_color="#000", background_color="#eee", key="canvas")
        
        submit = st.form_submit_button("SALVA E GENERA TUTTO")

        if submit:
            if not nome or not targa or not check_privacy:
                st.error("Assicurati di inserire Nome, Targa e accettare la Privacy!")
            else:
                n_fatt = genera_numero_fattura()
                url_f = upload_foto(f_fronte, targa, "F")
                url_r = upload_foto(f_retro, targa, "R")
                
                # --- DATI CON NAZIONALITÀ ---
                dati = {
                    "nome": nome, "cognome": cognome, "telefono": telefono, "targa": targa,
                    "inizio": str(inizio), "fine": str(fine), "prezzo": prezzo, "deposito": deposito,
                    "numero_fattura": n_fatt, "codice_fiscale": cod_fisc, "numero_patente": patente,
                    "luogo_nascita": luogo_nas, "data_nascita": str(data_nas),
                    "nazionalita": nazionalita, # Salvataggio nazionalità
                    "url_fronte": url_f, "url_retro": url_r
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

                st.success(f"Noleggio registrato! Fattura: {n_fatt}")
                msg = urllib.parse.quote(f"Buongiorno {nome}, Battaglia Rent le invia il riepilogo per lo scooter {targa}.\nTotale: €{prezzo}")
                st.markdown(f"[📲 Invia su WhatsApp](https://wa.me/{telefono}?text={msg})")

# -------------------------
# 2. ARCHIVIO STORICO
# -------------------------
elif menu == "Archivio Storico":
    st.header("📂 Archivio Storico")
    cerca = st.text_input("🔍 Cerca per Targa, Cognome o Fattura").lower()
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    
    if res.data:
        for c in res.data:
            stringa_cerca = f"{c.get('targa','')} {c.get('cognome','')} {c.get('numero_fattura','')}".lower()
            if cerca in stringa_cerca:
                with st.expander(f"📝 {c['numero_fattura']} | {c['targa']} | {c['cognome'].upper()}"):
                    st.write(f"*Cliente:* {c['nome']} {c['cognome']}")
                    st.write(f"*Nazionalità:* {c.get('nazionalita', 'N/D')} | *Patente:* {c['numero_patente']}")
                    st.write(f"*Cod. Fiscale:* {c['codice_fiscale']} | *Tel:* {c['telefono']}")
                    
                    st.divider()
                    if c.get("url_fronte"):
                        st.link_button("👁️ Vedi Foto Patente", c["url_fronte"])
                    
                    msg_wa = urllib.parse.quote(f"Ciao {c['nome']}, ecco i documenti del tuo noleggio.")
                    st.link_button("🟢 WhatsApp", f"https://wa.me/{str(c['telefono']).replace(' ','')}?text={msg_wa}")

# -------------------------
# 3. REGISTRO GIORNALIERO
# -------------------------
elif menu == "Registro Giornaliero":
    st.header("📊 Registro Incassi")
    res = supabase.table("registro_giornaliero").select("*").order("data", desc=True).execute()
    if res.data:
        st.table(pd.DataFrame(res.data)[['data', 'numero_noleggi', 'totale_incasso']])
