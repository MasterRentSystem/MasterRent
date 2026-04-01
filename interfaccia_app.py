import streamlit as st
import datetime
from supabase import create_client
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import io

# Connessione (Prendi i segreti)
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.set_page_config(page_title="MasterRent Ischia V1", layout="wide")

def crea_pdf(titolo, dati_cliente):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(300, 800, titolo)
    c.setFont("Helvetica", 12)
    text = c.beginText(50, 750)
    for linea in dati_cliente.split('\n'):
        text.textLine(linea)
    c.drawText(text)
    c.showPage()
    c.save()
    buf.seek(0)
    return buf

st.title("🛵 MasterRent - Gestione Noleggi")

tab1, tab2 = st.tabs(["📝 Nuovo", "🗄️ Archivio"])

with tab1:
    with st.form("nuovo_noleggio"):
        nome = st.text_input("Nome Cliente")
        targa = st.text_input("Targa").upper()
        prezzo = st.number_input("Prezzo (€)", min_value=0.0)
        accetto = st.checkbox("Accetto Privacy e Condizioni")
        if st.form_submit_button("SALVA"):
            if nome and targa and accetto:
                supabase.table("contratti").insert({"cliente": nome, "targa": targa, "prezzo": prezzo, "data_inizio": str(datetime.date.today())}).execute()
                st.success("Dati salvati!")
            else:
                st.error("Mancano dati o spunta privacy!")

with tab2:
    res = supabase.table("contratti").select("*").order("id", desc=True).limit(10).execute()
    for n in res.data:
        with st.expander(f"{n['cliente']} - {n['targa']}"):
            c1, c2 = st.columns(2)
            
            # Preparo i dati
            info = f"Cliente: {n['cliente']}\nTarga: {n['targa']}\nData: {n['data_inizio']}\nPrezzo: {n['prezzo']} Euro"
            
            # Bottone 1: Contratto
            pdf_contratto = crea_pdf("CONTRATTO DI NOLEGGIO", info + "\n\nFirma: ______________")
            c1.download_button("📜 Scarica Contratto", pdf_contratto, f"Contratto_{n['id']}.pdf", "application/pdf", key=f"btn_c_{n['id']}")
            
            # Bottone 2: Ricevuta
            pdf_ricevuta = crea_pdf("RICEVUTA DI PAGAMENTO", info + "\n\nPagamento Ricevuto.")
            c2.download_button("💰 Scarica Ricevuta", pdf_ricevuta, f"Ricevuta_{n['id']}.pdf", "application/pdf", key=f"btn_r_{n['id']}")

