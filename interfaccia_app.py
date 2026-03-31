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

# INTESTAZIONE UFFICIALE (Come da tue foto)
DITTA_NOME = "BATTAGLIA MARIANNA"
DITTA_INFO = "Via Cognole, 5 - 80075 Forio (NA)\nCod. Fisc. BTTMNN87A53Z112S - P. IVA 10252601215"

def clean_t(text):
    if not text or text == "None": return "---"
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in repls.items(): text = str(text).replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

# --- GENERATORE PDF MIGLIORATO ---
def genera_documento(c, tipo="CONTRATTO"):
    pdf = fpdf.FPDF()
    pdf.add_page()
    
    # INTESTAZIONE FISSA (Presente in ogni PDF)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 7, clean_t(DITTA_NOME), ln=1, align='L')
    pdf.set_font("Arial", size=9)
    pdf.multi_cell(0, 5, clean_t(DITTA_INFO), align='L')
    pdf.line(10, 30, 200, 30) # Linea estetica
    pdf.ln(12)
    
    # TITOLO DOCUMENTO
    pdf.set_font("Arial", 'B', 16)
    if tipo == "CONTRATTO": t = "CONTRATTO DI NOLEGGIO"
    elif tipo == "VIGILI": t = "DICHIARAZIONE DATI CONDUCENTE / ACCERTAMENTO"
    else: t = "RICEVUTA DI PAGAMENTO"
    pdf.cell(0, 10, clean_t(t), ln=1, align='C')
    pdf.ln(5)
    
    # DATI CLIENTE E PERIODO
    pdf.set_font("Arial", 'B', 10); pdf.cell(0, 7, "DETTAGLI DEL NOLEGGIO", ln=1)
    pdf.set_font("Arial", size=9)
    data_box = (
        f"CLIENTE: {c.get('cliente')} | C.F.: {c.get('cf')}\n"
        f"NATO A: {c.get('luogo_nascita')} | RESIDENTE: {c.get('residenza')}\n"
        f"TARGA VEICOLO: {c.get('targa')} | PATENTE: {c.get('num_doc')}\n"
        f"INIZIO: {c.get('data_inizio')} ore {c.get('ora_inizio')} | FINE: {c.get('data_fine')} ore {c.get('ora_fine')}"
    )
    pdf.multi_cell(0, 6, clean_t(data_box), border=1)
    pdf.ln(5)
    
    if tipo == "CONTRATTO":
        pdf.set_font("Arial", 'B', 8); pdf.cell(0, 5, "CONDIZIONI GENERALI DI CONTRATTO (Art. 1-14)", ln=1)
        pdf.set_font("Arial", size=7)
        clausole = (
            "1. Veicolo in ottimo stato. 2. Responsabilita danni/usura. 3. Sanzioni C.d.S. a carico cliente + 25.83 Euro gestione.\n"
            "4. RESPONSABILITA TOTALE PER FURTO E INCENDIO. 5. Obbligo comunicazione verbali entro 2gg.\n"
            "6. Copertura R.C.A. terzi. 7. Oggetti smarriti non rimborsabili. 8. Guasti meccanici fortuiti esclusi.\n"
            "9. FORO COMPETENTE: ISCHIA. 10. Uso casco obbligatorio (Fermo 90gg a carico cliente).\n"
            "11. Addebito sanzioni su carta. 12. Furto chiavi a carico cliente. 13. Denuncia immediata sinistri.\n"
            "14. PRIVACY: Autorizzazione trattamento dati e foto patente ai fini di Pubblica Sicurezza (GDPR)."
        )
        pdf.multi_cell(0, 4, clean_t(clausole), border='T')
        pdf.ln(10); pdf.set_font("Arial", 'B', 10); pdf.cell(0, 10, "Firma del Cliente per Accettazione: ______________________", align='R')
    
    elif tipo == "VIGILI":
        pdf.ln(5); pdf.set_font("Arial", size=11)
        testo_vigili = (
            f"Il sottoscritto titolare della ditta MasterRent, dichiara che il veicolo targa {c.get('targa')},\n"
            f"nel periodo indicato era affidato al Sig. {c.get('cliente')},\n"
            f"sopra identificato, il quale si assume ogni responsabilita civile e penale per la guida."
        )
        pdf.multi_cell(0, 7, clean_t(testo_vigili))
        pdf.ln(15); pdf.cell(0, 10, "Timbro e Firma MasterRent: ______________________", align='L')

    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACCIA STREAMLIT ---
