import streamlit as st
import datetime
import fpdf
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
import time
import urllib.parse

# 1. CONNESSIONE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)
BUCKET_NAME = "DOCUMENTI_PATENTI"

# INTESTAZIONE UFFICIALE
DITTA_NOME = "BATTAGLIA MARIANNA"
DITTA_INFO = "Via Cognole, 5 - 80075 Forio (NA)\nCod. Fisc. BTTMNN87A53Z112S - P. IVA 10252601215"

def clean_t(text):
    if not text or text == "None": return "---"
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in repls.items(): text = str(text).replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

# --- GENERATORE PDF DIFFERENZIATO ---
def genera_documento(c, tipo="CONTRATTO"):
    pdf = fpdf.FPDF()
    pdf.add_page()
    
    # Intestazione Standard
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 7, clean_t(DITTA_NOME), ln=1, align='L')
    pdf.set_font("Arial", size=9)
    pdf.multi_cell(0, 5, clean_t(DITTA_INFO), align='L')
    pdf.line(10, 30, 200, 30)
    pdf.ln(15)
    
    if tipo == "VIGILI":
        # MODULO ACCERTAMENTO (Dalla tua foto cartacea)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "OGGETTO: RIFERIMENTO VS. ACCERTAMENTO VIOLAZIONE N. _______ PROT.", ln=1)
        pdf.cell(0, 10, "COMUNICAZIONE LOCAZIONE VEICOLO", ln=1, align='C')
        pdf.ln(5)
        pdf.set_font("Arial", size=10)
        testo = (
            f"In riferimento al Verbale di accertamento di infrazione al Codice della strada di cui all'oggetto, "
            f"con la presente, la sottoscritta BATTAGLIA MARIANNA nata a Berlino (Germania) il 13/01/1987 "
            f"e residente in Forio alla Via Cognole n. 5 in qualita di titolare dell'omonima ditta individuale:\n\n"
            f"DICHIARA\n\n"
            f"Ai sensi della l. 445/2000 che il veicolo targa {c.get('targa')} il giorno {c.get('data_inizio')} "
            f"era concesso in locazione senza conducente al signor:\n\n"
            f"COGNOME E NOME: {c.get('cliente')}\n"
            f"LUOGO E DATA DI NASCITA: {c.get('luogo_nascita')}\n"
            f"RESIDENZA: {c.get('residenza')}\n"
            f"IDENTIFICATO A MEZZO PATENTE: {c.get('num_doc')}\n\n"
            f"La presente al fine di procedere alla rinotifica nei confronti del locatario sopra indicato.\n"
            f"Si allega copia del contratto di locazione."
        )
        pdf.multi_cell(0, 6, clean_t(testo))
        pdf.ln(20)
        pdf.cell(0, 10, "In fede, Marianna Battaglia", align='R')

    elif tipo == "FATTURA":
        # RICEVUTA DI PAGAMENTO
        pdf.set_font("Arial", 'B', 16); pdf.cell(0, 10, "RICEVUTA DI PAGAMENTO", ln=1, align='C')
        pdf.ln(10)
        pdf.set_font("Arial", size=11)
        pdf.cell(0, 10, clean_t(f"Cliente: {c.get('cliente')}"), ln=1)
        pdf.cell(0, 10, clean_t(f"Veicolo Targa: {c.get('targa')}"), ln=1)
        pdf.cell(0, 10, clean_t(f"Periodo: dal {c.get('data_inizio')} al {c.get('data_fine')}"), ln=1)
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 15, clean_t(f"TOTALE CORRISPETTO: Euro {c.get('prezzo')}"), border=1, ln=1, align='C')

    else:
        # CONTRATTO DI NOLEGGIO COMPLETO
        pdf.set_font("Arial", 'B', 16); pdf.cell(0, 10, "CONTRATTO DI NOLEGGIO", ln=1, align='C')
        pdf.ln(5)
        pdf.set_font("Arial", size=9)
        pdf.multi_cell(0, 6, clean_t(f"CLIENTE: {c.get('cliente')} | C.F.: {c.get('cf')}\nRESIDENZA: {c.get('residenza')}\nVEICOLO: {c.get('targa')} | PATENTE: {c.get('num_doc')}"), border=1)
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 8); pdf.cell(0, 5, "CONDIZIONI GENERALI (1-14)", ln=1)
        pdf.set_font("Arial", size=6.5)
        clausole = "1. Veicolo in ottimo stato. 2. Danni/Usura a carico cliente. 3. Multe + 25.83 Euro gestione. 4. RESPONSABILITA TOTALE FURTO. 5. Foro Ischia. 6. Casco obbligatorio. 7. Privacy GDPR."
        pdf.multi_cell(0, 4, clean_t(clausole), border='T')
        pdf.ln(10); pdf.cell(0, 10, "Firma del Cliente: ______________________", align='R')

    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACCIA APP ---
