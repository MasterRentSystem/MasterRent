import streamlit as st
from supabase import create_client, Client
import base64
from datetime import datetime
from fpdf import FPDF
import io
import urllib.parse

# --- CONFIGURAZIONE BATTAGLIA RENT ---
DITTA = "BATTAGLIA RENT"
TITOLARE = "BATTAGLIA MARIANNA"
SEDE = "Via Cognole n. 5 - 80075 Forio (NA)"
PIVA = "10252601215"
CF_TITOLARE = "BTTMNN87A53Z112S"

# Connessione al database Supabase
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- FUNZIONI DI UTILITÀ ---
def safe(t): 
    return str(t).encode("latin-1", "replace").decode("latin-1")

def get_prossimo_numero():
    try:
        res = supabase.table("contratti").select("numero_fattura").execute()
        nums = [int(r['numero_fattura']) for r in res.data if str(r['numero_fattura']).isdigit()]
        return max(nums) + 1 if nums else 1
    except: return 1

# --- GENERATORE MODULO RINOTIFICA (IDENTICO ALLA TUA FOTO) ---
def genera_rinotifica_pdf(c, v):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Times", "", 11)
    
    # Destinatario (in alto a destra)
    pdf.set_xy(110, 20)
    pdf.cell(0, 5, "Spett. le", ln=True)
    pdf.set_x(110)
    pdf.set_font("Times", "B", 11)
    pdf.cell(0, 5, f"Polizia Locale di {v['comune']}", ln=True)
    
    pdf.ln(15)
    pdf.set_font("Times", "B", 10)
    pdf.cell(20, 5, "OGGETTO:")
    pdf.set_font("Times", "", 10)
    pdf.cell(0, 5, f"RIFERIMENTO VS. ACCERTAMENTO VIOLAZIONE N. {v['num']} PROT. {v['prot']}")
    pdf.ln(5)
    pdf.cell(0, 5, "                       - COMUNICAZIONE LOCAZIONE VEICOLO")
    
    pdf.ln(10)
    testo = f"""In riferimento al Verbale di accertamento di infrazione al Codice della strada di cui all'oggetto, con la presente, la sottoscritta BATTAGLIA MARIANNA nata a Berlino (Germania) il 13/01/1987 e residente in Forio alla Via Cognole n. 5 in qualità di titolare dell'omonima ditta individuale, C.F.: {CF_TITOLARE} e P.IVA: {PIVA}
    
    DICHIARA
Ai sensi della L. 445/2000 che il veicolo modello {c['modello']} targato {c['targa']} il giorno {v['data']} era concesso in locazione senza conducente al signor:

COGNOME E NOME: {c['cognome'].upper()} {c['nome'].upper()}
LUOGO E DATA DI NASCITA: {c.get('luogo_nascita', '-').upper()} {c.get('data_nascita', '-')}
RESIDENZA: {c.get('indirizzo', '-').upper()}
IDENTIFICATO A MEZZO: Patente di Guida"""
    
    pdf.multi_cell(0, 6, safe(testo))
    pdf.ln(15)
    pdf.set_x(130)
    pdf.cell(0, 5, "In fede", ln=True, align="C")
    pdf.set_x(130)
    pdf.cell(0, 5, "Marianna Battaglia", ln=True, align="C")
    return bytes(pdf.output(dest="S"))

# --- INTERFACCIA STREAMLIT ---
st.set_page_config(page_title="BATTAGLIA RENT", layout="centered")

# Login Rapido
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    pwd = st.text_input("Inserisci Password", type="password")
    if st.button("ENTRA"):
        if pwd == "1234": st.session_state.auth = True; st.rerun()
    st.stop()

tab1, tab2, tab3 = st.tabs(["📝 NUOVO", "📂 ARCHIVIO", "🚨 MULTE"])

