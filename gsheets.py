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
    
    # ✅ FIX: astype(str) antes de zfill
    df["codigo"] = df["codigo"].astype(str).str.strip().str.zfill(5)
    df["torre"]  = df["torre"].astype(str).str.strip().str.zfill(2)
    df["dpto"]   = df["dpto"].astype(str).str.strip().str.zfill(3)
    df["dni"]    = df["dni"].astype(str).str.strip().str.zfill(8)
    
    # ✅ Limpiar filas vacías (reemplaza zeros puros por string vacío)
    df["codigo"] = df["codigo"].apply(lambda x: "" if x == "00000" else x)
    df["torre"]  = df["torre"].apply(lambda x: "" if x == "00" else x)
    df["dpto"]   = df["dpto"].apply(lambda x: "" if x == "000" else x)
    df["dni"]    = df["dni"].apply(lambda x: "" if x == "00000000" else x)
    
    return df
