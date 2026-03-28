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

# 1. CONNESSIONE (Le tue chiavi sono già inserite se hai lanciato i comandi precedenti)
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def clean_t(text):
    if not text: return ""
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in repls.items(): text = text.replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

# DATI AZIENDA (Precompilati per il modulo Vigili)
TITOLARE = "BATTAGLIA MARIANNA"
NATO_A = "Berlino (Germania)"
NATO_IL = "13/01/1987"
RESIDENTE_A = "Forio"
IN_VIA = "Via Cognole n. 5"
CF_TITOLARE = "BTTMNN87A53Z112S"
PIVA_TITOLARE = "10252601215"

# CLAUSOLE CONTRATTO (ITA/ENG)
TESTO_LEGALE_ITA = """1. Veicolo in ottimo stato con pieno. 2. Pieno alla riconsegna obbligatorio. 3. Responsabilita multe CdS cliente. 4. Spese gestione verbali: Euro 25.83. 5. Danni/Furto a carico cliente. 6. No alcool/droghe. 7. Termine ora indicata. 8. Denuncia sinistro immediata. 9. Vietato sub-noleggio. 10. Patente valida. 11. Penale chiavi perse: €50. 12. Solo Ischia. 13. Foro competente Ischia. 14. Privacy GDPR 679/2016."""
TESTO_LEGALE_ENG = """1. Excellent condition, full tank. 2. Refill mandatory upon return. 3. Traffic fines: Customer's liability. 4. Admin fee: Euro 25.83. 5. Damage/Theft: Customer's liability. 6. No drugs/alcohol. 7. Respect end time. 8. Immediate accident report. 9. Sub-rental prohibited. 10. Valid license. 11. Lost keys: €50. 12. Ischia Island only. 13. Jurisdiction Ischia. 14. Privacy GDPR 679/2016."""

st.sidebar.title("🚀 MasterRent Ischia")
aziende_res = supabase.table("aziende").select("*").execute()
lista_aziende = {a['nome_azienda']: a for a in aziende_res.data} if aziende_res.data else {}

