import streamlit as st
import pandas as pd
import datetime
import fpdf
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io
import urllib.parse

# CONNESSIONE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def clean_t(text):
    if not text: return ""
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'"}
    for k, v in repls.items(): text = text.replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

TESTO_LEGALE = [
    "1. Veicolo consegnato in ottimo stato. / Vehicle delivered in excellent condition.",
    "2. Riconsegna con pieno obbligatoria. / Return with full tank mandatory.",
    "3. Responsabilita multe a carico cliente. / Customer liable for traffic fines.",
    "4. Spese gestione verbali: Euro 25.83. / Admin fee for fines: Euro 25.83.",
    "5. Responsabilita danni e furto cliente. / Customer liable for damage and theft.",
    "6. No guida sotto alcool o droghe. / No driving under influence.",
    "7. Il noleggio termina all'ora indicata. / Rental ends at specified time.",
    "8. Denuncia immediata in caso di sinistro. / Immediate accident report required.",
    "9. Vietato sub-noleggio o cessione. / Sub-rental or transfer prohibited.",
    "10. Patente valida e in corso di validita. / Valid driving license required.",
    "11. Smarrimento chiavi: Euro 50. / Lost keys penalty: Euro 50.",
    "12. Solo per l'isola di Ischia. / For Ischia Island use only.",
    "13. Foro competente: Napoli - Sez. Ischia. / Jurisdiction: Naples Court.",
    "14. Privacy GDPR 679/2016 accettata. / GDPR Privacy policy accepted."
]

st.sidebar.title("🚀 MasterRent Ischia")
aziende_res = supabase.table("aziende").select("*").execute()
lista_aziende = {a['nome_azienda']: a for a in aziende_res.data} if aziende_res.data else {}

if lista_aziende:
    azienda = lista_aziende[st.sidebar.selectbox("Azienda", list(lista_aziende.keys()))]
    menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Contratto", "🚨 Archivio"])

    if menu == "📝 Nuovo Contratto":
        st.header(f"Contratto: {azienda['nome_azienda']}")
        with st.expander("👤 DATI CLIENTE", expanded=True):
            c1, c2 = st.columns(2)
            cliente = c1.text_input("NOME E COGNOME")
            cf = c2.text_input("CODICE FISCALE")
            residenza = c1.text_input("RESIDENZA")
            num_doc = c2.text_input("NUMERO DOCUMENTO")
            telefono = c1.text_input("TELEFONO (es. 39...)")

        with st.expander("🛵 DATI NOLEGGIO", expanded=True):
            c3, c4 = st.columns(2)
            targa = c3.text_input("TARGA").upper()
            km_uscita = c4.text_input("KM USCITA", value="0")
            prezzo_tot = st.number_input("PREZZO (€)", min_value=0)

        foto_p = st.camera_input("📸 FOTO PATENTE")
        canvas = st_canvas(fill_color="white", stroke_width=2, height=150, key="sig")

        if st.button("💾 SALVA TUTTO"):
            if cliente and targa and canvas.image_data is not None:
                try:
                    # 1. Database
                    dat = {"cliente": cliente, "cf": cf, "residenza": residenza, "num_doc": num_doc, "telefono": telefono, "targa": targa, "km_uscita": km_uscita, "prezzo_tot": str(prezzo_tot), "azienda_id": azienda['id'], "data_inizio": str(datetime.date.today())}
                    res = supabase.table("contratti").insert(dat).execute()
                    id_row = res.data[0]['id']

                    # 2. PDF
                    pdf = fpdf.FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", 'B', 15); pdf.cell(0, 10, txt=clean_t(azienda['nome_azienda']), ln=1, align='C')
                    pdf.set_font("Arial", size=9); pdf.multi_cell(0, 5, txt=clean_t(f"Cliente: {cliente}\nCF: {cf}\nTarga: {targa} | Doc: {num_doc}"))
                    pdf.ln(3); pdf.set_font("Arial", size=7)
                    for p in TESTO_LEGALE: pdf.multi_cell(0, 3.5, txt=clean_t(p))
                    
                    img_s = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA')
                    img_s.save("f.png")
                    pdf.image("f.png", x=10, w=35)
                    pdf_bytes = pdf.output(dest='S').encode('latin-1')

                    # 3. Upload (Percorsi puliti per l'archivio)
                    supabase.storage.from_("contratti_media").upload(f"pdf_{id_row}.pdf", pdf_bytes, {"content-type": "application/pdf"})
                    if foto_p:
                        supabase.storage.from_("contratti_media").upload(f"img_{id_row}.jpg", foto_p.getvalue(), {"content-type": "image/jpeg"})

                    st.success("✅ Contratto salvato con successo!")
                    
                    # 4. WhatsApp
                    msg = urllib.parse.quote(f"Ciao {cliente}, ecco il contratto MasterRent per {targa}. Grazie!")
                    st.markdown(f'''<a href="https://wa.me/{telefono}?text={msg}" target="_blank"><button style="background-color:#25D366;color:white;border:none;padding:10px 20px;border-radius:5px;cursor:pointer;font-weight:bold;">📲 WhatsApp Cliente</button></a>''', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Errore: {e}")

    elif menu == "🚨 Archivio":
        st.header("🗄️ Archivio Contratti")
        res = supabase.table("contratti").select("*").eq("azienda_id", azienda['id']).execute()
        if res.data:
            df = pd.DataFrame(res.data).sort_values(by='created_at', ascending=False)
            sel = st.selectbox("Seleziona", df['cliente'] + " - " + df['targa'])
            c = df[(df['cliente'] + " - " + df['targa']) == sel].iloc[0]
            
            st.link_button("📄 Vedi Contratto", f"{url}/storage/v1/object/public/contratti_media/pdf_{c['id']}.pdf")
            st.link_button("🪪 Vedi Patente", f"{url}/storage/v1/object/public/contratti_media/img_{c['id']}.jpg")
