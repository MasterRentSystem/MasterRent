import streamlit as st
from supabase import create_client, Client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from fpdf import FPDF
import io
import base64
from datetime import datetime
import urllib.parse

# --- CONFIGURAZIONE DATI DITTA ---
DITTA = "BATTAGLIA RENT"
INDIRIZZO_FISCALE = "Via Cognole n. 5, Forio (NA)"
DATI_IVA = "P.IVA: 10252601215 | C.F.: BTTMNN87A53Z112S"

# --- CONNESSIONE SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# ------------------------------------------------
# UTILITY
# ------------------------------------------------
def safe_text(text):
    """Converte in stringa sicura per il PDF evitando crash"""
    return str(text) if text is not None else ""

def upload_to_supabase(file, targa, prefix):
    try:
        if file is None: return None
        ext = file.name.split('.')[-1]
        # USIAMO FORMAT PER EVITARE L'ERRORE DI CONCATENAZIONE
        nome_f = "{}{}{}.{}".format(prefix, str(targa), datetime.now().strftime("%H%M%S"), ext)
        supabase.storage.from_("documenti").upload(nome_f, file.getvalue())
        return supabase.storage.from_("documenti").get_public_url(nome_f)
    except Exception as e:
        st.error("Errore foto: {}".format(e))
        return None

# ------------------------------------------------
# GENERAZIONE PDF INTEGRALI
# ------------------------------------------------
def genera_pdf_tipo(c, tipo):
    pdf = FPDF()
    pdf.add_page()
    oggi = datetime.now().strftime("%d/%m/%Y")
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, safe_text(DITTA), ln=True)
    pdf.set_font("Arial", "", 8)
    pdf.cell(0, 4, safe_text(INDIRIZZO_FISCALE), ln=True)
    pdf.cell(0, 4, safe_text(DATI_IVA), ln=True)
    pdf.ln(5)

    if tipo == "CONTRATTO":
        pdf.set_font("Arial", "B", 13)
        pdf.cell(0, 10, "CONTRATTO DI NOLEGGIO / RENTAL AGREEMENT", ln=True, align="C", border="B")
        pdf.set_font("Arial", "", 9)
        
        testo = "DATI CLIENTE: {} {} | CF: {}\nVEICOLO: {} | PATENTE: {}\nPERIODO: dal {} al {} | PREZZO: EUR {}\n\n".format(
            safe_text(c.get('nome')), safe_text(c.get('cognome')), safe_text(c.get('codice_fiscale')),
            safe_text(c.get('targa')), safe_text(c.get('numero_patente')),
            safe_text(c.get('inizio')), safe_text(c.get('fine')), safe_text(c.get('prezzo'))
        )
        testo += "1. STATO MEZZO: Il cliente riceve il mezzo in ottimo stato.\n"
        testo += "2. ASSICURAZIONE: Polizza R.C.A. a norma di legge.\n"
        testo += "3. RESPONSABILITA: Il cliente risponde di danni, furto e multe.\n"
        testo += "4. ART 1341-1342: Si approvano i punti 2 e 3.\n\n"
        testo += "Privacy: Si autorizza il trattamento dati (GDPR)."
        
        pdf.multi_cell(0, 5, safe_text(testo))
        if c.get("firma"):
            try:
                f_bytes = base64.b64decode(c["firma"])
                pdf.image(io.BytesIO(f_bytes), x=130, y=pdf.get_y()+5, w=50)
            except: pass
        pdf.ln(25)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 10, "Firma del Cliente per accettazione clausole 2-3", ln=True, align="R")

    elif tipo == "FATTURA":
        prezzo_totale = float(c.get('prezzo', 0))
        imponibile = prezzo_totale / 1.22
        iva = prezzo_totale - imponibile

        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "DOCUMENTO COMMERCIALE", ln=True, align="C", border="B")
        pdf.ln(5)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 6, "N. {}/A del {}".format(safe_text(c.get('numero_fattura')), oggi), ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, "Cliente: {} {}".format(safe_text(c.get('nome')), safe_text(c.get('cognome'))), ln=True)
        pdf.ln(5)

        pdf.set_fill_color(230, 230, 230)
        pdf.cell(90, 8, "Descrizione", 1, 0, 'L', True)
        pdf.cell(30, 8, "Imponibile", 1, 0, 'C', True)
        pdf.cell(20, 8, "IVA", 1, 0, 'C', True)
        pdf.cell(40, 8, "Totale", 1, 1, 'C', True)

        pdf.set_font("Arial", "", 9)
        pdf.cell(90, 8, "Noleggio Scooter {}".format(safe_text(c.get('targa'))), 1)
        pdf.cell(30, 8, "{:.2f}".format(imponibile), 1, 0, 'C')
        pdf.cell(20, 8, "22%", 1, 0, 'C')
        pdf.cell(40, 8, "{:.2f}".format(prezzo_totale), 1, 1, 'C')
        
        pdf.ln(10)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(150, 10, "TOTALE NETTO A PAGARE: EUR {:.2f}".format(prezzo_totale), 0, 1, 'R')

    elif tipo == "MULTE":
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "COMUNICAZIONE DATI CONDUCENTE", ln=True, align="C")
        pdf.ln(5)
        pdf.set_font("Arial", "", 10)
        corpo = "Il veicolo targato {} in data {} era locato a: {} {}. Nato a {} il {}. Residente in {}.".format(
            safe_text(c.get('targa')), safe_text(c.get('inizio')), safe_text(c.get('nome')), 
            safe_text(c.get('cognome')), safe_text(c.get('luogo_nascita')), safe_text(c.get('data_nascita')),
            safe_text(c.get('indirizzo_cliente'))
        )
        pdf.multi_cell(0, 6, safe_text(corpo))

    return pdf.output(dest="S").encode("latin-1")

