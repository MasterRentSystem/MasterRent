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
# IL "BLINDAGGIO" DEFINITIVO (ZERO CONCATENAZIONI)
# ------------------------------------------------
def forza_testo(dato):
    """Trasforma chirurgicamente ogni dato in stringa, eliminando i None"""
    if dato is None:
        return ""
    return str(dato)

def formatta_pdf(testo):
    """Rende il testo compatibile con FPDF senza errori di codifica"""
    return forza_testo(testo).encode("latin-1", "replace").decode("latin-1")

def carica_su_supabase(file, targa, prefisso):
    """Gestisce il caricamento file usando solo formattazione sicura"""
    try:
        if file is None: 
            return ""
        estensione = forza_testo(file.name).split('.')[-1]
        targa_pulita = forza_testo(targa).replace(" ", "")
        timestamp = datetime.now().strftime("%H%M%S")
        
        # NOME FILE: Usiamo f-string che non soffre l'errore del segno +
        nome_file = f"{prefisso}{targa_pulita}{timestamp}.{estensione}"
        
        supabase.storage.from_("documenti").upload(nome_file, file.getvalue())
        return supabase.storage.from_("documenti").get_public_url(nome_file)
    except Exception as e:
        st.error(f"Errore caricamento immagine: {e}")
        return ""

# ------------------------------------------------
# GENERAZIONE PDF INTEGRALI (VERSIONE MASSIMA XL)
# ------------------------------------------------
def genera_pdf_documento(dati_contratto, tipo_doc):
    pdf = FPDF()
    pdf.add_page()
    data_odierna = datetime.now().strftime("%d/%m/%Y")
    
    # Intestazione Aziendale
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, formatta_pdf(DITTA), ln=True)
    pdf.set_font("Arial", "", 8)
    pdf.cell(0, 4, formatta_pdf(INDIRIZZO_FISCALE), ln=True)
    pdf.cell(0, 4, formatta_pdf(DATI_IVA), ln=True)
    pdf.ln(5)

    # Estrazione dati sicura
    n = forza_testo(dati_contratto.get('nome'))
    c = forza_testo(dati_contratto.get('cognome'))
    t = forza_testo(dati_contratto.get('targa'))
    p = forza_testo(dati_contratto.get('prezzo'))
    i = forza_testo(dati_contratto.get('inizio'))
    f = forza_testo(dati_contratto.get('fine'))

    if tipo_doc == "CONTRATTO":
        pdf.set_font("Arial", "B", 13)
        pdf.cell(0, 10, "CONTRATTO DI NOLEGGIO / RENTAL AGREEMENT", ln=True, align="C", border="B")
        pdf.set_font("Arial", "", 9)
        
        testo_legale = f"""
DATI CLIENTE: {n} {c} | CF/ID: {forza_testo(dati_contratto.get('codice_fiscale'))}
VEICOLO: {t} | PATENTE: {forza_testo(dati_contratto.get('numero_patente'))}
PERIODO: dal {i} al {f} | PREZZO: EUR {p}

CONDIZIONI GENERALI DI CONTRATTO:
1.⁠ ⁠STATO DEL MEZZO: Il cliente dichiara di aver visionato il mezzo e di riceverlo in ottimo stato manutentivo, con il pieno di carburante e privo di danni non segnalati. Il cliente si impegna a riconsegnare il veicolo nelle stesse condizioni, salvo la normale usura. Ogni danno riscontrato alla riconsegna (graffi, rotture plastiche, danni meccanici) sarà addebitato al cliente secondo il listino ricambi ufficiale della casa costruttrice.
2.⁠ ⁠ASSICURAZIONE: Il veicolo è coperto da polizza R.C.A. a norma di legge. Sono esclusi dalla copertura i danni al conducente e i danni causati per dolo o colpa grave (es. guida in stato di ebbrezza, sotto effetto di stupefacenti, guida contromano o violazioni gravi del Codice della Strada). In caso di sinistro con colpa, il cliente risponde integralmente della franchigia assicurativa prevista.
3.⁠ ⁠RESPONSABILITÀ: Il cliente è pienamente responsabile per danni al veicolo, furto e per tutte le contravvenzioni (multe) elevate nel periodo di locazione. In caso di furto, il cliente risponde per l'intero valore del mezzo se non riconsegna le chiavi originali o se viene dimostrata la negligenza. Il cliente autorizza sin d'ora la ditta a comunicare i propri dati alle autorità competenti per la rinotifica dei verbali.
4.⁠ ⁠CLAUSOLE VESSATORIE: Ai sensi e per gli effetti degli art. 1341-1342 c.c. il cliente dichiara di aver letto e approvato specificamente i punti 2 e 3 del presente contratto relativi a Limitazioni di Responsabilità, Furto, Danni e Sanzioni Amministrative.

Informativa Privacy (GDPR): Il cliente autorizza il trattamento dei dati personali ai sensi del Regolamento UE 2016/679 per le finalità legate all'esecuzione del contratto.
"""
        pdf.multi_cell(0, 5, formatta_pdf(testo_legale))
        
        # Inserimento Firma
        firma_b64 = dati_contratto.get("firma")
        if firma_b64:
            try:
                img_data = base64.b64decode(forza_testo(firma_b64))
                pdf.image(io.BytesIO(img_data), x=130, y=pdf.get_y()+5, w=50)
            except: pass
        
        pdf.ln(25)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 10, "Firma del Cliente per accettazione specifica clausole 2-3 (Art. 1341 c.c.)", ln=True, align="R")

    elif tipo_doc == "FATTURA":
        prezzo_tot = float(dati_contratto.get('prezzo', 0))
        imponibile = prezzo_tot / 1.22
        iva_valore = prezzo_tot - imponibile

        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "DOCUMENTO COMMERCIALE DI VENDITA", ln=True, align="C", border="B")
        pdf.ln(5)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 6, f"Ricevuta n: {forza_testo(dati_contratto.get('numero_fattura'))}/A del {data_odierna}", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, f"Spett.le {n} {c}", ln=True)
        pdf.cell(0, 6, f"C.F./P.IVA Cliente: {forza_testo(dati_contratto.get('codice_fiscale', '---'))}", ln=True)
        pdf.ln(5)

        # Tabella Dettagliata
        pdf.set_fill_color(235, 235, 235)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(90, 8, "Descrizione", 1, 0, 'L', True)
        pdf.cell(25, 8, "Imponibile", 1, 0, 'C', True)
        pdf.cell(20, 8, "IVA", 1, 0, 'C', True)
        pdf.cell(45, 8, "Totale", 1, 1, 'C', True)

        pdf.set_font("Arial", "", 9)
        descrizione_servizio = f"Noleggio Scooter Targa {t} - dal {i} al {f}"
        pdf.cell(90, 8, formatta_pdf(descrizione_servizio), 1)
        pdf.cell(25, 8, f"{imponibile:.2f}", 1, 0, 'C')
        pdf.cell(20, 8, "22%", 1, 0, 'C')
        pdf.cell(45, 8, f"{prezzo_tot:.2f}", 1, 1, 'C')
        
        pdf.ln(10)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(150, 10, f"TOTALE NETTO A PAGARE: EUR {prezzo_tot:.2f}", 0, 1, 'R')

    elif tipo_doc == "MULTE":
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "COMUNICAZIONE DATI CONDUCENTE (L. 445/2000)", ln=True, align="C")
        pdf.ln(5)
        pdf.set_font("Arial", "", 10)
        testo_multe = f"""
La sottoscritta BATTAGLIA MARIANNA, in qualità di titolare della BATTAGLIA RENT, 
DICHIARA ai sensi della L. 445/2000 che il veicolo targato {t} nel giorno {i} 
era concesso in locazione senza conducente al signor:

COGNOME E NOME: {n} {c}
NATO A: {forza_testo(dati_contratto.get('luogo_nascita'))} IL {forza_testo(dati_contratto.get('data_nascita'))}
RESIDENTE IN: {forza_testo(dati_contratto.get('indirizzo_cliente'))}
IDENTIFICATO A MEZZO PATENTE: {forza_testo(dati_contratto.get('numero_patente'))}

Si allega copia del contratto di locazione e del documento d'identità.
In fede, Marianna Battaglia
"""
        pdf.multi_cell(0, 6, formatta_pdf(testo_multe))

    return pdf.output(dest="S").encode("latin-1")

