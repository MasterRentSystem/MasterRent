import streamlit as st
import pandas as pd
from supabase import create_client

# Connessione
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- SISTEMA DI LOGIN / SELEZIONE AZIENDA ---
# (In futuro questo sarà un vero login con email/password)
st.sidebar.title("🔑 Accesso Gestore")
aziende_res = supabase.table("aziende").select("*").execute()
lista_aziende = {a['nome_azienda']: a for a in aziende_res.data} if aziende_res.data else {}

if not lista_aziende:
    st.warning("Nessuna azienda registrata. Crea la prima azienda su Supabase!")
    scelta_azienda = None
else:
    nome_scelto = st.sidebar.selectbox("Seleziona il tuo Noleggio", list(lista_aziende.keys()))
    scelta_azienda = lista_aziende[nome_scelto]

if scelta_azienda:
    st.sidebar.success(f"Loggato come: {scelta_azienda['nome_azienda']}")
    
    # --- INTERFACCIA DINAMICA (WHITE LABEL) ---
    st.title(f"🚀 {scelta_azienda['nome_azienda'].upper()}")
    st.subheader("Sistema Gestione Contratti, Multe e SDI")

    menu = st.sidebar.radio("Navigazione", ["Nuovo Contratto", "Archivio & Multe", "Fatturazione SDI", "Configurazione"])

    if menu == "Nuovo Contratto":
        st.header("📝 Nuovo Noleggio")
        # Qui il codice di inserimento che abbiamo già creato...
        # IMPORTANTE: Al salvataggio useremo scelta_azienda['id']
        nome = st.text_input("Nome Cliente")
        if st.button("Salva Contratto"):
            data = {"cliente": nome, "azienda_id": scelta_azienda['id']}
            supabase.table("contratti").insert(data).execute()
            st.success("Salvato per la tua azienda!")

    elif menu == "Archivio & Multe":
        st.header("📂 I Tuoi Contratti")
        # Mostra solo i contratti di QUESTA azienda
        res = supabase.table("contratti").select("*").eq("azienda_id", scelta_azienda['id']).execute()
        if res.data:
            st.dataframe(pd.DataFrame(res.data))
        else:
            st.write("Nessun contratto trovato per questa azienda.")

    elif menu == "Fatturazione SDI":
        st.header("🏦 Invio Agenzia Entrate")
        st.write(f"Dati Fiscali: {scelta_azienda['partita_iva']} | SDI: {scelta_azienda['codice_sdi']}")
        st.button("Genera XML Fattura")

    elif menu == "Configurazione":
        st.header("⚙️ Impostazioni Azienda")
        st.write("Qui puoi caricare il tuo logo e cambiare i dati della ditta.")

else:
    st.info("Effettua il login per gestire i tuoi noleggi.")
