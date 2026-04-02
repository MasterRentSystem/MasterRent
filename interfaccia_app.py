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

def crea_pdf(titolo, info):
    buf = io.BytesIO()
    p = canvas.Canvas(buf, pagesize=A4)
    p.setFont("Helvetica-Bold", 16)
    p.drawCentredString(300, 800, titolo)
    p.setFont("Helvetica", 12)
    y = 750
    for linea in info.split('\n'):
        p.drawString(50, y, linea)
        y -= 20
    p.showPage()
    p.save()
    buf.seek(0)
    return buf

st.title("🛵 MasterRent Ischia - V65")

tab1, tab2 = st.tabs(["📝 Nuovo Noleggio", "🗄️ Archivio"])

with tab1:
    with st.form("f_v65"):
        n = st.text_input("Nome Cliente")
        t = st.text_input("Targa").upper()
        p = st.number_input("Prezzo (€)", min_value=0.0)
        if st.form_submit_button("SALVA"):
            if n and t:
                supabase.table("contratti").insert({"cliente": n, "targa": t, "prezzo": p, "data_inizio": str(datetime.date.today())}).execute()
                st.success("Salvato!")

with tab2:
    res = supabase.table("contratti").select("*").order("id", desc=True).limit(15).execute()
    for row in res.data:
        with st.expander(f"📄 {row['cliente']} - {row['targa']}"):
            c1, c2 = st.columns(2)
            
            # --- LOGICA PDF 1: CONTRATTO ---
            info_c = f"CONTRATTO DI NOLEGGIO\nCliente: {row['cliente']}\nTarga: {row['targa']}\nData: {row['data_inizio']}"
            pdf_c = crea_pdf("CONTRATTO DI NOLEGGIO", info_c)
            c1.download_button("📜 CONTRATTO", pdf_c, f"C_{row['id']}.pdf", "application/pdf", key=f"c_{row['id']}")
            
            # --- LOGICA PDF 2: RICEVUTA ---
            info_r = f"RICEVUTA DI PAGAMENTO\nRicevuto da: {row['cliente']}\nPer targa: {row['targa']}\nTOTALE: {row['prezzo']} Euro"
            pdf_r = crea_pdf("RICEVUTA DI PAGAMENTO", info_r)
            c2.download_button("💰 RICEVUTA", pdf_r, f"R_{row['id']}.pdf", "application/pdf", key=f"r_{row['id']}")
