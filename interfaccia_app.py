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

# TESTI LEGALI BILINGUE COMPLETI
ITA_14 = """1. Veicolo in ottimo stato, pieno carburante. 2. Cliente responsabile infrazioni C.d.S. 
 3.⁠ ⁠Spese gestione verbali: Euro 25.83. 4. Danni/Furto/Incendio a carico cliente. 5. No alcool/droghe. 
 6.⁠ ⁠Riconsegna entro ora stabilita. 7. Sinistri: denuncia immediata. 8. No sub-noleggio. 9. Patente valida. 
10.⁠ ⁠Smarrimento chiavi: Euro 50. 11. Solo Isola di Ischia. 12. Assistenza solo guasti meccanici. 
13.⁠ ⁠Foro: Napoli-Ischia. 14. Privacy: GDPR 679/2016."""

ENG_14 = """1. Perfect condition, full tank. 2. Customer liable for traffic fines. 
 3.⁠ ⁠Admin fee for fines: Euro 25.83. 4. Damage/Theft/Fire: Customer's liability. 5. No alcohol/drugs. 
 6.⁠ ⁠Return by agreed time. 7. Accidents: immediate report. 8. No sub-rental. 9. Valid license. 
10.⁠ ⁠Lost keys: Euro 50. 11. Ischia Island only. 12. Roadside assistance: mechanical only. 
13.⁠ ⁠Jurisdiction: Naples-Ischia. 14. Privacy: GDPR 679/2016."""

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
            telefono = col_b.text_input("TELEFONO (es. 39333...)")
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
                    p = {"cliente": cliente, "targa": targa, "telefono": telefono, "residenza": residenza, "num_doc": num_doc, "prezzo_tot": str(prezzo_tot), "km_uscita": km_uscita, "luogo_nascita": luogo_nascita, "azienda_id": azienda['id'], "data_inizio": str(datetime.date.today())}
                    res_db = supabase.table("contratti").insert(p).execute()
                    id_c = res_db.data[0]['id']

                    if foto_patente:
                        supabase.storage.from_("contratti_media").upload(f"{id_c}_patente.jpg", foto_patente.getvalue())

                    pdf = fpdf.FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, txt=clean_t(f"Noleggio {azienda['nome_azienda']}"), ln=1)
                    pdf.set_font("Arial", size=8); pdf.multi_cell(0, 4, txt=clean_t(f"Cliente: {cliente}\nCF: {cf}\nDoc: {num_doc}\nTarga: {targa}"))
                    pdf.ln(5); pdf.set_font("Arial", 'B', 7); pdf.cell(0, 4, "CONDIZIONI (ITA):", ln=1); pdf.set_font("Arial", size=6); pdf.multi_cell(0, 3, clean_t(ITA_14))
                    pdf.ln(2); pdf.set_font("Arial", 'B', 7); pdf.cell(0, 4, "TERMS (ENG):", ln=1); pdf.set_font("Arial", size=6); pdf.multi_cell(0, 3, clean_t(ENG_14))
                    
                    img_sig = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA')
                    img_sig.save("f.png")
                    pdf.ln(5); pdf.image("f.png", x=10, w=35)
                    
                    p_name = f"Contratto_{targa}.pdf"
                    pdf.output(p_name)
                    
                    with open(p_name, "rb") as f:
                        supabase.storage.from_("contratti_media").upload(f"{id_c}_contratto.pdf", f.read())

                    st.success("✅ Contratto registrato con successo!")
                    
                    msg = urllib.parse.quote(f"Ciao {cliente}, ecco il contratto per {targa}. Grazie!")
                    st.markdown(f'''<a href="https://wa.me/{telefono}?text={msg}" target="_blank"><button style="background-color: #25D366; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer;">📲 WhatsApp Cliente</button></a>''', unsafe_allow_html=True)
                    with open(p_name, "rb") as f:
                        st.download_button("📥 Scarica PDF", f, file_name=p_name)
                except Exception as e:
                    st.error(f"Errore tecnico: {e}")
            else:
                st.error("Inserisci Nome, Targa e Firma!")

    elif menu == "🚨 Archivio & Multe":
        st.header("🗄️ Archivio Contratti")
        # Fix errore order: usiamo una chiamata più semplice
        res = supabase.table("contratti").select("*").eq("azienda_id", azienda['id']).execute()
        
        if res.data:
            df = pd.DataFrame(res.data)
            # Ordiniamo i dati con Pandas invece che con Supabase per sicurezza
            df = df.sort_values(by='created_at', ascending=False)
            
            s = st.selectbox("Cerca Cliente o Targa", df['cliente'] + " - " + df['targa'])
            c = df[(df['cliente'] + " - " + df['targa']) == s].iloc[0]
            
            col1, col2 = st.columns(2)
            url_base = f"{url}/storage/v1/object/public/contratti_media/"
            col1.link_button("📄 Apri Contratto", f"{url_base}{c['id']}_contratto.pdf")
            col2.link_button("🪪 Vedi Patente", f"{url_base}{c['id']}_patente.jpg")
