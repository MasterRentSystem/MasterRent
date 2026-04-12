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
    """Converte qualsiasi dato in stringa sicura per il PDF"""
    if text is None: return ""
    return str(text).encode("latin-1", "replace").decode("latin-1")

def upload_to_supabase(file, targa, prefix):
    try:
        if file is None: return None
        ext = file.name.split('.')[-1]
        # Trasformiamo targa in stringa per sicurezza nel nome file
        targa_str = str(targa)
        nome_f = prefix + "" + targa_str + "" + datetime.now().strftime("%H%M%S") + "." + ext
        supabase.storage.from_("documenti").upload(nome_f, file.getvalue())
        return supabase.storage.from_("documenti").get_public_url(nome_f)
    except Exception as e:
        st.error("Errore caricamento foto: " + str(e))
        return None

# ------------------------------------------------
# GENERAZIONE PDF INTEGRALI (VERSIONE LUNGA CORRETTA)
# ------------------------------------------------
def genera_pdf_tipo(c, tipo):
    pdf = FPDF()
    pdf.add_page()
    oggi = datetime.now().strftime("%d/%m/%Y")
    
    # Intestazione Professionale
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, safe_text(DITTA), ln=True)
    pdf.set_font("Arial", "", 8)
    pdf.cell(0, 4, safe_text(INDIRIZZO_FISCALE), ln=True)
    pdf.cell(0, 4, safe_text(DATI_IVA), ln=True)
    pdf.ln(5)

    # Trasformiamo i dati principali in stringhe subito
    nome_c = safe_text(c.get('nome'))
    cognome_c = safe_text(c.get('cognome'))
    targa_c = safe_text(c.get('targa'))
    prezzo_c = safe_text(c.get('prezzo', '0'))
    inizio_c = safe_text(c.get('inizio'))
    fine_c = safe_text(c.get('fine'))
    nfatt_c = safe_text(c.get('numero_fattura'))

    if tipo == "CONTRATTO":
        pdf.set_font("Arial", "B", 13)
        pdf.cell(0, 10, "CONTRATTO DI NOLEGGIO / RENTAL AGREEMENT", ln=True, align="C", border="B")
        pdf.set_font("Arial", "", 9)
        
        testo_completo = "DATI CLIENTE: " + nome_c + " " + cognome_c + " | CF/ID: " + safe_text(c.get('codice_fiscale')) + "\n" + \
                         "VEICOLO: " + targa_c + " | PATENTE: " + safe_text(c.get('numero_patente')) + "\n" + \
                         "PERIODO: dal " + inizio_c + " al " + fine_c + " | PREZZO: EUR " + prezzo_c + "\n\n" + \
                         "CONDIZIONI GENERALI DI CONTRATTO:\n" + \
                         "1. STATO DEL MEZZO: Il cliente dichiara di aver visionato il mezzo e di riceverlo in ottimo stato manutentivo, con il pieno di carburante e privo di danni non segnalati. Il cliente si impegna a riconsegnare il veicolo nelle stesse condizioni, salvo la normale usura.\n" + \
                         "2. ASSICURAZIONE: Il veicolo è coperto da polizza R.C.A. a norma di legge. Sono esclusi dalla copertura i danni al conducente e i danni causati per dolo o colpa grave (es. guida in stato di ebbrezza, sotto effetto di stupefacenti o violazioni gravi del CdS).\n" + \
                         "3. RESPONSABILITA: Il cliente è pienamente responsabile per danni al veicolo, furto (risponde per l'intero valore del mezzo in caso di mancata riconsegna delle chiavi o negligenza) e per tutte le contravvenzioni (multe) elevate nel periodo di locazione.\n" + \
                         "4. CLAUSOLE VESSATORIE: Ai sensi e per gli effetti degli art. 1341-1342 c.c. il cliente dichiara di aver letto e approvato specificamente i punti 2 e 3 del presente contratto relativi a Limitazioni di Responsabilità, Furto, Danni e Sanzioni Amministrative.\n\n" + \
                         "Informativa Privacy (GDPR): Il cliente autorizza il trattamento dei dati personali ai sensi del Regolamento UE 2016/679 e la conservazione dei documenti d'identità per le finalità legate all'esecuzione del contratto e per eventuali comunicazioni obbligatorie alle autorità competenti."
        
        pdf.multi_cell(0, 5, safe_text(testo_completo))
        if c.get("firma"):
            try:
                f_bytes = base64.b64decode(c["firma"])
                pdf.image(io.BytesIO(f_bytes), x=130, y=pdf.get_y()+5, w=50)
            except: pass
        pdf.ln(25)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 10, "Firma del Cliente per accettazione e approvazione specifica clausole 2-3 (Art. 1341 c.c.)", ln=True, align="R")

    elif tipo == "FATTURA":
        prezzo_totale = float(c.get('prezzo', 0))
        imponibile = prezzo_totale / 1.22
        iva = prezzo_totale - imponibile

        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "DOCUMENTO COMMERCIALE DI VENDITA O PRESTAZIONE", ln=True, align="C", border="B")
        pdf.ln(5)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 6, "N. " + nfatt_c + "/A del " + oggi, ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, "Spett.le " + nome_c + " " + cognome_c, ln=True)
        pdf.cell(0, 6, "Codice Fiscale/P.IVA Cliente: " + safe_text(c.get('codice_fiscale', '---')), ln=True)
        pdf.ln(5)

        pdf.set_fill_color(230, 230, 230)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(90, 8, "Descrizione Servizio", 1, 0, 'L', True)
        pdf.cell(20, 8, "Qta", 1, 0, 'C', True)
        pdf.cell(30, 8, "Prezzo Un.", 1, 0, 'C', True)
        pdf.cell(20, 8, "IVA", 1, 0, 'C', True)
        pdf.cell(30, 8, "Importo", 1, 1, 'C', True)

        pdf.set_font("Arial", "", 9)
        desc_servizio = "Noleggio Scooter (Targa: " + targa_c + ") - dal " + inizio_c + " al " + fine_c
        pdf.cell(90, 8, safe_text(desc_servizio), 1)
        pdf.cell(20, 8, "1", 1, 0, 'C')
        pdf.cell(30, 8, "{:.2f}".format(imponibile), 1, 0, 'C')
        pdf.cell(20, 8, "22%", 1, 0, 'C')
        pdf.cell(30, 8, "{:.2f}".format(imponibile), 1, 1, 'C')
        
        pdf.ln(10)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(150, 7, "Totale Imponibile:", 0, 0, 'R')
        pdf.cell(40, 7, "EUR " + "{:.2f}".format(imponibile), 0, 1, 'R')
        pdf.cell(150, 7, "IVA (22%):", 0, 0, 'R')
        pdf.cell(40, 7, "EUR " + "{:.2f}".format(iva), 0, 1, 'R')
        pdf.ln(2)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(150, 10, "TOTALE NETTO A PAGARE:", 0, 0, 'R')
        pdf.cell(40, 10, "EUR " + "{:.2f}".format(prezzo_totale), 'T', 1, 'R')

    elif tipo == "MULTE":
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "COMUNICAZIONE DATI CONDUCENTE (L. 445/2000)", ln=True, align="C")
        pdf.ln(5)
        pdf.set_font("Arial", "", 10)
        corpo_multe = "La sottoscritta BATTAGLIA MARIANNA, titolare della ditta individuale BATTAGLIA RENT, " + \
                      "in riferimento al Verbale di accertamento violazione indicato, DICHIARA ai sensi della L. 445/2000 " + \
                      "che il veicolo targato " + targa_c + " nel giorno " + inizio_c + " era concesso in locazione a:\n\n" + \
                      "COGNOME E NOME: " + nome_c + " " + cognome_c + "\n" + \
                      "NATO A: " + safe_text(c.get('luogo_nascita')) + " IL " + safe_text(c.get('data_nascita')) + "\n" + \
                      "RESIDENTE IN: " + safe_text(c.get('indirizzo_cliente')) + "\n" + \
                      "IDENTIFICATO A MEZZO PATENTE: " + safe_text(c.get('numero_patente')) + "\n\n" + \
                      "Si allega: Copia del contratto di locazione e documento del trasgressore.\nIn fede, Marianna Battaglia"
        pdf.multi_cell(0, 6, safe_text(corpo_multe))

    return pdf.output(dest="S").encode("latin-1")

