import streamlit as st
from supabase import create_client, Client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from fpdf import FPDF
import io
import base64
from datetime import datetime

# --- CONFIGURAZIONE DATI DITTA ---
DITTA = "BATTAGLIA RENT"
TITOLARE = "BATTAGLIA MARIANNA"
DETTAGLI_TITOLARE = "nata a Berlino (Germania) il 13/01/1987 e residente in Forio alla Via Cognole n. 5"
INDIRIZZO_FISCALE = "Via Cognole n. 5, Forio (NA)"
DATI_IVA = "P.IVA: 10252601215 | C.F.: BTTMNN87A53Z112S"

# --- CONNESSIONE SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# ------------------------------------------------
# UTILITY
# ------------------------------------------------
def s(dato):
    if dato is None: return ""
    return str(dato)

def safe_pdf_text(text):
    return s(text).encode("latin-1", "replace").decode("latin-1")

def prossimo_numero_fattura():
    try:
        res = supabase.table("contratti").select("numero_fattura").order("numero_fattura", desc=True).limit(1).execute()
        if res.data:
            ultimo = res.data[0].get("numero_fattura")
            return int(ultimo) + 1 if ultimo else 1
        return 1
    except: return 1

def upload_foto(file, targa, prefix):
    try:
        if file is None: return None
        est = file.name.split('.')[-1]
        nome_f = f"{prefix}{targa}{datetime.now().strftime('%H%M%S')}.{est}"
        supabase.storage.from_("documenti").upload(nome_f, file.getvalue())
        return supabase.storage.from_("documenti").get_public_url(nome_f)
    except: return None

# ------------------------------------------------
# GENERAZIONE PDF (FIXATO PER ERRORI ENCODE)
# ------------------------------------------------
def genera_pdf_tipo(c, tipo):
    pdf = FPDF()
    pdf.add_page()
    oggi = datetime.now().strftime("%d/%m/%Y")
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, safe_pdf_text(DITTA), ln=True)
    pdf.set_font("Arial", "", 8)
    pdf.cell(0, 4, safe_pdf_text(INDIRIZZO_FISCALE), ln=True)
    pdf.cell(0, 4, safe_pdf_text(DATI_IVA), ln=True)
    pdf.ln(5)

    n_c = f"{s(c.get('nome'))} {s(c.get('cognome'))}"
    targa = s(c.get('targa'))

    if tipo == "CONTRATTO":
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "CONTRATTO DI NOLEGGIO / RENTAL AGREEMENT", ln=True, align="C", border="B")
        pdf.ln(5)
        pdf.set_font("Arial", "", 10)
        testo = f"Cliente: {n_c} | CF/ID: {s(c.get('codice_fiscale'))}\n" \
                f"Residenza: {s(c.get('indirizzo_cliente'))}\n" \
                f"Targa: {targa} | Patente: {s(c.get('numero_patente'))}\n" \
                f"Periodo: dal {s(c.get('inizio'))} al {s(c.get('fine'))} | Prezzo: EUR {s(c.get('prezzo'))}\n\n" \
                f"CONDIZIONI DI NOLEGGIO:\n" \
                f"1. Il conducente dichiara di essere in possesso di regolare patente.\n" \
                f"2. Il locatario e responsabile di ogni danno causato al veicolo o a terzi.\n" \
                f"3. In caso di furto, il locatario risponde per l'intero valore del veicolo.\n" \
                f"4. Le contravvenzioni (multe) prese durante il periodo sono a carico del locatario.\n" \
                f"5. Il veicolo va riconsegnato con lo stesso livello di carburante.\n\n" \
                f"Ai sensi artt. 1341-1342 c.c. si approvano i punti 2, 3 e 4."
        pdf.multi_cell(0, 5, safe_pdf_text(testo))
        if c.get("firma"):
            try:
                f_bytes = base64.b64decode(s(c["firma"]))
                pdf.image(io.BytesIO(f_bytes), x=130, y=pdf.get_y()+5, w=50)
            except: pass
        pdf.ln(20)
        pdf.cell(0, 10, "Firma del Cliente", ln=True, align="R")

    elif tipo == "MULTE":
        pdf.set_font("Arial", "", 10)
        pdf.ln(5)
        pdf.cell(0, 5, "Spett. le Polizia Locale di ________________", ln=True)
        pdf.ln(5)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 5, f"OGGETTO: COMUNICAZIONE LOCAZIONE VEICOLO {targa}", ln=True)
        pdf.ln(5)
        pdf.set_font("Arial", "", 10)
        corpo = f"La sottoscritta {TITOLARE}, {DETTAGLI_TITOLARE}, titolare di {DITTA},\n\n" \
                f"DICHIARA ai sensi L. 445/2000 che il veicolo targato {targa} " \
                f"il giorno {s(c.get('inizio'))} era locato a:\n\n" \
                f"SOGGETTO: {n_c}\n" \
                f"NATO A: {s(c.get('luogo_nascita'))} IL {s(c.get('data_nascita'))}\n" \
                f"RESIDENTE: {s(c.get('indirizzo_cliente'))}\n" \
                f"PATENTE: {s(c.get('numero_patente'))}\n\n" \
                f"Si allega contratto e documento. Copia conforme all'originale.\n\nIn fede, Marianna Battaglia"
        pdf.multi_cell(0, 5, safe_pdf_text(corpo))

    elif tipo == "FATTURA":
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "RICEVUTA DI PAGAMENTO", ln=True, align="C", border="B")
        pdf.ln(10)
        pdf.cell(0, 6, f"Ricevuta n: {s(c.get('numero_fattura'))}/A del {oggi}", ln=True)
        pdf.cell(0, 6, f"Cliente: {n_c}", ln=True)
        pdf.ln(5)
        pdf.cell(110, 10, safe_pdf_text(f"Noleggio Scooter {targa}"), 1)
        pdf.cell(40, 10, f"EUR {s(c.get('prezzo'))}", 1, 1, 'R')

    # FIX CRITICO: Controlliamo il tipo di output per evitare l'errore .encode()
    pdf_out = pdf.output(dest='S')
    if isinstance(pdf_out, str):
        return pdf_out.encode('latin-1')
    return bytes(pdf_out)

