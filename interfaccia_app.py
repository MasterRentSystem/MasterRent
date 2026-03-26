import streamlit as st
import datetime

st.set_page_config(page_title="MasterRent Forio", page_icon="🛵")

st.title("🛵 MasterRent System - Forio")
st.subheader("Gestione Professionale Noleggio & Multe")

# --- DATABASE FLOTTA ---
moto = ["Liberty 125 (EB12345)", "Bebe 125 (BX98765)", "SH 150 (AA111AA)"]

# --- SIDEBAR (Menu Laterale) ---
st.sidebar.header("Menu Operativo")
opzione = st.sidebar.selectbox("Cosa vuoi fare?", ["Nuovo Contratto", "Invia Multa ai Vigili", "Stato Flotta"])

if opzione == "Nuovo Contratto":
    st.header("📝 Crea Nuovo Contratto")
    nome = st.text_input("Nome e Cognome Cliente")
    mezzo = st.selectbox("Seleziona Motore", moto)
    giorni = st.number_input("Giorni di Noleggio", min_value=1, value=1)
    
    # Calcolo Prezzo Automatico (Alta/Bassa Stagione)
    mese = datetime.datetime.now().month
    prezzo_g = 50 if mese in [7, 8] else 30
    totale = giorni * prezzo_g
    
    st.write(f"*Tariffa applicata:* {'Alta Stagione (50€)' if mese in [7, 8] else 'Bassa Stagione (30€)'}")
    st.write(f"### Totale: {totale}€")
    
    if st.button("Genera Contratto Legale"):
        st.success(f"Contratto creato per {nome}! Pronto per la firma digitale.")
        st.info("Clausola: Il conducente è responsabile per ogni sanzione pecuniaria.")

elif opzione == "Invia Multa ai Vigili":
    st.header("⚠️ Gestione Multe (Rimbalzo)")
    targa_multa = st.text_input("Targa del verbale")
    data_multa = st.date_input("Data dell'infrazione")
    
    if st.button("Scarica Responsabilità"):
        st.warning(f"Modulo generato! Invio dati conducente al Comando di Forio per targa {targa_multa}.")

else:
    st.header("📊 Stato Flotta")
    st.table([{"Mezzo": "Liberty", "Stato": "Disponibile"}, {"Mezzo": "Bebe", "Stato": "Noleggiato"}])

