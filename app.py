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
    if text is None: return ""
    return str(text).encode("latin-1", "replace").decode("latin-1")

def upload_to_supabase(file, targa, prefix):
    try:
        if file is None: return None
        estensione = file.name.split('.')[-1]
        nome_file = f"{prefix}{targa}{datetime.now().strftime('%Y%m%d_%H%M%S')}.{estensione}"
        supabase.storage.from_("documenti").upload(nome_file, file.getvalue(), {"content-type": f"image/{estensione}"})
        return supabase.storage.from_("documenti").get_public_url(nome_file)
    except Exception as e:
        st.error(f"Errore caricamento foto: {e}")
        return None

# ------------------------------------------------
# GENERAZIONE PDF (CONTRATTO E FATTURA LEGALE)
# ------------------------------------------------
def genera_pdf_tipo(c, tipo):
    pdf = FPDF()
    pdf.add_page()
    oggi = datetime.now().strftime("%d/%m/%Y")
    
    # Intestazione comune
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
        
        testo_contratto = f"""
DATI CLIENTE: {c.get('nome')} {c.get('cognome')} | CF/ID: {c.get('codice_fiscale')}
VEICOLO: {c.get('targa')} | PATENTE: {c.get('numero_patente')}
PERIODO: dal {c.get('inizio')} al {c.get('fine')} | PREZZO: EUR {c.get('prezzo')}

CONDIZIONI GENERALI DI CONTRATTO:
1.⁠ ⁠STATO DEL MEZZO: Il cliente dichiara di aver visionato il mezzo, ricevendolo in ottimo stato, con il pieno e privo di danni non segnalati.
2.⁠ ⁠ASSICURAZIONE: Il veicolo è coperto da polizza R.C.A. a norma di legge. Sono esclusi dalla copertura i danni al conducente e i danni causati per dolo o colpa grave (es. guida in stato di ebbrezza).
3.⁠ ⁠RESPONSABILITÀ: Il cliente è pienamente responsabile per danni al veicolo, furto (risponde per l'intero valore del mezzo) e per tutte le contravvenzioni (multe) elevate nel periodo di locazione.
4.⁠ ⁠CLAUSOLE VESSATORIE: Ai sensi degli art. 1341-1342 c.c. il cliente approva specificamente i punti 2 e 3 relativi a Limitazioni di Responsabilità, Furto e Sanzioni Amministrative.

Informativa Privacy (GDPR): Il cliente autorizza il trattamento dei dati e la conservazione dei documenti d'identità.
"""
        pdf.multi_cell(0, 5, safe_text(testo_contratto))
        if c.get("firma"):
            try:
                firma_bytes = base64.b64decode(c["firma"])
                pdf.image(io.BytesIO(firma_bytes), x=130, y=pdf.get_y()+5, w=50)
            except: pass
        pdf.ln(15)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 10, "Firma del Cliente per accettazione specifica delle clausole", ln=True, align="R")

    elif tipo == "FATTURA":
        # Calcolo Scorporo IVA 22%
        prezzo_totale = float(c.get('prezzo', 0))
        imponibile = prezzo_totale / 1.22
        iva = prezzo_totale - imponibile

        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "DOCUMENTO COMMERCIALE DI VENDITA", ln=True, align="C", border="B")
        pdf.ln(5)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 6, f"Ricevuta n: {c.get('numero_fattura')} del {oggi}", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, f"Cliente: {c.get('nome')} {c.get('cognome')} | C.F.: {c.get('codice_fiscale', '---')}", ln=True)
        pdf.ln(5)

        # Tabella
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(100, 8, "Descrizione", border=1, fill=True)
        pdf.cell(30, 8, "Imponibile", border=1, fill=True, align="C")
        pdf.cell(20, 8, "IVA", border=1, fill=True, align="C")
        pdf.cell(40, 8, "Totale", border=1, fill=True, align="C")
        pdf.ln()

        pdf.set_font("Arial", "", 9)
        desc = f"Noleggio Scooter {c.get('targa')} (dal {c.get('inizio')} al {c.get('fine')})"
        pdf.cell(100, 8, safe_text(desc), border=1)
        pdf.cell(30, 8, f"{imponibile:.2f}", border=1, align="C")
        pdf.cell(20, 8, "22%", border=1, align="C")
        pdf.cell(40, 8, f"{prezzo_totale:.2f}", border=1, align="C")
        pdf.ln(10)

        pdf.set_font("Arial", "B", 10)
        pdf.cell(150, 7, "TOTALE IMPONIBILE:", align="R")
        pdf.cell(40, 7, f"EUR {imponibile:.2f}", align="R")
        pdf.ln()
        pdf.cell(150, 7, "IVA (22%):", align="R")
        pdf.cell(40, 7, f"EUR {iva:.2f}", align="R")
        pdf.ln()
        pdf.set_font("Arial", "B", 12)
        pdf.cell(150, 10, "TOTALE NETTO A PAGARE:", align="R")
        pdf.cell(40, 10, f"EUR {prezzo_totale:.2f}", border="T", align="R")

    elif tipo == "MULTE":
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 10, "COMUNICAZIONE DATI CONDUCENTE (L. 445/2000)", ln=True, align="C")
        pdf.set_font("Arial", "", 10)
        corpo = f"In riferimento al Verbale in oggetto, si dichiara che il veicolo {c.get('targa')} " \
                f"in data {c.get('inizio')} era concesso in locazione a:\n\n" \
                f"SOGGETTO: {c.get('nome')} {c.get('cognome')}\nNATO A: {c.get('luogo_nascita')} IL {c.get('data_nascita')}\n" \
                f"RESIDENTE: {c.get('indirizzo_cliente')}\nPATENTE: {c.get('numero_patente')}\n\n" \
                f"Si allega copia del contratto e documento. Firma titolare: ________________"
        pdf.multi_cell(0, 6, safe_text(corpo))

    pdf_out = pdf.output(dest="S")
    return bytes(pdf_out) if not isinstance(pdf_out, str) else pdf_out.encode("latin-1")

