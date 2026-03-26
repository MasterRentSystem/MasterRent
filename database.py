# --- Database MasterRent Forio ---
flotta_motorini = [
    {"id": 1, "modello": "Liberty 125", "targa": "AB12345", "stato": "Disponibile"},
    {"id": 2, "modello": "Bebe 125", "targa": "CD67890", "stato": "Noleggiato"},
    {"id": 3, "modello": "SH 150", "targa": "EF11223", "stato": "In Manutenzione"}
]

def controlla_flotta():
    print("\n--- STATO ATTUALE FLOTTA ---")
    for moto in flotta_motorini:
        print(f"Moto: {moto['modello']} | Targa: {moto['targa']} | Stato: {moto['stato']}")

controlla_flotta()
