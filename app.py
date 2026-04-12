import streamlit as st
from supabase import create_client, Client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from fpdf import FPDF
import io
import base64
from datetime import datetime
import urllib.parse

# --- CONFIGURAZIONE ---
DITTA = "BATTAGLIA RENT"
INDIRIZZO_FISCALE = "Via Cognole n. 5, Forio (NA)"
DATI_IVA = "P.IVA: 10252601215 | C.F.: BTTMNN87A53Z112S"

URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# ------------------------------------------------
# PROTEZIONE TOTALE (IL CUORE DEL PROBLEMA)
# ------------------------------------------------
def g(dizionario, chiave, default=""):
    """
    Funzione 'Get' Ultra-Sicura: 
    Prende un dato dal database e lo trasforma IMMEDIATAMENTE in testo.
    Se il dato è un numero (int) o vuoto (None), lo converte senza errori.
    """
    valore = dizionario.get(chiave)
    if valore is None:
        return str(default)
    return str(valore)

def upload_foto(file, targa, prefisso):
    try:
        if file is None: return ""
        est = str(file.name).split('.')[-1]
        targa_p = str(targa).replace(" ", "")
        nome_f = f"{prefisso}{targa_p}{datetime.now().strftime('%M%S')}.{est}"
        supabase.storage.from_("documenti").upload(nome_f, file.getvalue())
        return supabase.storage.from_("documenti").get_public_url(nome_f)
    except:
        return ""

# ------------------------------------------------
# GENERAZIONE PDF XL (TESTI LEGALI COMPLETI)
# ------------------------------------------------
def genera_pdf(c, tipo):
    pdf = FPDF()
    pdf.add_page()
    
    # Intestazione
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, DITTA.encode('latin-1', 'replace').decode('latin-1'), ln=True)
    pdf.set_font("Arial", "", 8)
    pdf.cell(0, 4, INDIRIZZO_FISCALE.encode('latin-1', 'replace').decode('latin-1'), ln=True)
    pdf.cell(0, 4, DATI_IVA.encode('latin-1', 'replace').decode('latin-1'), ln=True)
    pdf.ln(5)

    if tipo == "CONTRATTO":
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "CONTRATTO DI NOLEGGIO / RENTAL AGREEMENT", ln=True, align="C", border="B")
        pdf.set_font("Arial", "", 9)
        
        testo = f"""
DATI CLIENTE: {g(c,'nome')} {g(c,'cognome')} | CF/ID: {g(c,'codice_fiscale')}
VEICOLO: {g(c,'targa')} | PATENTE: {g(c,'numero_patente')}
PERIODO: dal {g(c,'inizio')} al {g(c,'fine')} | PREZZO: EUR {g(c,'prezzo')}

CONDIZIONI GENERALI DI CONTRATTO:
1.⁠ ⁠STATO DEL MEZZO: Il cliente riceve il mezzo in ottimo stato manutentivo, con il pieno e privo di danni. Si impegna a riconsegnarlo nelle stesse condizioni. Danni riscontrati alla riconsegna saranno addebitati secondo listino ufficiale.
2.⁠ ⁠ASSICURAZIONE: Polizza R.C.A. attiva. Esclusi danni al conducente e danni per dolo/colpa grave o violazioni del Codice della Strada. Il cliente risponde della franchigia.
3.⁠ ⁠RESPONSABILITÀ: Il cliente risponde di danni, furto (se non riconsegna le chiavi) e tutte le multe/contravvenzioni. Autorizza la ditta a comunicare i dati alle autorità per la rinotifica.
4.⁠ ⁠APPROVAZIONE SPECIFICA: Ai sensi art. 1341-1342 c.c. si approvano i punti 2 e 3 (Responsabilità, Furto, Danni e Sanzioni).

Privacy: Consenso al trattamento dati ai sensi del GDPR 2016/679.
"""
        pdf.multi_cell(0, 5, testo.encode('latin-1', 'replace').decode('latin-1'))
        
        if c.get("firma"):
            try:
                f_bytes = base64.b64decode(str(c["firma"]))
                pdf.image(io.BytesIO(f_bytes), x=130, y=pdf.get_y()+5, w=50)
            except: pass
        pdf.ln(25)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 10, "Firma del Cliente per accettazione specifica clausole 2-3 (Art. 1341 c.c.)", ln=True, align="R")

    elif tipo == "FATTURA":
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "DOCUMENTO COMMERCIALE", ln=True, align="C", border="B")
        pdf.ln(5)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 6, f"Ricevuta n: {g(c,'numero_fattura')}/A del {datetime.now().strftime('%d/%m/%Y')}", ln=True)
        pdf.cell(0, 6, f"Cliente: {g(c,'nome')} {g(c,'cognome')}", ln=True)
        pdf.ln(10)
        
        prezzo_t = float(c.get('prezzo', 0))
        imp = prezzo_t / 1.22
        pdf.cell(90, 8, f"Noleggio Scooter {g(c,'targa')}", 1)
        pdf.cell(40, 8, f"EUR {prezzo_t:.2f}", 1, 1, 'R')
        pdf.ln(5)
        pdf.cell(130, 10, f"TOTALE PAGATO: EUR {prezzo_t:.2f}", 0, 1, 'R')

    elif tipo == "MULTE":
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "COMUNICAZIONE DATI CONDUCENTE", ln=True, align="C")
        pdf.ln(10)
        testo_m = f"""
La ditta BATTAGLIA RENT dichiara che il veicolo {g(c,'targa')} 
in data {g(c,'inizio')} era locato a:
Nome: {g(c,'nome')} {g(c,'cognome')}
Nato a: {g(c,'luogo_nascita')} il {g(c,'data_nascita')}
Residente: {g(c,'indirizzo_cliente')}
Patente: {g(c,'numero_patente')}
"""
        pdf.multi_cell(0, 6, testo_m.encode('latin-1', 'replace').decode('latin-1'))

    return pdf.output(dest="S").encode("latin-1")

