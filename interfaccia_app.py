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
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '°': 'o', '’': "'", '–': '-'}
    for k, v in repls.items(): text = text.replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

# 14 PUNTI BILINGUE (ITA/ENG)
TESTO_LEGALE_ITA = """1. Veicolo in ottimo stato, pieno carburante. 2. Cliente responsabile infrazioni C.d.S. 3. Spese gestione verbali: Euro 25.83. 4. Danni/Furto/Incendio a carico cliente. 5. No alcool/droghe. 6. Riconsegna entro ora stabilita. 7. Sinistri: denuncia immediata. 8. No sub-noleggio. 9. Patente valida. 10. Smarrimento chiavi: Euro 50. 11. Solo Isola di Ischia. 12. Assistenza solo per guasti meccanici. 13. Foro: Napoli-Ischia. 14. Privacy: GDPR 679/2016."""

TESTO_LEGALE_ENG = """1. Vehicle in perfect condition, full tank. 2. Customer liable for traffic fines. 3. Admin fee for fines: Euro 25.83. 4. Damage/Theft/Fire: Customer's liability. 5. No alcohol/drugs. 6. Return by agreed time. 7. Accidents: immediate report. 8. No sub-rental. 9. Valid license required. 10. Lost keys: Euro 50. 11. Ischia Island only. 12. Roadside assistance for mechanical failure only. 13. Jurisdiction: Naples-Ischia. 14. Privacy: GDPR 679/2016."""

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
            col_d1, col_d2 = st.columns(2)
            tipo_doc = col_d1.selectbox("TIPO DOC", ["Patente", "C.I.", "Passaporto"])
            num_doc = col_d2.text_input("NUMERO DOCUMENTO")
            telefono = st.text_input("TELEFONO (es. +393331234567)")

        with st.expander("🛵 DATI NOLEGGIO", expanded=True):
            col_n1, col_n2 = st.columns(2)
            targa = col_n1.text_input("TARGA")
            km_uscita = col_n2.text_input("KM USCITA", value="0")
            prezzo_tot = st.number_input("PREZZO (€)", min_value=0)
            data_inizio = st.date_input("DATA INIZIO", datetime.date.today())

        st.camera_input("📸 FOTO PATENTE")
        st.checkbox("Accetto Termini e Privacy / I accept Terms and Privacy")
        
        st.subheader("✍️ Firma Cliente")
        canvas = st_canvas(fill_color="white", stroke_width=2, stroke_color="black", background_color="white", height=150, key="sig")

        if st.button("💾 SALVA E GENERA"):
            if cliente and targa and canvas.image_data is not None:
                payload = {
                    "cliente": cliente, "cf": cf, "luogo_nascita": luogo_nascita, "residenza": residenza,
                    "tipo_doc": tipo_doc, "num_doc": num_doc, "telefono": telefono, "targa": targa,
                    "km_uscita": km_uscita, "prezzo_tot": str(prezzo_tot), "data_inizio": str(data_inizio),
                    "azienda_id": azienda['id']
                }
                
                try:
                    supabase.table("contratti").insert(payload).execute()
                    
                    # Generazione PDF Bilingue
                    pdf = fpdf.FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", 'B', 14)
                    pdf.cell(0, 10, txt=clean_t(f"Noleggio {azienda['nome_azienda']}"), ln=1)
                    pdf.set_font("Arial", size=8)
                    pdf.cell(0, 5, txt="Via Cognole, 5 - 80075 Forio (NA) - P.IVA 10252601215", ln=1)
                    pdf.ln(5)
                    pdf.set_font("Arial", 'B', 9)
                    pdf.multi_cell(0, 5, txt=clean_t(f"Cliente: {cliente} | CF: {cf}\nDoc: {tipo_doc} {num_doc}\nTarga: {targa} | KM: {km_uscita}\nPrezzo: Euro {prezzo_tot}"))
                    
                    pdf.ln(3)
                    pdf.set_font("Arial", 'B', 7)
                    pdf.cell(0, 4, txt="CONDIZIONI GENERALI (ITA)", ln=1)
                    pdf.set_font("Arial", size=6)
                    pdf.multi_cell(0, 3, txt=clean_t(TESTO_LEGALE_ITA))
                    pdf.ln(2)
                    pdf.set_font("Arial", 'B', 7)
                    pdf.cell(0, 4, txt="TERMS AND CONDITIONS (ENG)", ln=1)
                    pdf.set_font("Arial", size=6)
                    pdf.multi_cell(0, 3, txt=clean_t(TESTO_LEGALE_ENG))
                    
                    # Firma
                    img = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA')
                    img.save("f.png")
                    pdf.ln(5)
                    pdf.image("f.png", x=10, w=35)
                    
                    pdf_name = f"Contratto_{targa}.pdf"
                    pdf.output(pdf_name)
                    st.success("✅ Contratto Salvato!")
                    
                    # TASTO WHATSAPP
                    msg = urllib.parse.quote(f"Ciao {cliente}, ecco il tuo contratto per il veicolo {targa}. Grazie da MasterRent Ischia!")
                    st.markdown(f'''<a href="https://wa.me/{telefono}?text={msg}" target="_blank"><button style="background-color: #25D366; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer;">📲 Invia Conferma via WhatsApp</button></a>''', unsafe_allow_html=True)
                    
                    with open(pdf_name, "rb") as f:
                        st.download_button("📥 Scarica PDF", f, file_name=pdf_name)
                except Exception as e:
                    st.error(f"Errore: {e}")

