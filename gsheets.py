import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

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
    import pandas as pd
    df = pd.DataFrame(datos)
    # Forzar texto con ceros
    for col in ["codigo", "torre", "dpto", "dni"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    return df
