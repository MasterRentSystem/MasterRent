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
# PROTEZIONE TOTALE CONTRO ERRORE CONCATENAZIONE
# ------------------------------------------------
def to_str(val):
    """Forza qualsiasi valore a diventare una stringa, gestendo i None"""
    if val is None:
        return ""
    return str(val)

def pdf_s(text):
    """Rende il testo sicuro per i caratteri FPDF"""
    return to_str(text).encode("latin-1", "replace").decode("latin-1")

def upload_to_supabase(file, targa, prefix):
    try:
        if file is None: return None
        ext = to_str(file.name).split('.')[-1]
        targa_p = to_str(targa).replace(" ", "")
        ora = datetime.now().strftime("%H%M%S")
        # NESSUN SEGNO + PER EVITARE L'ERRORE
        nome_f = f"{prefix}{targa_p}{ora}.{ext}"
        supabase.storage.from_("documenti").upload(nome_f, file.getvalue())
        return supabase.storage.from_("documenti").get_public_url(nome_f)
    except Exception as e:
        st.error(f"Errore caricamento foto: {e}")
        return None

# ------------------------------------------------
# GENERAZIONE PDF INTEGRALI (VERSIONE MASSIMA ESTESA)
# ------------------------------------------------
def genera_pdf_tipo(c, tipo):
    pdf = FPDF()
    pdf.add_page()
    oggi = datetime.now().strftime("%d/%m/%Y")
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, pdf_s(DITTA), ln=True)
    pdf.set_font("Arial", "", 8)
    pdf.cell(0, 4, pdf_s(INDIRIZZO_FISCALE), ln=True)
    pdf.cell(0, 4, pdf_s(DATI_IVA), ln=True)
    pdf.ln(5)

    if tipo == "CONTRATTO":
        pdf.set_font("Arial", "B", 13)
        pdf.cell(0, 10, "CONTRATTO DI NOLEGGIO / RENTAL AGREEMENT", ln=True, align="C", border="B")
        pdf.set_font("Arial", "", 9)
        
        # Testo Legale Integrale
        clausole = f"""
DATI CLIENTE: {to_str(c.get('nome'))} {to_str(c.get('cognome'))} | CF/ID: {to_str(c.get('codice_fiscale'))}
VEICOLO: {to_str(c.get('targa'))} | PATENTE: {to_str(c.get('numero_patente'))}
PERIODO: dal {to_str(c.get('inizio'))} al {to_str(c.get('fine'))} | PREZZO: EUR {to_str(c.get('prezzo'))}

CONDIZIONI GENERALI DI CONTRATTO:
1.⁠ ⁠STATO DEL MEZZO: Il cliente dichiara di aver visionato il mezzo e di riceverlo in ottimo stato manutentivo, con il pieno di carburante e privo di danni non segnalati. Il cliente si impegna a riconsegnare il veicolo nelle stesse condizioni, salvo la normale usura. Ogni danno riscontrato alla riconsegna (graffi, rotture plastiche, danni meccanici) sarà addebitato al cliente secondo il listino ricambi ufficiale.
2.⁠ ⁠ASSICURAZIONE: Il veicolo è coperto da polizza R.C.A. a norma di legge. Sono esclusi dalla copertura i danni al conducente e i danni causati per dolo o colpa grave (es. guida in stato di ebbrezza, sotto effetto di stupefacenti, guida contromano o violazioni gravi del Codice della Strada). In caso di sinistro con colpa, il cliente risponde della franchigia assicurativa.
3.⁠ ⁠RESPONSABILITÀ: Il cliente è pienamente responsabile per danni al veicolo, furto e per tutte le contravvenzioni (multe) elevate nel periodo di locazione. In caso di furto, il cliente risponde per l'intero valore del mezzo se non riconsegna le chiavi originali o se viene dimostrata la negligenza. Il cliente autorizza sin d'ora la ditta a comunicare i propri dati alle autorità competenti per la rinotifica dei verbali.
4.⁠ ⁠CLAUSOLE VESSATORIE: Ai sensi e per gli effetti degli art. 1341-1342 c.c. il cliente dichiara di aver letto e approvato specificamente i punti 2 e 3 del presente contratto relativi a Limitazioni di Responsabilità, Furto, Danni e Sanzioni Amministrative.

Informativa Privacy (GDPR): Il cliente autorizza il trattamento dei dati personali ai sensi del Regolamento UE 2016/679 e la conservazione dei documenti d'identità per le finalità legate all'esecuzione del contratto.
"""
        pdf.multi_cell(0, 5, pdf_s(clausole))
        
        if c.get("firma"):
            try:
                f_bytes = base64.b64decode(to_str(c["firma"]))
                pdf.image(io.BytesIO(f_bytes), x=130, y=pdf.get_y()+5, w=50)
            except: pass
        pdf.ln(25)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 10, "Firma del Cliente per accettazione e approvazione specifica clausole 2-3 (Art. 1341 c.c.)", ln=True, align="R")

    elif tipo == "FATTURA":
        prezzo_val = float(c.get('prezzo', 0))
        imp = prezzo_val / 1.22
        iva_v = prezzo_val - imp

        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "DOCUMENTO COMMERCIALE DI VENDITA", ln=True, align="C", border="B")
        pdf.ln(5)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 6, f"N. {to_str(c.get('numero_fattura'))}/A del {oggi}", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, f"Spett.le {to_str(c.get('nome'))} {to_str(c.get('cognome'))}", ln=True)
        pdf.cell(0, 6, f"C.F./P.IVA: {to_str(c.get('codice_fiscale', '---'))}", ln=True)
        pdf.ln(5)

        # Tabella
        pdf.set_fill_color(230, 230, 230)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(90, 8, "Descrizione Servizio", 1, 0, 'L', True)
        pdf.cell(20, 8, "Qta", 1, 0, 'C', True)
        pdf.cell(30, 8, "Prezzo Un.", 1, 0, 'C', True)
        pdf.cell(20, 8, "IVA", 1, 0, 'C', True)
        pdf.cell(30, 8, "Importo", 1, 1, 'C', True)

        pdf.set_font("Arial", "", 9)
        d_serv = f"Noleggio Scooter (Targa: {to_str(c.get('targa'))}) - dal {to_str(c.get('inizio'))} al {to_str(c.get('fine'))}"
        pdf.cell(90, 8, pdf_s(d_serv), 1)
        pdf.cell(20, 8, "1", 1, 0, 'C')
        pdf.cell(30, 8, f"{imp:.2f}", 1, 0, 'C')
        pdf.cell(20, 8, "22%", 1, 0, 'C')
        pdf.cell(30, 8, f"{imp:.2f}", 1, 1, 'C')
        
        pdf.ln(10)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(150, 10, f"TOTALE NETTO A PAGARE: EUR {prezzo_val:.2f}", 0, 1, 'R')

    elif tipo == "MULTE":
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "COMUNICAZIONE DATI CONDUCENTE (L. 445/2000)", ln=True, align="C")
        pdf.ln(5)
        pdf.set_font("Arial", "", 10)
        m_txt = f"""
La sottoscritta BATTAGLIA MARIANNA nata a Berlino (Germania) il 13/01/1987 e residente in Forio alla Via Cognole n. 5, in qualità di titolare della BATTAGLIA RENT, DICHIARA ai sensi della L. 445/2000 che il veicolo targato {to_str(c.get('targa'))} il giorno {to_str(c.get('inizio'))} era concesso in locazione senza conducente al signor:

COGNOME E NOME: {to_str(c.get('nome'))} {to_str(c.get('cognome'))}
LUOGO E DATA DI NASCITA: {to_str(c.get('luogo_nascita'))} il {to_str(c.get('data_nascita'))}
RESIDENZA: {to_str(c.get('indirizzo_cliente'))}
IDENTIFICATO A MEZZO PATENTE: {to_str(c.get('numero_patente'))}

Si allega copia del contratto di locazione e del documento del trasgressore.
In fede, Marianna Battaglia
"""
        pdf.multi_cell(0, 6, pdf_s(m_txt))

    return pdf.output(dest="S").encode("latin-1")

