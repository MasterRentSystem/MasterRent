import streamlit as st
import pandas as pd
import datetime
import fpdf
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io
import urllib.parse

# CONNESSIONE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

def clean_t(text):
    if not text: return ""
    repls = {'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u', '€': 'Euro', '’': "'", '°': 'o'}
    for k, v in repls.items(): text = text.replace(k, v)
    return text.encode('latin-1', 'ignore').decode('latin-1')

TESTO_LEGALE = [
    "1. Veicolo consegnato in ottimo stato. / Vehicle delivered in excellent condition.",
    "2. Riconsegna con pieno obbligatoria. / Return with full tank mandatory.",
    "3. Responsabilita multe a carico cliente. / Customer liable for traffic fines.",
    "4. Spese gestione verbali: Euro 25.83. / Admin fee for fines: Euro 25.83.",
    "5. Responsabilita danni e furto cliente. / Customer liable for damage and theft.",
    "6. No guida sotto alcool o droghe. / No driving under influence.",
    "7. Il noleggio termina all'ora indicata. / Rental ends at specified time.",
    "8. Denuncia immediata in caso di sinistro. / Immediate accident report required.",
    "9. Vietato sub-noleggio o cessione. / Sub-rental or transfer prohibited.",
    "10. Patente valida e in corso di validita. / Valid driving license required.",
    "11. Smarrimento chiavi: Euro 50. / Lost keys penalty: Euro 50.",
    "12. Solo per l'isola di Ischia. / For Ischia Island use only.",
    "13. Foro competente: Napoli - Sez. Ischia. / Jurisdiction: Naples Court.",
    "14. Privacy GDPR 679/2016 accettata. / GDPR Privacy policy accepted."
]

st.sidebar.title("🚀 MasterRent Ischia")
aziende_res = supabase.table("aziende").select("*").execute()
lista_aziende = {a['nome_azienda']: a for a in aziende_res.data} if aziende_res.data else {}

