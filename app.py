import streamlit as st
from supabase import create_client, Client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from fpdf import FPDF
import io
import base64
from datetime import datetime
import urllib.parse

# --- DATI AZIENDALI ---
DITTA = "BATTAGLIA RENT di Battaglia Marianna"
SEDE = "Via Cognole n. 5, 80075 Forio (NA)"
DETTAGLI_FISCALI = "P.IVA: 10252601215 | C.F.: BTTMNN87A53Z112S"

# --- CONNESSIONE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- FUNZIONE SALVA-VITA (IMPEDISCE L'ERRORE DI CONCATENAZIONE) ---
def fs(dato):
    """Forza qualsiasi dato a diventare testo sicuro"""
    return str(dato) if dato is not None else ""

def pdf_text(testo):
    """Converte il testo per renderlo leggibile dal PDF senza errori"""
    return fs(testo).encode('latin-1', 'replace').decode('latin-1')

# --- GENERAZIONE PDF CON I TUOI TESTI ORIGINALI ---
def genera_documento(d, tipo):
    pdf = FPDF()
    pdf.add_page()
    
    # Intestazione Professionale
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, pdf_text(DITTA), ln=True)
    pdf.set_font("Arial", "", 8)
    pdf.cell(0, 4, pdf_text(SEDE), ln=True)
    pdf.cell(0, 4, pdf_text(DETTAGLI_FISCALI), ln=True)
    pdf.ln(5)

    # Recupero dati dal database
    nome = fs(d.get('nome'))
    cognome = fs(d.get('cognome'))
    targa = fs(d.get('targa'))
    prezzo = fs(d.get('prezzo'))
    inizio = fs(d.get('inizio'))
    fine = fs(d.get('fine'))
    patente = fs(d.get('numero_patente'))
    cf = fs(d.get('codice_fiscale'))

    if tipo == "CONTRATTO":
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "CONTRATTO DI LOCAZIONE SCOOTER / RENTAL AGREEMENT", ln=True, align="C", border="B")
        pdf.set_font("Arial", "", 9)
        
        # --- QUI HO REINSERITO IL TUO TESTO INTEGRALE ---
        testo_legale = f"""
DATI LOCATARIO: {nome} {cognome} | CF: {cf} | PATENTE: {patente}
VEICOLO: {targa} | PERIODO: dal {inizio} al {fine} | CORRISPETTIVO: EUR {prezzo}

CONDIZIONI GENERALI DI LOCAZIONE:
1) STATO DEL VEICOLO: Il locatore consegna il veicolo in ottimo stato di conservazione e pulizia, con il pieno di carburante. Il locatario riconoscerà il veicolo nello stato in cui si trova e si impegna a riconsegnarlo nelle medesime condizioni. Eventuali danni riscontrati alla riconsegna (graffi, rotture, danni meccanici) saranno addebitati al locatario.
2) CARBURANTE E CHIAVI: Il veicolo deve essere riconsegnato con il pieno. In difetto, verrà addebitato il costo del carburante mancante più € 10,00 per il servizio di rifornimento. In caso di smarrimento o rottura delle chiavi, il locatario dovrà risarcire l'importo di € 250,00.
3) RESPONSABILITA' E MULTE: Il locatario è l'unico responsabile per le infrazioni al Codice della Strada commesse durante il periodo di locazione. Autorizza sin d'ora il locatore a comunicare i propri dati alle Autorità per la notifica dei verbali e si impegna a pagare una spesa di gestione pratica di € 30,00 per ogni verbale rinotificato.
4) FURTO E DANNI: In caso di furto del veicolo, il locatario è tenuto a risarcire l'intero valore commerciale del mezzo qualora non riconsegni le chiavi originali o venga accertata negligenza (es. chiavi lasciate nel quadro). I danni agli specchietti, bauletto e accessori sono sempre a carico del locatario.
5) FORO COMPETENTE: Per ogni controversia è competente il Foro di Napoli - Sez. distaccata di Ischia.

Ai sensi degli artt. 1341 e 1342 c.c. il sottoscritto dichiara di aver letto e approvato specificamente le clausole 1, 2, 3 e 4.
"""
        pdf.multi_cell(0, 5, pdf_text(testo_legale))
        
        # Gestione Firma
        if d.get("firma"):
            try:
                img_data = base64.b64decode(fs(d["firma"]))
                pdf.image(io.BytesIO(img_data), x=130, y=pdf.get_y()+5, w=50)
            except: pass
        
        pdf.ln(25)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 10, "Firma del Locatario (per accettazione e approvazione specifica)", ln=True, align="R")

    elif tipo == "FATTURA":
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "DOCUMENTO COMMERCIALE (RICEVUTA)", ln=True, align="C", border="B")
        pdf.ln(5)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 6, f"RICEVUTA N. {fs(d.get('numero_fattura'))}/A del {datetime.now().strftime('%d/%m/%Y')}", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, f"SPETT.LE: {nome} {cognome}", ln=True)
        pdf.cell(0, 6, f"CODICE FISCALE: {cf}", ln=True)
        pdf.ln(10)
        
        # Tabella economica
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(100, 10, "DESCRIZIONE SERVIZIO", 1, 0, 'L', True)
        pdf.cell(40, 10, "IMPORTO TOTALE", 1, 1, 'C', True)
        
        pdf.cell(100, 10, pdf_text(f"Noleggio Scooter {targa} (dal {inizio} al {fine})"), 1)
        pdf.cell(40, 10, f"EUR {prezzo}", 1, 1, 'R')
        
        pdf.ln(10)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(140, 10, f"TOTALE PAGATO: EUR {prezzo}", 0, 1, 'R')
        pdf.set_font("Arial", "I", 8)
        pdf.cell(0, 10, "Operazione effettuata ai sensi dell'art. 1, commi da 54 a 89, Legge n. 190/2014.", ln=True)

    return pdf.output(dest="S").encode("latin-1")

