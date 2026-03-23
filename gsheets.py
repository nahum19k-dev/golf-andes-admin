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
    return df

def subir_excel_a_sheets(ruta_excel):
    st.cache_resource.clear()
    df = pd.read_excel(ruta_excel, dtype=str)
    df = df.fillna("")
    sheet = get_sheet("Propietarios")
    sheet.clear()
    sheet.update(
        [df.columns.tolist()] + df.values.tolist(),
        value_input_option="RAW"
    )
    return len(df)

# ====================== FUNCIONES PARA PROGRAMACIÓN MENSUAL ======================
@st.cache_resource
def get_spreadsheet():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )
    client = gspread.authorize(creds)
    sheet_id = st.secrets["sheets"]["spreadsheet_id"]
    return client.open_by_key(sheet_id)

def existe_programacion(periodo_key: str) -> bool:
    nombre_hoja = f"Prog_{periodo_key.upper()}"
    spreadsheet = get_spreadsheet()
    try:
        spreadsheet.worksheet(nombre_hoja)
        return True
    except gspread.exceptions.WorksheetNotFound:
        return False

def crear_y_guardar_programacion(df: pd.DataFrame, periodo_key: str, mes: str, anio: int):
    nombre_hoja = f"Prog_{periodo_key.upper()}"
    if existe_programacion(periodo_key):
        raise ValueError(f"La hoja '{nombre_hoja}' ya existe. No se puede crear duplicado.")
    spreadsheet = get_spreadsheet()
    nueva_hoja = spreadsheet.add_worksheet(
        title=nombre_hoja,
        rows=700,
        cols=max(40, len(df.columns) + 10)
    )
    titulo = f"DETERMINACION DE CUOTA MES DE {mes.upper()}-{anio} - CONJUNTO RESIDENCIAL GOLF LOS ANDES I"
    nueva_hoja.update("A1", [[titulo]])
    nueva_hoja.format("A1", {
        "textFormat": {"bold": True, "fontSize": 14},
        "horizontalAlignment": "CENTER"
    })
    nueva_hoja.merge_cells("A1:AG1")
    nueva_hoja.update("A2", [[""]])
    encabezados = df.columns.tolist()
    nueva_hoja.update("A3", [encabezados])
    df_para_guardar = df.copy()
    for col in df_para_guardar.columns:
        if pd.api.types.is_datetime64_any_dtype(df_para_guardar[col]):
            df_para_guardar[col] = df_para_guardar[col].dt.strftime('%Y-%m-%d')
        elif df_para_guardar[col].dtype == 'object':
            df_para_guardar[col] = df_para_guardar[col].apply(
                lambda x: x.strftime('%Y-%m-%d') if isinstance(x, pd.Timestamp) else x
            )
    df_para_guardar = df_para_guardar.astype(str).fillna("")
    datos = df_para_guardar.values.tolist()
    if datos:
        nueva_hoja.update("A4", datos)
    st.cache_resource.clear()
    return nombre_hoja

# ====================== FUNCIONES PARA PAGOS ======================
def guardar_pagos(df: pd.DataFrame, mes: str, anio: int):
    """
    Guarda los pagos en una hoja con nombre amigable (Pagos {mes} {anio}).
    Si ya existe, agrega sufijo (2), (3), etc.
    """
    nombre_base = f"Pagos {mes} {anio}"
    spreadsheet = get_spreadsheet()
    nombre_hoja = nombre_base
    contador = 2
    while True:
        try:
            spreadsheet.worksheet(nombre_hoja)
            nombre_hoja = f"{nombre_base} ({contador})"
            contador += 1
        except gspread.exceptions.WorksheetNotFound:
            break
    nueva_hoja = spreadsheet.add_worksheet(title=nombre_hoja, rows=df.shape[0]+1, cols=df.shape[1])
    df_para_guardar = df.copy()
    for col in df_para_guardar.columns:
        if pd.api.types.is_datetime64_any_dtype(df_para_guardar[col]):
            df_para_guardar[col] = df_para_guardar[col].dt.strftime('%Y-%m-%d')
        elif df_para_guardar[col].dtype == 'object':
            df_para_guardar[col] = df_para_guardar[col].apply(
                lambda x: x.strftime('%Y-%m-%d') if isinstance(x, pd.Timestamp) else x
            )
    df_para_guardar = df_para_guardar.astype(str).fillna("")
    datos = [df_para_guardar.columns.tolist()] + df_para_guardar.values.tolist()
    nueva_hoja.update(datos, value_input_option="RAW")
    return nombre_hoja

def listar_hojas_pagos():
    """Devuelve una lista de nombres de hojas que empiezan con 'Pagos'"""
    spreadsheet = get_spreadsheet()
    hojas = spreadsheet.worksheets()
    nombres = [hoja.title for hoja in hojas if hoja.title.startswith("Pagos")]
    nombres.sort(reverse=True)
    return nombres

def leer_hoja_pagos(nombre_hoja):
    """Lee una hoja específica y devuelve un DataFrame con los datos"""
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.worksheet(nombre_hoja)
    datos = worksheet.get_all_values()
    if len(datos) < 2:
        return pd.DataFrame()
    headers = datos[0]
    filas = datos[1:]
    df = pd.DataFrame(filas, columns=headers)
    return df
# ====================== FUNCIONES PARA MEDIDORES ======================
def guardar_medidor(df: pd.DataFrame, mes: str, anio: int):
    """Guarda medidores con nombre amigable 'Medidor {mes} {anio}'"""
    nombre_base = f"Medidor {mes} {anio}"
    spreadsheet = get_spreadsheet()
    nombre_hoja = nombre_base
    contador = 2
    while True:
        try:
            spreadsheet.worksheet(nombre_hoja)
            nombre_hoja = f"{nombre_base} ({contador})"
            contador += 1
        except gspread.exceptions.WorksheetNotFound:
            break
    nueva_hoja = spreadsheet.add_worksheet(title=nombre_hoja, rows=df.shape[0]+1, cols=df.shape[1])
    df_para_guardar = df.copy()
    for col in df_para_guardar.columns:
        if pd.api.types.is_datetime64_any_dtype(df_para_guardar[col]):
            df_para_guardar[col] = df_para_guardar[col].dt.strftime('%Y-%m-%d')
        elif df_para_guardar[col].dtype == 'object':
            df_para_guardar[col] = df_para_guardar[col].apply(
                lambda x: x.strftime('%Y-%m-%d') if isinstance(x, pd.Timestamp) else x
            )
    df_para_guardar = df_para_guardar.astype(str).fillna("")
    datos = [df_para_guardar.columns.tolist()] + df_para_guardar.values.tolist()
    nueva_hoja.update(datos, value_input_option="RAW")
    return nombre_hoja

def listar_hojas_medidor():
    """Devuelve lista de hojas que empiezan con 'Medidor'"""
    spreadsheet = get_spreadsheet()
    hojas = spreadsheet.worksheets()
    nombres = [hoja.title for hoja in hojas if hoja.title.startswith("Medidor")]
    nombres.sort(reverse=True)
    return nombres

def leer_hoja_medidor(nombre_hoja):
    """Lee una hoja de medidor y devuelve DataFrame"""
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.worksheet(nombre_hoja)
    datos = worksheet.get_all_values()
    if len(datos) < 2:
        return pd.DataFrame()
    headers = datos[0]
    filas = datos[1:]
    df = pd.DataFrame(filas, columns=headers)
    return df
