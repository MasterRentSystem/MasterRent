import datetime

# 1. LA TUA FLOTTA (Il tuo garage virtuale)
flotta = [
    {"id": 1, "modello": "Liberty 125", "targa": "EB12345", "stato": "Disponibile"},
    {"id": 2, "modello": "SH 150", "targa": "BX98765", "stato": "Disponibile"},
    {"id": 3, "modello": "Bebe 125", "targa": "AA00000", "stato": "Noleggiato"},
]

# 2. IL CALCOLATORE DI PREZZI (Alta e Bassa Stagione Forio)
def calcola_prezzo(giorni):
    mese_attuale = datetime.datetime.now().month
    # Se siamo a Luglio (7) o Agosto (8) è ALTA STAGIONE
    if mese_attuale in [7, 8]:
        prezzo_giornaliero = 50  # Prezzo Agosto
        stagione = "ALTA STAGIONE"
    else:
        prezzo_giornaliero = 30  # Prezzo Bassa Stagione
        stagione = "BASSA STAGIONE"
    
    totale = giorni * prezzo_giornaliero
    return totale, stagione

# 3. L'INTERFACCIA DEL TUO GESTIONALE
print("\n****************")
print("* MASTER RENT SYSTEM - FORIO 2026    *")
print("**************")

print("\n--- STATO FLOTTA ---")
for moto in flotta:
    print(f"[{moto['id']}] {moto['modello']} ({moto['targa']}) - STATO: {moto['stato']}")

print("\n--- SIMULATORE PREVENTIVO ---")
giorni_noleggio = 3  # Esempio: il cliente vuole la moto per 3 giorni
totale, stagione = calcola_prezzo(giorni_noleggio)

print(f"Periodo: {stagione}")
print(f"Preventivo per {giorni_noleggio} giorni: {totale}€")
print("**************")