if lista_aziende:
    azienda = lista_aziende[st.sidebar.selectbox("Azienda", list(lista_aziende.keys()))]
    menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Contratto", "🚨 Archivio"])

    if menu == "📝 Nuovo Contratto":
        st.header(f"Contratto: {azienda['nome_azienda']}")
        
        with st.expander("👤 ANAGRAFICA CLIENTE (Dati DB)", expanded=True):
            c1, c2 = st.columns(2)
            cliente = c1.text_input("NOME E COGNOME")
            cf = c2.text_input("CODICE FISCALE")
            luogo_nascita = c1.text_input("LUOGO DI NASCITA")
            residenza = c2.text_input("RESIDENZA (Via/Città)")
            tipo_doc = c1.selectbox("TIPO DOCUMENTO", ["Patente", "C.I.", "Passaporto"])
            num_doc = c2.text_input("NUMERO DOCUMENTO")
            scadenza_patente = c1.date_input("SCADENZA PATENTE", value=datetime.date.today() + datetime.timedelta(days=365))
            telefono = c2.text_input("TELEFONO (es. 39...)")

        with st.expander("🛵 DATI NOLEGGIO & FATTURAZIONE", expanded=True):
            c3, c4 = st.columns(2)
            targa = c3.text_input("TARGA VEICOLO").upper()
            km_uscita = c4.text_input("KM USCITA", value="0")
            prezzo_tot = st.number_input("PREZZO TOTALE (€)", min_value=0)
            note_fattura = st.text_area("NOTE FATTURAZIONE / VIGILI", placeholder="Es: Pagamento contanti, consegna porto...")

        foto_p = st.camera_input("📸 FOTO PATENTE")
        canvas = st_canvas(fill_color="white", stroke_width=2, height=150, key="sig")

        if st.button("💾 SALVA E GENERA DOCUMENTI"):
            if cliente and targa and canvas.image_data is not None:
                try:
                    # 1. SALVATAGGIO DATABASE
                    dat = {
                        "cliente": cliente, "cf": cf, "luogo_nascita": luogo_nascita, "residenza": residenza,
                        "tipo_doc": tipo_doc, "num_doc": num_doc, "scadenza_patente": str(scadenza_patente),
                        "telefono": telefono, "targa": targa, "km_uscita": km_uscita, "prezzo_tot": str(prezzo_tot),
                        "azienda_id": azienda['id'], "data_inizio": str(datetime.date.today()), "note": note_fattura
                    }
                    res = supabase.table("contratti").insert(dat).execute()
                    id_row = res.data[0]['id']

                    # 2. GENERAZIONE PDF PROFESSIONALE
                    pdf = fpdf.FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", 'B', 16); pdf.cell(0, 10, txt=clean_t(azienda['nome_azienda']), ln=1, align='C')
                    pdf.set_font("Arial", size=8); pdf.cell(0, 5, txt="MasterRent - Via Cognole, 5 - Forio (NA) - P.IVA 10252601215", ln=1, align='C')
                    pdf.ln(5)
                    
                    # Dati Cliente e Veicolo
                    pdf.set_font("Arial", 'B', 10); pdf.cell(0, 8, "DETTAGLI CONTRATTUALI E FATTURAZIONE", ln=1, border='B')
                    pdf.set_font("Arial", size=9)
                    dati_txt = (f"Cliente: {cliente} | CF: {cf}\n"
                               f"Nato a: {luogo_nascita} | Residente: {residenza}\n"
                               f"Documento: {tipo_doc} n. {num_doc} (Scad: {scadenza_patente})\n"
                               f"Veicolo: {targa} | KM Uscita: {km_uscita} | Prezzo: Euro {prezzo_tot}\n"
                               f"Note: {note_fattura}")
                    pdf.multi_cell(0, 5, txt=clean_t(dati_txt))
                    
                    # Condizioni
                    pdf.ln(3); pdf.set_font("Arial", 'B', 8); pdf.cell(0, 5, "CONDIZIONI GENERALI (1-14)", ln=1)
                    pdf.set_font("Arial", size=7)
                    for p in TESTO_LEGALE: pdf.multi_cell(0, 3.5, txt=clean_t(p))
                    
                    # Firma
                    img_s = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA')
                    img_s.save("temp_sig.png")
                    pdf.ln(2); pdf.set_font("Arial", 'I', 7); pdf.cell(0, 5, "Firma Legale ed Accettazione Clausole Vessatorie:", ln=1)
                    pdf.image("temp_sig.png", x=10, w=35)
                    
                    pdf_bytes = pdf.output(dest='S').encode('latin-1')

                    # 3. UPLOAD STORAGE
                    supabase.storage.from_("contratti_media").upload(f"pdf_{id_row}.pdf", pdf_bytes, {"content-type": "application/pdf"})
                    if foto_p:
                        supabase.storage.from_("contratti_media").upload(f"img_{id_row}.jpg", foto_p.getvalue(), {"content-type": "image/jpeg"})

                    st.success("✅ Tutto salvato correttamente!")

                    # 4. TASTI AZIONE
                    c_btn1, c_btn2 = st.columns(2)
                    
                    # Messaggio per Vigili/WhatsApp
                    testo_vigili = f"CONTROLLO NOLEGGIO\nCliente: {cliente}\nCF: {cf}\nVeicolo: {targa}\nPrezzo: {prezzo_tot}€\nKM: {km_uscita}\nData: {datetime.date.today()}"
                    msg_wa = urllib.parse.quote(testo_vigili)
                    
                    c_btn1.markdown(f'''<a href="https://wa.me/{telefono}?text={msg_wa}" target="_blank"><button style="background-color:#25D366;color:white;width:100%;border:none;padding:12px;border-radius:5px;font-weight:bold;cursor:pointer;">📲 Invia Dati (WhatsApp)</button></a>''', unsafe_allow_html=True)
                    c_btn2.download_button("📥 Scarica PDF Contratto", pdf_bytes, file_name=f"Contratto_{targa}.pdf", mime="application/pdf")
                    
                except Exception as e:
                    st.error(f"Errore: {e}")

    elif menu == "🚨 Archivio":
        st.header("🗄️ Archivio")
        res = supabase.table("contratti").select("*").eq("azienda_id", azienda['id']).execute()
        if res.data:
            df = pd.DataFrame(res.data).sort_values(by='created_at', ascending=False)
            sel = st.selectbox("Seleziona Contratto", df['cliente'] + " - " + df['targa'])
            c = df[(df['cliente'] + " - " + df['targa']) == sel].iloc[0]
            
            st.link_button("📄 Apri PDF", f"{url}/storage/v1/object/public/contratti_media/pdf_{c['id']}.pdf")
            st.link_button("🪪 Vedi Patente", f"{url}/storage/v1/object/public/contratti_media/img_{c['id']}.jpg")

