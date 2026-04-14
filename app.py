import streamlit as st
from supabase import create_client, Client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from fpdf import FPDF
import io
import base64
from datetime import datetime

# --- DATI AZIENDA ---
DITTA = "BATTAGLIA RENT"
TITOLARE = "BATTAGLIA MARIANNA"
INDIRIZZO = "Via Cognole n. 5, Forio (NA)"
DATI_IVA = "P.IVA: 10252601215 | C.F.: BTTMNN87A53Z112S"

# --- SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- UTILITY ---
def s(v): return "" if v is None else str(v)

def safe_text(text):
    return s(text).encode("latin-1", "replace").decode("latin-1")

def genera_numero_univoco():
    """
    Recupera l'ultimo numero e aggiunge 1. 
    In un sistema professionale, questo campo dovrebbe essere 
    un 'Identity Column' seriale direttamente su Supabase.
    """
    try:
        res = supabase.table("contratti").select("numero_fattura").order("numero_fattura", desc=True).limit(1).execute()
        if res.data and res.data[0].get("numero_fattura"):
            return int(res.data[0]["numero_fattura"]) + 1
        return 1
    except:
        return 1

def upload_foto(file, targa, tipo):
    if file is None: return None
    try:
        img = Image.open(file)
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
        img.thumbnail((1000, 1000))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        nome = f"{tipo}{targa}{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
        supabase.storage.from_("documenti").upload(nome, buf.getvalue(), {"content-type": "image/jpeg"})
        return supabase.storage.from_("documenti").get_public_url(nome)
    except: return None

# --- MOTORE PDF (CON NUMERAZIONE LEGALE) ---
def genera_pdf(c, tipo="CONTRATTO"):
    pdf = FPDF()
    pdf.add_page()
    
    # Intestazione Legale
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, safe_text(DITTA), ln=True)
    pdf.set_font("Arial", "", 8)
    pdf.cell(0, 4, safe_text(INDIRIZZO), ln=True)
    pdf.cell(0, 4, safe_text(DATI_IVA), ln=True)
    
    # Numero Documento e Data
    pdf.ln(5)
    pdf.set_font("Arial", "I", 10)
    data_doc = s(c.get('created_at'))[:10] if c.get('created_at') else datetime.now().strftime("%Y-%m-%d")
    pdf.cell(0, 5, f"Documento N: {s(c.get('numero_fattura'))} / {datetime.now().year}", ln=True, align="R")
    pdf.cell(0, 5, f"Data: {data_doc}", ln=True, align="R")
    pdf.ln(5)

    n_c = f"{s(c.get('nome'))} {s(c.get('cognome'))}"
    targa = s(c.get('targa'))

    if tipo == "CONTRATTO":
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, f"CONTRATTO DI NOLEGGIO N. {s(c.get('numero_fattura'))}", ln=True, align="C", border="B")
        pdf.ln(5)
        pdf.set_font("Arial", "", 10)
        corpo = f"""Il locatore {DITTA} concede in noleggio al cliente:
CLIENTE: {n_c} | NAZIONALITA': {s(c.get('nazionalita'))}
NATO A: {s(c.get('luogo_nascita'))} IL {s(c.get('data_nascita'))}
RESIDENTE: {s(c.get('indirizzo_cliente'))} | C.F.: {s(c.get('codice_fiscale'))}
VEICOLO: {targa} | PATENTE: {s(c.get('numero_patente'))}
PERIODO: Dal {s(c.get('inizio'))} Al {s(c.get('fine'))}
PREZZO PATTUITO: EUR {s(c.get('prezzo'))}

CONDIZIONI GENERALI (Artt. 1341-1342 c.c.):
1.⁠ ⁠Il cliente è costituito custode del veicolo ed è responsabile di ogni danno o furto.
2.⁠ ⁠Le sanzioni amministrative elevate durante il noleggio sono a carico del cliente.
3.⁠ ⁠Il cliente dichiara di aver preso visione dello stato del mezzo.
4.⁠ ⁠Trattamento dati: il cliente autorizza ai fini del contratto (GDPR 679/2016)."""
        pdf.multi_cell(0, 5, safe_text(corpo))
        
        # Firma di sicurezza
        if c.get("firma") and len(str(c["firma"])) > 20:
            try:
                pdf.image(io.BytesIO(base64.b64decode(c["firma"])), x=130, y=pdf.get_y()+5, w=50)
            except: pass

    elif tipo == "FATTURA":
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, f"RICEVUTA/FATTURA N. {s(c.get('numero_fattura'))}", ln=True, align="C", border="B")
        pdf.ln(10)
        pdf.set_font("Arial", "", 11)
        pdf.cell(0, 8, f"Destinatario: {n_c}", ln=True)
        pdf.cell(0, 8, f"C.F.: {s(c.get('codice_fiscale'))}", ln=True)
        pdf.ln(5)
        pdf.cell(0, 8, f"Descrizione: Noleggio scooter targa {targa}", ln=True)
        pdf.cell(0, 8, f"Dal {s(c.get('inizio'))} al {s(c.get('fine'))}", ln=True)
        pdf.ln(10)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, f"TOTALE CORRISPETTIVO: EUR {s(c.get('prezzo'))}", align="R", border="T")

    elif tipo == "VIGILI":
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "DICHIARAZIONE DATI CONDUCENTE PER VERBALE", ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("Arial", "", 10)
        testo_v = f"""In relazione al contratto di noleggio N. {s(c.get('numero_fattura'))},
il sottoscritto {TITOLARE} comunica che il conducente del veicolo {targa} era:

NOME: {n_c}
NATO A: {s(c.get('luogo_nascita'))} IL {s(c.get('data_nascita'))}
CODICE FISCALE: {s(c.get('codice_fiscale'))}
PATENTE: {s(c.get('numero_patente'))}

Si allega copia del documento di identità."""
        pdf.multi_cell(0, 5, safe_text(testo_v))

    out = pdf.output(dest="S")
    return bytes(out) if isinstance(out, bytearray) else out.encode("latin-1", "replace")

