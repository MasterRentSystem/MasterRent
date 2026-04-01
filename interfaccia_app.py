import streamlit as st
import datetime
from supabase import create_client
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import io

# Connessione
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.set_page_config(page_title="MasterRent V47", layout="wide")

def genera_pdf_reportlab(titolo, contenuto):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    p.setFont("Helvetica-Bold", 16)
    p.drawCentredString(300, 800, titolo)
    
    p.setFont("Helvetica", 12)
    y = 750
    for linea in contenuto.split('\n'):
        p.drawString(50, y, linea)
        y -= 20
    
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

menu = st.sidebar.radio("Menu", ["📝 Nuovo Noleggio", "🗄️ Archivio"])

if menu == "📝 Nuovo Noleggio":
    with st.form("f_v47"):
        nome = st.text_input("Nome Cliente")
        targa = st.text_input("Targa").upper()
        prezzo = st.number_input("Prezzo (€)", min_value=0.0)
        cf = st.text_input("Codice Fiscale")
        accetto = st.checkbox("Accetto Privacy")
        if st.form_submit_button("💾 SALVA"):
            if nome and targa and accetto:
                supabase.table("contratti").insert({"cliente": nome, "targa": targa, "prezzo": prezzo, "cf": cf, "data_inizio": str(datetime.date.today())}).execute()
                st.success("Salvato!")

elif menu == "🗄️ Archivio":
    res = supabase.table("contratti").select("*").order("id", desc=True).execute()
    for c in res.data:
        with st.expander(f"📄 {c['cliente']} - {c['targa']}"):
            col1, col2 = st.columns(2)
            
            # --- CONTRATTO ---
            testo_c = f"CLIENTE: {c['cliente']}\nTARGA: {c['targa']}\nCF: {c['cf']}\nDATA: {c['data_inizio']}\n\nCONTRATTO DI NOLEGGIO SCOOTER\nIl cliente dichiara di ricevere il veicolo in ottimo stato."
            pdf_c = genera_pdf_reportlab("CONTRATTO DI NOLEGGIO", testo_c)
            col1.download_button("📜 SCARICA CONTRATTO", data=pdf_c, file_name=f"C_{c['id']}.pdf", mime="application/pdf", key=f"c_{c['id']}")

            # --- RICEVUTA ---
            testo_r = f"RICEVUTO DA: {c['cliente']}\nPER NOLEGGIO TARGA: {c['targa']}\n\nTOTALE PAGATO: Euro {c['prezzo']}\n\nGrazie per aver scelto MasterRent!"
            pdf_r = genera_pdf_reportlab("RICEVUTA DI PAGAMENTO", testo_r)
            col2.download_button("💰 SCARICA RICEVUTA", data=pdf_r, file_name=f"R_{c['id']}.pdf", mime="application/pdf", key=f"r_{c['id']}")
