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
    todos = sheet.get_all_values()
    if len(todos) < 2:
        return pd.DataFrame()
    
    headers = todos[0]
    filas = todos[1:]
    df = pd.DataFrame(filas, columns=headers)
    
    # Limpia decimales y agrega ceros
    def fix_zeros(col, length):
        return (col.astype(str)
                   .str.strip()
                   .str.replace(r"\.0$", "", regex=True)
                   .str.replace(r"[^0-9]", "", regex=True)
                   .str.zfill(length))
    
    df["codigo"] = fix_zeros(df["codigo"], 5)
    df["torre"]  = fix_zeros(df["torre"],  2)
    df["dpto"]   = fix_zeros(df["dpto"],   3)
    df["dni"]    = fix_zeros(df["dni"],    8)
    
    # Limpiar vacíos
    df["codigo"] = df["codigo"].apply(lambda x: "" if x == "00000" else x)
    df["torre"]  = df["torre"].apply(lambda x: "" if x == "00" else x)
    df["dpto"]   = df["dpto"].apply(lambda x: "" if x == "000" else x)
    df["dni"]    = df["dni"].apply(lambda x: "" if x == "00000000" else x)
    
    return df
