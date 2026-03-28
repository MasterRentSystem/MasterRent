import streamlit as st
import pandas as pd
import datetime
import fpdf
import base64
from supabase import create_client
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io

# Connessione
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.sidebar.title("🔑 Accesso Gestore")
aziende_res = supabase.table("aziende").select("*").execute()
lista_aziende = {a['nome_azienda']: a for a in aziende_res.data} if aziende_res.data else {}

if lista_aziende:
    nome_scelto = st.sidebar.selectbox("Seleziona il tuo Noleggio", list(lista_aziende.keys()))
    scelta_azienda = lista_aziende[nome_scelto]
    
    menu = st.sidebar.radio("Navigazione", ["Nuovo Contratto", "Archivio & Multe", "Fatturazione SDI"])

    if menu == "Nuovo Contratto":
        st.header(f"📝 {scelta_azienda['nome_azienda'].upper()}")
        
        with st.expander("👤 Anagrafica Cliente / Customer Info", expanded=True):
            col1, col2 = st.columns(2)
            nome = col1.text_input("NOME E COGNOME / FULL NAME")
            cf = col2.text_input("CODICE FISCALE / TAX ID")
            luogo_nascita = col1.text_input("LUOGO DI NASCITA / PLACE OF BIRTH")
            residenza = col2.text_input("RESIDENZA / ADDRESS")
            telefono = col1.text_input("TELEFONO / PHONE")

        with st.expander("🛵 Dati Veicolo / Vehicle Info", expanded=True):
            col3, col4 = st.columns(2)
            targa = col3.text_input("TARGA / PLATE")
            km_uscita = col4.text_input("KM USCITA / KM OUT")
            prezzo_tot = col3.number_input("TOTALE (€)", min_value=0)
            data_inizio = col4.date_input("DATA / DATE", datetime.date.today())

        st.subheader("✍️ Firma del Cliente / Customer Signature")
        st.caption("Il cliente accetta i termini bilingue (Multe, Danni, Privacy GDPR)")
        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 255, 1)",
            stroke_width=3,
            stroke_color="#000000",
            background_color="#FFFFFF",
            height=150,
            key="signature",
        )

        if st.button("💾 GENERA CONTRATTO E SALVA"):
            if nome and cf and targa and canvas_result.image_data is not None:
                # 1. Salva dati su DB
                payload = {
                    "cliente": nome, "cf": cf, "targa": targa, "prezzo_tot": str(prezzo_tot),
                    "data_inizio": str(data_inizio), "azienda_id": scelta_azienda['id'],
                    "residenza": residenza, "telefono": telefono
                }
                supabase.table("contratti").insert(payload).execute()

                # 2. Crea PDF con i tuoi Termini e Condizioni
                pdf = fpdf.FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(200, 10, txt=scelta_azienda['nome_azienda'], ln=1, align='C')
                
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 10, txt="CONTRATTO DI NOLEGGIO / RENTAL AGREEMENT", ln=1, align='C')
                
                pdf.set_font("Arial", size=10)
                pdf.ln(5)
                pdf.cell(0, 8, txt=f"Cliente: {nome} | CF: {cf}", ln=1)
                pdf.cell(0, 8, txt=f"Veicolo: {targa} | Data: {data_inizio} | Prezzo: {prezzo_tot} Euro", ln=1)
                
                # Inserimento Termini dal tuo testo
                pdf.ln(5)
                pdf.set_font("Arial", 'B', 9)
                pdf.cell(0, 5, txt="TERMINI E CONDIZIONI / TERMS AND CONDITIONS", ln=1)
                pdf.set_font("Arial", size=7)
                
                termini = [
                    ("1. Stato Veicolo", "Il cliente riceve il veicolo in ottimo stato... / Excellent condition, full tank."),
                    ("2. Multe", "Responsabilità Codice della Strada. Addebito €20,00 gestione pratica. / Driver liable, €20 fee."),
                    ("3. Danni/Furto", "Responsabile danni. Obbligo riconsegna chiavi originali. / Liable for damage/theft."),
                    ("4. Clausola Legale", "Firma digitale ai sensi dell'art. 21 D.Lgs. 82/2005 (C.A.D.). Valore legale pieno.")
                ]
                for tit, desc in termini:
                    pdf.set_font("Arial", 'B', 7)
                    pdf.cell(0, 4, txt=tit, ln=1)
                    pdf.set_font("Arial", size=7)
                    pdf.multi_cell(0, 4, txt=desc)
                
                # Firma nel PDF
                signature_img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                signature_img.save("firma.png")
                pdf.ln(5)
                pdf.cell(0, 5, txt="FIRMA DEL CLIENTE / CUSTOMER SIGNATURE:", ln=1)
                pdf.image("firma.png", x=10, w=50)
                
                pdf_name = f"Contratto_{targa}.pdf"
                pdf.output(pdf_name)
                
                st.success("✅ Contratto firmato e archiviato!")
                with open(pdf_name, "rb") as f:
                    st.download_button("📥 SCARICA PDF FIRMATO", f, file_name=pdf_name)
            else:
                st.error("Dati mancanti o firma non rilevata!")

    elif menu == "Archivio & Multe":
        st.header("🚨 Archivio Storico")
        res = supabase.table("contratti").select("*").eq("azienda_id", scelta_azienda['id']).execute()
        if res.data:
            st.dataframe(pd.DataFrame(res.data))
