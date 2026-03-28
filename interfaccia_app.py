import streamlit as st
import pandas as pd
import datetime
import fpdf
import urllib.parse
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
            telefono = col1.text_input("CELLULARE (con prefisso es: +39)")

        with st.expander("🛵 Dati Veicolo / Vehicle Info", expanded=True):
            col3, col4 = st.columns(2)
            targa = col3.text_input("TARGA / PLATE")
            data_inizio = col4.date_input("DATA / DATE", datetime.date.today())

        st.subheader("✍️ Firma del Cliente / Customer Signature")
        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 255, 1)", stroke_width=3,
            stroke_color="#000000", background_color="#FFFFFF",
            height=150, key="signature",
        )

        if st.button("💾 GENERA CONTRATTO E SALVA"):
            if nome and cf and targa and canvas_result.image_data is not None:
                # 1. Salva dati su DB
                payload = {
                    "cliente": nome, "cf": cf, "targa": targa, 
                    "data_inizio": str(data_inizio), "azienda_id": scelta_azienda['id'],
                    "telefono": telefono
                }
                supabase.table("contratti").insert(payload).execute()

                # 2. Crea PDF (Versione compatta con termini legali)
                pdf = fpdf.FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(0, 10, txt=scelta_azienda['nome_azienda'], ln=1, align='C')
                pdf.set_font("Arial", size=10)
                pdf.cell(0, 10, txt=f"Contratto Targa: {targa} | Cliente: {nome}", ln=1)
                
                # Firma nel PDF
                signature_img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                signature_img.save("firma.png")
                pdf.image("firma.png", x=10, w=40)
                
                pdf_name = f"Contratto_{targa}.pdf"
                pdf.output(pdf_name)
                
                st.success("✅ Contratto firmato!")
                
                # --- FUNZIONE WHATSAPP ---
                if telefono:
                    msg = f"Ciao {nome}, grazie per aver scelto {scelta_azienda['nome_azienda']}! Ecco il riepilogo del tuo noleggio per lo scooter {targa}. A breve riceverai il PDF ufficiale."
                    msg_encoded = urllib.parse.quote(msg)
                    wa_url = f"https://wa.me/{telefono.replace('+', '').replace(' ', '')}?text={msg_encoded}"
                    st.markdown(f'### [📲 INVIA RIEPILOGO SU WHATSAPP]({wa_url})')

                with open(pdf_name, "rb") as f:
                    st.download_button("📥 SCARICA PDF FIRMATO", f, file_name=pdf_name)
            else:
                st.error("Dati o firma mancanti!")

    elif menu == "Archivio & Multe":
        st.header("🚨 Archivio Storico")
        res = supabase.table("contratti").select("*").eq("azienda_id", scelta_azienda['id']).execute()
        if res.data:
            st.dataframe(pd.DataFrame(res.data))
