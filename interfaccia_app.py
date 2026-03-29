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

# DATI AZIENDA MARIANNA
TITOLARE = "BATTAGLIA MARIANNA"
NATO_A = "Berlino (Germania)"
NATO_IL = "13/01/1987"
RESIDENTE_A = "Forio"
IN_VIA = "Via Cognole n. 5"
CF_TITOLARE = "BTTMNN87A53Z112S"
PIVA_TITOLARE = "10252601215"

# TESTI LEGALI
PRIVACY = "Informativa Privacy Reg. UE 2016/679: I dati sono trattati per fini contrattuali e legali. Il cliente acconsente."
LEGAL_NOTE = "Ai sensi artt. 1341-1342 c.c. si approvano le clausole 3, 4, 5 (Multe e Danni)."

st.sidebar.title("🚀 MasterRent Ischia")
aziende_res = supabase.table("aziende").select("*").execute()
lista_aziende = {a['nome_azienda']: a for a in aziende_res.data} if aziende_res.data else {}

if lista_aziende:
    azienda = lista_aziende[st.sidebar.selectbox("Azienda", list(lista_aziende.keys()))]
    menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Noleggio", "🚨 Archivio Documenti"])

    if menu == "📝 Nuovo Noleggio":
        st.header(f"Nuovo Noleggio: {azienda['nome_azienda']}")
        
        with st.expander("👤 DATI CLIENTE", expanded=True):
            c1, c2 = st.columns(2)
            cliente = c1.text_input("NOME E COGNOME")
            cf_cliente = c2.text_input("CODICE FISCALE")
            nascita_cliente = c1.text_input("LUOGO/DATA NASCITA")
            residenza_cliente = c2.text_input("RESIDENZA COMPLETA")
            num_doc = c1.text_input("NUMERO PATENTE")
            telefono = c2.text_input("TELEFONO (WhatsApp)")

        with st.expander("💰 FATTURAZIONE E NOLEGGIO", expanded=True):
            c3, c4 = st.columns(2)
            targa = c3.text_input("TARGA").upper()
            prezzo = c4.number_input("PREZZO TOTALE (€)", min_value=0)
            p_iva = c3.text_input("P.IVA (Opzionale)")
            sdi = c4.text_input("SDI / PEC")

        foto_p = st.camera_input("📸 FOTO PATENTE (Fronte/Retro)")
        st.subheader("✍️ Firma per tutto")
        canvas = st_canvas(fill_color="white", stroke_width=2, height=150, key="sig_v3")

        if st.button("💾 GENERA E SALVA TUTTI I MODULI"):
            if cliente and targa and canvas.image_data is not None:
                try:
                    oggi = str(datetime.date.today())
                    id_c = str(datetime.datetime.now().timestamp()).replace(".","")
                    
                    # Salvataggio DB
                    dat = {"cliente": cliente, "cf": cf_cliente, "targa": targa, "azienda_id": azienda['id'], "data_inizio": oggi, "telefono": telefono, "p_iva": p_iva, "sdi": sdi}
                    res_db = supabase.table("contratti").insert(dat).execute()
                    
                    # Firma per i PDF
                    img_s = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA'); img_s.save("f.png")

                    # --- PDF 1: IL CONTRATTO ---
                    p1 = fpdf.FPDF()
                    p1.add_page()
                    p1.set_font("Arial", 'B', 16); p1.cell(0, 10, clean_t(azienda['nome_azienda']), ln=1, align='C')
                    p1.set_font("Arial", size=10); p1.multi_cell(0, 5, txt=clean_t(f"CONTRATTO DI NOLEGGIO\nCliente: {cliente}\nTarga: {targa}\nData: {oggi}\n\n{PRIVACY}\n{LEGAL_NOTE}"))
                    p1.ln(5); p1.image("f.png", x=10, w=40)
                    b1 = p1.output(dest='S').encode('latin-1')

                    # --- PDF 2: IL MODULO VIGILI (Multe) ---
                    p2 = fpdf.FPDF()
                    p2.add_page()
                    p2.set_font("Arial", size=10); p2.multi_cell(0, 5, txt=clean_t(f"{TITOLARE}\n{NATO_A} il {NATO_IL}\nCF: {CF_TITOLARE} P.IVA: {PIVA_TITOLARE}\n\nCOMUNICAZIONE LOCAZIONE VEICOLO\n\nSi dichiara che il veicolo {targa} era in locazione a:\nNome: {cliente}\nCF: {cf_cliente}\nNato a: {nascita_cliente}\nResidenza: {residenza_cliente}\nDoc: {num_doc}"))
                    p2.ln(10); p2.cell(0, 10, "Firma del Titolare: Marianna Battaglia", align='R')
                    b2 = p2.output(dest='S').encode('latin-1')

                    # --- PDF 3: MODULO FATTURA ---
                    p3 = fpdf.FPDF()
                    p3.add_page()
                    p3.set_font("Arial", 'B', 14); p3.cell(0, 10, "DATI PER FATTURAZIONE", ln=1, align='C')
                    p3.set_font("Arial", size=10); p3.multi_cell(0, 8, txt=clean_t(f"Cliente: {cliente}\nP.IVA: {p_iva}\nSDI/PEC: {sdi}\nImporto: {prezzo} Euro\nVeicolo: {targa}\nData: {oggi}"))
                    b3 = p3.output(dest='S').encode('latin-1')

                    # STORAGE
                    supabase.storage.from_("contratti_media").upload(f"con_{id_c}.pdf", b1)
                    supabase.storage.from_("contratti_media").upload(f"mul_{id_c}.pdf", b2)
                    supabase.storage.from_("contratti_media").upload(f"fat_{id_c}.pdf", b3)
                    if foto_p:
                        supabase.storage.from_("contratti_media").upload(f"pat_{id_c}.jpg", foto_p.getvalue())

                    st.success("✅ Moduli generati separatamente!")
                    
                    # WHATSAPP
                    msg = urllib.parse.quote(f"Ciao {cliente}, ecco il tuo contratto MasterRent ({targa}). Grazie!")
                    st.markdown(f'''<a href="https://wa.me/{telefono}?text={msg}" target="_blank"><button style="background-color:#25D366;color:white;width:100%;border:none;padding:15px;border-radius:10px;font-weight:bold;cursor:pointer;">📲 INVIA SU WHATSAPP</button></a>''', unsafe_allow_html=True)
                    
                    c1, c2, c3 = st.columns(3)
                    c1.download_button("📥 Contratto", b1, f"Contratto_{targa}.pdf")
                    c2.download_button("📥 Modulo Multe", b2, f"Multe_{targa}.pdf")
                    c3.download_button("📥 Dati Fattura", b3, f"Fattura_{targa}.pdf")

                except Exception as e:
                    st.error(f"Errore: {e}")

    elif menu == "🚨 Archivio Documenti":
        st.header("🗄️ Archivio")
        res = supabase.table("contratti").select("*").execute()
        if res.data:
            df = pd.DataFrame(res.data).sort_values(by='created_at', ascending=False)
            sel = st.selectbox("Seleziona Noleggio", df['cliente'] + " - " + df['targa'])
            c = df[(df['cliente'] + " - " + df['targa']) == sel].iloc[0]
            
            id_f = c['created_at'] # Nota: andrebbe usato l'ID corretto salvato
            st.write(f"Documenti per {c['cliente']} ({c['targa']}):")
            st.info("Scarica i file direttamente dal pannello Storage di Supabase con i prefissi: con_, mul_, fat_, pat_")

