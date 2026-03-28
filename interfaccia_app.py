import streamlit as st
import pandas as pd
import datetime
import fpdf
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io
import urllib.parse
import requests

# 1. CONNESSIONE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def clean_t(text):
    if not text: return ""
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '°': 'o', '’': "'"}
    for k, v in repls.items(): text = text.replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

# TESTI LEGALI
ITA_14 = "1.Pieno/Ottimo stato. 2.Multe cliente. 3.Gestione €25.83. 4.Danni/Furto cliente. 5.No alcool. 6.Riconsegna puntuale. 7.Sinistri: denuncia. 8.No sub-noleggio. 9.Patente valida. 10.Chiavi €50. 11.Solo Ischia. 12.Assistenza meccanica. 13.Foro Napoli. 14.Privacy GDPR."
ENG_14 = "1.Perfect condition. 2.Fines: customer. 3.Fee €25.83. 4.Damage/Theft: customer. 5.No drugs/alcohol. 6.Return time. 7.Accidents: report. 8.No sub-rental. 9.Valid license. 10.Lost keys €50. 11.Ischia only. 12.Mechanical help. 13.Court Naples. 14.Privacy GDPR."

st.sidebar.title("🚀 MasterRent Ischia")
aziende_res = supabase.table("aziende").select("*").execute()
lista_aziende = {a['nome_azienda']: a for a in aziende_res.data} if aziende_res.data else {}

if lista_aziende:
    azienda = lista_aziende[st.sidebar.selectbox("Azienda", list(lista_aziende.keys()))]
    menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Contratto", "🚨 Archivio & Multe", "🏦 Fatturazione Aruba"])

    if menu == "📝 Nuovo Contratto":
        st.header(f"Contratto: {azienda['nome_azienda']}")
        with st.expander("👤 DATI CLIENTE", expanded=True):
            c1, c2 = st.columns(2)
            cliente = c1.text_input("NOME E COGNOME")
            telefono = c2.text_input("TELEFONO")
            residenza = c1.text_input("RESIDENZA")
            num_doc = c2.text_input("NUMERO DOCUMENTO")
            cf = c1.text_input("CODICE FISCALE")
            luogo_nascita = c2.text_input("LUOGO NASCITA")

        with st.expander("🛵 DATI NOLEGGIO", expanded=True):
            c3, c4 = st.columns(2)
            targa = c3.text_input("TARGA")
            km_uscita = c4.text_input("KM USCITA", value="0")
            prezzo_tot = st.number_input("PREZZO (€)", min_value=0)

        foto_p = st.camera_input("📸 FOTO PATENTE")
        canvas = st_canvas(fill_color="white", stroke_width=2, height=150, key="sig")

        if st.button("💾 SALVA TUTTO"):
            if cliente and targa and canvas.image_data is not None:
                try:
                    # Salva DB
                    dat = {"cliente": cliente, "targa": targa, "telefono": telefono, "residenza": residenza, "num_doc": num_doc, "prezzo_tot": str(prezzo_tot), "km_uscita": km_uscita, "luogo_nascita": luogo_nascita, "azienda_id": azienda['id'], "data_inizio": str(datetime.date.today())}
                    res = supabase.table("contratti").insert(dat).execute()
                    id_c = res.data[0]['id']

                    # PDF & Foto
                    pdf = fpdf.FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, txt=clean_t(f"Noleggio {azienda['nome_azienda']}"), ln=1)
                    pdf.set_font("Arial", size=8); pdf.multi_cell(0, 4, txt=clean_t(f"Cliente: {cliente}\nDoc: {num_doc}\nTarga: {targa}"))
                    pdf.ln(5); pdf.multi_cell(0, 3, clean_t(ITA_14 + "\n" + ENG_14))
                    
                    img_s = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA')
                    img_s.save("f.png")
                    pdf.image("f.png", x=10, w=35)
                    pdf.output("c.pdf")

                    # Upload
                    supabase.storage.from_("contratti_media").upload(f"{id_c}_contratto.pdf", open("c.pdf", "rb").read())
                    if foto_p:
                        supabase.storage.from_("contratti_media").upload(f"{id_c}_patente.jpg", foto_p.getvalue())

                    st.success("✅ Salvato!")
                    msg = urllib.parse.quote(f"Ciao {cliente}, contratto {targa} ok!")
                    st.markdown(f'''<a href="https://wa.me/{telefono}?text={msg}" target="_blank"><button style="background-color:#25D366;color:white;border:none;padding:10px;border-radius:5px;">📲 WhatsApp</button></a>''', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Errore: {e}")

    elif menu == "🚨 Archivio & Multe":
        st.header("🗄️ Archivio")
        res = supabase.table("contratti").select("*").eq("azienda_id", azienda['id']).execute()
        if res.data:
            df = pd.DataFrame(res.data).sort_values(by='created_at', ascending=False)
            sel = st.selectbox("Seleziona", df['cliente'] + " - " + df['targa'])
            c = df[(df['cliente'] + " - " + df['targa']) == sel].iloc[0]
            
            # Controllo esistenza file prima di mostrare il tasto
            url_pdf = f"{url}/storage/v1/object/public/contratti_media/{c['id']}_contratto.pdf"
            url_img = f"{url}/storage/v1/object/public/contratti_media/{c['id']}_patente.jpg"
            
            col1, col2 = st.columns(2)
            if requests.head(url_pdf).status_code == 200:
                col1.link_button("📄 Vedi Contratto", url_pdf)
            else:
                col1.warning("Contratto PDF non trovato")
                
            if requests.head(url_img).status_code == 200:
                col2.link_button("🪪 Vedi Patente", url_img)
            else:
                col2.info("Foto patente non presente")

