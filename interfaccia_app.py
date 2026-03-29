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

# DATI AZIENDA MARIANNA (Per intestazione moduli)
TITOLARE_INFO = "BATTAGLIA MARIANNA, nata a Berlino (Germania) il 13/01/1987\nResidente a Forio in Via Cognole n. 5\nC.F.: BTTMNN87A53Z112S | P.IVA: 10252601215"

st.sidebar.title("🚀 MasterRent Ischia")
aziende_res = supabase.table("aziende").select("*").execute()
lista_aziende = {a['nome_azienda']: a for a in aziende_res.data} if aziende_res.data else {}

if lista_aziende:
    azienda = lista_aziende[st.sidebar.selectbox("Azienda", list(lista_aziende.keys()))]
    menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Noleggio", "🗄️ Archivio"])

    if menu == "📝 Nuovo Noleggio":
        st.header(f"Nuovo Noleggio: {azienda['nome_azienda']}")
        
        c1, c2 = st.columns(2)
        cliente = c1.text_input("Nome e Cognome")
        cf_cliente = c2.text_input("Codice Fiscale")
        nascita = c1.text_input("Luogo e Data Nascita")
        residenza = c2.text_input("Residenza")
        num_doc = c1.text_input("Numero Patente")
        telefono = c2.text_input("Telefono (WhatsApp)")
        targa = c1.text_input("TARGA").upper()
        prezzo = c2.number_input("Prezzo (€)", min_value=0)

        with st.expander("💰 DATI FATTURA (SOLO PER MODULO FATTURA)"):
            p_iva = st.text_input("Partita IVA")
            sdi = st.text_input("Codice SDI / PEC")

        foto_p = st.camera_input("📸 Scansione Patente")
        st.subheader("✍️ Firma Cliente")
        canvas = st_canvas(fill_color="white", stroke_width=2, height=150, key="sig_v6")

        if st.button("💾 SALVA E GENERA"):
            if cliente and targa and canvas.image_data is not None:
                try:
                    oggi = str(datetime.date.today())
                    id_c = str(datetime.datetime.now().timestamp()).replace(".","")
                    img_s = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA'); img_s.save("f.png")

                    # --- PDF 1: IL CONTRATTO (PULITO - NO P.IVA/SDI) ---
                    p1 = fpdf.FPDF()
                    p1.add_page()
                    p1.set_font("Arial", 'B', 16); p1.cell(0, 10, clean_t(azienda['nome_azienda']), ln=1, align='C')
                    p1.set_font("Arial", size=10)
                    p1.multi_cell(0, 6, txt=clean_t(f"CONTRATTO DI NOLEGGIO\n\nConducente: {cliente}\nNato a: {nascita}\nResidenza: {residenza}\nPatente: {num_doc}\n\nVEICOLO TARGA: {targa}\nDATA: {oggi}\nPREZZO: {prezzo} Euro"))
                    p1.ln(10); p1.cell(0, 5, "Firma del Cliente:", ln=1); p1.image("f.png", x=10, w=40)
                    b1 = p1.output(dest='S').encode('latin-1')

                    # --- PDF 2: MODULO MULTE (VIGILI) ---
                    p2 = fpdf.FPDF()
                    p2.add_page()
                    p2.set_font("Arial", size=10); p2.multi_cell(0, 5, txt=clean_t(TITOLARE_INFO))
                    p2.ln(10); p2.set_font("Arial", 'B', 12); p2.cell(0, 7, "COMUNICAZIONE LOCAZIONE VEICOLO", ln=1, align='C')
                    p2.ln(5); p2.set_font("Arial", size=10)
                    p2.multi_cell(0, 6, txt=clean_t(f"Si comunica che il veicolo {targa} era in locazione a:\n\nNome: {cliente}\nCF: {cf_cliente}\nNato a: {nascita}\nResidenza: {residenza}\nDocumento: {num_doc}"))
                    p2.ln(10); p2.cell(0, 10, "In fede, Marianna Battaglia", align='R')
                    b2 = p2.output(dest='S').encode('latin-1')

                    # --- PDF 3: MODULO FATTURA (QUI ESCONO P.IVA E SDI) ---
                    p3 = fpdf.FPDF()
                    p3.add_page()
                    p3.set_font("Arial", 'B', 14); p3.cell(0, 10, "RIEPILOGO FISCALE FATTURA", ln=1, align='C')
                    p3.set_font("Arial", size=11)
                    p3.multi_cell(0, 8, txt=clean_t(f"CLIENTE: {cliente}\nPARTITA IVA: {p_iva}\nCODICE SDI/PEC: {sdi}\nIMPORTO: {prezzo} Euro\nTARGA: {targa}\nDATA: {oggi}"))
                    b3 = p3.output(dest='S').encode('latin-1')

                    # DATABASE E STORAGE
                    dat = {"cliente": cliente, "cf": cf_cliente, "targa": targa, "azienda_id": azienda['id'], "data_inizio": oggi, "p_iva": p_iva, "sdi": sdi, "luogo_nascita": nascita, "residenza": residenza, "num_doc": num_doc}
                    supabase.table("contratti").insert(dat).execute()
                    
                    supabase.storage.from_("contratti_media").upload(f"con_{id_c}.pdf", b1)
                    supabase.storage.from_("contratti_media").upload(f"mul_{id_c}.pdf", b2)
                    supabase.storage.from_("contratti_media").upload(f"fat_{id_c}.pdf", b3)
                    if foto_p: supabase.storage.from_("contratti_media").upload(f"pat_{id_c}.jpg", foto_p.getvalue())

                    st.success("✅ Salvato! Ora puoi scaricare i moduli separati.")
                    
                    wa_msg = urllib.parse.quote(f"Ciao {cliente}, ecco il tuo contratto MasterRent ({targa}).")
                    st.markdown(f'''<a href="https://wa.me/{telefono}?text={wa_msg}" target="_blank"><button style="background-color:#25D366;color:white;width:100%;border:none;padding:12px;border-radius:10px;font-weight:bold;cursor:pointer;">📲 Invia Contratto WhatsApp</button></a>''', unsafe_allow_html=True)
                    
                    c_con, c_mul, c_fat = st.columns(3)
                    c_con.download_button("📄 Contratto", b1, f"Contratto_{targa}.pdf")
                    c_mul.download_button("🚨 Modulo Vigili", b2, f"Modulo_Vigili_{targa}.pdf")
                    c_fat.download_button("💰 Dati Fattura", b3, f"Fattura_{targa}.pdf")

                except Exception as e:
                    st.error(f"Errore: {e}")

    elif menu == "🗄️ Archivio":
        st.header("🗄️ Ricerca Documenti")
        t_search = st.text_input("CERCA TARGA").upper()
        if t_search:
            res = supabase.table("contratti").select("*").eq("targa", t_search).execute()
            if res.data:
                for c in res.data:
                    st.write(f"Noleggio del {c['data_inizio']} - {c['cliente']}")
                    # Qui puoi aggiungere i tasti di download recuperando i dati dal DB come sopra
            else: st.warning("Nessun noleggio trovato.")