st.set_page_config(page_title="MasterRent Ischia", layout="wide")
menu = st.sidebar.radio("Menu", ["📝 Nuovo Noleggio", "🗄️ Archivio", "🚨 Multe"])

if menu == "📝 Nuovo Noleggio":
    with st.form("form_v17"):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Cognome e Nome")
        cf = col2.text_input("Codice Fiscale")
        nascita = col1.text_input("Luogo/Data Nascita")
        residenza = col2.text_input("Residenza")
        patente = col1.text_input("Num. Patente")
        targa = col1.text_input("TARGA").upper()
        tel = col2.text_input("Telefono")
        
        d1, d2, d3, d4 = st.columns(4)
        data_i = d1.date_input("Inizio", datetime.date.today())
        ora_i = d2.text_input("Ora Inizio", "10:00")
        data_f = d3.date_input("Fine", datetime.date.today() + datetime.timedelta(days=1))
        ora_f = d4.text_input("Ora Fine", "10:00")
        prezzo = st.number_input("Prezzo (€)", min_value=0.0)
        
        accetto = st.checkbox("Accetto le 14 clausole (Art. 1341-1342 c.c.)")
        foto = st.camera_input("📸 Patente")
        st_canvas(fill_color="white", stroke_width=2, height=150, key="c_v17")
        
        if st.form_submit_button("💾 SALVA"):
            if accetto:
                fn = f"{targa}_{int(time.time())}.jpg"
                if foto: supabase.storage.from_(BUCKET_NAME).upload(fn, foto.getvalue())
                dat = {"cliente": nome, "cf": cf, "luogo_nascita": nascita, "residenza": residenza, "num_doc": patente, "targa": targa, "prezzo": prezzo, "data_inizio": str(data_i), "ora_inizio": ora_i, "data_fine": str(data_f), "ora_fine": ora_f, "telefono": tel, "foto_path": fn if foto else None}
                supabase.table("contratti").insert(dat).execute()
                st.success("Salvato!")
            else: st.error("Accetta le condizioni!")

elif menu == "🗄️ Archivio":
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"📄 {c['cliente']} - {c['targa']}"):
            col1, col2, col3 = st.columns(3)
            col1.download_button("📜 Contratto", genera_documento(c, "CONTRATTO"), f"C_{c['targa']}.pdf")
            col2.download_button("💰 Ricevuta", genera_documento(c, "FATTURA"), f"R_{c['id']}.pdf")
            tel_c = str(c.get('telefono','')).replace(" ","")
            if tel_c: col3.link_button("💬 WhatsApp", f"https://wa.me/39{tel_c}")

elif menu == "🚨 Multe":
    t_m = st.text_input("Targa").upper()
    if t_m:
        res_m = supabase.table("contratti").select("*").eq("targa", t_m).execute()
        if res_m.data:
            st.download_button("📥 Scarica Accertamento per Vigili", genera_documento(res_m.data[0], "VIGILI"), f"Vigili_{t_m}.pdf")
