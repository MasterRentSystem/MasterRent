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

# DATI TUA AZIENDA (Per modulo Vigili)
TITOLARE = "BATTAGLIA MARIANNA"
NATO_A = "Berlino (Germania)"
NATO_IL = "13/01/1987"
RESIDENTE_A = "Forio"
IN_VIA = "Via Cognole n. 5"
CF_TITOLARE = "BTTMNN87A53Z112S"
PIVA_TITOLARE = "10252601215"

# TESTI LEGALI
PRIVACY_TEXT = "I dati personali sono trattati ai sensi del Reg. UE 2016/679 (GDPR) per finalita contrattuali e obblighi di legge. Il cliente acconsente al trattamento."
CLAUSOLE_VESSATORIE = "Ai sensi degli artt. 1341 e 1342 c.c. il Cliente approva specificamente le clausole: 3 (Multe), 4 (Spese gestione), 5 (Danni/Furto), 11 (Chiavi), 13 (Foro)."

st.sidebar.title("🚀 MasterRent Ischia")
aziende_res = supabase.table("aziende").select("*").execute()
lista_aziende = {a['nome_azienda']: a for a in aziende_res.data} if aziende_res.data else {}

if lista_aziende:
    azienda = lista_aziende[st.sidebar.selectbox("Azienda", list(lista_aziende.keys()))]
    menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Noleggio", "🚨 Archivio Rinotifiche"])

    if menu == "📝 Nuovo Noleggio":
        st.header(f"Nuovo Noleggio: {azienda['nome_azienda']}")
        
        with st.expander("👤 DATI CLIENTE", expanded=True):
            c1, c2 = st.columns(2)
            cliente = c1.text_input("NOME E COGNOME")
            cf_cliente = c2.text_input("CODICE FISCALE")
            nascita_cliente = c1.text_input("LUOGO/DATA NASCITA")
            residenza_cliente = c2.text_input("RESIDENZA (Via/Citta)")
            num_doc = c1.text_input("NUMERO PATENTE")
            telefono = c2.text_input("TELEFONO")

        with st.expander("🛵 DATI VEICOLO", expanded=True):
            targa = st.text_input("TARGA").upper()
            prezzo = st.number_input("PREZZO (€)", min_value=0)

        foto_p = st.camera_input("📸 FOTO PATENTE (Fronte/Retro)")
        
        st.subheader("✍️ Firma per Contratto, Privacy e Multe")
        canvas = st_canvas(fill_color="white", stroke_width=2, height=150, key="sig_final")

        if st.button("💾 SALVA E GENERA TUTTO"):
            if cliente and targa and canvas.image_data is not None:
                try:
                    oggi = str(datetime.date.today())
                    # DATABASE
                    dat = {"cliente": cliente, "cf": cf_cliente, "targa": targa, "azienda_id": azienda['id'], "data_inizio": oggi, "telefono": telefono}
                    res_db = supabase.table("contratti").insert(dat).execute()
                    id_c = res_db.data[0]['id']

                    # --- PDF 1: IL CONTRATTO CON PRIVACY ---
                    p1 = fpdf.FPDF()
                    p1.add_page()
                    p1.set_font("Arial", 'B', 14); p1.cell(0, 10, txt=clean_t(azienda['nome_azienda']), ln=1, align='C')
                    p1.set_font("Arial", size=9); p1.multi_cell(0, 5, txt=clean_t(f"Cliente: {cliente}\nTarga: {targa}\nData: {oggi}"))
                    p1.ln(5); p1.set_font("Arial", 'B', 8); p1.cell(0, 5, "PRIVACY E CLAUSOLE VESSATORIE", ln=1)
                    p1.set_font("Arial", size=7); p1.multi_cell(0, 4, txt=clean_t(f"{PRIVACY_TEXT}\n{CLAUSOLE_VESSATORIE}"))
                    img_s = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA')
                    img_s.save("f.png")
                    p1.ln(5); p1.image("f.png", x=10, w=35)
                    bytes_contratto = p1.output(dest='S').encode('latin-1')

                    # --- PDF 2: IL MODULO VIGILI (IL TUO CARTACEO) ---
                    p2 = fpdf.FPDF()
                    p2.add_page()
                    p2.set_font("Arial", size=10)
                    testo_int = f"{TITOLARE}\n{NATO_A} il {NATO_IL} e residente a {RESIDENTE_A} alla {IN_VIA}\nin qualita di titolare dell'omonima ditta individuale, C.F.: {CF_TITOLARE} e P. IVA: {PIVA_TITOLARE}"
                    p2.multi_cell(0, 5, txt=clean_t(testo_int))
                    p2.ln(10); p2.set_font("Arial", 'B', 11); p2.cell(0, 7, "COMUNICAZIONE LOCAZIONE VEICOLO", ln=1, align='C')
                    p2.ln(5); p2.set_font("Arial", size=10); p2.multi_cell(0, 6, txt=clean_t(f"Si comunica che il veicolo targato {targa} era concesso in locazione al signor:"))
                    p2.ln(5); p2.set_font("Arial", 'B', 10)
                    p2.cell(0, 7, txt=clean_t(f"COGNOME E NOME: {cliente}"), ln=1)
                    p2.cell(0, 7, txt=clean_t(f"NATO A/IL: {nascita_cliente}"), ln=1)
                    p2.cell(0, 7, txt=clean_t(f"RESIDENZA: {residenza_cliente}"), ln=1)
                    p2.cell(0, 7, txt=clean_t(f"CODICE FISCALE: {cf_cliente}"), ln=1)
                    p2.cell(0, 7, txt=clean_t(f"DOC. IDENTITA: {num_doc}"), ln=1)
                    p2.ln(10); p2.set_font("Arial", size=10); p2.cell(0, 7, "In fede, Marianna Battaglia", ln=1, align='R')
                    bytes_vigili = p2.output(dest='S').encode('latin-1')

                    # STORAGE
                    supabase.storage.from_("contratti_media").upload(f"doc_{id_c}.pdf", bytes_contratto, {"content-type": "application/pdf"})
                    supabase.storage.from_("contratti_media").upload(f"vigili_{id_c}.pdf", bytes_vigili, {"content-type": "application/pdf"})
                    if foto_p:
                        supabase.storage.from_("contratti_media").upload(f"pat_{id_c}.jpg", foto_p.getvalue(), {"content-type": "image/jpeg"})

                    st.success("✅ Tutto salvato correttamente!")
                    st.download_button("📥 Scarica Modulo Multe (Vigili)", bytes_vigili, file_name=f"Modulo_Multe_{targa}.pdf")

                except Exception as e:
                    st.error(f"Errore: {e}")

    elif menu == "🚨 Archivio Rinotifiche":
        st.header("🗄️ Archivio")
        res = supabase.table("contratti").select("*").eq("azienda_id", azienda['id']).execute()
        if res.data:
            df = pd.DataFrame(res.data).sort_values(by='created_at', ascending=False)
            sel = st.selectbox("Cerca", df['cliente'] + " - " + df['targa'])
            c = df[(df['cliente'] + " - " + df['targa']) == sel].iloc[0]
            st.link_button("🚨 Scarica Modulo Vigili", f"{url}/storage/v1/object/public/contratti_media/vigili_{c['id']}.pdf")
            st.link_button("📄 Vedi Contratto Firmato", f"{url}/storage/v1/object/public/contratti_media/doc_{c['id']}.pdf")
            st.link_button("🪪 Vedi Foto Patente", f"{url}/storage/v1/object/public/contratti_media/pat_{c['id']}.jpg")

