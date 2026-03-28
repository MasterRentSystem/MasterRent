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

# I 14 PUNTI COMPLETI (Trascrizione fedele bilingue)
TESTO_14_PUNTI = [
    ("1. Il veicolo e consegnato in ottimo stato. / Vehicle delivered in excellent condition.", "2. Riconsegna con pieno di carburante. / Return with full tank."),
    ("3. Responsabilita infrazioni C.d.S. a carico del cliente. / Driver liable for traffic fines.", "4. Spese gestione verbali: Euro 25.83. / Administrative fee for fines: Euro 25.83."),
    ("5. Responsabilita danni e furto del cliente. / Customer liable for damage and theft.", "6. Divieto guida sotto effetto di alcool o droghe. / No driving under influence."),
    ("7. Il noleggio termina alla data e ora indicata. / Rental ends at specified date and time.", "8. Obbligo di denuncia immediata in caso di sinistro. / Mandatory immediate accident report."),
    ("9. Divieto di sub-noleggio o cessione del mezzo. / Sub-rental or vehicle transfer prohibited.", "10. Il cliente dichiara patente valida. / Customer declares valid driving license."),
    ("11. Smarrimento chiavi penale Euro 50. / Lost keys penalty Euro 50.", "12. Il veicolo deve restare sull'isola di Ischia. / Vehicle must stay on Ischia island."),
    ("13. Foro competente: Napoli - Sez. Ischia. / Jurisdiction: Naples - Ischia Court.", "14. Trattamento dati personali GDPR 679/2016. / GDPR Data protection policy.")
]

st.sidebar.title("🚀 MasterRent Ischia")
aziende_res = supabase.table("aziende").select("*").execute()
lista_aziende = {a['nome_azienda']: a for a in aziende_res.data} if aziende_res.data else {}

