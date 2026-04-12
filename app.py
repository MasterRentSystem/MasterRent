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
# UTILITY DI SICUREZZA
# ------------------------------------------------
def safe_val(val):
    """Converte qualsiasi valore in stringa sicura"""
    return str(val) if val is not None else ""

def safe_pdf(text):
    """Rende il testo compatibile con i caratteri PDF"""
    return safe_val(text).encode("latin-1", "replace").decode("latin-1")

def upload_to_supabase(file, targa, prefix):
    try:
        if file is None: return None
        ext = file.name.split('.')[-1]
        targa_clean = safe_val(targa).replace(" ", "")
        # Nomi file protetti
        nome_f = f"{prefix}{targa_clean}{datetime.now().strftime('%H%M%S')}.{ext}"
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
    
    # Intestazione Professionale
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, safe_pdf(DITTA), ln=True)
    pdf.set_font("Arial", "", 8)
    pdf.cell(0, 4, safe_pdf(INDIRIZZO_FISCALE), ln=True)
    pdf.cell(0, 4, safe_pdf(DATI_IVA), ln=True)
    pdf.ln(5)

    if tipo == "CONTRATTO":
        pdf.set_font("Arial", "B", 13)
        pdf.cell(0, 10, "CONTRATTO DI NOLEGGIO / RENTAL AGREEMENT", ln=True, align="C", border="B")
        pdf.set_font("Arial", "", 9)
        
        # Clausole Legali Complete e Protette
        testo_contratto = f"""
DATI CLIENTE: {c.get('nome')} {c.get('cognome')} | CF/ID: {c.get('codice_fiscale')}
VEICOLO: {c.get('targa')} | PATENTE: {c.get('numero_patente')}
PERIODO: dal {c.get('inizio')} al {c.get('fine')} | PREZZO: EUR {c.get('prezzo')}

CONDIZIONI GENERALI DI CONTRATTO:
1.⁠ ⁠STATO DEL MEZZO: Il cliente dichiara di aver visionato il mezzo e di riceverlo in ottimo stato manutentivo, con il pieno di carburante e privo di danni non segnalati. Il cliente si impegna a riconsegnare il veicolo nelle stesse condizioni, salvo la normale usura. Ogni danno riscontrato alla riconsegna (graffi, rotture plastiche, danni meccanici) sarà addebitato al cliente secondo il listino ricambi ufficiale.
2.⁠ ⁠ASSICURAZIONE: Il veicolo è coperto da polizza R.C.A. a norma di legge. Sono esclusi dalla copertura i danni al conducente e i danni causati per dolo o colpa grave (es. guida in stato di ebbrezza, sotto effetto di stupefacenti, guida contromano o violazioni gravi del Codice della Strada). In caso di sinistro con colpa, il cliente risponde della franchigia assicurativa.
3.⁠ ⁠RESPONSABILITÀ: Il cliente è pienamente responsabile per danni al veicolo, furto e per tutte le contravvenzioni (multe) elevate nel periodo di locazione. In caso di furto, il cliente risponde per l'intero valore del mezzo se non riconsegna le chiavi originali o se viene dimostrata la negligenza. Il cliente autorizza sin d'ora la ditta a comunicare i propri dati alle autorità competenti per la rinotifica dei verbali.
4.⁠ ⁠CLAUSOLE VESSATORIE: Ai sensi e per gli effetti degli art. 1341-1342 c.c. il cliente dichiara di aver letto e approvato specificamente i punti 2 e 3 del presente contratto relativi a Limitazioni di Responsabilità, Furto, Danni e Sanzioni Amministrative.

Informativa Privacy (GDPR): Il cliente autorizza il trattamento dei dati personali ai sensi del Regolamento UE 2016/679 e la conservazione dei documenti d'identità per le finalità legate all'esecuzione del contratto.
"""
        pdf.multi_cell(0, 5, safe_pdf(testo_contratto))
        
        if c.get("firma"):
            try:
                f_bytes = base64.b64decode(safe_val(c["firma"]))
                pdf.image(io.BytesIO(f_bytes), x=130, y=pdf.get_y()+5, w=50)
            except: pass
        pdf.ln(25)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 10, "Firma del Cliente per accettazione e approvazione specifica clausole 2-3 (Art. 1341 c.c.)", ln=True, align="R")

    elif tipo == "FATTURA":
        p_tot = float(c.get('prezzo', 0))
        imp = p_tot / 1.22
        iva_v = p_tot - imp

        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "DOCUMENTO COMMERCIALE DI VENDITA O PRESTAZIONE", ln=True, align="C", border="B")
        pdf.ln(5)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 6, f"N. {c.get('numero_fattura')}/A del {oggi}", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, f"Spett.le {c.get('nome')} {c.get('cognome')}", ln=True)
        pdf.cell(0, 6, f"Codice Fiscale/P.IVA Cliente: {c.get('codice_fiscale', '---')}", ln=True)
        pdf.ln(5)

        # Tabella Professionale
        pdf.set_fill_color(230, 230, 230)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(90, 8, "Descrizione Servizio", 1, 0, 'L', True)
        pdf.cell(20, 8, "Qtà", 1, 0, 'C', True)
        pdf.cell(30, 8, "Prezzo Un.", 1, 0, 'C', True)
        pdf.cell(20, 8, "IVA", 1, 0, 'C', True)
        pdf.cell(30, 8, "Importo", 1, 1, 'C', True)

        pdf.set_font("Arial", "", 9)
        desc = f"Noleggio Scooter (Targa: {c.get('targa')}) - dal {c.get('inizio')} al {c.get('fine')}"
        pdf.cell(90, 8, safe_pdf(desc), 1)
        pdf.cell(20, 8, "1", 1, 0, 'C')
        pdf.cell(30, 8, f"{imp:.2f}", 1, 0, 'C')
        pdf.cell(20, 8, "22%", 1, 0, 'C')
        pdf.cell(30, 8, f"{imp:.2f}", 1, 1, 'C')
        
        pdf.ln(10)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(150, 7, "Totale Imponibile:", 0, 0, 'R')
        pdf.cell(40, 7, f"EUR {imp:.2f}", 0, 1, 'R')
        pdf.cell(150, 7, "IVA (22%):", 0, 0, 'R')
        pdf.cell(40, 7, f"EUR {iva_v:.2f}", 0, 1, 'R')
        pdf.ln(2)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(150, 10, "TOTALE NETTO A PAGARE:", 0, 0, 'R')
        pdf.cell(40, 10, f"EUR {p_tot:.2f}", 'T', 1, 'R')

    elif tipo == "MULTE":
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "COMUNICAZIONE DATI CONDUCENTE (L. 445/2000)", ln=True, align="C")
        pdf.ln(5)
        pdf.set_font("Arial", "", 10)
        testo_multe = f"""
La sottoscritta BATTAGLIA MARIANNA nata a Berlino (Germania) il 13/01/1987 e residente in Forio alla Via Cognole n. 5, in qualità di titolare della BATTAGLIA RENT, DICHIARA ai sensi della L. 445/2000 che il veicolo targato {c.get('targa')} il giorno {c.get('inizio')} era concesso in locazione senza conducente al signor:

COGNOME E NOME: {c.get('nome')} {c.get('cognome')}
LUOGO E DATA DI NASCITA: {c.get('luogo_nascita')} il {c.get('data_nascita')}
RESIDENZA: {c.get('indirizzo_cliente')}
IDENTIFICATO A MEZZO PATENTE: {c.get('numero_patente')}

Si allega copia del contratto di locazione firmato e del documento del trasgressore. Si dichiara che la copia allegata è conforme all'originale depositato presso i nostri uffici.

In fede, Marianna Battaglia
"""
        pdf.multi_cell(0, 6, safe_pdf(testo_multe))

    return pdf.output(dest="S").encode("latin-1")

