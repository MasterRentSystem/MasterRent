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

st.sidebar.title("🚀 MasterRent Ischia")
aziende_res = supabase.table("aziende").select("*").execute()
lista_aziende = {a['nome_azienda']: a for a in aziende_res.data} if aziende_res.data else {}

if lista_aziende:
    azienda = lista_aziende[st.sidebar.selectbox("Azienda", list(lista_aziende.keys()))]
    menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Contratto", "🚨 Archivio"])

    if menu == "📝 Nuovo Contratto":
        st.header(f"Contratto: {azienda['nome_azienda']}")
        
        with st.expander("👤 ANAGRAFICA CLIENTE", expanded=True):
            c1, c2 = st.columns(2)
            cliente = c1.text_input("NOME E COGNOME")
            cf = c2.text_input("CODICE FISCALE")
            luogo_nascita = c1.text_input("LUOGO DI NASCITA")
            residenza = c2.text_input("RESIDENZA")
            tipo_doc = c1.selectbox("TIPO DOCUMENTO", ["Patente", "C.I.", "Passaporto"])
            num_doc = c2.text_input("NUMERO DOCUMENTO")
            scad_p = c1.date_input("SCADENZA DOCUMENTO")
            telefono = c2.text_input("TELEFONO (es. 39...)")

        with st.expander("🛵 DATI NOLEGGIO", expanded=True):
            c3, c4 = st.columns(2)
            targa = c3.text_input("TARGA").upper()
            km_uscita = c4.text_input("KM USCITA", value="0")
            prezzo_tot = st.number_input("PREZZO (€)", min_value=0)
            note_extra = st.text_area("NOTE FATTURAZIONE / VARIE")

        foto_p = st.camera_input("📸 FOTO PATENTE")
        st.subheader("✍️ Firma per Contratto e Assunzione Responsabilità Multe")
        canvas = st_canvas(fill_color="white", stroke_width=2, height=150, key="sig")

        if st.button("💾 SALVA E GENERA DOCUMENTI"):
            if cliente and targa and canvas.image_data is not None:
                try:
                    # SALVATAGGIO DB
                    dat = {"cliente": cliente, "cf": cf, "luogo_nascita": luogo_nascita, "residenza": residenza, "tipo_doc": tipo_doc, "num_doc": num_doc, "scadenza_patente": str(scad_p), "telefono": telefono, "targa": targa, "km_uscita": km_uscita, "prezzo_tot": str(prezzo_tot), "azienda_id": azienda['id'], "data_inizio": str(datetime.date.today()), "note": note_extra}
                    res = supabase.table("contratti").insert(dat).execute()
                    id_row = res.data[0]['id']

                    # GENERAZIONE PDF UNIFICATO (CONTRATTO + MODULO MULTE)
                    pdf = fpdf.FPDF()
                    pdf.add_page()
                    
                    # INTESTAZIONE
                    pdf.set_font("Arial", 'B', 16); pdf.cell(0, 10, txt=clean_t(azienda['nome_azienda']), ln=1, align='C')
                    pdf.set_font("Arial", size=8); pdf.cell(0, 5, txt="MasterRent - Forio (NA) - P.IVA 10252601215", ln=1, align='C')
                    pdf.ln(5)

                    # --- SEZIONE 1: MODULO PER I VIGILI (MULTE) ---
                    pdf.set_fill_color(240, 240, 240)
                    pdf.set_font("Arial", 'B', 11); pdf.cell(0, 8, " DICHIARAZIONE ASSUNZIONE RESPONSABILITA' (Art. 196 CdS)", ln=1, fill=True)
                    pdf.set_font("Arial", size=9)
                    testo_multe = (f"Il sottoscritto {cliente}, nato a {luogo_nascita}, CF: {cf}, residente in {residenza}, "
                                   f"titolare di {tipo_doc} n. {num_doc}, DICHIARA di avere la piena disponibilita del veicolo "
                                   f"targato {targa} in data {datetime.date.today()} e si assume la piena e totale responsabilita "
                                   f"per ogni infrazione al Codice della Strada (multe, verbali, sequestri) commessa durante il periodo di noleggio.")
                    pdf.multi_cell(0, 5, txt=clean_t(testo_multe), border=1)
                    pdf.ln(5)

                    # --- SEZIONE 2: DATI NOLEGGIO ---
                    pdf.set_font("Arial", 'B', 10); pdf.cell(0, 7, "DETTAGLI NOLEGGIO", ln=1)
                    pdf.set_font("Arial", size=9)
                    pdf.cell(0, 5, txt=clean_t(f"Targa: {targa} | KM Partenza: {km_uscita} | Prezzo: {prezzo_tot} Euro"), ln=1)
                    pdf.ln(3)

                    # --- SEZIONE 3: FIRMA ---
                    img_s = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA')
                    img_s.save("f.png")
                    pdf.image("f.png", x=10, w=40)
                    pdf.set_font("Arial", 'I', 7); pdf.cell(0, 5, "Firma del Conducente per Ricevuta e Responsabilita", ln=1)
                    
                    pdf_bytes = pdf.output(dest='S').encode('latin-1')

                    # STORAGE
                    supabase.storage.from_("contratti_media").upload(f"doc_{id_row}.pdf", pdf_bytes, {"content-type": "application/pdf"})
                    if foto_p:
                        supabase.storage.from_("contratti_media").upload(f"pat_{id_row}.jpg", foto_p.getvalue(), {"content-type": "image/jpeg"})

                    st.success("✅ Contratto e Modulo Multe pronti!")
                    
                    # TASTI AZIONE
                    c1, c2 = st.columns(2)
                    # Messaggio WhatsApp con dati per rinotifica multa
                    txt_wa = f"MASTERRENT - DATI PER VERBALE\nVeicolo: {targa}\nConducente: {cliente}\nCF: {cf}\nDoc: {num_doc}\nData: {datetime.date.today()}\nIl cliente ha firmato l'assunzione di responsabilità."
                    c1.markdown(f'''<a href="https://wa.me/{telefono}?text={urllib.parse.quote(txt_wa)}" target="_blank"><button style="background-color:#25D366;color:white;width:100%;border:none;padding:12px;border-radius:5px;font-weight:bold;cursor:pointer;">📲 Invia Dati Multe (WA)</button></a>''', unsafe_allow_html=True)
                    c2.download_button("📥 Scarica PDF (Per Vigili/Multe)", pdf_bytes, file_name=f"Modulo_Multe_{targa}.pdf")

                except Exception as e:
                    st.error(f"Errore: {e}")

    elif menu == "🚨 Archivio":
        st.header("🗄️ Archivio")
        res = supabase.table("contratti").select("*").eq("azienda_id", azienda['id']).execute()
        if res.data:
            df = pd.DataFrame(res.data).sort_values(by='created_at', ascending=False)
            sel = st.selectbox("Cerca Contratto", df['cliente'] + " - " + df['targa'])
            c = df[(df['cliente'] + " - " + df['targa']) == sel].iloc[0]
            st.link_button("📄 Vedi Modulo Multe/Contratto", f"{url}/storage/v1/object/public/contratti_media/doc_{c['id']}.pdf")
            st.link_button("🪪 Vedi Foto Patente", f"{url}/storage/v1/object/public/contratti_media/pat_{c['id']}.jpg")