# ------------------------------------------------
# APP
# ------------------------------------------------
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.title("🔐 Accesso Master Rent")
    pw = st.text_input("Password", type="password")
    if st.button("Accedi"):
        if pw == "1234":
            st.session_state.autenticato = True
            st.rerun()
else:
    menu = st.sidebar.radio("Navigazione", ["Nuovo Noleggio", "Archivio"])

    if menu == "Nuovo Noleggio":
        st.title("🛵 Nuovo Noleggio")
        with st.form("form_noleggio", clear_on_submit=True):
            col1, col2 = st.columns(2)
            nome = col1.text_input("Nome")
            cognome = col1.text_input("Cognome")
            tel = col1.text_input("Telefono")
            cf = col1.text_input("C.F. / ID")
            targa = col2.text_input("Targa").upper()
            pat = col2.text_input("N. Patente")
            l_nas = col2.text_input("Luogo Nascita")
            d_nas = col2.text_input("Data Nascita")
            prezzo = col2.number_input("Prezzo Totale", min_value=0.0)
            inizio = st.date_input("Inizio")
            fine = st.date_input("Fine")
            ind = st.text_area("Indirizzo Residenza")
            fronte = st.file_uploader("Fronte Patente")
            retro = st.file_uploader("Retro Patente")
            c1 = st.checkbox("Mezzo OK")
            c2 = st.checkbox("Accetto Danni/Multe")
            c3 = st.checkbox("Privacy")
            canvas = st_canvas(stroke_width=3, stroke_color="#000", background_color="#eee", height=150, width=400, key="firma")
            
            if st.form_submit_button("💾 SALVA"):
                if c1 and c2 and c3 and nome and targa:
                    try:
                        f_b64 = ""
                        if canvas.image_data is not None:
                            img = Image.fromarray(canvas.image_data.astype("uint8"))
                            buf = io.BytesIO()
                            img.save(buf, format="PNG")
                            f_b64 = base64.b64encode(buf.getvalue()).decode()

                        u_f = upload_to_supabase(fronte, targa, "fronte")
                        u_r = upload_to_supabase(retro, targa, "retro")
                        
                        last = supabase.table("contratti").select("numero_fattura").order("id", desc=True).limit(1).execute()
                        n_f = (last.data[0]['numero_fattura'] + 1) if last.data else 1

                        dati = {
                            "nome": str(nome), "cognome": str(cognome), "telefono": str(tel), "targa": str(targa),
                            "prezzo": float(prezzo), "inizio": str(inizio), "fine": str(fine),
                            "firma": str(f_b64), "numero_fattura": int(n_f), "luogo_nascita": str(l_nas),
                            "data_nascita": str(d_nas), "numero_patente": str(pat), "url_fronte": str(u_f),
                            "url_retro": str(u_r), "codice_fiscale": str(cf), "indirizzo_cliente": str(ind)
                        }
                        supabase.table("contratti").insert(dati).execute()
                        st.success("Salvato!")
                        st.rerun()
                    except Exception as e: st.error("Errore: {}".format(e))

    else:
        st.title("📂 Archivio")
        try:
            res = supabase.table("contratti").select("*").order("id", desc=True).execute()
            if res.data:
                cerca = st.text_input("Cerca").lower()
                for c in res.data:
                    t_l = str(c.get('targa', ''))
                    c_l = str(c.get('cognome', '')).upper()
                    if cerca in (t_l + " " + c_l).lower():
                        with st.expander("📝 {} - {}".format(t_l, c_l)):
                            col_p1, col_p2, col_p3 = st.columns(3)
                            col_p1.download_button("📜 Contratto", genera_pdf_tipo(c, "CONTRATTO"), "Cont_{}.pdf".format(t_l))
                            col_p2.download_button("💰 Fattura", genera_pdf_tipo(c, "FATTURA"), "Fatt_{}.pdf".format(t_l))
                            col_p3.download_button("🚨 Multe", genera_pdf_tipo(c, "MULTE"), "Multe_{}.pdf".format(t_l))
                            if c.get("url_fronte"): st.image(c["url_fronte"])
        except Exception as e: st.error("Errore: {}".format(e))