with tab1:
    with st.form("registrazione"):
        st.subheader("👤 Dati Cliente")
        c1, c2 = st.columns(2)
        n = c1.text_input("Nome")
        cg = c2.text_input("Cognome")
        ln = st.text_input("Luogo di Nascita")
        dn = st.text_input("Data di Nascita (GG/MM/AAAA)")
        ind = st.text_input("Residenza (Indirizzo completo)")
        cf = st.text_input("Codice Fiscale")
        pat = st.text_input("Numero Patente")
        wa = st.text_input("Cellulare (WhatsApp)")

        st.subheader("🛵 Mezzo")
        m1, m2, m3 = st.columns(3)
        mod = m1.text_input("Modello")
        tg = m2.text_input("Targa").upper()
        prz = m3.number_input("Prezzo €", 0.0)

        st.subheader("📸 Foto Documenti")
        f1 = st.camera_input("FOTO PATENTE")
        f2 = st.camera_input("FOTO CONTRATTO FIRMATO")

        if st.form_submit_button("💾 SALVA NOLEGGIO"):
            if not n or not tg or not f2:
                st.error("Mancano dati o la foto del contratto!")
            else:
                def b64(f): return "data:image/png;base64," + base64.b64encode(f.getvalue()).decode()
                num_f = get_prossimo_numero()
                dati = {
                    "nome": n, "cognome": cg, "luogo_nascita": ln, "data_nascita": dn,
                    "indirizzo": ind, "codice_fiscale": cf, "numero_patente": pat,
                    "pec": wa, "modello": mod, "targa": tg, "prezzo": prz,
                    "data_inizio": datetime.now().strftime("%d/%m/%Y"),
                    "numero_fattura": num_f, "foto_patente": b64(f1), "firma": b64(f2)
                }
                supabase.table("contratti").insert(dati).execute()
                st.success(f"Archiviato! Contratto N. {num_f}")

with tab2:
    cerca = st.text_input("🔍 Cerca Targa o Cognome")
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for r in res.data:
        if cerca.lower() in f"{r['targa']} {r['cognome']}".lower():
            with st.expander(f"📄 {r['targa']} - {r['cognome']}"):
                st.write(f"Data: {r['data_inizio']} | Fattura: {r['numero_fattura']}")
                
                # Link WhatsApp veloce
                msg = f"Ciao {r['nome']}, grazie da Battaglia Rent!"
                st.link_button("📲 CONTATTA SU WHATSAPP", f"https://wa.me/{r['pec']}?text={urllib.parse.quote(msg)}")
                
                # Visualizzazione Immagini Corretta
                c_a, c_b = st.columns(2)
                try:
                    if r.get("foto_patente"):
                        img_p = base64.b64decode(r["foto_patente"].split("base64,")[1])
                        c_a.image(img_p, caption="Patente")
                    if r.get("firma"):
                        img_c = base64.b64decode(r["firma"].split("base64,")[1])
                        c_b.image(img_c, caption="Contratto Firmato")
                except Exception as e:
                    st.error("Errore nel caricamento immagini.")

with tab3:
    st.subheader("🚨 Genera Rinotifica per i Vigili")
    tg_multa = st.text_input("Targa del mezzo multato").upper()
    v_comune = st.text_input("Polizia Locale di (es: Serrara Fontana)")
    v_data = st.text_input("Data dell'infrazione")
    v_num = st.text_input("Verbale Numero")
    v_prot = st.text_input("Protocollo")

    if st.button("📄 CREA MODULO PRONTO"):
        db_res = supabase.table("contratti").select("*").eq("targa", tg_multa).execute()
        if db_res.data:
            cliente = db_res.data[0]
            v_info = {"comune": v_comune, "data": v_data, "num": v_num, "prot": v_prot}
            pdf_v = genera_rinotifica_pdf(cliente, v_info)
            st.download_button("📩 SCARICA MODULO COMPILATO", pdf_v, f"Rinotifica_{tg_multa}.pdf")
        else:
            st.error("Targa non trovata in archivio!")
