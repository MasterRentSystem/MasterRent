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
st.set_page_config(page_title="Battaglia Rent", layout="centered")

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
# FUNZIONI UPGRADE (Fattura e Registro)
# -------------------------

def genera_numero_fattura():
    anno = datetime.date.today().year
    try:
        res = supabase.table("contratti").select("numero_fattura").filter("numero_fattura", "ilike", f"{anno}-%").order("numero_fattura", desc=True).limit(1).execute()
        if not res.data: return f"{anno}-001"
        ultimo = int(res.data[0]["numero_fattura"].split("-")[1])
        return f"{anno}-{str(ultimo + 1).zfill(3)}"
    except:
        return f"{anno}-001"

def genera_pdf_base(d, tipo):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, f"{tipo} - Battaglia Rent", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.ln(10)
    pdf.cell(0, 10, f"Cliente: {d['nome']} {d['cognome']}", ln=True)
    pdf.cell(0, 10, f"Targa: {d.get('targa', 'N/D')} | Fattura: {d.get('numero_fattura', 'N/D')}", ln=True)
    pdf.cell(0, 10, f"Periodo: {d.get('inizio', 'N/D')} / {d.get('fine', 'N/D')}", ln=True)
    
    # MODIFICA QUESTA RIGA:
    return bytes(pdf.output())
# MENU
# -------------------------
menu = st.sidebar.radio("Navigazione", ["Nuovo Noleggio", "Archivio Storico", "Registro Giornaliero"])

# -------------------------
# 1. NUOVO NOLEGGIO
# -------------------------
if menu == "Nuovo Noleggio":
    st.header("🛵 Nuovo Noleggio")
    with st.form("form_noleggio"):
        nome = st.text_input("Nome")
        cognome = st.text_input("Cognome")
        telefono = st.text_input("Telefono")
        targa = st.text_input("Targa").upper()
        inizio = st.date_input("Inizio")
        fine = st.date_input("Fine")
        prezzo = st.number_input("Prezzo (€)", min_value=0.0)
        
        st.write("Firma:")
        canvas = st_canvas(height=150, stroke_width=2, key="canvas")
        
        submit = st.form_submit_button("SALVA CONTRATTO")

        if submit:
            n_fatt = genera_numero_fattura()
            
            dati = {
                "nome": nome, "cognome": cognome, "telefono": telefono,
                "targa": targa, "inizio": str(inizio), "fine": str(fine),
                "prezzo": prezzo, "numero_fattura": n_fatt
            }
            
            # Salvataggio Contratto
            supabase.table("contratti").insert(dati).execute()

            # --- AGGIORNAMENTO REGISTRO FISCALE (Il pezzo che hai chiesto) ---
            oggi = str(datetime.date.today())
            res_reg = supabase.table("registro_giornaliero").select("*").eq("data", oggi).execute()
            if res_reg.data:
                n = res_reg.data[0]["numero_noleggi"] + 1
                t = float(res_reg.data[0]["totale_incasso"]) + float(prezzo)
                supabase.table("registro_giornaliero").update({"numero_noleggi": n, "totale_incasso": t}).eq("data", oggi).execute()
            else:
                supabase.table("registro_giornaliero").insert({"data": oggi, "numero_noleggi": 1, "totale_incasso": prezzo}).execute()

            st.success(f"Salvato! Fattura n. {n_fatt}")
            
            # WhatsApp Rapido dopo salvataggio
            msg = urllib.parse.quote(f"Ciao {nome}, ecco il contratto per lo scooter {targa}. Grazie da Battaglia Rent!")
            st.link_button("🟢 Invia su WhatsApp", f"https://wa.me/{telefono}?text={msg}")

# -------------------------
# 2. ARCHIVIO CON RICERCA
# -------------------------
elif menu == "Archivio Storico":
    st.header("📂 Archivio")
    cerca = st.text_input("🔍 Cerca per Targa o Cognome").lower()
    
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    
    if res.data:
        for c in res.data:
            if cerca in c['targa'].lower() or cerca in c['cognome'].lower():
                with st.expander(f"{c['numero_fattura']} - {c['targa']} - {c['cognome']}"):
                    st.download_button("📜 Scarica Contratto", genera_pdf_base(c, "CONTRATTO"), f"Contratto_{c['id']}.pdf")
                    
                    # Tasto WhatsApp in archivio
                    msg_wa = urllib.parse.quote(f"Ciao {c['nome']}, ti invio il contratto per lo scooter {c['targa']}.")
                    st.link_button("🟢 WhatsApp", f"https://wa.me/{str(c['telefono']).replace(' ','')}?text={msg_wa}")

# -------------------------
# 3. REGISTRO GIORNALIERO (Visualizzazione)
# -------------------------
elif menu == "Registro Giornaliero":
    st.header("📊 Registro Fiscale")
    res = supabase.table("registro_giornaliero").select("*").order("data", desc=True).execute()
    if res.data:
        st.table(pd.DataFrame(res.data)[['data', 'numero_noleggi', 'totale_incasso']])
    else:
        st.info("Nessun dato nel registro.")