if lista_aziende:
    azienda = lista_aziende[st.sidebar.selectbox("Azienda", list(lista_aziende.keys()))]
    menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Noleggio", "🚨 Archivio Rinotifiche"])

    if menu == "📝 Nuovo Noleggio":
        st.header(f"Nuovo Contratto: {azienda['nome_azienda']}")
        
        with st.expander("👤 DATI CLIENTE (Per Rinotifica)", expanded=True):
            c1, c2 = st.columns(2)
            cliente = c1.text_input("NOME E COGNOME")
            cf_cliente = c2.text_input("CODICE FISCALE CLIENTE")
            nascita_cliente = c1.text_input("LUOGO E DATA NASCITA CLIENTE")
            residenza_cliente = c2.text_input("RESIDENZA CLIENTE (Via/Città)")
            num_doc_cliente = c1.text_input("NUMERO DOCUMENTO CLIENTE")
            telefono = c2.text_input("TELEFONO CLIENTE (es. 39...)")

        with st.expander("🛵 DATI VEICOLO", expanded=True):
            c3, c4 = st.columns(2)
            targa = c3.text_input("TARGA").upper()
            prezzo_tot = st.number_input("PREZZO TOT (€)", min_value=0)

        foto_p = st.camera_input("📸 FOTO PATENTE (Fronte e Retro)")
        canvas = st_canvas(fill_color="white", stroke_width=2, height=150, key="sig")

        if st.button("💾 SALVA E GENERA DOCUMENTI"):
            if cliente and targa and canvas.image_data is not None:
                try:
                    oggi = str(datetime.date.today())
                    
                    # 1. SALVA NEL DATABASE
                    dat = {"cliente": cliente, "cf": cf_cliente, "targa": targa, "azienda_id": azienda['id'], "data_inizio": oggi, "telefono": telefono}
                    res_db = supabase.table("contratti").insert(dat).execute()
                    id_c = res_db.data[0]['id']

                    # 2. PDF 1: IL CONTRATTO (Clausole legali)
                    p1 = fpdf.FPDF()
                    p1.add_page()
                    p1.set_font("Arial", 'B', 16); p1.cell(0, 10, txt=clean_t(azienda['nome_azienda']), ln=1, align='C')
                    p1.set_font("Arial", size=10); p1.multi_cell(0, 5, txt=clean_t(f"Cliente: {cliente}\nTarga: {targa} | Data: {oggi}"))
                    p1.ln(5); p1.set_font("Arial", size=7); p1.multi_cell(0, 3.5, clean_t(f"CONDIZIONI (ITA):\n{TESTO_LEGALE_ITA}\n\nTERMS (ENG):\n{TESTO_LEGALE_ENG}"))
                    
                    img_s = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA')
                    img_s.save("temp.png")
                    p1.ln(5); p1.set_font("Arial", 'I', 7); p1.cell(0, 5, "Firma del Cliente:", ln=1)
                    p1.image("temp.png", x=10, w=35)
                    bytes1 = p1.output(dest='S').encode('latin-1')

                    # 3. PDF 2: IL MODULO VIGILI (Il tuo cartaceo)
                    p2 = fpdf.FPDF()
                    p2.add_page()
                    p2.set_font("Arial", size=10)
                    
                    # Intestazione Precompilata
                    testo_int = f"{TITOLARE}\n{NATO_A} il {NATO_IL} e residente a {RESIDENTE_A} alla {IN_VIA}\nin qualita di titolare dell'omonima ditta individuale, C.F.: {CF_TITOLARE} e P. IVA: {PIVA_TITOLARE}"
                    p2.multi_cell(0, 5, txt=clean_t(testo_int))
                    p2.ln(10)
                    
                    # Titoli (Con spazi vuoti da completare per il verbale)
                    p2.set_font("Arial", 'B', 12); p2.cell(0, 7, "Spett. le Polizia Locale di _____________", ln=1, align='R')
                    p2.ln(10)
                    p2.cell(0, 7, "OGGETTO: RIFERIMENTO VS. ACCERTAMENTO VIOLAZIONE N. _____________ PROT. _____________", ln=1)
                    p2.cell(0, 7, "          - COMUNICAZIONE LOCAZIONE VEICOLO", ln=1)
                    p2.ln(10)
                    
                    # Corpo
                    p2.set_font("Arial", size=11); p2.cell(0, 7, txt="DICHIARA", ln=1, align='C'); p2.ln(5)
                    p2.multi_cell(0, 6, txt=clean_t(f"Ai sensi della L. 445/2000 che il veicolo targato {targa}\nera concesso in locazione senza conducente al signor:"))
                    p2.ln(5)
                    
                    # Dati Cliente Precompilati
                    p2.set_font("Arial", 'B', 11)
                    p2.cell(0, 7, txt=clean_t(f"COGNOME E NOME: {cliente}"), ln=1)
                    p2.cell(0, 7, txt=clean_t(f"LUOGO E DATA DI NASCITA: {nascita_cliente}"), ln=1)
                    p2.cell(0, 7, txt=clean_t(f"RESIDENZA: {residenza_cliente}"), ln=1)
                    p2.cell(0, 7, txt=clean_t(f"IDENTIFICATO A MEZZO: {num_doc_cliente}"), ln=1) # Usiamo solo il numero per semplicità
                    p2.ln(10)
                    
                    p2.set_font("Arial", size=10); p2.multi_cell(0, 5, txt="La presente al fine di procedere alla rinotifica nei confronti del locatario sopra indicato.")
                    p2.ln(5); p2.cell(0, 5, "Si allega: Copia del contratto di locazione con documento del trasgressore.", ln=1)
                    p2.ln(10); p2.cell(0, 7, "In fede, Marianna Battaglia", ln=1, align='R')
                    
                    bytes2 = p2.output(dest='S').encode('latin-1')

                    # 4. STORAGE (3 File: Contratto, Modulo Vigili, Patente)
                    supabase.storage.from_("contratti_media").upload(f"contratto_{id_c}.pdf", bytes1, {"content-type": "application/pdf"})
                    supabase.storage.from_("contratti_media").upload(f"vigili_{id_c}.pdf", bytes2, {"content-type": "application/pdf"})
                    if foto_p:
                        supabase.storage.from_("contratti_media").upload(f"pat_{id_c}.jpg", foto_p.getvalue(), {"content-type": "image/jpeg"})

                    st.success("✅ Salvataggio completato!")
                    
                    c1, c2 = st.columns(2)
                    c1.download_button("📥 Scarica Contratto PDF", bytes1, file_name=f"Contratto_{targa}.pdf")
                    c2.download_button("📥 Scarica Modulo Multe Precompilato", bytes2, file_name=f"Modulo_Multe_{targa}.pdf")
                    
                    msg_wa = urllib.parse.quote(f"Ciao {cliente}, ecco il tuo contratto MasterRent Ischia per {targa}. Grazie!")
                    st.markdown(f'''<a href="https://wa.me/{telefono}?text={msg_wa}" target="_blank"><button style="background-color:#25D366;color:white;width:100%;border:none;padding:12px;border-radius:5px;font-weight:bold;cursor:pointer;">📲 Invia WhatsApp</button></a>''', unsafe_allow_html=True)

                except Exception as e:
                    st.error(f"Errore tecnico: {e}")

    elif menu == "🚨 Archivio Rinotifiche":
        st.header("🗄️ Archivio Rinotifiche Multe")
        res = supabase.table("contratti").select("*").eq("azienda_id", azienda['id']).execute()
        if res.data:
            df = pd.DataFrame(res.data).sort_values(by='created_at', ascending=False)
            sel = st.selectbox("Cerca Contratto", df['cliente'] + " - " + df['targa'])
            c = df[(df['cliente'] + " - " + df['targa']) == sel].iloc[0]
            
            # --- I TRE TASTI FONDAMENTALI ---
            st.link_button("📄 Vedi Contratto PDF", f"{url}/storage/v1/object/public/contratti_media/contratto_{c['id']}.pdf")
            st.link_button("🚨 Scarica Modulo Multe Precompilato", f"{url}/storage/v1/object/public/contratti_media/vigili_{c['id']}.pdf")
            st.link_button("🪪 Vedi Patente (Per Rinotifica)", f"{url}/storage/v1/object/public/contratti_media/pat_{c['id']}.jpg")
