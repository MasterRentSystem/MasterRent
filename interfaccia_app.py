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

# DATI FISSI AZIENDA
TITOLARE_INFO = "BATTAGLIA MARIANNA, nata a Berlino (Germania) il 13/01/1987\nResidente a Forio in Via Cognole n. 5\nC.F.: BTTMNN87A53Z112S | P.IVA: 10252601215"

# TESTI LEGALI OBBLIGATORI
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
        
        # --- DATI ANAGRAFICI ---
        st.subheader("👤 Dati Conducente")
        c1, c2 = st.columns(2)
        cliente = c1.text_input("Nome e Cognome")
        cf_cliente = c2.text_input("Codice Fiscale")
        nascita = c1.text_input("Luogo/Data Nascita")
        residenza = c2.text_input("Indirizzo Residenza")
        num_doc = c1.text_input("Numero Patente")
        telefono = c2.text_input("Cellulare (WhatsApp)")

        # --- DATI VEICOLO ---
        st.subheader("🛵 Veicolo")
        c3, c4 = st.columns(2)
        targa = c3.text_input("TARGA").upper()
        prezzo = c4.number_input("Prezzo (€)", min_value=0)

        # --- DATI FATTURA (SEPARATI) ---
        with st.expander("💰 Dati Fatturazione (Escono solo nel modulo fattura)"):
            p_iva = st.text_input("Partita IVA")
            sdi = st.text_input("Codice SDI o PEC")

        foto_p = st.camera_input("📸 Foto Patente")
        
        st.subheader("✍️ Firma Legale")
        st.info("Firmando accetti l'informativa Privacy e le clausole vessatorie (Art. 1341-1342 c.c.)")
        canvas = st_canvas(fill_color="white", stroke_width=2, height=150, key="sig_final_v7")

        if st.button("💾 GENERA E ARCHIVIA"):
            if cliente and targa and canvas.image_data is not None:
                try:
                    oggi = str(datetime.date.today())
                    id_c = str(datetime.datetime.now().timestamp()).replace(".","")
                    img_s = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA'); img_s.save("f.png")

                    # --- 1. PDF CONTRATTO (Con Privacy e Clausole) ---
                    p1 = fpdf.FPDF()
                    p1.add_page()
                    p1.set_font("Arial", 'B', 16); p1.cell(0, 10, clean_t(azienda['nome_azienda']), ln=1, align='C')
                    p1.set_font("Arial", size=10)
                    p1.multi_cell(0, 6, txt=clean_t(f"CONTRATTO DI NOLEGGIO\n\nCliente: {cliente}\nNato a: {nascita}\nResidenza: {residenza}\nDoc: {num_doc}\n\nVeicolo: {targa} | Data: {oggi}\nPrezzo: {prezzo} Euro"))
                    p1.ln(5); p1.set_font("Arial", 'B', 8); p1.cell(0, 5, "PRIVACY E CLAUSOLE LEGALI", ln=1)
                    p1.set_font("Arial", size=7); p1.multi_cell(0, 4, txt=clean_t(f"{PRIVACY_TEXT}\n\n{CLAUSOLE_VESSATORIE}"))
                    p1.ln(5); p1.image("f.png", x=10, w=40)
                    b1 = p1.output(dest='S').encode('latin-1')

                    # --- 2. PDF MODULO MULTE (VIGILI) ---
                    p2 = fpdf.FPDF()
                    p2.add_page()
                    p2.set_font("Arial", size=10); p2.multi_cell(0, 5, txt=clean_t(TITOLARE_INFO))
                    p2.ln(10); p2.set_font("Arial", 'B', 12); p2.cell(0, 7, "COMUNICAZIONE LOCAZIONE VEICOLO", ln=1, align='C')
                    p2.ln(5); p2.set_font("Arial", size=10)
                    p2.multi_cell(0, 6, txt=clean_t(f"Si dichiara che il veicolo {targa} era in uso a:\n\nNome: {cliente}\nCF: {cf_cliente}\nNato a: {nascita}\nResidenza: {residenza}\nDocumento: {num_doc}"))
                    p2.ln(10); p2.cell(0, 10, "In fede, Marianna Battaglia", align='R')
                    b2 = p2.output(dest='S').encode('latin-1')

                    # --- 3. PDF FATTURA (Solo dati fiscali) ---
                    p3 = fpdf.FPDF()
                    p3.add_page()
                    p3.set_font("Arial", 'B', 14); p3.cell(0, 10, "RIEPILOGO FATTURAZIONE", ln=1, align='C')
                    p3.set_font("Arial", size=11)
                    p3.multi_cell(0, 8, txt=clean_t(f"Cliente: {cliente}\nPartita IVA: {p_iva}\nSDI/PEC: {sdi}\nImporto: {prezzo} Euro\nTarga: {targa}"))
                    b3 = p3.output(dest='S').encode('latin-1')

                    # DATABASE
                    dat = {"cliente": cliente, "cf": cf_cliente, "targa": targa, "azienda_id": azienda['id'], "data_inizio": oggi, "p_iva": p_iva, "sdi": sdi, "luogo_nascita": nascita, "residenza": residenza, "num_doc": num_doc}
                    supabase.table("contratti").insert(dat).execute()
                    
                    # STORAGE
                    supabase.storage.from_("contratti_media").upload(f"con_{id_c}.pdf", b1)
                    supabase.storage.from_("contratti_media").upload(f"mul_{id_c}.pdf", b2)
                    supabase.storage.from_("contratti_media").upload(f"fat_{id_c}.pdf", b3)
                    if foto_p: supabase.storage.from_("contratti_media").upload(f"pat_{id_c}.jpg", foto_p.getvalue())

                    st.success("✅ Moduli generati con successo!")
                    
                    # WHATSAPP
                    wa_msg = urllib.parse.quote(f"Ciao {cliente}, ecco il tuo contratto MasterRent ({targa}).")
                    st.markdown(f'''<a href="https://wa.me/{telefono}?text={wa_msg}" target="_blank"><button style="background-color:#25D366;color:white;width:100%;border:none;padding:12px;border-radius:10px;font-weight:bold;cursor:pointer;">📲 INVIA CONTRATTO WHATSAPP</button></a>''', unsafe_allow_html=True)
                    
                    c_con, c_mul, c_fat = st.columns(3)
                    c_con.download_button("📄 Contratto + Privacy", b1, f"Contratto_{targa}.pdf")
                    c_mul.download_button("🚨 Modulo Vigili", b2, f"Multe_{targa}.pdf")
                    c_fat.download_button("💰 Dati Fattura", b3, f"Fattura_{targa}.pdf")

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
                    # Qui si possono rigenerare i PDF dai dati del DB se necessario
            else: st.warning("Nessun noleggio trovato.")
