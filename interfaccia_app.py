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
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '°': 'o', '’': "'"}
    for k, v in repls.items(): text = text.replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

# TESTI LEGALI (Versione Compatta per PDF)
ITA_14 = "1.Pieno/Ottimo stato. 2.Multe cliente. 3.Gestione €25.83. 4.Danni/Furto/Incendio cliente. 5.No alcool/droghe. 6.Termine contratto. 7.Sinistri:denuncia. 8.No subnoleggio. 9.Patente valida. 10.Chiavi €50. 11.Solo Ischia. 12.Assistenza meccanica. 13.Foro Napoli. 14.Privacy GDPR."
ENG_14 = "1.Full tank. 2.Fines: customer. 3.Fee €25.83. 4.Damage/Theft/Fire: customer. 5.No drugs/alcohol. 6.Return time. 7.Accidents: report. 8.No sub-rental. 9.Valid license. 10.Lost keys €50. 11.Ischia only. 12.Mechanical help. 13.Court Naples. 14.Privacy GDPR."

st.sidebar.title("🚀 MasterRent Ischia")
aziende_res = supabase.table("aziende").select("*").execute()
lista_aziende = {a['nome_azienda']: a for a in aziende_res.data} if aziende_res.data else {}

if lista_aziende:
    azienda = lista_aziende[st.sidebar.selectbox("Azienda", list(lista_aziende.keys()))]
    menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Contratto", "🚨 Archivio & Multe", "🏦 Fatturazione Aruba"])

    if menu == "📝 Nuovo Contratto":
        st.header(f"Contratto: {azienda['nome_azienda']}")
        
        with st.expander("👤 DATI CLIENTE", expanded=True):
            col_a, col_b = st.columns(2)
            cliente = col_a.text_input("NOME E COGNOME")
            telefono = col_b.text_input("TELEFONO")
            residenza = col_a.text_input("RESIDENZA")
            num_doc = col_b.text_input("NUMERO DOCUMENTO")
            cf = col_a.text_input("CODICE FISCALE")
            luogo_nascita = col_b.text_input("LUOGO NASCITA")

        with st.expander("🛵 DATI NOLEGGIO", expanded=True):
            col_c, col_d = st.columns(2)
            targa = col_c.text_input("TARGA")
            km_uscita = col_d.text_input("KM USCITA", value="0")
            prezzo_tot = st.number_input("PREZZO (€)", min_value=0)

        foto_patente = st.camera_input("📸 SCATTA FOTO PATENTE")
        st.subheader("✍️ Firma Cliente")
        canvas = st_canvas(fill_color="white", stroke_width=2, stroke_color="black", background_color="white", height=150, key="sig")

        if st.button("💾 SALVA E GENERA"):
            if cliente and targa and canvas.image_data is not None:
                try:
                    # 1. Salva DB
                    p = {"cliente": cliente, "targa": targa, "telefono": telefono, "residenza": residenza, "num_doc": num_doc, "prezzo_tot": str(prezzo_tot), "km_uscita": km_uscita, "luogo_nascita": luogo_nascita, "azienda_id": azienda['id'], "data_inizio": str(datetime.date.today())}
                    res_db = supabase.table("contratti").insert(p).execute()
                    id_c = res_db.data[0]['id']

                    # 2. Upload Foto (se presente)
                    if foto_patente:
                        supabase.storage.from_("contratti_media").upload(f"{id_c}_patente.jpg", foto_patente.getvalue())

                    # 3. PDF
                    pdf = fpdf.FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, txt=clean_t(f"Noleggio {azienda['nome_azienda']}"), ln=1)
                    pdf.set_font("Arial", size=8); pdf.multi_cell(0, 4, txt=clean_t(f"Cliente: {cliente}\nCF: {cf}\nDoc: {num_doc}\nTarga: {targa}\nKM: {km_uscita}"))
                    pdf.ln(5); pdf.set_font("Arial", 'B', 7); pdf.cell(0, 4, "ITA:", ln=1); pdf.set_font("Arial", size=6); pdf.multi_cell(0, 3, clean_t(ITA_14))
                    pdf.ln(2); pdf.set_font("Arial", 'B', 7); pdf.cell(0, 4, "ENG:", ln=1); pdf.set_font("Arial", size=6); pdf.multi_cell(0, 3, clean_t(ENG_14))
                    
                    img_sig = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA')
                    img_sig.save("f.png")
                    pdf.ln(5); pdf.image("f.png", x=10, w=35)
                    
                    p_name = f"Contratto_{targa}.pdf"
                    pdf.output(p_name)
                    
                    # 4. Upload PDF
                    with open(p_name, "rb") as f:
                        supabase.storage.from_("contratti_media").upload(f"{id_c}_contratto.pdf", f.read())

                    st.success("✅ Salvataggio Completato!")
                    
                    # WhatsApp
                    msg = urllib.parse.quote(f"Ciao {cliente}, ecco la conferma per {targa}. Grazie da MasterRent!")
                    st.markdown(f'''<a href="https://wa.me/{telefono}?text={msg}" target="_blank"><button style="background-color: #25D366; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer;">📲 WhatsApp Cliente</button></a>''', unsafe_allow_html=True)
                    with open(p_name, "rb") as f:
                        st.download_button("📥 Scarica PDF", f, file_name=p_name)
                except Exception as e:
                    st.error(f"Errore: {e}. Hai creato il bucket 'contratti_media' su Supabase?")
            else:
                st.error("Dati obbligatori mancanti!")

    elif menu == "🚨 Archivio & Multe":
        st.header("🗄️ Archivio")
        res = supabase.table("contratti").select("*").eq("azienda_id", azienda['id']).order('created_at', descending=True).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            s = st.selectbox("Seleziona", df['cliente'] + " (" + df['targa'] + ")")
            c = df[(df['cliente'] + " (" + df['targa'] + ")") == s].iloc[0]
            
            # Link Storage
            st.link_button("📄 Vedi Contratto", f"{url}/storage/v1/object/public/contratti_media/{c['id']}_contratto.pdf")
            st.link_button("🪪 Vedi Patente", f"{url}/storage/v1/object/public/contratti_media/{c['id']}_patente.jpg")