# --- INTERFACCIA ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    pwd = st.text_input("Inserisci Password", type="password")
    if st.button("Accedi"):
        if pwd == "1234": st.session_state.auth = True; st.rerun()
    st.stop()

t1, t2 = st.tabs(["🆕 Crea Noleggio", "📂 Archivio Fiscale"])

with t1:
    with st.form("form_legale", clear_on_submit=True):
        st.subheader("Dati Cliente")
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome")
        cognome = c1.text_input("Cognome")
        nazion = c2.text_input("Nazionalità")
        cf = c2.text_input("Codice Fiscale")
        luogo = c1.text_input("Luogo Nascita")
        data_n = c2.text_input("Data Nascita (GG/MM/AAAA)")
        indirizzo = st.text_area("Indirizzo Residenza")
        
        st.subheader("Dati Mezzo")
        c3, c4, c5 = st.columns(3)
        targa = c3.text_input("Targa").upper()
        patente = c4.text_input("N. Patente")
        prezzo = c5.number_input("Totale Prezzo (€)", min_value=0.0)
        
        ini, fin = st.columns(2)
        d_inizio = ini.date_input("Inizio Noleggio")
        d_fine = fin.date_input("Fine Noleggio")
        
        f_p = st.file_uploader("Carica Patente (Fronte)")
        r_p = st.file_uploader("Carica Patente (Retro)")
        
        st.info("⚠️ Il cliente firmando accetta di pagare tutte le multe e i danni.")
        accetto_privacy = st.checkbox("Il cliente accetta l'informativa privacy e i termini contrattuali")
        
        st.write("Firma Cliente (Obbligatoria):")
        canvas = st_canvas(height=150, width=400, stroke_width=3, key="sig_legale")

        if st.form_submit_button("REGISTRA E GENERA NUMERO"):
            firma_data = base64.b64encode(Image.fromarray(canvas.image_data.astype("uint8")).tobytes()).decode() if canvas.image_data is not None else None
            # Controllo firma reale (non solo pixel vuoti)
            bbox = Image.fromarray(canvas.image_data.astype("uint8")).getbbox() if canvas.image_data is not None else None
            
            if not nome or not targa or not accetto_privacy or bbox is None:
                st.error("ERRORE: Compilare tutti i campi, accettare i termini e apporre la firma.")
            else:
                with st.spinner("Generazione numero fattura e salvataggio..."):
                    num_univoco = genera_numero_univoco()
                    uf = upload_foto(f_p, targa, "FRONT")
                    ur = upload_foto(r_p, targa, "BACK")
                    
                    # Converti firma in b64 corretta per PDF
                    img_f = Image.fromarray(canvas.image_data.astype("uint8"))
                    buf_f = io.BytesIO()
                    img_f.save(buf_f, format="PNG")
                    f_b64 = base64.b64encode(buf_f.getvalue()).decode()

                    supabase.table("contratti").insert({
                        "nome": nome, "cognome": cognome, "nazionalita": nazion, "codice_fiscale": cf,
                        "luogo_nascita": luogo, "data_nascita": data_n, "indirizzo_cliente": indirizzo,
                        "targa": targa, "numero_patente": patente, "prezzo": prezzo,
                        "inizio": str(d_inizio), "fine": str(d_fine), "firma": f_b64,
                        "url_fronte": uf, "url_retro": ur, "numero_fattura": num_univoco,
                        "created_at": datetime.now().isoformat()
                    }).execute()
                    st.success(f"CONTRATTO N. {num_univoco} SALVATO!")

with t2:
    st.subheader("Ricerca Documenti")
    filtro = st.text_input("Cerca per Cognome o Targa").lower()
    res = supabase.table("contratti").select("*").order("numero_fattura", desc=True).execute()
    
    for r in res.data:
        if filtro in f"{r['cognome']} {r['targa']}".lower():
            with st.expander(f"N. {r['numero_fattura']} - {r['targa']} ({r['cognome']})"):
                col1, col2, col3 = st.columns(3)
                col1.download_button("📜 Contratto", genera_pdf(r, "CONTRATTO"), f"Contratto_{r['numero_fattura']}.pdf")
                col2.download_button("💰 Ricevuta", genera_pdf(r, "FATTURA"), f"Ricevuta_{r['numero_fattura']}.pdf")
                col3.download_button("🚨 Modulo Vigili", genera_pdf(r, "VIGILI"), f"Vigili_{r['numero_fattura']}.pdf")