if lista_aziende:
    azienda = lista_aziende[st.sidebar.selectbox("Azienda", list(lista_aziende.keys()))]
    menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Contratto", "🚨 Archivio & Multe"])

    if menu == "📝 Nuovo Contratto":
        st.header(f"Contratto: {azienda['nome_azienda']}")
        
        with st.expander("👤 DATI CLIENTE", expanded=True):
            c1, c2 = st.columns(2)
            cliente = c1.text_input("NOME E COGNOME")
            cf = c2.text_input("CODICE FISCALE")
            luogo_nascita = c1.text_input("LUOGO DI NASCITA")
            residenza = c2.text_input("RESIDENZA")
            tipo_doc = c1.selectbox("TIPO DOC", ["Patente", "C.I."])
            num_doc = c2.text_input("NUMERO DOCUMENTO")
            telefono = c1.text_input("TELEFONO (es. 39333...)")

        with st.expander("🛵 DATI NOLEGGIO", expanded=True):
            c3, c4 = st.columns(2)
            targa = c3.text_input("TARGA")
            km_uscita = c4.text_input("KM USCITA", value="0")
            prezzo_tot = st.number_input("PREZZO (€)", min_value=0)

        foto_p = st.camera_input("📸 FOTO PATENTE")
        st.subheader("✍️ Firma Cliente")
        canvas = st_canvas(fill_color="white", stroke_width=2, stroke_color="black", background_color="white", height=150, key="sig")

        if st.button("💾 SALVA E GENERA"):
            if cliente and targa and canvas.image_data is not None:
                try:
                    # 1. Inserimento Database
                    dat = {
                        "cliente": cliente, "cf": cf, "luogo_nascita": luogo_nascita, "residenza": residenza,
                        "tipo_doc": tipo_doc, "num_doc": num_doc, "telefono": telefono, "targa": targa,
                        "km_uscita": km_uscita, "prezzo_tot": str(prezzo_tot), "azienda_id": azienda['id'],
                        "data_inizio": str(datetime.date.today())
                    }
                    res_db = supabase.table("contratti").insert(dat).execute()
                    id_c = res_db.data[0]['id']

                    # 2. Generazione PDF Professionale
                    pdf = fpdf.FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", 'B', 16)
                    pdf.cell(0, 10, txt=clean_t(azienda['nome_azienda']), ln=1, align='C')
                    pdf.set_font("Arial", size=8)
                    pdf.cell(0, 5, txt=clean_t("Via Cognole, 5 - 80075 Forio (NA) - P.IVA 10252601215"), ln=1, align='C')
                    pdf.ln(5)
                    
                    # Sezione Dati
                    pdf.set_fill_color(240, 240, 240)
                    pdf.set_font("Arial", 'B', 10)
                    pdf.cell(0, 8, txt="DATI DEL CONTRATTO", ln=1, fill=True)
                    pdf.set_font("Arial", size=9)
                    info_txt = f"Cliente: {cliente}  |  CF: {cf}\nNato a: {luogo_nascita}  |  Residente: {residenza}\nDoc: {tipo_doc} - {num_doc}\nVeicolo: {targa}  |  KM Uscita: {km_uscita}  |  Prezzo: Euro {prezzo_tot}"
                    pdf.multi_cell(0, 5, txt=clean_t(info_txt))
                    
                    # I 14 Punti
                    pdf.ln(5)
                    pdf.set_font("Arial", 'B', 9)
                    pdf.cell(0, 6, txt="CONDIZIONI GENERALI / TERMS AND CONDITIONS", ln=1, border='B')
                    pdf.set_font("Arial", size=7)
                    for p1, p2 in TESTO_14_PUNTI:
                        pdf.multi_cell(0, 4, txt=clean_t(f"{p1}\n{p2}"))
                        pdf.ln(1)
                    
                    # Firma
                    img_sig = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA')
                    img_sig.save("f.png")
                    pdf.ln(5)
                    pdf.set_font("Arial", 'I', 8)
                    pdf.cell(0, 5, txt="Firma per accettazione e clausole vessatorie (Art. 1341-1342 C.C.):", ln=1)
                    pdf.image("f.png", x=10, w=45)
                    
                    pdf_name = f"Contratto_{targa}.pdf"
                    pdf.output(pdf_name)
                    
                    # 3. Upload File
                    with open(pdf_name, "rb") as f:
                        supabase.storage.from_("contratti_media").upload(f"{id_c}_contratto.pdf", f.read())
                    if foto_p:
                        supabase.storage.from_("contratti_media").upload(f"{id_c}_patente.jpg", foto_p.getvalue())

                    st.success("✅ Salvato!")
                    
                    # WhatsApp
                    msg = urllib.parse.quote(f"Ciao {cliente}, ecco la conferma per il noleggio della targa {targa}. Grazie!")
                    st.markdown(f'''<a href="https://wa.me/{telefono}?text={msg}" target="_blank"><button style="background-color:#25D366;color:white;border:none;padding:10px 20px;border-radius:5px;cursor:pointer;">📲 Invia su WhatsApp</button></a>''', unsafe_allow_html=True)
                    with open(pdf_name, "rb") as f:
                        st.download_button("📥 Scarica PDF", f, file_name=pdf_name)
                except Exception as e:
                    st.error(f"Errore: {e}")

    elif menu == "🚨 Archivio & Multe":
        st.header("🗄️ Archivio Contratti")
        res = supabase.table("contratti").select("*").eq("azienda_id", azienda['id']).execute()
        if res.data:
            df = pd.DataFrame(res.data).sort_values(by='created_at', ascending=False)
            sel = st.selectbox("Cerca Cliente", df['cliente'] + " - " + df['targa'])
            c = df[(df['cliente'] + " - " + df['targa']) == sel].iloc[0]
            
            url_pdf = f"{url}/storage/v1/object/public/contratti_media/{c['id']}_contratto.pdf"
            url_img = f"{url}/storage/v1/object/public/contratti_media/{c['id']}_patente.jpg"
            
            st.link_button("📄 Vedi Contratto Completo", url_pdf)
            st.link_button("🪪 Vedi Foto Patente", url_img)
