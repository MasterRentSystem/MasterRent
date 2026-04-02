import streamlit as st
from fpdf import FPDF
from supabase import create_client
from streamlit_drawable_canvas import st_canvas

st.set_page_config(layout="wide", page_title="MasterRent V240")
url, key = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def clean(t):
    if not t: return ""
    repl = {"à":"a","è":"e","é":"e","ì":"i","ò":"o","ù":"u","€":"Euro"}
    for k,v in repl.items(): t = str(t).replace(k,v)
    return t.encode("latin-1", "ignore").decode("latin-1")

def genera_pdf(c, tipo="CONTRATTO"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 7, "BATTAGLIA MARIANNA", ln=True)
    pdf.set_font("Arial", size=9)
    pdf.cell(0, 5, "Via Cognole, 5 - 80075 Forio (NA)", ln=True)
    pdf.cell(0, 5, "C.F. BTTMNN87A53Z112S - P. IVA 10252601215", ln=True)
    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    titolo = "MODULO DATI CONDUCENTE (MULTE)" if tipo == "MULTE" else f"{tipo} DI NOLEGGIO"
    pdf.cell(0, 10, clean(titolo), ln=True, align="C", border="B")
    pdf.ln(5)
    pdf.set_font("Arial", size=10)
    if tipo == "MULTE":
        t = f"Il veicolo TARGA {c.get('targa','')} in data {c.get('data_contratto',' ')[:10]} era affidato a:\n\nCONDUCENTE: {c.get('nome','')} {c.get('cognome','')}\nNATO A: {c.get('luogo_nascita','')}\nRESIDENTE: {c.get('indirizzo','')}\nC.F.: {c.get('codice_fiscale','')}\nPATENTE: {c.get('numero_patente','')}"
        pdf.multi_cell(0, 8, clean(t))
    else:
        info = f"CLIENTE: {c.get('nome','')} {c.get('cognome','')}\nRESIDENTE: {c.get('indirizzo','')}\nC.F.: {c.get('codice_fiscale','')}\nTARGA: {c.get('targa','')} | PATENTE: {c.get('numero_patente','')}\nPREZZO: {c.get('prezzo',0)} Euro"
        pdf.multi_cell(0, 8, clean(info), border=1)
        if tipo == "CONTRATTO":
            pdf.ln(5); pdf.set_font("Arial", "B", 9); pdf.cell(0, 7, "CONDIZIONI LEGALI & PRIVACY", ln=True)
            pdf.set_font("Arial", size=8); pdf.multi_cell(0, 4, clean("Responsabilita danni e multe a carico del cliente. Privacy GDPR Reg. UE 2016/679."))
            pdf.ln(15); pdf.cell(0, 10, "FIRMA DEL CLIENTE: ______________________________", ln=True)
    return bytes(pdf.output())

st.header("🛵 MasterRent V240 - Marianna")
with st.form("f"):
    c1, c2 = st.columns(2)
    n, cog = c1.text_input("Nome"), c1.text_input("Cognome")
    luo, ind = c1.text_input("Luogo Nascita"), c1.text_input("Indirizzo Residenza")
    cf, pat = c2.text_input("Codice Fiscale"), c2.text_input("N. Patente")
    tar, pre = c2.text_input("Targa").upper(), c2.number_input("Prezzo (€)", min_value=0.0)
    st_canvas(stroke_width=2, height=100, width=300, key="v240")
    if st.form_submit_button("💾 SALVA"):
        d = {"nome":n,"cognome":cog,"luogo_nascita":luo,"indirizzo":ind,"codice_fiscale":cf,"numero_patente":pat,"targa":tar,"prezzo":pre}
        supabase.table("contratti").insert(d).execute()
        st.success("Salvato!")

st.divider()
res = supabase.table("contratti").select("*").order("id", desc=True).execute()
for c in res.data:
    with st.expander(f"📄 {c.get('nome','')} - {c.get('targa','')}"):
        b1, b2, b3 = st.columns(3)
        b1.download_button("📜 CONTRATTO", genera_pdf(c, "CONTRATTO"), f"C_{c['id']}.pdf", key=f"c_{c['id']}")
        b2.download_button("💰 RICEVUTA", genera_pdf(c, "RICEVUTA"), f"R_{c['id']}.pdf", key=f"r_{c['id']}")
        b3.download_button("🚨 MODULO MULTE", genera_pdf(c, "MULTE"), f"M_{c['id']}.pdf", key=f"m_{c['id']}")
