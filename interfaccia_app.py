import streamlit as st
import datetime
from supabase import create_client
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import io

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def genera_pdf_contratto(n, t, d):
    buf = io.BytesIO()
    p = canvas.Canvas(buf, pagesize=A4)
    p.setFont("Helvetica-Bold", 16)
    p.drawCentredString(300, 800, "CONTRATTO DI NOLEGGIO")
    p.setFont("Helvetica", 12)
    p.drawString(50, 750, f"CLIENTE: {n}")
    p.drawString(50, 730, f"TARGA: {t}")
    p.drawString(50, 710, f"DATA: {d}")
    p.drawString(50, 650, "Firma del cliente: ________________________")
    p.showPage()
    p.save()
    buf.seek(0)
    return buf

def genera_pdf_ricevuta(n, p):
    buf = io.BytesIO()
    p_pdf = canvas.Canvas(buf, pagesize=A4)
    p_pdf.setFont("Helvetica-Bold", 16)
    p_pdf.drawCentredString(300, 800, "RICEVUTA DI PAGAMENTO")
    p_pdf.setFont("Helvetica", 12)
    p_pdf.drawString(50, 750, f"RICEVUTO DA: {n}")
    p_pdf.drawString(50, 730, f"IMPORTO: Euro {p}")
    p_pdf.drawString(50, 710, "Pagamento effettuato con successo.")
    p_pdf.showPage()
    p_pdf.save()
    buf.seek(0)
    return buf

st.title("🛵 MasterRent V70 - FIX")

res = supabase.table("contratti").select("*").order("id", desc=True).limit(10).execute()
for r in res.data:
    with st.expander(f"{r['cliente']} - {r['targa']}"):
        c1, c2 = st.columns(2)
        
        # TASTO CONTRATTO
        pdf_c = genera_pdf_contratto(r['cliente'], r['targa'], r['data_inizio'])
        c1.download_button("📜 SCARICA CONTRATTO", pdf_c, f"Contratto_{r['id']}.pdf", "application/pdf", key=f"c_{r['id']}")
        
        # TASTO RICEVUTA
        pdf_r = genera_pdf_ricevuta(r['cliente'], r['prezzo'])
        c2.download_button("💰 SCARICA RICEVUTA", pdf_r, f"Ricevuta_{r['id']}.pdf", "application/pdf", key=f"r_{r['id']}")