# ------------------------------------------------
# LOGICA APP STREAMLIT (INTEGRALE)
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
            tel = col1.text_input("Telefono (es. 39...)")
            cf = col1.text_input("C.F. / ID")
            targa = col2.text_input("Targa").upper()
            pat = col2.text_input("N. Patente")
            l_nas = col2.text_input("Luogo Nascita")
            d_nas = col2.text_input("Data Nascita")
            prezzo = col2.number_input("Prezzo Totale (€)", min_value=0.0)
            
            d_col1, d_col2 = st.columns(2)
            inizio = d_col1.date_input("Inizio Noleggio")
            fine = d_col2.date_input("Fine Noleggio")
            ind = st.text_area("Indirizzo di Residenza Completo")
            
            st.subheader("📸 Documenti d'Identità")
            f1, f2 = st.columns(2)
            fronte = f1.file_uploader("Fronte Patente", type=["jpg", "png", "jpeg"])
            retro = f2.file_uploader("Retro Patente", type=["jpg", "png", "jpeg"])
            
            st.subheader("⚖️ Accettazione Legale")
            check1 = st.checkbox("Mezzo in ottimo stato")
            check2 = st.checkbox("Accetto clausole Responsabilità/Multe (Art. 1341)")
            check3 = st.checkbox("Consenso Privacy e RCA")
            
            canvas = st_canvas(stroke_width=3, stroke_color="#000", background_color="#eee", height=150, width=400, key="firma")
            
            if st.form_submit_button("💾 SALVA E GENERA"):
                if check1 and check2 and check3 and nome and targa:
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
                        st.success("Salvato correttamente!")
                        st.rerun()
                    except Exception as e: st.error("Errore salvataggio: " + str(e))
                else: st.warning("Compila i campi obbligatori.")

    else:
        st.title("📂 Archivio Contratti")
        try:
            res = supabase.table("contratti").select("*").order("id", desc=True).execute()
            if res.data:
                cerca = st.text_input("🔍 Cerca per Targa o Cognome").lower()
                for c in res.data:
                    # FISSA ERRORE CONCATENAZIONE USANDO STR()
                    t_l = str(c.get('targa', ''))
                    c_l = str(c.get('cognome', '')).upper()
                    nf_str = str(c.get('numero_fattura', ''))
                    id_str = str(c.get('id', ''))
                    
                    if cerca in (t_l + " " + c_l).lower():
                        with st.expander("📝 " + t_l + " - " + c_l + " (Fatt. N. " + nf_str + ")"):
                            col_p1, col_p2, col_p3 = st.columns(3)
                            col_p1.download_button("📜 Contratto", genera_pdf_tipo(c, "CONTRATTO"), "Cont_" + t_l + ".pdf")
                            col_p2.download_button("💰 Fattura", genera_pdf_tipo(c, "FATTURA"), "Fatt_" + t_l + ".pdf")
                            col_p3.download_button("🚨 Multe", genera_pdf_tipo(c, "MULTE"), "Multe_" + t_l + ".pdf")
                            
                            st.write("---")
                            i1, i2 = st.columns(2)
                            if c.get("url_fronte"): i1.image(c["url_fronte"], caption="Fronte")
                            if c.get("url_retro"): i2.image(c["url_retro"], caption="Retro")
                            
                            tel_cl = str(c.get('telefono', ''))
                            if tel_cl:
                                n_cl = str(c.get('nome', ''))
                                t_cl = str(c.get('targa', ''))
                                msg_wa = urllib.parse.quote("Buongiorno " + n_cl + ", ecco i documenti Battaglia Rent per lo scooter " + t_cl + ".")
                                st.markdown("[💬 WhatsApp](https://wa.me/" + tel_cl + "?text=" + msg_wa + ")")
        except Exception as e: st.error("Errore: " + str(e))