# ------------------------------------------------
# INTERFACCIA PRINCIPALE STREAMLIT
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
    menu = st.sidebar.radio("Navigazione", ["Nuovo Noleggio", "Archivio Storico"])

    if menu == "Nuovo Noleggio":
        st.title("🛵 Gestione Nuovo Noleggio")
        with st.form("form_completo", clear_on_submit=True):
            c1, c2 = st.columns(2)
            nome_cli = c1.text_input("Nome")
            cognome_cli = c1.text_input("Cognome")
            telefono_cli = c1.text_input("Telefono WhatsApp")
            cf_cli = c1.text_input("Codice Fiscale / ID")
            targa_mezzo = c2.text_input("Targa Scooter").upper()
            patente_cli = c2.text_input("Numero Patente")
            luogo_nas = c2.text_input("Luogo di Nascita")
            data_nas = c2.text_input("Data di Nascita")
            
            p_col1, p_col2, p_col3 = st.columns(3)
            prezzo_noleggio = p_col1.number_input("Prezzo Totale (€)", min_value=0.0)
            data_inizio = p_col2.date_input("Inizio Noleggio")
            data_fine = p_col3.date_input("Fine Noleggio")
            
            indirizzo_cli = st.text_area("Indirizzo di Residenza Completo")
            
            st.subheader("📸 Caricamento Documenti")
            f_col1, f_col2 = st.columns(2)
            foto_fronte = f_col1.file_uploader("Fronte Patente")
            foto_retro = f_col2.file_uploader("Retro Patente")
            
            st.subheader("⚖️ Clausole Legali e Firma")
            st.info("L'accettazione delle clausole è obbligatoria per generare il contratto.")
            cl_1 = st.checkbox("Il cliente conferma che il mezzo è in ottimo stato (Verbale Consegna)")
            cl_2 = st.checkbox("Il cliente accetta Responsabilità, Furto e Multe (Art. 1341-1342 c.c.)")
            cl_3 = st.checkbox("Il cliente autorizza il trattamento dei dati (Privacy GDPR)")
            
            firma_pad = st_canvas(stroke_width=3, stroke_color="#000", background_color="#eee", height=150, width=400, key="pad_firma")
            
            if st.form_submit_button("💾 SALVA E GENERA TUTTO"):
                if cl_1 and cl_2 and cl_3 and nome_cli and targa_mezzo:
                    try:
                        # Gestione Firma
                        firma_b64 = ""
                        if firma_pad.image_data is not None:
                            img_obj = Image.fromarray(firma_pad.image_data.astype("uint8"))
                            buffer_firma = io.BytesIO()
                            img_obj.save(buffer_firma, format="PNG")
                            firma_b64 = base64.b64encode(buffer_firma.getvalue()).decode()

                        # Caricamento Foto
                        url_f = carica_su_supabase(foto_fronte, targa_mezzo, "fronte")
                        url_r = carica_su_supabase(foto_retro, targa_mezzo, "retro")
                        
                        # Calcolo Numero Fattura
                        query_last = supabase.table("contratti").select("numero_fattura").order("id", desc=True).limit(1).execute()
                        nuova_fatt = (query_last.data[0]['numero_fattura'] + 1) if query_last.data else 1

                        # Creazione Record Blindato (Tutto forzato a stringa o numero corretto)
                        record = {
                            "nome": forza_testo(nome_cli),
                            "cognome": forza_testo(cognome_cli),
                            "telefono": forza_testo(telefono_cli),
                            "targa": forza_testo(targa_mezzo),
                            "prezzo": float(prezzo_noleggio),
                            "inizio": forza_testo(data_inizio),
                            "fine": forza_testo(data_fine),
                            "firma": forza_testo(firma_b64),
                            "numero_fattura": int(nuova_fatt),
                            "luogo_nascita": forza_testo(luogo_nas),
                            "data_nascita": forza_testo(data_nas),
                            "numero_patente": forza_testo(patente_cli),
                            "url_fronte": forza_testo(url_f),
                            "url_retro": forza_testo(url_r),
                            "codice_fiscale": forza_testo(cf_cli),
                            "indirizzo_cliente": forza_testo(indirizzo_cli)
                        }
                        
                        supabase.table("contratti").insert(record).execute()
                        st.success("Noleggio registrato con successo!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore critico durante il salvataggio: {e}")
                else:
                    st.warning("Assicurati di aver compilato Nome, Targa e accettato le 3 clausole legali.")

    else:
        st.title("📂 Archivio Storico Contratti")
        try:
            dati_db = supabase.table("contratti").select("*").order("id", desc=True).execute()
            if dati_db.data:
                ricerca = st.text_input("🔍 Filtra per Targa o Cognome").lower()
                for r in dati_db.data:
                    targa_str = forza_testo(r.get('targa', ''))
                    cognome_str = forza_testo(r.get('cognome', '')).upper()
                    fatt_str = forza_testo(r.get('numero_fattura', ''))
                    
                    if ricerca in f"{targa_str} {cognome_str}".lower():
                        with st.expander(f"📋 {targa_str} - {cognome_str} (Ricevuta {fatt_str})"):
                            p1, p2, p3 = st.columns(3)
                            
                            # Generazione PDF al volo protetta
                            p1.download_button("📜 Contratto", genera_pdf_documento(r, "CONTRATTO"), f"Contratto_{targa_str}.pdf")
                            p2.download_button("💰 Ricevuta", genera_pdf_documento(r, "FATTURA"), f"Ricevuta_{fatt_str}.pdf")
                            p3.download_button("🚨 Modulo Multe", genera_pdf_documento(r, "MULTE"), f"Multe_{targa_str}.pdf")
                            
                            st.divider()
                            c_img1, c_img2 = st.columns(2)
                            if r.get("url_fronte"): c_img1.image(r["url_fronte"], caption="Fronte Patente")
                            if r.get("url_retro"): c_img2.image(r["url_retro"], caption="Retro Patente")
                            
                            # WhatsApp
                            num_tel = forza_testo(r.get('telefono'))
                            if num_tel:
                                msg = urllib.parse.quote(f"Gentile {r.get('nome','')}, ecco i documenti Battaglia Rent per il noleggio dello scooter {targa_str}. Buona giornata!")
                                st.markdown(f"[📲 Invia Documenti via WhatsApp](https://wa.me/{num_tel}?text={msg})")
        except Exception as e:
            st.error(f"Impossibile caricare l'archivio: {e}")
