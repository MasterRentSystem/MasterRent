# --- MASTER RENT SYSTEM: CORE BRIDGE ---
# Questo file collega il tuo iMac alla cassaforte dei dati (Supabase)

import datetime

def crea_contratto_legale(targa, cliente, giorni, prezzo_totale):
    data_oggi = datetime.datetime.now().strftime("%Y-%m-%d")
    data_fine = (datetime.datetime.now() + datetime.timedelta(days=giorni)).strftime("%Y-%m-%d")
    
    # Struttura dati per il Database (Supabase)
    nuovo_contratto = {
        "targa": targa,
        "cliente": cliente,
        "data_inizio": data_oggi,
        "data_fine": data_fine,
        "prezzo": prezzo_totale,
        "fattura_emessa": False  # Il tasto ON/OFF che abbiamo deciso!
    }
    
    print(f"\n[OK] Contratto creato per {cliente} (Targa: {targa})")
    print(f"[INFO] Scadenza il: {data_fine}")
    print(f"[STATUS] Fattura pronta per invio: {nuovo_contratto['fattura_emessa']}")
    return nuovo_contratto

# TEST OPERATIVO
contratto_test = crea_contratto_legale("EB12345", "Cliente Prova Ischia", 3, 150.0)
