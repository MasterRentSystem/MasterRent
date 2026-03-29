import streamlit as st
import datetime
import fpdf
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
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
INFO_MARIANNA = "BATTAGLIA MARIANNA\nNata a Berlino (Germania) il 13/01/1987\nResidente in Forio alla Via Cognole n. 5\nC.F.: BTTMNN87A53Z112S | P.IVA: 10252601215"
PRIVACY = "INFORMATIVA PRIVACY: I dati sono trattati ai sensi del Reg. UE 2016/679 (GDPR) per la gestione del noleggio."
CLAUSOLE = "APPROVAZIONE CLAUSOLE: Ai sensi degli artt. 1341 e 1342 c.c. il Cliente approva: Art. 3 (Multe), Art. 5 (Danni)."

def genera_pdf_contratto(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 10); pdf.multi_cell(0, 5, txt=clean_t(INFO_MARIANNA))
    pdf.ln(8); pdf.set_font("Arial", 'B', 16); pdf.cell(0, 10, clean_t("CONTRATTO DI NOLEGGIO"), ln=1, align='C')
    pdf.ln(5); pdf.set_font("Arial", size=11)
    testo = f"Cliente: {c['cliente']}\nCF: {c.get('cf','')}\nNato a: {c.get('luogo_nascita','')}\nDoc: {c.get('num_doc','')}\n\nVEICOLO: {c['targa']}\nPERIODO: dal {c.get('data_inizio','')} al {c.get('data_fine','')}\nPREZZO: {c.get('prezzo', 0)} Euro"
    pdf.multi_cell(0, 7, txt=clean_t(testo))
    pdf.ln(10); pdf.set_font("Arial", 'B', 9); pdf.cell(0, 5, clean_t("PRIVACY E CLAUSOLE"), ln=1)
    pdf.set_font("Arial", size=8); pdf.multi_cell(0, 4, txt=clean_t(f"{PRIVACY}\n\n{CLAUSOLE}"))
    pdf.ln(15); pdf.cell(0, 10, clean_t("Firma Cliente: ________________________"), ln=1)
    return pdf.output(dest='S').encode('latin-1')

def genera_pdf_multe(c):
    pdf = fpdf.FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10); pdf.multi_cell(0, 5, txt=clean_t(INFO_MARIANNA))
    pdf.ln(10); pdf.set_font("Arial", 'B', 12); pdf.cell(0, 7, clean_t("DICHIARAZIONE PER VERBALE DI MULTA"), ln=1, align='C')
    pdf.ln(10); pdf.set_font("Arial", size=11)
    testo = f"Si dichiara che il veicolo {c['targa']} nel periodo dal {c.get('data_inizio','')} al {c.get('data_fine','')}\nera locato a:\n\nSOGGETTO: {c['cliente']}\nCF: {c.get('cf','')}\nNATO A: {c.get('luogo_nascita','')}\nPATENTE: {c.get('num_doc','')}"
    pdf.multi_cell(0, 7, txt=clean_t(testo))
    pdf.ln(20); pdf.cell(0, 10, "In fede, Marianna Battaglia", align='R')
    return pdf.output(dest='S').encode('latin-1')

st.sidebar.title("🚀 MasterRent")
menu = st.sidebar.radio("Menu", ["📝 Nuovo Noleggio", "🗄️ Archivio Documenti"])

if menu == "📝 Nuovo Noleggio":
    st.header("Nuovo Noleggio")
    c1, c2 = st.columns(2)
    cliente = c1.text_input("Nome Cliente")
    cf = c2.text_input("Codice Fiscale")
    nascita = c1.text_input("Luogo/Data Nascita")
    num_doc = c2.text_input("Numero Patente")
    targa = c1.text_input("TARGA").upper()
    prezzo = c2.number_input("Prezzo (€)", min_value=0.0)
    d_ini = c1.date_input("Inizio Noleggio", datetime.date.today())
    d_fin = c2.date_input("Fine Noleggio", datetime.date.today() + datetime.timedelta(days=1))
    tel = c1.text_input("Telefono (per WhatsApp)")

    st.camera_input("📸 Foto Patente")
    st_canvas(fill_color="white", stroke_width=2, height=150, key="sig_arch")

    if st.button("💾 SALVA E ARCHIVIA"):
        if cliente and targa:
            try:
                dat = {"cliente": cliente, "cf": cf, "luogo_nascita": nascita, "num_doc": num_doc, "targa": targa, "prezzo": prezzo, "data_inizio": str(d_ini), "data_fine": str(d_fin), "telefono": tel}
                supabase.table("contratti").insert(dat).execute()
                st.success("Archiviato! Vai in 'Archivio Documenti' per scaricare i PDF.")
            except Exception as e: st.error(f"Errore: {e}")
        else: st.warning("Mancano Nome o Targa!")

elif menu == "🗄️ Archivio Documenti":
    st.header("🔎 Ricerca Contratti")
    t_search = st.text_input("INSERISCI TARGA").upper()
    if t_search:
        res = supabase.table("contratti").select("*").eq("targa", t_search).execute()
        if res.data:
            for c in res.data:
                with st.expander(f"📂 {c['cliente']} (Periodo: {c.get('data_inizio','')} - {c.get('data_fine','')})"):
                    p_con = genera_pdf_contratto(c)
                    p_mul = genera_pdf_multe(c)
                    col1, col2 = st.columns(2)
                    col1.download_button("📄 Scarica Contratto", p_con, f"Contratto_{c['targa']}.pdf", key=f"c_{c['id']}")
                    col2.download_button("🚨 Modulo per Multe", p_mul, f"Multe_{c['targa']}.pdf", key=f"m_{c['id']}")
                    if c.get('telefono'):
                        msg = urllib.parse.quote(f"Ciao {c['cliente']}, ecco il tuo contratto.")
                        st.link_button("📲 Invia su WhatsApp", f"https://wa.me/{c['telefono']}?text={msg}")
        else: st.warning("Nessun noleggio trovato per questa targa.")
