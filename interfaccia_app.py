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

# DATI AZIENDA
TITOLARE = "BATTAGLIA MARIANNA"
PIVA = "10252601215"
SEDE = "Via Cognole n. 5, Forio (NA)"

# TESTI LEGALI
CONTRATTO_COMPLETO = """
1.⁠ ⁠CONDIZIONI VEICOLO: Il veicolo viene consegnato in ottimo stato e con il pieno di carburante.
2.⁠ ⁠RICONSEGNA: Il veicolo deve essere riconsegnato nelle stesse condizioni e con il pieno.
3.⁠ ⁠MULTE E INFRAZIONI: Il Cliente si assume la piena responsabilita per ogni violazione al CdS (Art. 196 CdS).
4.⁠ ⁠SPESE GESTIONE: Per ogni verbale notificato, verranno addebitati Euro 25.83 per spese amministrative.
5.⁠ ⁠DANNI E FURTO: Il Cliente e interamente responsabile per danni al veicolo, furto o incendio.
6.⁠ ⁠DIVIETI: Vietata la guida sotto effetto di alcool o stupefacenti.
7.⁠ ⁠AREA DI CIRCOLAZIONE: Il veicolo puo circolare esclusivamente sull'Isola di Ischia.
8.⁠ ⁠FIRMA E PRIVACY: I dati sono trattati secondo il GDPR 679/2016 per fini contrattuali e legali.
"""

st.sidebar.title("🚀 MasterRent Ischia")
aziende_res = supabase.table("aziende").select("*").execute()
lista_aziende = {a['nome_azienda']: a for a in aziende_res.data} if aziende_res.data else {}

if lista_aziende:
    azienda = lista_aziende[st.sidebar.selectbox("Azienda", list(lista_aziende.keys()))]
    menu = st.sidebar.radio("Navigazione", ["📝 Nuovo Noleggio", "🚨 Archivio Documenti"])

    if menu == "📝 Nuovo Noleggio":
        st.header(f"Contratto: {azienda['nome_azienda']}")
        
        with st.expander("👤 ANAGRAFICA CLIENTE", expanded=True):
            c1, c2 = st.columns(2)
            cliente = c1.text_input("NOME E COGNOME")
            cf = c2.text_input("CODICE FISCALE")
            nascita = c1.text_input("NATO A / IL")
            residenza = c2.text_input("RESIDENZA")
            num_doc = c1.text_input("NUMERO PATENTE")
            telefono = c2.text_input("TELEFONO")

        with st.expander("🛵 DATI VEICOLO", expanded=True):
            targa = st.text_input("TARGA").upper()
            prezzo = st.number_input("PREZZO TOT (€)", min_value=0)

        # LETTURA CLAUSOLE PRIMA DI FIRMARE
        st.warning("⚠️ IL CLIENTE DEVE LEGGERE QUI SOTTO PRIMA DI FIRMARE")
        with st.expander("🔎 LEGGI TERMINI, CONDIZIONI E PRIVACY"):
            st.write(CONTRATTO_COMPLETO)
            st.info("Approvando specificamente le clausole 3, 4, 5 e 13 ai sensi degli artt. 1341-1342 c.c.")

        foto_p = st.camera_input("📸 SCANSIONE DOCUMENTO (Fronte/Retro)")
        
        st.subheader("✍️ FIRMA QUI")
        canvas = st_canvas(fill_color="white", stroke_width=2, height=150, key="sig_new")

        if st.button("💾 SALVA E GENERA DOCUMENTAZIONE LEGALE"):
            if cliente and targa and canvas.image_data is not None:
                try:
                    # SALVA DB
                    dat = {"cliente": cliente, "cf": cf, "targa": targa, "azienda_id": azienda['id'], "data_inizio": str(datetime.date.today()), "telefono": telefono}
                    res_db = supabase.table("contratti").insert(dat).execute()
                    id_c = res_db.data[0]['id']

                    # GENERA PDF UNICO (Contratto + Privacy + Firma)
                    pdf = fpdf.FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, txt=clean_t(azienda['nome_azienda']), ln=1, align='C')
                    pdf.set_font("Arial", size=8); pdf.cell(0, 5, txt=f"P.IVA {PIVA} - {SEDE}", ln=1, align='C')
                    pdf.ln(5)

                    # Dati Cliente
                    pdf.set_font("Arial", 'B', 10); pdf.cell(0, 8, "RIEPILOGO CONTRATTO E SOGGETTO", ln=1, fill=True)
                    pdf.set_font("Arial", size=9)
                    pdf.multi_cell(0, 5, txt=clean_t(f"Conduttore: {cliente}\nNato il: {nascita}\nResidente: {residenza}\nCF: {cf}\nDoc: {num_doc}\nVeicolo: {targa}\nPrezzo: {prezzo} Euro"))
                    pdf.ln(5)

                    # Testo Legale
                    pdf.set_font("Arial", 'B', 9); pdf.cell(0, 5, "CONDIZIONI GENERALI E PRIVACY", ln=1)
                    pdf.set_font("Arial", size=7); pdf.multi_cell(0, 4, txt=clean_t(CONTRATTO_COMPLETO))
                    
                    # Riquadro Firme
                    img_s = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA')
                    img_s.save("firma.png")
                    pdf.ln(5); pdf.set_font("Arial", 'B', 8); pdf.cell(0, 5, "FIRMA PER ACCETTAZIONE E CLAUSOLE VESSATORIE (ART. 1341-1342 C.C.)", ln=1)
                    pdf.image("firma.png", x=10, w=45)
                    
                    bytes_pdf = pdf.output(dest='S').encode('latin-1')

                    # STORAGE
                    supabase.storage.from_("contratti_media").upload(f"doc_{id_c}.pdf", bytes_pdf, {"content-type": "application/pdf"})
                    if foto_p:
                        supabase.storage.from_("contratti_media").upload(f"pat_{id_c}.jpg", foto_p.getvalue(), {"content-type": "image/jpeg"})

                    st.success("✅ Contratto firmato e archiviato!")
                    st.download_button("📥 Scarica PDF per Cliente", bytes_pdf, file_name=f"Contratto_{targa}.pdf")

                except Exception as e:
                    st.error(f"Errore: {e}")

    elif menu == "🚨 Archivio Documenti":
        st.header("🗄️ Archivio")
        res = supabase.table("contratti").select("*").eq("azienda_id", azienda['id']).execute()
        if res.data:
            df = pd.DataFrame(res.data).sort_values(by='created_at', ascending=False)
            sel = st.selectbox("Cerca Cliente/Targa", df['cliente'] + " - " + df['targa'])
            c = df[(df['cliente'] + " - " + df['targa']) == sel].iloc[0]
            st.link_button("📄 Vedi Contratto Firmato", f"{url}/storage/v1/object/public/contratti_media/doc_{c['id']}.pdf")
            st.link_button("🪪 Vedi Foto Patente", f"{url}/storage/v1/object/public/contratti_media/pat_{c['id']}.jpg")

