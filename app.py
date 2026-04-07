import streamlit as st
import datetime
import pandas as pd
from supabase import create_client, Client
from fpdf import FPDF
import base64
from streamlit_drawable_canvas import st_canvas
import urllib.parse
import numpy as np
import cv2

# -------------------------
# CONFIGURAZIONE PAGINA
# -------------------------

st.set_page_config(
    page_title="Battaglia Rent - Sistema Ufficiale",
    layout="centered"
)

# -------------------------
# CONNESSIONE SUPABASE
# -------------------------

url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(url, key)

# -------------------------
# LOGIN
# -------------------------

def check_password():

    if "auth" not in st.session_state:
        st.session_state.auth = False

    if not st.session_state.auth:

        st.title("🔒 Accesso Riservato")

        pwd = st.text_input(
            "Inserisci Password",
            type="password"
        )

        if pwd == st.secrets["APP_PASSWORD"]:

            st.session_state.auth = True
            st.rerun()

        elif pwd != "":

            st.error("Password errata")

        return False

    return True


if not check_password():
    st.stop()

# -------------------------
# NUMERO FATTURA
# -------------------------

def get_next_fattura():

    year = datetime.date.today().year

    try:

        res = supabase.table("contratti") \
            .select("numero_fattura") \
            .filter(
                "numero_fattura",
                "ilike",
                f"{year}-%"
            ) \
            .order(
                "numero_fattura",
                desc=True
            ) \
            .limit(1) \
            .execute()

        if not res.data:

            return f"{year}-001"

        last_num = int(
            res.data[0]["numero_fattura"]
            .split("-")[1]
        )

        return f"{year}-{str(last_num + 1).zfill(3)}"

    except:

        return f"{year}-001"

# -------------------------
# REGISTRO GIORNALIERO
# -------------------------

def aggiorna_registro(prezzo):

    oggi = str(datetime.date.today())

    try:

        res = supabase.table(
            "registro_giornaliero"
        ).select("*").eq(
            "data",
            oggi
        ).execute()

        if res.data:

            nuovo_n = res.data[0][
                "numero_noleggi"
            ] + 1

            nuovo_t = float(
                res.data[0]["totale_incasso"]
            ) + float(prezzo)

            supabase.table(
                "registro_giornaliero"
            ).update(
                {
                    "numero_noleggi": nuovo_n,
                    "totale_incasso": nuovo_t
                }
            ).eq(
                "data",
                oggi
            ).execute()

        else:

            supabase.table(
                "registro_giornaliero"
            ).insert(
                {
                    "data": oggi,
                    "numero_noleggi": 1,
                    "totale_incasso": prezzo
                }
            ).execute()

    except:

        st.error(
            "Errore aggiornamento registro"
        )

# -------------------------
# UPLOAD FOTO
# -------------------------

def upload_foto(file, targa, tipo):

    if file is None:

        return None

    try:

        ext = file.name.split(".")[-1]

        nome = (
            f"{tipo}_"
            f"{targa}_"
            f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            f".{ext}"
        )

        supabase.storage \
            .from_("documenti") \
            .upload(
                nome,
                file.getvalue()
            )

        url = supabase.storage \
            .from_("documenti") \
            .get_public_url(nome)

        return url

    except:

        st.error("Errore upload foto")

        return None

# -------------------------
# GENERAZIONE PDF
# -------------------------

def genera_pdf(d, tipo):

    pdf = FPDF()

    pdf.add_page()

    pdf.set_font(
        "Arial",
        "B",
        16
    )

    if tipo == "MULTE":

        pdf.cell(
            200,
            10,
            "DICHIARAZIONE DATI CONDUCENTE (L. 445/2000)",
            ln=True,
            align="C"
        )

        pdf.ln(10)

        pdf.set_font(
            "Arial",
            "",
            11
        )

        testo = (
            f"La sottoscritta Marianna Battaglia "
            f"dichiara che in data {d.get('inizio')} "
            f"il veicolo targa {d.get('targa')} "
            f"era affidato al Sig. "
            f"{d.get('nome')} {d.get('cognome')} "
            f"nato a {d.get('luogo_nascita')} "
            f"il {d.get('data_nascita')} "
            f"patente n. {d.get('numero_patente')}."
        )

        pdf.multi_cell(
            0,
            10,
            testo
        )

    elif tipo == "FATTURA":

        pdf.cell(
            200,
            10,
            f"RICEVUTA FISCALE N. {d.get('numero_fattura')}",
            ln=True,
            align="C"
        )

        pdf.ln(10)

        pdf.set_font(
            "Arial",
            "",
            12
        )

        pdf.cell(
            0,
            10,
            f"Cliente: {d.get('nome')} {d.get('cognome')}",
            ln=True
        )

        pdf.cell(
            0,
            10,
            f"Codice Fiscale: {d.get('codice_fiscale')}",
            ln=True
        )

        pdf.cell(
            0,
            10,
            f"Importo: Euro {d.get('prezzo')}",
            ln=True
        )

    else:

        pdf.cell(
            200,
            10,
            "CONTRATTO DI NOLEGGIO VEICOLO",
            ln=True,
            align="C"
        )

        pdf.ln(10)

        pdf.set_font(
            "Arial",
            "",
            11
        )

        testo = (
            f"Locatario: {d.get('nome')} {d.get('cognome')}\n"
            f"Targa: {d.get('targa')}\n"
            f"Dal: {d.get('inizio')} "
            f"Al: {d.get('fine')}\n"
            f"Prezzo: Euro {d.get('prezzo')}"
        )

        pdf.multi_cell(
            0,
            10,
            testo
        )

    return pdf.output(
        dest="S"
    ).encode(
        "latin-1",
        "ignore"
    )