# ------------------------------------------------
# LOGICA APP STREAMLIT
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
            prezzo = col2.number_input("Prezzo Totale (€)", min_value=0.0)
            
            d1, d2 = st.columns(2)
            inizio = d1.date_input("Inizio Noleggio")
            fine = d2.date_input("Fine Noleggio")
            ind = st.text_area("Indirizzo Residenza")
            
            st.subheader("📸 Foto Documenti")
            f_col1, f_col2 = st.columns(2)
            fronte = f_col1.file_uploader("Fronte Patente")
            retro = f_col2.file_uploader("Retro Patente")
            
            st.subheader("⚖️ Accettazione Legale")
            check1 = st.checkbox("Mezzo in ottimo stato")
            check2 = st.checkbox("Accetto clausole Responsabilità/Multe (Art. 1341-1342)")
            check3 = st.checkbox("Privacy e RCA")
            
            canvas = st_canvas(stroke_width=3, stroke_color="#000", background_color="#eee", height=150, width=400, key="firma")
            
            if st.form_submit_button("💾 SALVA CONTRATTO"):
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
                        nf_n = (last.data[0]['numero_fattura'] + 1) if last.data else 1

                        dati = {
                            "nome": to_str(nome), "cognome": to_str(cognome), "telefono": to_str(tel), "targa": to_str(targa),
                            "prezzo": float(prezzo), "inizio": to_str(inizio), "fine": to_str(fine),
                            "firma": to_str(f_b64), "numero_fattura": int(nf_n), "luogo_nascita": to_str(l_nas),
                            "data_nascita": to_str(d_nas), "numero_patente": to_str(pat), "url_fronte": to_str(u_f),
                            "url_retro": to_str(u_r), "codice_fiscale": to_str(cf), "indirizzo_cliente": to_str(ind)
                        }
                        supabase.table("contratti").insert(dati).execute()
                        st.success("Salvato correttamente!")
                        st.rerun()
                    except Exception as e: st.error(f"Errore Salvataggio: {e}")
                else: st.warning("Compila tutto e accetta le clausole.")

    else:
        st.title("📂 Archivio Contratti")
        try:
            res = supabase.table("contratti").select("*").order("id", desc=True).execute()
            if res.data:
                cerca = st.text_input("🔍 Cerca per Targa o Cognome").lower()
                for c in res.data:
                    t_l = to_str(c.get('targa', ''))
                    c_l = to_str(c.get('cognome', '')).upper()
                    nf_s = to_str(c.get('numero_fattura', ''))
                    
                    if cerca in f"{t_l} {c_l}".lower():
                        with st.expander(f"📝 {t_l} - {c_l} (Fatt. {nf_s})"):
                            p1, p2, p3 = st.columns(3)
                            p1.download_button("📜 Contratto", genera_pdf_tipo(c, "CONTRATTO"), f"Cont_{t_l}.pdf")
                            p2.download_button("💰 Fattura", genera_pdf_tipo(c, "FATTURA"), f"Fatt_{t_l}.pdf")
                            p3.download_button("🚨 Multe", genera_pdf_tipo(c, "MULTE"), f"Multe_{t_l}.pdf")
                            
                            st.write("---")
                            i1, i2 = st.columns(2)
                            if c.get("url_fronte"): i1.image(c["url_fronte"], caption="Fronte")
                            if c.get("url_retro"): i2.image(c["url_retro"], caption="Retro")
                            
                            tel_cl = to_str(c.get('telefono'))
                            if tel_cl:
                                n_cl = to_str(c.get('nome'))
                                msg_wa = urllib.parse.quote(f"Buongiorno {n_cl}, ecco i documenti per lo scooter {t_l}.")
                                st.markdown(f"[💬 WhatsApp](https://wa.me/{tel_cl}?text={msg_wa})")
        except Exception as e: st.error(f"Errore Archivio: {e}")