# --- INTERFACCIA APP ---
if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Battaglia Rent - Login")
    passw = st.text_input("Inserisci Password", type="password")
    if st.button("Accedi"):
        if passw == "1234":
            st.session_state.auth = True
            st.rerun()
else:
    scelta = st.sidebar.radio("Navigazione", ["Nuovo Noleggio", "Archivio Documenti"])

    if scelta == "Nuovo Noleggio":
        st.title("📝 Registra Noleggio")
        with st.form("form_noleggio", clear_on_submit=True):
            col1, col2 = st.columns(2)
            nome_c = col1.text_input("Nome Cliente")
            cognome_c = col1.text_input("Cognome Cliente")
            targa_v = col2.text_input("Targa").upper()
            prezzo_v = col2.number_input("Prezzo (€)", min_value=0.0)
            
            c3, c4 = st.columns(2)
            pat_v = c3.text_input("N. Patente")
            cf_v = c4.text_input("Codice Fiscale")
            ln_v = c3.text_input("Luogo Nascita")
            dn_v = c4.text_input("Data Nascita")
            
            ind_v = st.text_area("Indirizzo di Residenza")
            d_ini = st.date_input("Data Inizio")
            d_fin = st.date_input("Data Fine")
            
            st.subheader("📸 Documenti")
            f1 = st.file_uploader("Carica Fronte Patente")
            f2 = st.file_uploader("Carica Retro Patente")
            
            st.subheader("🖋️ Firma")
            canvas = st_canvas(stroke_width=3, height=150, width=400, key="canvas_firma")
            
            accetta = st.checkbox("Accetto i termini e le clausole del contratto (Art. 1341-1342 c.c.)")

            if st.form_submit_button("💾 SALVA E GENERA"):
                if accetta and nome_c and targa_v:
                    try:
                        # Processo Firma
                        firma_b64 = ""
                        if canvas.image_data is not None:
                            img = Image.fromarray(canvas.image_data.astype("uint8"))
                            buf = io.BytesIO()
                            img.save(buf, format="PNG")
                            firma_b64 = base64.b64encode(buf.getvalue()).decode()
                        
                        # Caricamento Foto
                        url1, url2 = "", ""
                        if f1:
                            n1 = f"F_{targa_v}_{datetime.now().strftime('%M%S')}.jpg"
                            supabase.storage.from_("documenti").upload(n1, f1.getvalue())
                            url1 = supabase.storage.from_("documenti").get_public_url(n1)
                        if f2:
                            n2 = f"R_{targa_v}_{datetime.now().strftime('%M%S')}.jpg"
                            supabase.storage.from_("documenti").upload(n2, f2.getvalue())
                            url2 = supabase.storage.from_("documenti").get_public_url(n2)

                        # Calcolo Numero Fattura
                        res_f = supabase.table("contratti").select("numero_fattura").order("id", desc=True).limit(1).execute()
                        nuova_f = (res_f.data[0]['numero_fattura'] + 1) if res_f.data else 1

                        # Inserimento database (TUTTO PROTETTO)
                        supabase.table("contratti").insert({
                            "nome": fs(nome_c), "cognome": fs(cognome_c), "targa": fs(targa_v),
                            "prezzo": float(prezzo_v), "inizio": fs(d_ini), "fine": fs(d_fin),
                            "firma": fs(firma_b64), "numero_fattura": int(nuova_f),
                            "luogo_nascita": fs(ln_v), "data_nascita": fs(dn_v),
                            "numero_patente": fs(pat_v), "url_fronte": fs(url1),
                            "url_retro": fs(url2), "codice_fiscale": fs(cf_v),
                            "indirizzo_cliente": fs(ind_v)
                        }).execute()
                        
                        st.success("✅ Noleggio salvato correttamente!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore: {e}")
                else:
                    st.warning("⚠️ Compila i dati obbligatori e firma.")

    else:
        st.title("📂 Archivio Storico")
        dati_db = supabase.table("contratti").select("*").order("id", desc=True).execute()
        if dati_db.data:
            cerca = st.text_input("🔍 Cerca per targa o cognome").lower()
            for r in dati_db.data:
                titolo = f"{fs(r.get('targa'))} - {fs(r.get('cognome')).upper()}"
                if cerca in titolo.lower():
                    with st.expander(titolo):
                        c1, c2 = st.columns(2)
                        c1.download_button("📜 Scarica Contratto", genera_documento(r, "CONTRATTO"), f"Contr_{fs(r.get('targa'))}.pdf")
                        c2.download_button("💰 Scarica Fattura", genera_documento(r, "FATTURA"), f"Fatt_{fs(r.get('targa'))}.pdf")
                        
                        st.write("---")
                        i1, i2 = st.columns(2)
                        if r.get("url_fronte"): i1.image(r["url_fronte"], caption="Fronte Patente")
                        if r.get("url_retro"): i2.image(r["url_retro"], caption="Retro Patente")
