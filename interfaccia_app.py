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

# DATI AZIENDA MARIANNA
TITOLARE_INFO = "BATTAGLIA MARIANNA, nata a Berlino (Germania) il 13/01/1987\nResidente a Forio in Via Cognole n. 5\nC.F.: BTTMNN87A53Z112S | P.IVA: 10252601215"

# TESTI LEGALI
PRIVACY_TEXT = "INFORMATIVA PRIVACY: I dati personali sono trattati ai sensi del Reg. UE 2016/679 (GDPR) esclusivamente per la gestione del contratto di noleggio e obblighi di legge. Il cliente presta il consenso al trattamento."
CLAUSOLE_VESSATORIE = "APPROVAZIONE SPECIFICA: Ai sensi degli artt. 1341 e 1342 c.c. il Cliente dichiara di aver letto e approvato le clausole: 3 (Responsabilita multe), 4 (Spese gestione verbali), 5 (Penali danni e furto), 13 (Foro competente)."

st.sidebar.title("🚀 MasterRent Ischia")
aziende_res = supabase.table("aziende").select("*").execute()
lista_aziende = {a['nome_azienda']: a for a in aziende_res.data} if aziende_res.data else {}

if lista_aziende:
    azienda = lista_aziende[st.sidebar.selectbox("Azienda", list(lista_aziende.keys()))]
    menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Noleggio", "🗄️ Archivio"])

    if menu == "📝 Nuovo Noleggio":
        st.header(f"Contratto: {azienda['nome_azienda']}")
        
        c1, c2 = st.columns(2)
        cliente = c1.text_input("Nome e Cognome")
        cf_cliente = c2.text_input("Codice Fiscale")
        nascita = c1.text_input("Luogo/Data Nascita")
        residenza = c2.text_input("Indirizzo Residenza")
        num_doc = c1.text_input("Numero Patente")
        telefono = c2.text_input("Cellulare (WhatsApp)")
        targa = c1.text_input("TARGA").upper()
        prezzo = c2.number_input("Prezzo (€)", min_value=0)

        with st.expander("💰 Dati Fatturazione (SOLO per modulo fattura)"):
            p_iva = st.text_input("Partita IVA")
            sdi = st.text_input("Codice SDI / PEC")

        foto_p = st.camera_input("📸 Foto Patente")
        st.subheader("✍️ Firma Cliente")
        canvas = st_canvas(fill_color="white", stroke_width=2, height=150, key="sig_v8")

        if st.button("💾 SALVA TUTTO"):
            if cliente and targa and canvas.image_data is not None:
                try:
                    id_c = str(datetime.datetime.now().timestamp()).replace(".","")
                    img_s = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA'); img_s.save("f.png")

                    # --- 1. CONTRATTO (PULITO: Niente P.IVA o SDI qui) ---
                    p1 = fpdf.FPDF()
                    p1.add_page()
                    p1.set_font("Arial", 'B', 16); p1.cell(0, 10, clean_t(azienda['nome_azienda']), ln=1, align='C')
                    p1.set_font("Arial", size=10)
                    p1.multi_cell(0, 6, txt=clean_t(f"CONTRATTO DI NOLEGGIO\n\nConducente: {cliente}\nNato a: {nascita}\nResidenza: {residenza}\nPatente: {num_doc}\nVeicolo: {targa}\nData: {datetime.date.today()}\nPrezzo: {prezzo} Euro"))
                    p1.ln(5); p1.set_font("Arial", 'B', 8); p1.cell(0, 5, "PRIVACY E CLAUSOLE LEGALI", ln=1)
                    p1.set_font("Arial", size=7); p1.multi_cell(0, 4, txt=clean_t(f"{PRIVACY_TEXT}\n{CLAUSOLE_VESSATORIE}"))
                    p1.ln(5); p1.image("f.png", x=10, w=40)
                    b1 = p1.output(dest='S').encode('latin-1')

                    # --- 2. MODULO MULTE (VIGILI) ---
                    p2 = fpdf.FPDF()
                    p2.add_page()
                    p2.set_font("Arial", size=10); p2.multi_cell(0, 5, txt=clean_t(TITOLARE_INFO))
                    p2.ln(10); p2.set_font("Arial", 'B', 12); p2.cell(0, 7, "COMUNICAZIONE LOCAZIONE VEICOLO", ln=1, align='C')
                    p2.ln(5); p2.set_font("Arial", size=10)
                    p2.multi_cell(0, 6, txt=clean_t(f"Si comunica che il veicolo {targa} era in locazione a:\n\nNome: {cliente}\nCF: {cf_cliente}\nNato a: {nascita}\nResidenza: {residenza}\nDoc: {num_doc}"))
                    p2.ln(10); p2.cell(0, 10, "In fede, Marianna Battaglia", align='R')
                    b2 = p2.output(dest='S').encode('latin-1')

                    # --- 3. MODULO FATTURA (Dati fiscali solo qui) ---
                    p3 = fpdf.FPDF()
                    p3.add_page()
                    p3.set_font("Arial", 'B', 14); p3.cell(0, 10, "RIEPILOGO FATTURAZIONE", ln=1, align='C')
                    p3.set_font("Arial", size=11)
                    p3.multi_cell(0, 8, txt=clean_t(f"Cliente: {cliente}\nP.IVA: {p_iva}\nSDI/PEC: {sdi}\nImporto: {prezzo} Euro\nTarga: {targa}"))
                    b3 = p3.output(dest='S').encode('latin-1')

                    # SALVATAGGIO
                    dat = {"cliente": cliente, "cf": cf_cliente, "targa": targa, "azienda_id": azienda['id'], "data_inizio": str(datetime.date.today()), "p_iva": p_iva, "sdi": sdi, "luogo_nascita": nascita, "residenza": residenza, "num_doc": num_doc}
                    supabase.table("contratti").insert(dat).execute()
                    
                    supabase.storage.from_("contratti_media").upload(f"con_{id_c}.pdf", b1)
                    supabase.storage.from_("contratti_media").upload(f"mul_{id_c}.pdf", b2)
                    supabase.storage.from_("contratti_media").upload(f"fat_{id_c}.pdf", b3)
                    if foto_p: supabase.storage.from_("contratti_media").upload(f"pat_{id_c}.jpg", foto_p.getvalue())

                    st.success("✅ Moduli generati correttamente!")
                    
                    wa_msg = urllib.parse.quote(f"Ciao {cliente}, ecco il tuo contratto MasterRent ({targa}).")
                    st.markdown(f'''<a href="https://wa.me/{telefono}?text={wa_msg}" target="_blank"><button style="background-color:#25D366;color:white;width:100%;border:none;padding:12px;border-radius:10px;font-weight:bold;cursor:pointer;">📲 Invia Contratto WhatsApp</button></a>''', unsafe_allow_html=True)
                    
                    c1, c2, c3 = st.columns(3)
                    c1.download_button("📄 Contratto", b1, f"Contratto_{targa}.pdf")
                    c2.download_button("🚨 Modulo Vigili", b2, f"Multe_{targa}.pdf")
                    c3.download_button("💰 Dati Fattura", b3, f"Fattura_{targa}.pdf")

                except Exception as e:
                    st.error(f"Errore: {e}")

    elif menu == "🗄️ Archivio":
        st.header("🗄️ Ricerca per Targa")
        t_search = st.text_input("Inserisci TARGA").upper()
        if t_search:
            res = supabase.table("contratti").select("*").eq("targa", t_search).execute()
            if res.data:
                for c in res.data:
                    st.write(f"Noleggio: {c['cliente']} ({c['data_inizio']})")
                    # Qui aggiungeremo il recupero dei 3 PDF salvati
            else: st.warning("Nessun noleggio trovato.")