# ------------------------------------------------
# LOGICA INTERFACCIA STREAMLIT
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
            f_col1, f_col2 = st.columns(2)
            fronte = f_col1.file_uploader("Fronte Patente", type=["jpg", "png", "jpeg"])
            retro = f_col2.file_uploader("Retro Patente", type=["jpg", "png", "jpeg"])
            
            st.subheader("⚖️ Accettazione Legale Obbligatoria")
            check1 = st.checkbox("Il cliente dichiara che il mezzo è in ottimo stato manutentivo.")
            check2 = st.checkbox("Il cliente accetta le clausole su Responsabilità, Furto e Multe (Art. 1341-1342 c.c.)")
            check3 = st.checkbox("Il cliente accetta l'Informativa Privacy e la copertura Assicurativa.")
            
            canvas = st_canvas(stroke_width=3, stroke_color="#000", background_color="#eee", height=150, width=400, key="firma")
            
            if st.form_submit_button("💾 SALVA E GENERA DOCUMENTI"):
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
                            "nome": safe_val(nome), "cognome": safe_val(cognome), "telefono": safe_val(tel), "targa": safe_val(targa),
                            "prezzo": float(prezzo), "inizio": safe_val(inizio), "fine": safe_val(fine),
                            "firma": f_b64, "numero_fattura": int(n_f), "luogo_nascita": safe_val(l_nas),
                            "data_nascita": safe_val(d_nas), "numero_patente": safe_val(pat), "url_fronte": safe_val(u_f),
                            "url_retro": safe_val(u_r), "codice_fiscale": safe_val(cf), "indirizzo_cliente": safe_val(ind)
                        }
                        supabase.table("contratti").insert(dati).execute()
                        st.success("Noleggio salvato con successo nell'Archivio!")
                        st.rerun()
                    except Exception as e: st.error(f"Errore nel salvataggio: {e}")
                else: st.warning("Compila tutti i campi obbligatori e accetta le clausole legali.")

    else:
        st.title("📂 Archivio Contratti")
        try:
            res = supabase.table("contratti").select("*").order("id", desc=True).execute()
            if res.data:
                cerca = st.text_input("🔍 Cerca per Targa o Cognome").lower()
                for c in res.data:
                    t_str = safe_val(c.get('targa', ''))
                    c_str = safe_val(c.get('cognome', '')).upper()
                    nf_str = safe_val(c.get('numero_fattura', ''))
                    
                    if cerca in f"{t_str} {c_str}".lower():
                        with st.expander(f"📝 {t_str} - {c_str} (Fatt. {nf_str})"):
                            col_p1, col_p2, col_p3 = st.columns(3)
                            col_p1.download_button("📜 Contratto", genera_pdf_tipo(c, "CONTRATTO"), f"Cont_{t_str}.pdf")
                            col_p2.download_button("💰 Fattura", genera_pdf_tipo(c, "FATTURA"), f"Fatt_{t_str}.pdf")
                            col_p3.download_button("🚨 Multe", genera_pdf_tipo(c, "MULTE"), f"Multe_{t_str}.pdf")
                            
                            st.write("---")
                            i1, i2 = st.columns(2)
                            if c.get("url_fronte"): i1.image(c["url_fronte"], caption="Fronte")
                            if c.get("url_retro"): i2.image(c["url_retro"], caption="Retro")
                            
                            tel_cl = safe_val(c.get('telefono'))
                            if tel_cl:
                                msg_wa = urllib.parse.quote(f"Buongiorno {c.get('nome','')}, ecco i documenti Battaglia Rent per lo scooter {t_str}. Grazie!")
                                st.markdown(f"[💬 WhatsApp](https://wa.me/{tel_cl}?text={msg_wa})")
        except Exception as e: st.error(f"Errore caricamento: {e}")
