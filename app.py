import streamlit as st
from supabase import create_client, Client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
from fpdf import FPDF
import io
import base64
from datetime import datetime
import urllib.parse

# --- DATI AZIENDALI FISSI ---
DITTA_INFO = {
    "ragione_sociale": "BATTAGLIA RENT di Battaglia Marianna",
    "indirizzo": "Via Cognole n. 5, 80075 Forio (NA)",
    "fiscale": "P.IVA: 10252601215 | C.F.: BTTMNN87A53Z112S"
}

# --- CONNESSIONE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- FUNZIONE DI PROTEZIONE ESTREMA ---
def T(dato):
    """Trasforma QUALSIASI cosa in stringa in modo atomico"""
    if dato is None:
        return ""
    return str(dato)

def clean_pdf(testo):
    """Pulisce il testo per evitare errori di caratteri nel PDF"""
    return T(testo).encode('latin-1', 'replace').decode('latin-1')

# --- GENERAZIONE PDF INTEGRALE (VERSIONE XL) ---
def genera_pdf_completo(d, tipo):
    pdf = FPDF()
    pdf.add_page()
    
    # Intestazione
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, clean_pdf(DITTA_INFO["ragione_sociale"]), ln=True)
    pdf.set_font("Arial", "", 8)
    pdf.cell(0, 4, clean_pdf(DITTA_INFO["indirizzo"]), ln=True)
    pdf.cell(0, 4, clean_pdf(DITTA_INFO["fiscale"]), ln=True)
    pdf.ln(5)

    # Estrazione dati con protezione T()
    cliente = f"{T(d.get('nome'))} {T(d.get('cognome'))}"
    targa = T(d.get('targa'))
    prezzo = T(d.get('prezzo'))
    data_in = T(d.get('inizio'))
    data_fi = T(d.get('fine'))
    patente = T(d.get('numero_patente'))
    cf = T(d.get('codice_fiscale'))

    if tipo == "CONTRATTO":
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "CONTRATTO DI LOCAZIONE SCOOTER", ln=True, align="C", border="B")
        pdf.set_font("Arial", "", 9)
        
        testo_legale = f"""
LOCATARIO: {cliente} | CF: {cf} | PATENTE: {patente}
VEICOLO: {targa} | PERIODO: dal {data_in} al {data_fi}

CONDIZIONI GENERALI:
1) CONSEGNA: Il locatario riceve il veicolo in ottimo stato e con il pieno. Si impegna a restituirlo identico.
2) DANNI E PENALI: In caso di smarrimento chiavi, la penale è di € 250,00. Danni a specchietti e accessori sono a carico del cliente.
3) RESPONSABILITA': Il locatario risponde di ogni infrazione al Codice della Strada e autorizza la rinotifica dei verbali.
4) FURTO: Il cliente risponde dell'intero valore del mezzo se non riconsegna le chiavi o per negligenza.

Firma per approvazione specifica clausole 1, 2, 3, 4 (Art. 1341-1342 c.c.)
"""
        pdf.multi_cell(0, 5, clean_pdf(testo_legale))
        
        # Firma
        firma_raw = d.get("firma")
        if firma_raw:
            try:
                img_b = base64.b64decode(T(firma_raw))
                pdf.image(io.BytesIO(img_b), x=130, y=pdf.get_y()+5, w=50)
            except: pass
        
        pdf.ln(25)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 10, "IL LOCATARIO (Firma)", ln=True, align="R")

    elif tipo == "FATTURA":
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "RICEVUTA DI PAGAMENTO", ln=True, align="C", border="B")
        pdf.ln(5)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 6, f"Ricevuta N. {T(d.get('numero_fattura'))}/A del {datetime.now().strftime('%d/%m/%Y')}", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, f"Spett.le {cliente}", ln=True)
        pdf.ln(10)
        
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(100, 10, "DESCRIZIONE", 1, 0, 'L', True)
        pdf.cell(40, 10, "TOTALE", 1, 1, 'C', True)
        
        pdf.cell(100, 10, clean_pdf(f"Noleggio scooter targa {targa}"), 1)
        pdf.cell(40, 10, f"EUR {prezzo}", 1, 1, 'R')
        
        pdf.ln(10)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(140, 10, f"TOTALE NETTO: EUR {prezzo}", 0, 1, 'R')

    return pdf.output(dest="S").encode("latin-1")

# --- INTERFACCIA ---
if "log" not in st.session_state: st.session_state.log = False

if not st.session_state.log:
    st.title("Accedi")
    if st.text_input("PW", type="password") == "1234":
        if st.button("Entra"): 
            st.session_state.log = True
            st.rerun()
else:
    mode = st.sidebar.selectbox("Menu", ["Nuovo", "Archivio"])

    if mode == "Nuovo":
        st.title("Nuovo Noleggio")
        with st.form("form"):
            c1, c2 = st.columns(2)
            n = c1.text_input("Nome")
            c = c1.text_input("Cognome")
            t = c2.text_input("Targa").upper()
            p = c2.number_input("Prezzo", min_value=0.0)
            pat = c2.text_input("Patente")
            cf = c1.text_input("CF")
            d_ini = st.date_input("Inizio")
            d_fin = st.date_input("Fine")
            
            canvas = st_canvas(stroke_width=2, height=150, width=400, key="f_canvas")
            
            if st.form_submit_button("Salva"):
                try:
                    # Firma
                    f_b64 = ""
                    if canvas.image_data is not None:
                        img = Image.fromarray(canvas.image_data.astype("uint8"))
                        b = io.BytesIO()
                        img.save(b, format="PNG")
                        f_b64 = base64.b64encode(b.getvalue()).decode()

                    # Numero Fattura
                    res = supabase.table("contratti").select("numero_fattura").order("id", desc=True).limit(1).execute()
                    nf = (res.data[0]['numero_fattura'] + 1) if res.data else 1

                    # Inserimento database (FORZA OGNI TIPO DI DATO)
                    obj = {
                        "nome": T(n), "cognome": T(c), "targa": T(t), "prezzo": float(p),
                        "inizio": T(d_ini), "fine": T(d_fin), "firma": T(f_b64),
                        "numero_fattura": int(nf), "numero_patente": T(pat), "codice_fiscale": T(cf)
                    }
                    supabase.table("contratti").insert(obj).execute()
                    st.success("Salvato!")
                    st.rerun()
                except Exception as e: st.error(f"Errore: {e}")

    else:
        st.title("Archivio")
        rows = supabase.table("contratti").select("*").order("id", desc=True).execute()
        for r in rows.data:
            # Protezione totale del titolo dell'expander
            label = f"{T(r.get('targa'))} - {T(r.get('cognome'))}"
            with st.expander(label):
                st.download_button("📜 Contratto", genera_pdf_completo(r, "CONTRATTO"), f"C_{T(r.get('id'))}.pdf")
                st.download_button("💰 Fattura", genera_pdf_completo(r, "FATTURA"), f"F_{T(r.get('id'))}.pdf")
