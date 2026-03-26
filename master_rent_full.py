import datetime

# --- DATABASE FLOTTA ---
flotta = [
    {"id": 1, "modello": "Liberty 125", "targa": "EB12345", "stato": "Disponibile"},
    {"id": 2, "modello": "Bebe 125", "targa": "BX98765", "stato": "Disponibile"},
]

# --- CALCOLATORE PREZZI FORIO ---
def calcola_prezzo(giorni):
    mese = datetime.datetime.now().month
    prezzo_giornaliero = 50 if mese in [7, 8] else 30
    stagione = "ALTA STAGIONE" if mese in [7, 8] else "BASSA STAGIONE"
    return giorni * prezzo_giornaliero, stagione

# --- GENERAZIONE DOCUMENTI LEGALI ---
def genera_sistema_completo(cliente, targa, giorni):
    totale, stagione = calcola_prezzo(giorni)
    data_oggi = datetime.datetime.now().strftime("%d/%m/%Y")
    
    print("\n" + "="*45)
    print("       MASTER RENT SYSTEM - FORIO 2026       ")
    print("="*45)
    
    # 1. IL CONTRATTO (Valore Legale)
    print(f"\n[ DOCUMENTO 1: CONTRATTO DI NOLEGGIO ]")
    print(f"Data: {data_oggi} | Cliente: {cliente}")
    print(f"Mezzo: {targa} | Durata: {giorni} giorni")
    print(f"CLAUSOLA: Il cliente è responsabile per ogni sanzione.")
    
    # 2. LA FATTURA
    print(f"\n[ DOCUMENTO 2: FATTURA AUTOMATICA ]")
    print(f"Periodo: {stagione} | Totale: {totale}€")
    print(f"Stato: PRONTA PER INVIO (Fattura emessa: SI)")
    
    # 3. IL MODULO MULTE PER I VIGILI
    print(f"\n[ DOCUMENTO 3: COMUNICAZIONE VIGILI ]")
    print(f"Spett.le Comando Polizia Locale di Forio,")
    print(f"Il conducente del mezzo {targa} in data {data_oggi}")
    print(f"era il Sig. {cliente}. Si prega di notificare a lui.")
    print("="*45 + "\n")

# ESECUZIONE
genera_sistema_completo("Mario Rossi", "EB12345", 3)
