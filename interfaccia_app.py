import streamlit as st
import pandas as pd
import datetime
import fpdf
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io
import urllib.parse

# 1. CONNESSIONE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def clean_t(text):
    if not text: return ""
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in repls.items(): text = text.replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

# DATI AZIENDA
TITOLARE = "BATTAGLIA MARIANNA"
PIVA_TITOLARE = "10252601215"

# TESTI LEGALI LUNGHI
PRIVACY_TEXT = "INFORMATIVA PRIVACY: I dati personali raccolti saranno trattati ai sensi del Regolamento UE 2016/679 (GDPR). Il trattamento e finalizzato esclusivamente alla gestione del contratto di noleggio e agli obblighi di legge. Il cliente acconsente al trattamento per le finalita indicate."
CLAUSOLE_VESSATORIE = "Ai sensi degli artt. 1341 e 1342 c.c. il Cliente dichiara di aver letto e approvato specificamente le clausole: 3 (Responsabilita multe), 4 (Spese gestione verbali), 5 (Penali danni/furto), 11 (Smarrimento chiavi), 13 (Foro competente)."

st.sidebar.title("🚀 MasterRent Ischia")
aziende_res = supabase.table("aziende").select("*").execute()
lista_aziende = {a['nome_azienda']: a for a in aziende_res.data} if aziende_res.data else {}

if lista_aziende:
    azienda = lista_aziende[st.sidebar.selectbox("Azienda", list(lista_aziende.keys()))]
    menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Noleggio", "🚨 Archivio"])

    if menu == "📝 Nuovo Noleggio":
        st.header(f"Contratto: {azienda['nome_azienda']}")
        
        with st.expander("👤 DATI CLIENTE", expanded=True):
            c1, c2 = st.columns(2)
            cliente = c1.text_input("NOME E COGNOME")
            cf_cliente = c2.text_input("CODICE FISCALE")
            nascita_cliente = c1.text_input("DATA/LUOGO NASCITA")
            residenza_cliente = c2.text_input("RESIDENZA")
            num_doc = c1.text_input("NUMERO PATENTE/DOC")
            telefono = c2.text_input("TELEFONO")

        with st.expander("🛵 VEICOLO", expanded=True):
            targa = st.text_input("TARGA").upper()
            prezzo = st.number_input("PREZZO (€)", min_value=0)

        foto_p = st.camera_input("📸 FOTO PATENTE")
        
        st.subheader("✍️ Firma Elettronica")
        st.write("Firmando qui sotto accetti il contratto, la privacy e le clausole specifiche.")
        canvas = st_canvas(fill_color="white", stroke_width=2, height=150, key="sig")

        if st.button("💾 SALVA E GENERA PDF"):
            if cliente and targa and canvas.image_data is not None:
                try:
                    oggi = str(datetime.date.today())
                    dat = {"cliente": cliente, "cf": cf_cliente, "targa": targa, "azienda_id": azienda['id'], "data_inizio": oggi, "telefono": telefono}
                    res_db = supabase.table("contratti").insert(dat).execute()
                    id_c = res_db.data[0]['id']

                    # --- PDF CONTRATTO COMPLETO ---
                    pdf = fpdf.FPDF()
                    pdf.add_page()
                    
                    # Intestazione
                    pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, txt=clean_t(azienda['nome_azienda']), ln=1, align='C')
                    pdf.set_font("Arial", size=8); pdf.cell(0, 5, txt=f"P.IVA {PIVA_TITOLARE}", ln=1, align='C')
                    pdf.ln(5)

                    # Dati Cliente
                    pdf.set_font("Arial", 'B', 10); pdf.cell(0, 7, "DATI CONTRATTUALI", ln=1, fill=True)
                    pdf.set_font("Arial", size=9)
                    pdf.multi_cell(0, 5, txt=clean_t(f"Cliente: {cliente}\nNato il: {nascita_cliente}\nResidente: {residenza_cliente}\nCF: {cf_cliente}\nDoc: {num_doc}\nVeicolo: {targa}"))
                    pdf.ln(5)

                    # Sezione Privacy
                    pdf.set_font("Arial", 'B', 9); pdf.cell(0, 5, "INFORMATIVA SULLA PRIVACY", ln=1)
                    pdf.set_font("Arial", size=7); pdf.multi_cell(0, 4, txt=clean_t(PRIVACY_TEXT))
                    pdf.ln(3)

                    # Sezione Clausole
                    pdf.set_font("Arial", 'B', 9); pdf.cell(0, 5, "APPROVAZIONE CLAUSOLE SPECIFICHE", ln=1)
                    pdf.set_font("Arial", size=7); pdf.multi_cell(0, 4, txt=clean_t(CLAUSOLE_VESSATORIE))
                    pdf.ln(5)

                    # Firma (Unica firma che viene applicata a tutto il documento)
                    img_s = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA')
                    img_s.save("firma.png")
                    pdf.set_font("Arial", 'I', 8); pdf.cell(0, 5, "Firma del Cliente per accettazione totale:", ln=1)
                    pdf.image("firma.png", x=10, w=40)
                    
                    bytes_pdf = pdf.output(dest='S').encode('latin-1')

                    # STORAGE
                    supabase.storage.from_("contratti_media").upload(f"contratto_{id_c}.pdf", bytes_pdf, {"content-type": "application/pdf"})
                    if foto_p:
                        supabase.storage.from_("contratti_media").upload(f"pat_{id_c}.jpg", foto_p.getvalue(), {"content-type": "image/jpeg"})

                    st.success("✅ Documento creato!")
                    st.download_button("📥 Scarica Contratto Firmato", bytes_pdf, file_name=f"Contratto_{targa}.pdf")

                except Exception as e:
                    st.error(f"Errore: {e}")

    elif menu == "🚨 Archivio":
        st.header("🗄️ Archivio")
        res = supabase.table("contratti").select("*").eq("azienda_id", azienda['id']).execute()
        if res.data:
            df = pd.DataFrame(res.data).sort_values(by='created_at', ascending=False)
            sel = st.selectbox("Seleziona", df['cliente'] + " - " + df['targa'])
            c = df[(df['cliente'] + " - " + df['targa']) == sel].iloc[0]
            st.link_button("📄 Vedi Contratto e Privacy", f"{url}/storage/v1/object/public/contratti_media/contratto_{c['id']}.pdf")
