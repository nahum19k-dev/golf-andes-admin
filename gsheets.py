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
    datos = sheet.get_all_records(value_render_option="FORMATTED_VALUE")
    df = pd.DataFrame(datos)
    # Forzar ceros con longitud fija
    df["codigo"] = df["codigo"].astype(str).str.strip().str.zfill(5)
    df["torre"]  = df["torre"].astype(str).str.strip().str.zfill(2)
    df["dpto"]   = df["dpto"].astype(str).str.strip().str.zfill(3)
    df["dni"]    = df["dni"].astype(str).str.strip().str.zfill(8)
    # Limpiar valores "00000" o "000" que son vacíos
    df["codigo"] = df["codigo"].replace("00000", "")
    df["torre"]  = df["torre"].replace("00", "")
    df["dpto"]   = df["dpto"].replace("000", "")
    df["dni"]    = df["dni"].replace("00000000", "")
    return df
