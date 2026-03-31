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

# DATI AZIENDALI DA CARTA INTESTATA
DITTA = "BATTAGLIA MARIANNA"
INDIRIZZO = "Via Cognole, 5 - 80075 Forio (NA)"
PIVA = "10252601215"
TESTO_INTESTAZIONE = f"{DITTA}\n{INDIRIZZO}\nP. IVA {PIVA}"

def clean_t(text):
    if not text or text == "None": return "---"
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in repls.items(): text = str(text).replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

# --- MOTORE PDF CON 14 CLAUSOLE ---
def genera_contratto_legale(c, tipo="CONTRATTO"):
    pdf = fpdf.FPDF()
    pdf.add_page()
    
    # Intestazione
    pdf.set_font("Arial", 'B', 11)
    pdf.multi_cell(0, 5, txt=clean_t(TESTO_INTESTAZIONE), align='L')
    pdf.ln(5)
    
    # Titolo e Numero Contratto
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, clean_t(f"CONTRATTO DI NOLEGGIO N. {c.get('id', '_')}"), ln=1, align='C')
    pdf.ln(5)
    
    # Dati Cliente
    pdf.set_font("Arial", size=9)
    pdf.multi_cell(0, 6, txt=clean_t(f"Il sottoscritto {c.get('cliente')} nato a {c.get('luogo_nascita')} residnete in {c.get('residenza')}\nCod. Fisc: {c.get('cf')} | Patente: {c.get('num_doc')}"), border=1)
    pdf.ln(2)
    
    # Dati Veicolo e Orari
    pdf.multi_cell(0, 6, txt=clean_t(f"VEICOLO TARGA: {c.get('targa')} | Prezzo: {c.get('prezzo')} Euro\n"
                                   f"NOLEGGIO DALLE ORE: {c.get('ora_inizio')} DEL GIORNO {c.get('data_inizio')}\n"
                                   f"ALLE ORE: {c.get('ora_fine')} DEL GIORNO {c.get('data_fine')}"), border=1)
    pdf.ln(5)
    
    if tipo == "CONTRATTO":
        # CONDIZIONI GENERALI (Sintesi dei 14 punti dalle tue foto)
        pdf.set_font("Arial", 'B', 8); pdf.cell(0, 5, "CONDIZIONI GENERALI DEL CONTRATTO", ln=1)
        pdf.set_font("Arial", size=6.5)
        clausole = (
            "1) La ditta concede in locazione il veicolo sopra indicato. 2) Il cliente dichiara di riceverlo in perfetto stato.\n"
            "3) Il cliente e responsabile di tutti i danni al veicolo per uso improprio o usura sproporzionata. 4) Responsabilita totale in caso di FURTO.\n"
            "5) Pagamento sanzioni: le multe occorse durante il noleggio sono a carico del cliente, oltre € 25.83 per gestione amministrativa.\n"
            "6) Il cliente deve comunicare ogni verbale entro 2 giorni. 7) Il veicolo e coperto da polizza R.C.A. verso terzi.\n"
            "8) La ditta non e responsabile per oggetti lasciati nel veicolo. 9) Esclusione responsabilita per guasti meccanici fortuiti.\n"
            "10) Per ogni controversia il foro competente e quello di ISCHIA. 11) Autorizzazione addebito sanzioni su carta di credito.\n"
            "12) Obbligo uso casco: in mancanza e previsto fermo amministrativo di 90gg a carico del cliente. 13) Responsabilita esclusiva per furto chiavi.\n"
            "14) Obbligo denuncia immediata in caso di sinistro o furto. In mancanza, il cliente risponde di ogni danno subito dalla ditta."
        )
        pdf.multi_cell(0, 4, txt=clean_t(clausole), border='T')
        
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 7)
        pdf.multi_cell(0, 4, txt=clean_t("Ai sensi e per gli effetti degli artt. 1341 e 1342 c.c. il Cliente dichiara di approvare specificamente i punti: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14."))
        
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 10, "Firma del Cliente: ______________________", align='R')
    
    return pdf.output(dest='S').encode('latin-1')

# --- APP ---
st.set_page_config(page_title="MasterRent - Contratto Legale", layout="centered")

menu = st.sidebar.radio("Menu", ["📝 Nuovo Noleggio", "🗄️ Archivio"])

if menu == "📝 Nuovo Noleggio":
    st.header("Nuovo Contratto MasterRent")
    with st.form("legale_form"):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Cognome e Nome")
        cf = c2.text_input("Codice Fiscale")
        nascita = c1.text_input("Luogo e Data Nascita")
        residenza = c2.text_input("Residenza")
        num_pat = c1.text_input("Num. Patente")
        targa = c2.text_input("TARGA").upper()
        
        st.divider()
        d1, d2, d3, d4 = st.columns(4)
        data_i = d1.date_input("Inizio", datetime.date.today())
        ora_i = d2.text_input("Ore Inizio", "10:00")
        data_f = d3.date_input("Fine", datetime.date.today() + datetime.timedelta(days=1))
        ora_f = d4.text_input("Ore Fine", "10:00")
        
        prezzo = st.number_input("Prezzo Totale (€)", min_value=0.0)
        
        st.error("*CONDIZIONI:* Il cliente dichiara di aver letto le 14 clausole (Art. 1341-1342 cc) e accetta responsabilita per FURTO, DANNI e MULTE.")
        
        foto = st.camera_input("📸 Foto Patente")
        st.write("✍️ *Firma Digitale*")
        st_canvas(fill_color="white", stroke_width=2, height=150, key="sign_v14")
        
        if st.form_submit_button("CONFERMA E SALVA"):
            fn = f"{targa}_{int(time.time())}.jpg"
            if foto: supabase.storage.from_(BUCKET_NAME).upload(fn, foto.getvalue())
            
            dat = {
                "cliente": nome, "cf": cf, "luogo_nascita": nascita, "residenza": residenza, 
                "num_doc": num_pat, "targa": targa, "prezzo": prezzo,
                "data_inizio": str(data_i), "ora_inizio": ora_i,
                "data_fine": str(data_f), "ora_fine": ora_f, "foto_path": fn if foto else None
            }
            supabase.table("contratti").insert(dat).execute()
            st.success("Contratto Salvato!")

elif menu == "🗄️ Archivio":
    st.header("Archivio Contratti")
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"{c['cliente']} - {c['targa']} ({c['data_inizio']})"):
            c1, c2 = st.columns(2)
            c1.download_button("📜 Scarica Contratto", genera_contratto_legale(c), f"Contratto_{c['targa']}.pdf")
            if c.get("foto_path"):
                u = supabase.storage.from_(BUCKET_NAME).get_public_url(c["foto_path"])
                c2.link_button("📸 Vedi Patente", u)
