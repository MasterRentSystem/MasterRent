import streamlit as st
import datetime
import fpdf
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
import time

# 1. CONNESSIONE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# Nome del bucket corretto
BUCKET_NAME = "DOCUMENTI_PATENTI"

def clean_t(text):
    if not text or text == "None": return "---"
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in repls.items(): text = str(text).replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

INTESTAZIONE = "MASTERRENT DI MARIANNA BATTAGLIA\nVia Cognole n. 5 - 80075 Forio (NA)\nC.F.: BTTMNN87A53Z112S | P.IVA: 10252601215"

def genera_pdf(c, tipo="CONTRATTO"):
    pdf = fpdf.FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 11); pdf.set_fill_color(235, 235, 235)
    pdf.multi_cell(0, 6, txt=clean_t(INTESTAZIONE), border=1, align='L', fill=True)
    pdf.ln(8)
    pdf.set_font("Arial", 'B', 16)
    titolo = "CONTRATTO DI NOLEGGIO" if tipo == "CONTRATTO" else "RICEVUTA DI PAGAMENTO"
    pdf.cell(0, 10, clean_t(titolo), ln=1, align='C')
    pdf.ln(5); pdf.set_font("Arial", size=10)
    
    # Tabella Dati
    pdf.cell(95, 8, clean_t(f"CLIENTE: {c.get('cliente')}"), border=1)
    pdf.cell(95, 8, clean_t(f"C.F.: {c.get('cf')}"), border=1, ln=1)
    pdf.cell(190, 8, clean_t(f"RESIDENZA: {c.get('residenza')}"), border=1, ln=1)
    pdf.cell(60, 8, clean_t(f"TARGA: {c.get('targa')}"), border=1)
    pdf.cell(65, 8, clean_t(f"DAL: {c.get('data_inizio')}"), border=1)
    pdf.cell(65, 8, clean_t(f"AL: {c.get('data_fine')}"), border=1, ln=1)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(190, 10, clean_t(f"TOTALE PAGATO: {c.get('prezzo', 0)} EURO"), border=1, ln=1, align='C', fill=True)
    
    if tipo == "CONTRATTO":
        pdf.ln(5); pdf.set_font("Arial", 'B', 8); pdf.cell(0, 5, "NOTE LEGALI E PRIVACY", ln=1)
        pdf.set_font("Arial", size=7.5)
        pdf.multi_cell(0, 4, txt=clean_t("Il cliente autorizza la foto del documento per Pubblica Sicurezza (GDPR). Si assume ogni responsabilita per multe e danni. Accetta artt. 1341-1342 c.c."), border='T')
        pdf.ln(15); pdf.cell(0, 10, "Firma Digitale del Cliente: ______________________", ln=1, align='R')
    
    return pdf.output(dest='S').encode('latin-1')

# --- APP ---
st.sidebar.title("🚀 MasterRent")
menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Noleggio", "🗄️ Archivio Documenti"])

if menu == "📝 Nuovo Noleggio":
    st.header("Nuovo Noleggio")
    with st.form("form_v7"):
        c1, c2 = st.columns(2)
        cliente = c1.text_input("Nome Cliente")
        cf = c2.text_input("Codice Fiscale")
        residenza = c1.text_input("Residenza")
        targa = c2.text_input("TARGA").upper()
        prezzo = c1.number_input("Prezzo (€)", min_value=0.0)
        d_ini = c1.date_input("Inizio", datetime.date.today())
        d_fin = c2.date_input("Fine", datetime.date.today() + datetime.timedelta(days=1))
        
        foto = st.camera_input("📸 Foto Patente")
        st.write("✍️ *Firma Cliente*")
        st_canvas(fill_color="white", stroke_width=2, height=120, key="canvas_v7")
        
        if st.form_submit_button("💾 SALVA ED ARCHIVIA"):
            path_foto = None
            if foto:
                try:
                    fname = f"{targa}_{int(time.time())}.jpg"
                    supabase.storage.from_(BUCKET_NAME).upload(fname, foto.getvalue())
                    path_foto = fname
                except Exception as e:
                    st.error(f"Errore caricamento foto: {e}")
            
            dat = {"cliente": cliente, "cf": cf, "residenza": residenza, "targa": targa, "prezzo": prezzo, "data_inizio": str(d_ini), "data_fine": str(d_fin), "foto_path": path_foto}
            supabase.table("contratti").insert(dat).execute()
            st.success("Contratto Salvato con Successo!")

elif menu == "🗄️ Archivio Documenti":
    st.header("Archivio Generale")
    res = supabase.table("contratti").select("*").order("data_inizio", desc=True).execute()
    
    if res.data:
        # Intestazione Colonne
        col_h = st.columns([2, 1, 1, 1])
        col_h[0].write("*CLIENTE / TARGA*")
        col_h[1].write("*CONTRATTO*")
        col_h[2].write("*RICEVUTA*")
        col_h[3].write("*FOTO*")
        st.divider()

        for c in res.data:
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            c1.write(f"*{c['cliente']}*\n{c['targa']}")
            
            # Contratti e Ricevute
            c2.download_button("📜 PDF", genera_pdf(c, "CONTRATTO"), f"Contratto_{c['targa']}.pdf", key=f"c_{c['id']}")
            c3.download_button("💰 PDF", genera_pdf(c, "FATTURA"), f"Ricevuta_{c['id']}.pdf", key=f"f_{c['id']}")
            
            # Foto
            if c.get("foto_path"):
                url_foto = supabase.storage.from_(BUCKET_NAME).get_public_url(c["foto_path"])
                c4.link_button("📸 VEDI", url_foto)
            else:
                c4.write("Nessuna")