# ------------------------------------------------
# INTERFACCIA
# ------------------------------------------------
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.title("🔐 Accesso")
    pw = st.text_input("Password", type="password")
    if st.button("Entra"):
        if pw == "1234":
            st.session_state.autenticato = True
            st.rerun()
else:
    menu = st.sidebar.radio("Menu", ["Nuovo", "Archivio"])

    if menu == "Nuovo":
        st.title("🛵 Nuovo Noleggio")
        with st.form("main_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Nome")
            cognome = c1.text_input("Cognome")
            targa = c2.text_input("Targa").upper()
            prezzo = c2.number_input("Prezzo (€)", min_value=0.0)
            cf = c1.text_input("Codice Fiscale")
            patente = c2.text_input("N. Patente")
            luogo_n = c1.text_input("Luogo Nascita")
            data_n = c1.text_input("Data Nascita")
            ind = st.text_area("Indirizzo Residenza")
            inizio = st.date_input("Inizio")
            fine = st.date_input("Fine")
            f_fronte = st.file_uploader("Foto Fronte")
            f_retro = st.file_uploader("Foto Retro")
            
            st.write("---")
            st.warning("Firma obbligatoria e accettazione clausole")
            accetta = st.checkbox("Accetto termini e condizioni (Art. 1341-1342 c.c.)")
            canvas = st_canvas(stroke_width=2, stroke_color="#000", background_color="#eee", height=150, width=400, key="f1")
            
            if st.form_submit_button("💾 SALVA"):
                if accetta and nome and targa:
                    try:
                        # Firma
                        f_b64 = ""
                        if canvas.image_data is not None:
                            img = Image.fromarray(canvas.image_data.astype("uint8"))
                            buf = io.BytesIO()
                            img.save(buf, format="PNG")
                            f_b64 = base64.b64encode(buf.getvalue()).decode()
                        
                        # Foto
                        u1 = upload_foto(f_fronte, targa, "F")
                        u2 = upload_foto(f_retro, targa, "R")

                        # Numero Fattura
                        res = supabase.table("contratti").select("numero_fattura").order("id", desc=True).limit(1).execute()
                        nf = (res.data[0]['numero_fattura'] + 1) if res.data else 1

                        # Inserimento (Forziamo tutto a stringa/numero pulito)
                        dati = {
                            "nome": str(nome), "cognome": str(cognome), "targa": str(targa),
                            "prezzo": float(prezzo), "inizio": str(inizio), "fine": str(fine),
                            "firma": str(f_b64), "numero_fattura": int(nf),
                            "luogo_nascita": str(luogo_n), "data_nascita": str(data_n),
                            "numero_patente": str(patente), "url_fronte": str(u1),
                            "url_retro": str(u2), "codice_fiscale": str(cf), "indirizzo_cliente": str(ind)
                        }
                        supabase.table("contratti").insert(dati).execute()
                        st.success("Salvato!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore durante il salvataggio: {e}")

    else:
        st.title("📂 Archivio")
        try:
            res = supabase.table("contratti").select("*").order("id", desc=True).execute()
            if res.data:
                ricerca = st.text_input("🔍 Cerca...").lower()
                for r in res.data:
                    # USIAMO LA FUNZIONE 'g' PER EVITARE IL CRASH NELL'ARCHIVIO
                    t = g(r, 'targa')
                    c = g(r, 'cognome').upper()
                    
                    if ricerca in f"{t} {c}".lower():
                        # Usiamo f-string per il titolo dell'expander (molto più sicuro del +)
                        with st.expander(f"📄 {t} - {c}"):
                            c1, c2, c3 = st.columns(3)
                            
                            # Generiamo i PDF passando l'intero pacchetto dati
                            c1.download_button("📜 Contratto", genera_pdf(r, "CONTRATTO"), f"Cont_{t}.pdf")
                            c2.download_button("💰 Ricevuta", genera_pdf(r, "FATTURA"), f"Ric_{t}.pdf")
                            c3.download_button("🚨 Multe", genera_pdf(r, "MULTE"), f"Multe_{t}.pdf")
                            
                            st.divider()
                            i1, i2 = st.columns(2)
                            if r.get("url_fronte"): i1.image(r["url_fronte"], caption="Fronte")
                            if r.get("url_retro"): i2.image(r["url_retro"], caption="Retro")
        except Exception as e:
            st.error(f"Errore visualizzazione archivio: {e}")