# -------------------------
# MENU
# -------------------------

menu = st.sidebar.radio(

    "Menu",

    [
        "Nuovo Noleggio",
        "Archivio Storico",
        "Registro Giornaliero",
        "Backup"
    ]

)

# -------------------------
# NUOVO NOLEGGIO
# -------------------------

if menu == "Nuovo Noleggio":

    st.header("🛵 Nuovo Noleggio")

    with st.form(
        "form_noleggio",
        clear_on_submit=True
    ):

        nome = st.text_input("Nome")

        cognome = st.text_input("Cognome")

        telefono = st.text_input("Telefono")

        targa = st.text_input("Targa")

        inizio = st.date_input("Inizio")

        fine = st.date_input("Fine")

        prezzo = st.number_input(
            "Prezzo",
            min_value=0.0
        )

        deposito = st.number_input(
            "Deposito",
            min_value=0.0
        )

        st.write("Firma Cliente")

        canvas = st_canvas(
            height=150,
            stroke_width=2
        )

        submit = st.form_submit_button(
            "SALVA"
        )

        if submit:

            if not nome:

                st.error("Nome obbligatorio")

                st.stop()

            if not targa:

                st.error("Targa obbligatoria")

                st.stop()

            if canvas.image_data is None:

                st.error("Firma obbligatoria")

                st.stop()

            numero_fattura = get_next_fattura()

            try:

                img = canvas.image_data.astype(
                    np.uint8
                )

                _, buffer = cv2.imencode(
                    ".png",
                    img
                )

                firma_b64 = (
                    "data:image/png;base64,"
                    + base64.b64encode(
                        buffer
                    ).decode()
                )

                dati = {

                    "nome": nome,
                    "cognome": cognome,
                    "telefono": telefono,
                    "targa": targa,
                    "inizio": str(inizio),
                    "fine": str(fine),
                    "prezzo": prezzo,
                    "deposito": deposito,
                    "numero_fattura": numero_fattura,
                    "firma": firma_b64

                }

                supabase.table(
                    "contratti"
                ).insert(
                    dati
                ).execute()

                aggiorna_registro(
                    prezzo
                )

                st.success(
                    f"Noleggio salvato - "
                    f"Fattura {numero_fattura}"
                )

                if telefono:

                    msg = urllib.parse.quote(
                        f"Buongiorno {nome}, "
                        f"Battaglia Rent.\n"
                        f"Scooter {targa}\n"
                        f"Totale €{prezzo}"
                    )

                    st.markdown(
                        f"[📲 Invia WhatsApp]"
                        f"(https://wa.me/{telefono.replace(' ','')}?text={msg})"
                    )

            except:

                st.error(
                    "Errore salvataggio"
                )

# -------------------------
# ARCHIVIO
# -------------------------

elif menu == "Archivio Storico":

    st.header("📂 Archivio")

    cerca = st.text_input(
        "Cerca"
    ).lower()

    res = supabase.table(
        "contratti"
    ).select("*").order(
        "id",
        desc=True
    ).execute()

    for c in res.data:

        testo = (
            f"{c.get('targa')} "
            f"{c.get('cognome')} "
            f"{c.get('numero_fattura')}"
        ).lower()

        if cerca in testo:

            with st.expander(

                f"{c.get('numero_fattura')} "
                f"{c.get('targa')}"

            ):

                st.download_button(
                    "📜 Contratto",
                    genera_pdf(
                        c,
                        "CONTRATTO"
                    ),
                    file_name="contratto.pdf"
                )

                st.download_button(
                    "💰 Ricevuta",
                    genera_pdf(
                        c,
                        "FATTURA"
                    ),
                    file_name="ricevuta.pdf"
                )

                st.download_button(
                    "🚨 Multe",
                    genera_pdf(
                        c,
                        "MULTE"
                    ),
                    file_name="multe.pdf"
                )

# -------------------------
# REGISTRO
# -------------------------

elif menu == "Registro Giornaliero":

    st.header("📊 Registro")

    res = supabase.table(
        "registro_giornaliero"
    ).select("*").order(
        "data",
        desc=True
    ).execute()

    df = pd.DataFrame(
        res.data
    )

    if not df.empty:

        st.table(df)

# -------------------------
# BACKUP
# -------------------------

elif menu == "Backup":

    st.header("💾 Backup")

    if st.button(
        "Genera Backup"
    ):

        res = supabase.table(
            "contratti"
        ).select("*").execute()

        df = pd.DataFrame(
            res.data
        )

        csv = df.to_csv(
            index=False
        ).encode(
            "utf-8"
        )

        nome = (
            f"backup_"
            f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            ".csv"
        )

        supabase.storage \
            .from_("backup") \
            .upload(
                nome,
                csv
            )

        st.success(
            "Backup completato"
        )