# ------------------------------------------------
# LOGICA APP STREAMLIT
# ------------------------------------------------
if "autenticato" not in st.session_state: st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.title("🔐 Accesso Master Rent")
    passw = st.text_input("Password", type="password")
    if st.button("Accedi"):
        if passw == "1234":
            st.session_state.autenticato = True
            st.rerun()
else:
    menu = st.sidebar.radio("Navigazione", ["Nuovo Noleggio", "Archivio"])

    if menu == "Nuovo Noleggio":
        st.title("🛵 Nuovo Noleggio")
        with st.form("form_noleggio", clear_on_submit=True):
            c1, c2 = st.columns(2)
            nome, cognome = c1.text_input("Nome"), c1.text_input("Cognome")
            tel, cf = c1.text_input("Telefono (es. 39333...)"), c1.text_input("C.F. / ID")
            targa, pat = c2.text_input("Targa").upper(), c2.text_input("N. Patente")
            l_nas, d_nas = c2.text_input("Luogo Nascita"), c2.text_input("Data Nascita")
            prezzo = c2.number_input("Prezzo Totale (€)", min_value=0.0)
            
            d_col1, d_col2 = st.columns(2)
            inizio, fine = d_col1.date_input("Inizio"), d_col2.date_input("Fine")
            ind = st.text_area("Indirizzo di Residenza")

            st.subheader("📸 Documenti Patente")
            f_col1, f_col2 = st.columns(2)
            fronte = f_col1.file_uploader("Fronte", type=["jpg", "png", "jpeg"])
            retro = f_col2.file_uploader("Retro", type=["jpg", "png", "jpeg"])

            st.subheader("⚖️ Accettazione Legale")
            check1 = st.checkbox("Mezzo visionato in ottimo stato (Verbale di consegna).")
            check2 = st.checkbox("Approvazione specifica Clausole 2 e 3 (Responsabilità e RCA).")
            check3 = st.checkbox("Consenso trattamento dati e Privacy.")

            st.subheader("✍️ Firma")
            canvas = st_canvas(stroke_width=3, stroke_color="#000", background_color="#eee", height=150, width=400, key="firma")

            if st.form_submit_button("💾 SALVA E GENERA"):
                if check1 and check2 and check3 and nome and targa:
                    try:
                        firma_b64 = ""
                        if canvas.image_data is not None:
                            img = Image.fromarray(canvas.image_data.astype("uint8"))
                            buf = io.BytesIO()
                            img.save(buf, format="PNG")
                            firma_b64 = base64.b64encode(buf.getvalue()).decode()

                        u_f = upload_to_supabase(fronte, targa, "fronte")
                        u_r = upload_to_supabase(retro, targa, "retro")
                        
                        res_n = supabase.table("contratti").select("numero_fattura").order("id", desc=True).limit(1).execute()
                        n_f = (res_n.data[0]['numero_fattura'] + 1) if res_n.data else 1

                        dati = {
                            "nome": nome, "cognome": cognome, "telefono": tel, "targa": targa,
                            "prezzo": prezzo, "inizio": str(inizio), "fine": str(fine),
                            "firma": firma_b64, "numero_fattura": n_f, "luogo_nascita": l_nas,
                            "data_nascita": d_nas, "numero_patente": pat, "url_fronte": u_f,
                            "url_retro": u_r, "codice_fiscale": cf, "indirizzo_cliente": ind
                        }
                        supabase.table("contratti").insert(dati).execute()
                        st.success("Contratto Salvato!")
                        st.rerun()
                    except Exception as e: st.error(f"Errore: {e}")
                else: st.warning("Compila i campi obbligatori e spunta tutte le caselle legali.")

    else:
        st.title("📂 Archivio Storico")
        res = supabase.table("contratti").select("*").order("id", desc=True).execute()
        if res.data:
            cerca = st.text_input("🔍 Cerca per Targa o Cognome").lower()
            for c in res.data:
                if cerca in f"{c['targa']} {c['cognome']}".lower():
                    with st.expander(f"📝 {c['targa']} - {c['cognome'].upper()} (Fattura {c['numero_fattura']})"):
                        p_col1, p_col2, p_col3 = st.columns(3)
                        p_col1.download_button("📜 Contratto", genera_pdf_tipo(c, "CONTRATTO"), f"Cont_{c['id']}.pdf")
                        p_col2.download_button("💰 Fattura", genera_pdf_tipo(c, "FATTURA"), f"Fatt_{c['id']}.pdf")
                        p_col3.download_button("🚨 Multe", genera_pdf_tipo(c, "MULTE"), f"Multe_{c['id']}.pdf")
                        
                        st.write("---")
                        img_col1, img_col2 = st.columns(2)
                        if c.get("url_fronte"): img_col1.image(c["url_fronte"], caption="Fronte Patente")
                        if c.get("url_retro"): img_col2.image(c["url_retro"], caption="Retro Patente")
                        
                        t_tel = c.get('telefono')
                        if t_tel:
                            msg = urllib.parse.quote(f"Buongiorno {c['nome']}, ecco i documenti Battaglia Rent per lo scooter {c['targa']}.")
                            st.markdown(f"[💬 Invia su WhatsApp](https://wa.me/{t_tel}?text={msg})")