# ------------------------------------------------
# INTERFACCIA APP
# ------------------------------------------------
if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🛵 BATTAGLIA RENT")
    if st.text_input("Password", type="password") == "1234":
        if st.button("Accedi"):
            st.session_state.auth = True
            st.rerun()
else:
    m = st.sidebar.radio("Naviga", ["Nuovo Noleggio", "Archivio Storico"])

    if m == "Nuovo Noleggio":
        st.title("🛵 Nuovo Contratto")
        with st.form("form_n", clear_on_submit=True):
            col1, col2 = st.columns(2)
            nome = col1.text_input("Nome")
            cognome = col1.text_input("Cognome")
            tel = col1.text_input("WhatsApp")
            cf = col1.text_input("Codice Fiscale")
            targa = col2.text_input("Targa").upper()
            pat = col2.text_input("N. Patente")
            l_n = col2.text_input("Luogo Nascita")
            d_n = col2.text_input("Data Nascita")
            prez = col2.number_input("Prezzo (€)", min_value=0.0)
            ind = st.text_area("Indirizzo Completo")
            i_d, f_d = st.columns(2)
            ini, fin = i_d.date_input("Inizio"), f_d.date_input("Fine")
            
            st.subheader("📸 Foto Patente")
            f_col, r_col = st.columns(2)
            front_f = f_col.file_uploader("Fronte")
            back_f = r_col.file_uploader("Retro")
            
            canvas = st_canvas(stroke_width=3, height=150, width=400, key="sig")
            acc = st.checkbox("Accetta Condizioni")

            if st.form_submit_button("💾 SALVA"):
                if acc and nome and targa:
                    try:
                        f_b64 = ""
                        if canvas.image_data is not None:
                            img = Image.fromarray(canvas.image_data.astype("uint8"))
                            buf = io.BytesIO()
                            img.save(buf, format="PNG")
                            f_b64 = base64.b64encode(buf.getvalue()).decode()

                        u_f = upload_foto(front_f, targa, "F")
                        u_r = upload_foto(back_f, targa, "R")
                        n_fat = prossimo_numero_fattura()

                        supabase.table("contratti").insert({
                            "nome": nome, "cognome": cognome, "telefono": tel, "targa": targa,
                            "prezzo": prez, "inizio": str(ini), "fine": str(fin),
                            "firma": f_b64, "numero_fattura": n_fat, "luogo_nascita": l_n,
                            "data_nascita": d_n, "numero_patente": pat, "url_fronte": u_f,
                            "url_retro": u_r, "codice_fiscale": cf, "indirizzo_cliente": ind
                        }).execute()
                        st.success("Salvato!")
                        st.rerun()
                    except Exception as e: st.error(f"Errore: {e}")

    else:
        st.title("📂 Archivio")
        res = supabase.table("contratti").select("*").order("id", desc=True).execute()
        cerca = st.text_input("🔍 Cerca Targa o Cognome").lower()
        
        for r in res.data:
            if cerca in f"{r['targa']} {r['cognome']}".lower():
                with st.expander(f"📄 {r['targa']} - {r['cognome'].upper()}"):
                    c1, c2, c3 = st.columns(3)
                    try:
                        # Generiamo i PDF gestendo i bytes correttamente
                        pdf_c = genera_pdf_tipo(r, "CONTRATTO")
                        c1.download_button("📜 Contratto", pdf_c, f"Cont_{r['targa']}.pdf", "application/pdf")
                        
                        pdf_f = genera_pdf_tipo(r, "FATTURA")
                        c2.download_button("💰 Ricevuta", pdf_f, f"Ric_{r['numero_fattura']}.pdf", "application/pdf")
                        
                        pdf_m = genera_pdf_tipo(r, "MULTE")
                        c3.download_button("🚨 Modulo Vigili", pdf_m, f"Multe_{r['targa']}.pdf", "application/pdf")
                    except Exception as e:
                        st.error(f"Errore PDF: {e}")

                    st.write("---")
                    st.subheader("📸 Documenti")
                    f_col, r_col = st.columns(2)
                    if r.get("url_fronte"): f_col.image(r["url_fronte"], caption="Fronte")
                    if r.get("url_retro"): r_col.image(r["url_retro"], caption="Retro")
