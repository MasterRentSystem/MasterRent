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
# GENERAZIONE PDF
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

    nome_completo = f"{s(c.get('nome'))} {s(c.get('cognome'))}"
    targa = s(c.get('targa'))

    if tipo == "CONTRATTO":
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "CONTRATTO DI NOLEGGIO / RENTAL AGREEMENT", ln=True, align="C", border="B")
        pdf.ln(5)
        pdf.set_font("Arial", "", 10)
        testo = f"Cliente: {nome_completo} | CF/ID: {s(c.get('codice_fiscale'))}\n" \
                f"Residenza: {s(c.get('indirizzo_cliente'))}\n" \
                f"Targa: {targa} | Patente: {s(c.get('numero_patente'))}\n" \
                f"Periodo: dal {s(c.get('inizio'))} al {s(c.get('fine'))} | Prezzo: EUR {s(c.get('prezzo'))}\n\n" \
                f"CONDIZIONI DI NOLEGGIO:\n" \
                f"1. Il conducente dichiara di essere in possesso di regolare patente di guida.\n" \
                f"2. Il locatario e responsabile di ogni danno causato al veicolo o a terzi.\n" \
                f"3. In caso di furto, il locatario risponde per l'intero valore del veicolo se non riconsegna le chiavi.\n" \
                f"4. Tutte le contravvenzioni (multe) prese durante il periodo sono a carico del locatario.\n" \
                f"5. Il veicolo deve essere riconsegnato con lo stesso livello di carburante iniziale.\n\n" \
                f"Ai sensi degli artt. 1341 e 1342 c.c. si approvano specificamente i punti 2, 3 e 4."
        pdf.multi_cell(0, 5, safe_pdf_text(testo))
        if c.get("firma"):
            try:
                firma_bytes = base64.b64decode(s(c["firma"]))
                pdf.image(io.BytesIO(firma_bytes), x=130, y=pdf.get_y()+5, w=50)
            except: pass
        pdf.ln(20)
        pdf.cell(0, 10, "Firma del Cliente", ln=True, align="R")

    elif tipo == "MULTE":
        pdf.set_font("Arial", "", 10)
        pdf.ln(5)
        pdf.cell(0, 5, "Spett. le Polizia Locale di ________________", ln=True)
        pdf.ln(5)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 5, "OGGETTO: COMUNICAZIONE LOCAZIONE VEICOLO - VERBALE N. ______________", ln=True)
        pdf.ln(5)
        pdf.set_font("Arial", "", 10)
        corpo = f"La sottoscritta {TITOLARE}, {DETTAGLI_TITOLARE}, titolare della ditta {DITTA},\n\n" \
                f"DICHIARA ai sensi della L. 445/2000 che il veicolo targato {targa} " \
                f"il giorno {s(c.get('inizio'))} era concesso in locazione a:\n\n" \
                f"COGNOME E NOME: {nome_completo}\n" \
                f"NATO A: {s(c.get('luogo_nascita'))} IL {s(c.get('data_nascita'))}\n" \
                f"RESIDENTE: {s(c.get('indirizzo_cliente'))}\n" \
                f"PATENTE: {s(c.get('numero_patente'))}\n\n" \
                f"Si allega contratto conforme all'originale.\n\nIn fede, Marianna Battaglia"
        pdf.multi_cell(0, 5, safe_pdf_text(corpo))

    elif tipo == "FATTURA":
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "RICEVUTA DI PAGAMENTO", ln=True, align="C", border="B")
        pdf.ln(10)
        pdf.cell(0, 6, f"Ricevuta n: {s(c.get('numero_fattura'))}/A del {oggi}", ln=True)
        pdf.cell(0, 6, f"Cliente: {nome_completo}", ln=True)
        pdf.ln(5)
        pdf.cell(100, 10, safe_pdf_text(f"Noleggio Scooter {targa}"), 1)
        pdf.cell(40, 10, f"EUR {s(c.get('prezzo'))}", 1, 1, 'R')

    return pdf.output(dest="S").encode("latin-1")

# ------------------------------------------------
# INTERFACCIA
# ------------------------------------------------
if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Login")
    if st.text_input("Password", type="password") == "1234":
        if st.button("Accedi"):
            st.session_state.auth = True
            st.rerun()
else:
    menu = st.sidebar.radio("Menu", ["Nuovo", "Archivio"])

    if menu == "Nuovo":
        st.title("🛵 Nuovo Noleggio")
        with st.form("f_noleggio", clear_on_submit=True):
            c1, c2 = st.columns(2)
            n = c1.text_input("Nome")
            c = c1.text_input("Cognome")
            tel = c1.text_input("Telefono (WhatsApp)")
            cf = c1.text_input("Codice Fiscale")
            
            t = c2.text_input("Targa").upper()
            pat = c2.text_input("N. Patente")
            l_n = c2.text_input("Luogo Nascita")
            d_n = c2.text_input("Data Nascita")
            p = c2.number_input("Prezzo (€)", min_value=0.0)
            
            ind = st.text_area("Indirizzo Residenza")
            ini, fin = st.columns(2)
            d_ini = ini.date_input("Inizio")
            d_fin = fin.date_input("Fine")
            
            f_col1, f_col2 = st.columns(2)
            foto_f = f_col1.file_uploader("Fronte Patente")
            foto_r = f_col2.file_uploader("Retro Patente")
            
            canvas = st_canvas(stroke_width=3, height=150, width=400, key="f_sig")
            acc = st.checkbox("Accetto Condizioni e Privacy")

            if st.form_submit_button("💾 SALVA"):
                if acc and n and t:
                    try:
                        sig = ""
                        if canvas.image_data is not None:
                            img = Image.fromarray(canvas.image_data.astype("uint8"))
                            buf = io.BytesIO()
                            img.save(buf, format="PNG")
                            sig = base64.b64encode(buf.getvalue()).decode()

                        u_f = upload_foto(foto_f, t, "F")
                        u_r = upload_foto(foto_r, t, "R")
                        nf = prossimo_numero_fattura()

                        res = supabase.table("contratti").insert({
                            "nome": n, "cognome": c, "telefono": tel, "targa": t, "prezzo": p,
                            "inizio": str(d_ini), "fine": str(d_fin), "firma": sig,
                            "numero_fattura": nf, "luogo_nascita": l_n, "data_nascita": d_n,
                            "numero_patente": pat, "url_fronte": u_f, "url_retro": u_r,
                            "codice_fiscale": cf, "indirizzo_cliente": ind
                        }).execute()
                        st.success("Salvato!")
                        st.rerun()
                    except Exception as e: st.error(f"Errore: {e}")

    else:
        st.title("📂 Archivio")
        data = supabase.table("contratti").select("*").order("id", desc=True).execute()
        for r in data.data:
            with st.expander(f"📄 {r['targa']} - {r['cognome']}"):
                col_d1, col_d2, col_d3 = st.columns(3)
                col_d1.download_button("📜 Contratto", genera_pdf_tipo(r, "CONTRATTO"), f"Contr_{r['targa']}.pdf")
                col_d2.download_button("💰 Ricevuta", genera_pdf_tipo(r, "FATTURA"), f"Ric_{r['id']}.pdf")
                col_d3.download_button("🚨 Modulo Vigili", genera_pdf_tipo(r, "MULTE"), f"Multe_{r['targa']}.pdf")
                
                st.write("---")
                im1, im2 = st.columns(2)
                if r.get("url_fronte"): im1.image(r["url_fronte"], caption="Fronte")
                if r.get("url_retro"): im2.image(r["url_retro"], caption="Retro")
