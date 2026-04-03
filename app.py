import streamlit as st
import datetime
import base64
from fpdf import FPDF
from supabase import create_client
from streamlit_drawable_canvas import st_canvas

st.set_page_config(layout="wide", page_title="MasterRent Pro")

# --- DATI FISCALI FISSI ---
INTESTAZIONE = "BATTAGLIA MARIANNA\nVia Cognole, 5 - 80075 Forio (NA)\nC.F. BTTMNN87A53Z112S - P. IVA 10252601215"

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def clean(t):
    if not t: return ""
    repl = {"à":"a","è":"e","é":"e","ì":"i","ò":"o","ù":"u","€":"Euro"}
    for k,v in repl.items(): t = str(t).replace(k,v)
    return t.encode("latin-1", "ignore").decode("latin-1")

def prossimo_numero():
    anno = datetime.date.today().year
    res = supabase.table("contatore_fatture").select("*").eq("anno", anno).execute()
    if not res.data:
        supabase.table("contatore_fatture").insert({"anno": anno, "ultimo_numero": 1}).execute()
        return 1
    numero = res.data[0]["ultimo_numero"] + 1
    supabase.table("contatore_fatture").update({"ultimo_numero": numero}).eq("anno", anno).execute()
    return numero

# --- PDF GENERATOR ---
def genera_pdf_tipo(c, tipo="CONTRATTO"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.multi_cell(0, 7, clean(INTESTAZIONE))
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 12)
    titolo = "MODULO DATI CONDUCENTE (PER MULTE)" if tipo == "MULTE" else f"{tipo} DI NOLEGGIO"
    pdf.cell(0, 10, clean(titolo), ln=True, align="C", border="B")
    pdf.ln(5)

    pdf.set_font("Arial", size=11)
    if tipo == "MULTE":
        testo = f"Il veicolo targa {c['targa']} in data {str(c.get('data_contratto',''))[:10]} era affidato a:\n\n" \
                f"CLIENTE: {c['nome']} {c['cognome']}\n" \
                f"NATO A: {c.get('luogo_nascita','')}\n" \
                f"RESIDENTE IN: {c.get('indirizzo','')}\n" \
                f"C.F.: {c['codice_fiscale']}\n" \
                f"PATENTE: {c['numero_patente']}\n\n" \
                f"Si rilascia per accertamento violazione."
    else:
        testo = f"CLIENTE: {c['nome']} {c['cognome']}\n" \
                f"RESIDENTE: {c.get('indirizzo','')}\n" \
                f"C.F.: {c['codice_fiscale']}\n" \
                f"TARGA: {c['targa']} | PATENTE: {c['numero_patente']}\n" \
                f"PREZZO: Euro {c['prezzo']}\n"
        if tipo == "CONTRATTO":
            testo += "\n\nCLAUSOLE: Il cliente e responsabile per danni e MULTE.\n" \
                     "Privacy: Dati trattati secondo Reg. UE 2016/679 (GDPR)."

    pdf.multi_cell(0, 8, clean(testo))
    if tipo == "CONTRATTO":
        pdf.ln(10)
        pdf.cell(0, 10, "FIRMA CLIENTE: ________________________", ln=True)
    
    return bytes(pdf.output())

# --- FORM ---
with st.form("contratto"):
    st.header("Nuovo Contratto / New Rental")
    col1, col2 = st.columns(2)
    nome = col1.text_input("Nome")
    cognome = col1.text_input("Cognome")
    luogo_n = col1.text_input("Luogo di Nascita")
    indirizzo = col1.text_input("Indirizzo Residenza")
    cf = col1.text_input("Codice Fiscale")
    
    tel = col2.text_input("Telefono")
    pat = col2.text_input("Numero Patente")
    targa = col2.text_input("Targa").upper()
    prezzo = col2.number_input("Prezzo", min_value=0.0)
    deposito = col2.number_input("Deposito", min_value=0.0)

    st.subheader("Firma Cliente")
    canvas = st_canvas(stroke_width=3, height=150, width=400, key="firma")
    privacy = st.checkbox("Accetto Privacy GDPR e Clausole Multe")

    if st.form_submit_button("SALVA CONTRATTO"):
        if not privacy or not nome or not targa:
            st.error("Dati mancanti o privacy non accettata")
        else:
            numero = prossimo_numero()
 # --- SALVATAGGIO DATI ---
            try:
                dati = {
                    "nome": nome,
                    "cognome": cognome,
                    "telefono": tel,
                    "numero_patente": pat,
                    "targa": targa,
                    "prezzo": prezzo,
                    "indirizzo": indirizzo,
                    "luogo_nascita": luogo_n,
                    "data_nascita": str(data_n),
                    "privacy_accettata": True
                }
                supabase.table("contratti").insert(dati).execute()
                st.success(f"✅ Contratto di {nome} salvato con successo!")
            except Exception as e:
                st.error(f"Errore database: {e}")

# --- ARCHIVIO ---
st.divider()
st.header("Archivio Contratti")
res = supabase.table("contratti").select("*").order("id", desc=True).execute()

for c in res.data:
    num_f = c.get('id', '0')
    nome_c = c.get('nome', 'Sconosciuto')
    cognome_c = c.get('cognome', '')
    targa_c = c.get('targa', 'No Targa')

    with st.expander(f"ID: {num_f} - {nome_c} {cognome_c} - {targa_c}"):
        col1, col2, col3 = st.columns(3)
        # Generazione PDF con i 3 tasti
        col1.download_button("📜 Contratto", genera_pdf_tipo(c, "CONTRATTO"), f"C_{num_f}.pdf")
        col2.download_button("💰 Fattura", genera_pdf_tipo(c, "FATTURA"), f"F_{num_f}.pdf")
        col3.download_button("🚨 Modulo Multe", genera_pdf_tipo(c, "MULTE"), f"M_{targa_c}.pdf")