st.set_page_config(page_title="MasterRent Ischia", layout="wide")
st.title("🛵 MasterRent - Gestione Contratti")

menu = st.sidebar.radio("Menu Principale", ["📝 Registra Noleggio", "🗄️ Archivio", "🚨 Modulo Multe"])

if menu == "📝 Registra Noleggio":
    with st.form("main_form_v16"):
        st.subheader("Dati Anagrafici e Mezzo")
        col1, col2 = st.columns(2)
        nome = col1.text_input("Cognome e Nome")
        cf = col2.text_input("Codice Fiscale")
        nascita = col1.text_input("Luogo e Data di Nascita")
        residenza = col2.text_input("Residenza")
        patente = col1.text_input("Numero Patente")
        scadenza_p = col2.date_input("Scadenza Patente")
        targa = col1.text_input("TARGA").upper()
        tel = col2.text_input("Telefono (per WhatsApp)", help="Es: 3331234567")
        
        st.divider()
        st.subheader("Periodo e Prezzo")
        d1, d2, d3, d4 = st.columns(4)
        data_i = d1.date_input("Data Inizio", datetime.date.today())
        ora_i = d2.text_input("Ora Inizio", "10:00")
        data_f = d3.date_input("Data Fine", datetime.date.today() + datetime.timedelta(days=1))
        ora_f = d4.text_input("Ora Fine", "10:00", key="ora_f_new")
        prezzo = st.number_input("Prezzo Totale (€)", min_value=0.0)
        
        st.warning("*CONTRATTO:* Il cliente accetta le clausole 1-14, la responsabilita per FURTO/DANNI e le sanzioni del C.d.S.")
        accetto = st.checkbox("CONFERMO DI AVER LETTO E ACCETTO LE CONDIZIONI GENERALI")
        
        foto = st.camera_input("📸 Foto Patente")
        st.write("✍️ *Firma Cliente*")
        st_canvas(fill_color="white", stroke_width=2, height=150, key="canvas_v16")
        
        if st.form_submit_button("💾 SALVA E GENERA CONTRATTO"):
            if not accetto: st.error("Bisogna accettare le clausole!")
            else:
                fn = f"{targa}_{int(time.time())}.jpg"
                if foto: supabase.storage.from_(BUCKET_NAME).upload(fn, foto.getvalue())
                dat = {"cliente": nome, "cf": cf, "luogo_nascita": nascita, "residenza": residenza, 
                       "num_doc": patente, "scadenza_patente": str(scadenza_p), "targa": targa, "prezzo": prezzo,
                       "data_inizio": str(data_i), "ora_inizio": ora_i, "data_fine": str(data_f), "ora_fine": ora_f, 
                       "foto_path": fn if foto else None, "telefono": tel}
                supabase.table("contratti").insert(dat).execute()
                st.success("Noleggio Registrato con Successo!")

elif menu == "🗄️ Archivio":
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"📄 {c['cliente']} - {c['targa']} ({c['data_inizio']})"):
            c1, c2, c3, c4 = st.columns([1,1,1,1.5])
            c1.download_button("📜 Contratto", genera_documento(c, "CONTRATTO"), f"C_{c['targa']}.pdf")
            c2.download_button("💰 Fattura", genera_documento(c, "FATTURA"), f"F_{c['id']}.pdf")
            if c.get("foto_path"):
                u = supabase.storage.from_(BUCKET_NAME).get_public_url(c["foto_path"])
                c3.link_button("📸 Patente", u)
            
            # WhatsApp Diretto
            tel_clean = str(c.get('telefono', '')).replace(" ", "").replace("+39", "")
            if tel_clean:
                testo = urllib.parse.quote(f"Ciao {c['cliente']}, MasterRent ti invia il riepilogo: Targa {c['targa']}, riconsegna il {c['data_fine']} ore {c['ora_fine']}. Grazie!")
                c4.link_button("💬 WhatsApp", f"https://wa.me/39{tel_clean}?text={testo}")

elif menu == "🚨 Modulo Multe":
    t_m = st.text_input("Inserisci Targa per accertamento").upper()
    if t_m:
        res_m = supabase.table("contratti").select("*").eq("targa", t_m).execute()
        if res_m.data:
            st.success(f"Trovato: {res_m.data[0]['cliente']}")
            st.download_button("📥 Scarica Modulo per Vigili", genera_documento(res_m.data[0], "VIGILI"), f"Accertamento_{t_m}.pdf")
