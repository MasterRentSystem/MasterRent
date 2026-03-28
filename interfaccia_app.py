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

# TESTI LEGALI BILINGUE
ITA_14 = """1. Stato veicolo ottimo. 2. Infrazioni CdS cliente. 3. Gestione multe €25.83. 4. Danni/Furto cliente. 5. No alcool. 6. Riconsegna puntuale. 7. Sinistri: denuncia. 8. No sub-noleggio. 9. Patente valida. 10. Chiavi perse €50. 11. Solo Ischia. 12. Soccorso solo guasti. 13. Foro Napoli. 14. Privacy GDPR."""
ENG_14 = """1. Perfect condition. 2. Traffic fines: customer. 3. Admin fee €25.83. 4. Damage/Theft: customer. 5. No alcohol. 6. On-time return. 7. Accidents: report. 8. No sub-rental. 9. Valid license. 10. Lost keys €50. 11. Ischia only. 12. Assistance: mechanical only. 13. Court: Naples. 14. Privacy GDPR."""

st.sidebar.title("🚀 MasterRent Ischia")
aziende_res = supabase.table("aziende").select("*").execute()
lista_aziende = {a['nome_azienda']: a for a in aziende_res.data} if aziende_res.data else {}

if lista_aziende:
    azienda = lista_aziende[st.sidebar.selectbox("Azienda", list(lista_aziende.keys()))]
    menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Contratto", "🚨 Archivio & Multe", "🏦 Fatturazione Aruba"])

    if menu == "📝 Nuovo Contratto":
        st.header(f"Contratto: {azienda['nome_azienda']}")
        
        with st.expander("👤 DATI CLIENTE", expanded=True):
            cliente = st.text_input("NOME E COGNOME")
            telefono = st.text_input("TELEFONO")
            residenza = st.text_input("RESIDENZA")
            num_doc = st.text_input("NUMERO DOCUMENTO")
            cf = st.text_input("CODICE FISCALE")

        with st.expander("🛵 DATI NOLEGGIO", expanded=True):
            targa = st.text_input("TARGA")
            km_uscita = st.text_input("KM USCITA", value="0")
            prezzo_tot = st.number_input("PREZZO (€)", min_value=0)

        foto_patente = st.camera_input("📸 SCATTA FOTO PATENTE")
        
        st.subheader("✍️ Firma")
        canvas = st_canvas(fill_color="white", stroke_width=2, stroke_color="black", background_color="white", height=150, key="sig")

        if st.button("💾 SALVA TUTTO (Contratto + Foto)"):
            if cliente and targa and foto_patente and canvas.image_data is not None:
                # 1. Salva dati su DB
                payload = {"cliente": cliente, "targa": targa, "telefono": telefono, "residenza": residenza, "num_doc": num_doc, "prezzo_tot": str(prezzo_tot), "km_uscita": km_uscita, "azienda_id": azienda['id'], "data_inizio": str(datetime.date.today())}
                res_db = supabase.table("contratti").insert(payload).execute()
                id_contratto = res_db.data[0]['id']

                # 2. Upload Foto Patente su Storage
                foto_bytes = foto_patente.getvalue()
                supabase.storage.from_("contratti_media").upload(f"{id_contratto}_patente.jpg", foto_bytes)

                # 3. Genera PDF
                pdf = fpdf.FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, txt=clean_t(f"Noleggio {azienda['nome_azienda']}"), ln=1)
                pdf.set_font("Arial", size=9); pdf.multi_cell(0, 5, txt=clean_t(f"Cliente: {cliente}\nDoc: {num_doc}\nTarga: {targa}"))
                pdf.ln(5); pdf.set_font("Arial", size=7); pdf.multi_cell(0, 4, txt=clean_t(ITA_14 + "\n" + ENG_14))
                
                # Inserisce Firma nel PDF
                img_sig = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA')
                img_sig.save("f.png")
                pdf.image("f.png", x=10, w=40)
                
                pdf_name = f"Contratto_{targa}.pdf"
                pdf.output(pdf_name)
                
                # 4. Upload PDF su Storage
                with open(pdf_name, "rb") as f:
                    supabase.storage.from_("contratti_media").upload(f"{id_contratto}_contratto.pdf", f.read())

                st.success("✅ Tutto salvato in archivio!")
                
                # WhatsApp
                msg = urllib.parse.quote(f"Ciao {cliente}, contratto {targa} registrato. Grazie!")
                st.markdown(f'''<a href="https://wa.me/{telefono}?text={msg}" target="_blank"><button style="background-color: #25D366; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer;">📲 WhatsApp Cliente</button></a>''', unsafe_allow_html=True)
            else:
                st.error("Mancano dati, foto o firma!")

    elif menu == "🚨 Archivio & Multe":
        st.header("🗄️ Archivio Documenti")
        res = supabase.table("contratti").select("*").eq("azienda_id", azienda['id']).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            scelta = st.selectbox("Seleziona Noleggio", df['cliente'] + " (" + df['targa'] + ")")
            c_sel = df[(df['cliente'] + " (" + df['targa'] + ")") == scelta].iloc[0]
            
            col_a, col_b, col_c = st.columns(3)
            
            # Link diretti ai file nello storage
            url_pdf = f"{url}/storage/v1/object/public/contratti_media/{c_sel['id']}_contratto.pdf"
            url_patente = f"{url}/storage/v1/object/public/contratti_media/{c_sel['id']}_patente.jpg"
            
            col_a.link_button("📄 PDF Contratto", url_pdf)
            col_b.link_button("🪪 Foto Patente", url_patente)
            if col_c.button("🚨 Genera Modulo Vigili"):
                st.info("Modulo precompilato generato con i dati dell'archivio.")

