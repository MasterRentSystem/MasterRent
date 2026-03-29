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
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in repls.items(): text = text.replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

# DATI FISSI AZIENDA
TITOLARE = "BATTAGLIA MARIANNA"
NATO_A = "Berlino (Germania)"
NATO_IL = "13/01/1987"
RESIDENTE_A = "Forio"
IN_VIA = "Via Cognole n. 5"
CF_TITOLARE = "BTTMNN87A53Z112S"
PIVA_TITOLARE = "10252601215"

st.sidebar.title("🚀 MasterRent Ischia")
aziende_res = supabase.table("aziende").select("*").execute()
lista_aziende = {a['nome_azienda']: a for a in aziende_res.data} if aziende_res.data else {}

if lista_aziende:
    azienda = lista_aziende[st.sidebar.selectbox("Azienda", list(lista_aziende.keys()))]
    menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Noleggio", "🚨 Archivio Completo"])

    if menu == "📝 Nuovo Noleggio":
        st.header(f"Nuovo Contratto: {azienda['nome_azienda']}")
        
        with st.expander("👤 DATI CLIENTE E FATTURAZIONE", expanded=True):
            c1, c2 = st.columns(2)
            cliente = c1.text_input("NOME E COGNOME")
            cf_cliente = c2.text_input("CODICE FISCALE")
            nascita_cliente = c1.text_input("LUOGO/DATA NASCITA")
            residenza_cliente = c2.text_input("RESIDENZA COMPLETA")
            num_doc = c1.text_input("NUMERO PATENTE")
            telefono = c2.text_input("CELLULARE (es. 39333...)")
            p_iva = c1.text_input("P.IVA (Se fattura)")
            sdi = c2.text_input("CODICE UNIVOCO / PEC")

        with st.expander("🛵 DATI NOLEGGIO", expanded=True):
            c3, c4 = st.columns(2)
            targa = c3.text_input("TARGA").upper()
            prezzo = st.number_input("PREZZO TOTALE (€)", min_value=0)

        foto_p = st.camera_input("📸 SCANSIONE PATENTE")
        
        st.subheader("✍️ Firma Legale")
        canvas = st_canvas(fill_color="white", stroke_width=2, height=150, key="sig_final_v1")

        if st.button("💾 SALVA E GENERA DOCUMENTI"):
            if cliente and targa and canvas.image_data is not None:
                try:
                    id_c = str(datetime.datetime.now().timestamp()).replace(".","")
                    # 1. PDF CONTRATTO + PRIVACY
                    p1 = fpdf.FPDF()
                    p1.add_page()
                    p1.set_font("Arial", 'B', 14); p1.cell(0, 10, txt=clean_t(azienda['nome_azienda']), ln=1, align='C')
                    p1.set_font("Arial", size=9); p1.multi_cell(0, 5, txt=clean_t(f"Contratto Noleggio\nCliente: {cliente}\nTarga: {targa}\nData: {datetime.date.today()}"))
                    img_s = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA'); img_s.save("f.png")
                    p1.ln(10); p1.image("f.png", x=10, w=40); bytes_contratto = p1.output(dest='S').encode('latin-1')

                    # 2. PDF MODULO MULTE (VIGILI)
                    p2 = fpdf.FPDF()
                    p2.add_page()
                    p2.set_font("Arial", size=10); p2.multi_cell(0, 5, txt=clean_t(f"{TITOLARE}\nP.IVA: {PIVA_TITOLARE}\nComando Polizia Municipale\n\nCOMUNICAZIONE LOCAZIONE\nIl veicolo {targa} era in uso a:\n{cliente}\nNato a: {nascita_cliente}\nResidente: {residenza_cliente}\nCF: {cf_cliente}\nDoc: {num_doc}")); bytes_vigili = p2.output(dest='S').encode('latin-1')

                    # 3. PDF RIEPILOGO FATTURA
                    p3 = fpdf.FPDF()
                    p3.add_page()
                    p3.set_font("Arial", 'B', 14); p3.cell(0, 10, "RIEPILOGO PER FATTURAZIONE", ln=1, align='C')
                    p3.set_font("Arial", size=10); p3.multi_cell(0, 7, txt=clean_t(f"Cliente: {cliente}\nP.IVA: {p_iva}\nSDI/PEC: {sdi}\nImporto: {prezzo} Euro\nDescrizione: Noleggio veicolo {targa}")); bytes_fattura = p3.output(dest='S').encode('latin-1')

                    # STORAGE
                    supabase.storage.from_("contratti_media").upload(f"contratto_{id_c}.pdf", bytes_contratto)
                    supabase.storage.from_("contratti_media").upload(f"vigili_{id_c}.pdf", bytes_vigili)
                    supabase.storage.from_("contratti_media").upload(f"fattura_{id_c}.pdf", bytes_fattura)
                    if foto_p:
                        supabase.storage.from_("contratti_media").upload(f"pat_{id_c}.jpg", foto_p.getvalue())

                    st.success("✅ Documentazione creata con successo!")
                    
                    # WHATSAPP TASTO
                    msg = urllib.parse.quote(f"Ciao {cliente}, ecco i documenti del tuo noleggio con MasterRent Ischia ({targa}). A presto!")
                    st.markdown(f'''<a href="https://wa.me/{telefono}?text={msg}" target="_blank"><button style="background-color:#25D366;color:white;width:100%;border:none;padding:15px;border-radius:10px;font-weight:bold;cursor:pointer;">📲 INVIA SU WHATSAPP</button></a>''', unsafe_allow_html=True)
                    
                    c1, c2, c3 = st.columns(3)
                    c1.download_button("📄 Contratto", bytes_contratto, f"Contratto_{targa}.pdf")
                    c2.download_button("🚨 Modulo Vigili", bytes_vigili, f"Multe_{targa}.pdf")
                    c3.download_button("💰 Dati Fattura", bytes_fattura, f"Fattura_{targa}.pdf")

                except Exception as e:
                    st.error(f"Errore: {e}")

    elif menu == "🚨 Archivio Completo":
        st.header("🗄️ Archivio")
        res = supabase.table("contratti").select("*").execute()
        if res.data:
            df = pd.DataFrame(res.data).sort_values(by='created_at', ascending=False)
            sel = st.selectbox("Seleziona Noleggio", df['cliente'] + " - " + df['targa'])
            c = df[(df['cliente'] + " - " + df['targa']) == sel].iloc[0]
            # Qui andrebbero i link dinamici dello storage
            st.info(f"Dati di {c['cliente']} disponibili nello storage di Supabase.")
