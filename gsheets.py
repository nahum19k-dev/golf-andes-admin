import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def get_sheet(nombre_hoja):
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )
    client = gspread.authorize(creds)
    sheet_id = st.secrets["sheets"]["spreadsheet_id"]
    spreadsheet = client.open_by_key(sheet_id)
    return spreadsheet.worksheet(nombre_hoja)

def leer_propietarios():
    sheet = get_sheet("Propietarios")
    # Leer como texto puro sin convertir tipos
    todos = sheet.get_all_values()
    if len(todos) < 2:
        return pd.DataFrame()
    headers = todos[0]
    filas = todos[1:]
    df = pd.DataFrame(filas, columns=headers)
    # Forzar ceros
    df["codigo"] = df["codigo"].str.zfill(5)
    df["torre"]  = df["torre"].str.zfill(2)
    df["dpto"]   = df["dpto"].str.zfill(3)
    df["dni"]    = df["dni"].str.zfill(8)
    # Limpiar vacíos
    df["codigo"] = df["codigo"].replace("00000", "")
    df["torre"]  = df["torre"].replace("00", "")
    df["dpto"]   = df["dpto"].replace("000", "")
    df["dni"]    = df["dni"].replace("00000000", "")
    return df
