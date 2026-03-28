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

# 14 PUNTI ORIGINALI + PRIVACY
TESTO_LEGALE = [
    "1. Veicolo in ottimo stato con pieno. / Vehicle in excellent condition with full tank.",
    "2. Riconsegna obbligatoria con pieno. / Return with full tank mandatory.",
    "3. Cliente responsabile infrazioni C.d.S. / Customer liable for traffic fines.",
    "4. Spese gestione verbali: Euro 25.83. / Admin fee for fines: Euro 25.83.",
    "5. Responsabilita danni/furto del cliente. / Customer liable for damage/theft.",
    "6. No guida sotto alcool/droghe. / No driving under influence.",
    "7. Termine noleggio data/ora indicata. / Rental ends at agreed date/time.",
    "8. Denuncia immediata sinistri. / Immediate accident report required.",
    "9. Divieto di sub-noleggio. / Sub-rental strictly prohibited.",
    "10. Patente valida dichiarata. / Valid driving license declared.",
    "11. Penale chiavi perse: Euro 50. / Lost keys penalty: Euro 50.",
    "12. Solo Isola di Ischia. / For Ischia Island use only.",
    "13. Foro: Napoli-Sez. Ischia. / Jurisdiction: Naples-Ischia Court.",
    "14. Privacy: Dati trattati ai sensi del GDPR 679/2016. / Data processed per GDPR."
]

st.sidebar.title("🚀 MasterRent Ischia")
aziende_res = supabase.table("aziende").select("*").execute()
lista_aziende = {a['nome_azienda']: a for a in aziende_res.data} if aziende_res.data else {}

if lista_aziende:
    azienda = lista_aziende[st.sidebar.selectbox("Azienda", list(lista_aziende.keys()))]
    menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Contratto", "🚨 Archivio"])

    if menu == "📝 Nuovo Contratto":
        st.header(f"Contratto: {azienda['nome_azienda']}")
        
        with st.expander("👤 DATI CLIENTE", expanded=True):
            c1, c2 = st.columns(2)
            cliente = c1.text_input("NOME E COGNOME")
            cf = c2.text_input("CODICE FISCALE")
            residenza = c1.text_input("RESIDENZA")
            luogo_nascita = c2.text_input("LUOGO NASCITA")
            num_doc = c1.text_input("NUMERO DOCUMENTO")
            telefono = c2.text_input("TELEFONO (es. 39333...)")

        with st.expander("🛵 DATI NOLEGGIO", expanded=True):
            c3, c4 = st.columns(2)
            targa = c3.text_input("TARGA")
            km_uscita = c4.text_input("KM USCITA", value="0")
            prezzo_tot = st.number_input("PREZZO (€)", min_value=0)

        foto_p = st.camera_input("📸 FOTO PATENTE")
        st.subheader("✍️ Firma Legale")
        canvas = st_canvas(fill_color="white", stroke_width=2, height=150, key="sig")

        if st.button("💾 SALVA E INVIA"):
            if cliente and targa and canvas.image_data is not None:
                try:
                    # SALVATAGGIO DB
                    dat = {"cliente": cliente, "cf": cf, "residenza": residenza, "luogo_nascita": luogo_nascita, "num_doc": num_doc, "telefono": telefono, "targa": targa, "km_uscita": km_uscita, "prezzo_tot": str(prezzo_tot), "azienda_id": azienda['id'], "data_inizio": str(datetime.date.today())}
                    res = supabase.table("contratti").insert(dat).execute()
                    id_c = res.data[0]['id']

                    # GENERAZIONE PDF
                    pdf = fpdf.FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", 'B', 15); pdf.cell(0, 10, txt=clean_t(azienda['nome_azienda']), ln=1, align='C')
                    pdf.set_font("Arial", size=8); pdf.cell(0, 5, txt="MasterRent - Via Cognole, 5 - Forio (NA) - P.IVA 10252601215", ln=1, align='C')
                    pdf.ln(5)
                    pdf.set_font("Arial", 'B', 10); pdf.cell(0, 8, "DETTAGLI CONTRATTUALI", ln=1, border='B')
                    pdf.set_font("Arial", size=9)
                    pdf.multi_cell(0, 5, txt=clean_t(f"Cliente: {cliente} | CF: {cf}\nNato a: {luogo_nascita} | Residente: {residenza}\nDoc: {num_doc} | Targa: {targa} | KM: {km_uscita}\nPrezzo: Euro {prezzo_tot}"))
                    
                    pdf.ln(3); pdf.set_font("Arial", 'B', 8); pdf.cell(0, 5, "CONDIZIONI (1-14) & PRIVACY", ln=1)
                    pdf.set_font("Arial", size=7)
                    for p in TESTO_LEGALE: pdf.multi_cell(0, 3.5, txt=clean_t(p))
                    
                    img_s = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA')
                    img_s.save("f.png")
                    pdf.ln(4); pdf.set_font("Arial", 'I', 7); pdf.cell(0, 5, "Firma ai sensi degli Art. 1341-1342 C.C. e Privacy GDPR:", ln=1)
                    pdf.image("f.png", x=10, w=35)
                    pdf_name = f"Contratto_{targa}.pdf"
                    pdf.output(pdf_name)

                    # STORAGE
                    supabase.storage.from_("contratti_media").upload(f"{id_c}_c.pdf", open(pdf_name, "rb").read())
                    if foto_p: supabase.storage.from_("contratti_media").upload(f"{id_c}_p.jpg", foto_p.getvalue())

                    st.success("✅ Contratto salvato e archiviato!")
                    
                    # WHATSAPP
                    msg = urllib.parse.quote(f"Ciao {cliente}, ecco il tuo contratto per {targa}. Grazie da MasterRent!")
                    st.markdown(f'''<a href="https://wa.me/{telefono}?text={msg}" target="_blank"><button style="background-color:#25D366;color:white;border:none;padding:10px 20px;border-radius:5px;cursor:pointer;">📲 Invia WhatsApp al Cliente</button></a>''', unsafe_allow_html=True)
                    with open(pdf_name, "rb") as f: st.download_button("📥 Scarica PDF", f, file_name=pdf_name)
                except Exception as e:
                    st.error(f"Errore 403? Esegui il comando SQL su Supabase! Dettaglio: {e}")

    elif menu == "🚨 Archivio":
        st.header("🗄️ Archivio")
        res = supabase.table("contratti").select("*").eq("azienda_id", azienda['id']).execute()
        if res.data:
            df = pd.DataFrame(res.data).sort_values(by='created_at', ascending=False)
            sel = st.selectbox("Seleziona", df['cliente'] + " - " + df['targa'])
            c = df[(df['cliente'] + " - " + df['targa']) == sel].iloc[0]
            st.link_button("📄 Vedi Contratto", f"{url}/storage/v1/object/public/contratti_media/{c['id']}_c.pdf")
            st.link_button("🪪 Vedi Patente", f"{url}/storage/v1/object/public/contratti_media/{c['id']}_p.jpg")

