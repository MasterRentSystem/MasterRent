import streamlit as st
import pandas as pd
import datetime
import fpdf
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io

# 1. CONNESSIONE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def clean_t(text):
    if not text: return ""
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '°': 'o', '’': "'", '–': '-'}
    for k, v in repls.items(): text = text.replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

# 14 PUNTI ORIGINALI
TESTO_LEGALE = """1. Veicolo in ottimo stato, riconsegna con pieno. 2. Cliente responsabile infrazioni C.d.S. 3. Euro 25.83 spese gestione verbali. 4. Danni/Furto/Incendio a carico cliente. 5. No sovrappeso, no alcool/droghe. 6. Riconsegna entro data/ora stabilita. 7. Sinistri: denuncia immediata. 8. No sub-noleggio. 9. Patente valida obbligatoria. 10. Smarrimento chiavi: Euro 50. 11. Solo Isola di Ischia. 12. Assistenza gratuita solo per guasti meccanici. 13. Foro: Napoli-Ischia. 14. Privacy: Dati trattati ai sensi del GDPR 679/2016."""

st.sidebar.title("🚀 MasterRent Ischia")
aziende_res = supabase.table("aziende").select("*").execute()
lista_aziende = {a['nome_azienda']: a for a in aziende_res.data} if aziende_res.data else {}

if lista_aziende:
    nome_scelto = st.sidebar.selectbox("Azienda", list(lista_aziende.keys()))
    azienda = lista_aziende[nome_scelto]
    menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Contratto", "🚨 Archivio & Multe", "🏦 Fatturazione Aruba"])

    if menu == "📝 Nuovo Contratto":
        st.header(f"Contratto: {azienda['nome_azienda']}")
        
        with st.expander("👤 DATI CLIENTE", expanded=True):
            cliente = st.text_input("NOME E COGNOME")
            cf = st.text_input("CODICE FISCALE")
            luogo_nascita = st.text_input("LUOGO DI NASCITA")
            residenza = st.text_input("RESIDENZA")
            col_doc1, col_doc2 = st.columns(2)
            tipo_doc = col_doc1.selectbox("TIPO DOCUMENTO", ["Patente", "C.I.", "Passaporto"])
            num_doc = col_doc2.text_input("NUMERO DOCUMENTO")
            telefono = st.text_input("TELEFONO")

        with st.expander("🛵 DATI NOLEGGIO", expanded=True):
            col_n1, col_n2 = st.columns(2)
            targa = col_n1.text_input("TARGA")
            km_uscita = col_n2.text_input("KM USCITA", value="0")
            prezzo_tot = st.number_input("PREZZO TOTALE (€)", min_value=0)
            data_inizio = st.date_input("DATA INIZIO", datetime.date.today())

        st.camera_input("📸 FOTO PATENTE")
        st.checkbox("Accetto i 14 punti e la Privacy")
        
        st.subheader("✍️ Firma Cliente")
        canvas = st_canvas(fill_color="white", stroke_width=2, stroke_color="black", background_color="white", height=150, key="sig")

        if st.button("💾 SALVA E GENERA CONTRATTO"):
            if cliente and targa and canvas.image_data is not None:
                # NOMI COLONNE IDENTICI A SUPABASE
                payload = {
                    "cliente": cliente,
                    "cf": cf,
                    "luogo_nascita": luogo_nascita,
                    "residenza": residenza,
                    "tipo_doc": tipo_doc,
                    "num_doc": num_doc,
                    "telefono": telefono,
                    "targa": targa,
                    "km_uscita": km_uscita,
                    "prezzo_tot": str(prezzo_tot),
                    "data_inizio": str(data_inizio),
                    "azienda_id": azienda['id']
                }
                
                try:
                    supabase.table("contratti").insert(payload).execute()
                    
                    # Generazione PDF
                    pdf = fpdf.FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", 'B', 15)
                    pdf.cell(0, 10, txt=clean_t(f"Noleggio {azienda['nome_azienda']}"), ln=1)
                    pdf.set_font("Arial", size=9)
                    info = f"Cliente: {cliente}\nCF: {cf}\nNato a: {luogo_nascita}\nResidenza: {residenza}\nDoc: {tipo_doc} {num_doc}\nTel: {telefono}\nTarga: {targa} | KM: {km_uscita}\nPrezzo: Euro {prezzo_tot}"
                    pdf.multi_cell(0, 5, txt=clean_t(info))
                    pdf.ln(5)
                    pdf.set_font("Arial", size=7)
                    pdf.multi_cell(0, 4, txt=clean_t(TESTO_LEGALE))
                    
                    # Firma
                    img = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA')
                    img.save("f.png")
                    pdf.image("f.png", x=10, w=40)
                    
                    pdf.output("contratto.pdf")
                    st.success("✅ Salvato correttamente su Supabase!")
                    with open("contratto.pdf", "rb") as f:
                        st.download_button("📥 Scarica PDF", f, file_name=f"Contratto_{targa}.pdf")
                except Exception as e:
                    st.error(f"Errore durante il salvataggio: {e}")
            else:
                st.error("Dati obbligatori mancanti (Nome, Targa o Firma)!")

    elif menu == "🚨 Archivio & Multe":
        st.header("Gestione Verbali")
        st.write("Seleziona contratto per modulo Vigili.")

    elif menu == "🏦 Fatturazione Aruba":
        st.header("Aruba SDI")
        st.write("Pronto per l'invio.")

