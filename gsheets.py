import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# ------------------- Conexión básica a Sheets -------------------
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

@st.cache_resource
def get_spreadsheet():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )
    client = gspread.authorize(creds)
    sheet_id = st.secrets["sheets"]["spreadsheet_id"]
    return client.open_by_key(sheet_id)

# ------------------- Propietarios -------------------
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

# ------------------- Programación (Determinación de cuotas) -------------------
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
    # Título
    titulo = f"DETERMINACION DE CUOTA MES DE {mes.upper()}-{anio} - CONJUNTO RESIDENCIAL GOLF LOS ANDES I"
    nueva_hoja.update("A1", [[titulo]])
    nueva_hoja.format("A1", {
        "textFormat": {"bold": True, "fontSize": 14},
        "horizontalAlignment": "CENTER"
    })
    nueva_hoja.merge_cells("A1:AG1")
    nueva_hoja.update("A2", [[""]])
    # Encabezados
    encabezados = df.columns.tolist()
    nueva_hoja.update("A3", [encabezados])
    # Datos (convertir fechas a string)
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

# ------------------- Pagos -------------------
def guardar_pagos(df: pd.DataFrame, mes: str, anio: int):
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
    spreadsheet = get_spreadsheet()
    hojas = spreadsheet.worksheets()
    nombres = [hoja.title for hoja in hojas if hoja.title.startswith("Pagos")]
    nombres.sort(reverse=True)
    return nombres

def leer_hoja_pagos(nombre_hoja):
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.worksheet(nombre_hoja)
    datos = worksheet.get_all_values()
    if len(datos) < 2:
        return pd.DataFrame()
    headers = datos[0]
    filas = datos[1:]
    df = pd.DataFrame(filas, columns=headers)
    return df

# ------------------- Medidores -------------------
def guardar_medidor(df: pd.DataFrame, mes: str, anio: int):
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
    spreadsheet = get_spreadsheet()
    hojas = spreadsheet.worksheets()
    nombres = [hoja.title for hoja in hojas if hoja.title.startswith("Medidor")]
    nombres.sort(reverse=True)
    return nombres

def leer_hoja_medidor(nombre_hoja):
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.worksheet(nombre_hoja)
    datos = worksheet.get_all_values()
    if len(datos) < 2:
        return pd.DataFrame()
    headers = datos[0]
    filas = datos[1:]
    df = pd.DataFrame(filas, columns=headers)
    return df

# ------------------- Amortización -------------------
def guardar_amortizacion(df: pd.DataFrame, mes: str, anio: int):
    nombre_base = f"Amortización {mes} {anio}"
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

def listar_hojas_amortizacion():
    spreadsheet = get_spreadsheet()
    hojas = spreadsheet.worksheets()
    nombres = [hoja.title for hoja in hojas if hoja.title.startswith("Amortización")]
    nombres.sort(reverse=True)
    return nombres

def leer_hoja_amortizacion(nombre_hoja):
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.worksheet(nombre_hoja)
    datos = worksheet.get_all_values()
    if len(datos) < 2:
        return pd.DataFrame()
    headers = datos[0]
    filas = datos[1:]
    df = pd.DataFrame(filas, columns=headers)
    return df
# ====================== FUNCIONES PARA DEUDA INICIAL ======================
def guardar_deuda_inicial(df: pd.DataFrame, anio: int):
    nombre_base = f"Deuda Inicial {anio}"
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

def listar_hojas_deuda():
    spreadsheet = get_spreadsheet()
    hojas = spreadsheet.worksheets()
    nombres = [hoja.title for hoja in hojas if hoja.title.startswith("Deuda Inicial")]
    nombres.sort(reverse=True)
    return nombres

def leer_hoja_deuda(nombre_hoja):
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.worksheet(nombre_hoja)
    datos = worksheet.get_all_values()
    if len(datos) < 2:
        return pd.DataFrame()
    headers = datos[0]
    filas = datos[1:]
    df = pd.DataFrame(filas, columns=headers)
    return df
# ====================== FUNCIONES PARA OPERACIONES ======================
def leer_programacion(mes: str, anio: int):
    """Lee la hoja de programación (determinación de cuotas) para el mes y año dados.
    Retorna DataFrame con columnas: torre, departamento, total_programacion (columna que se detecta automáticamente)"""
    nombre_hoja = f"Prog_{mes.upper()}_{anio}"
    spreadsheet = get_spreadsheet()
    try:
        worksheet = spreadsheet.worksheet(nombre_hoja)
    except gspread.exceptions.WorksheetNotFound:
        return pd.DataFrame()
    datos = worksheet.get_all_values()
    if len(datos) < 4:  # hay título, fila vacía, encabezados, datos
        return pd.DataFrame()
    headers = datos[3]  # después del título y fila vacía
    filas = datos[4:]
    df = pd.DataFrame(filas, columns=headers)
    # Limpiar nombres de columnas
    df.columns = df.columns.str.strip().str.replace('\n', ' ')
    # Buscar la columna que contiene el monto total a pagar
    col_monto = None
    for col in df.columns:
        if 'total' in col.lower() or 'cuota' in col.lower() or 'pagar' in col.lower():
            col_monto = col
            break
    if col_monto is None:
        return pd.DataFrame()
    # Renombrar columnas clave
    rename_map = {}
    for col in df.columns:
        if 'torre' in col.lower():
            rename_map[col] = 'torre'
        elif 'departamento' in col.lower() or 'dpto' in col.lower():
            rename_map[col] = 'departamento'
        elif col == col_monto:
            rename_map[col] = 'total_programacion'
    df = df.rename(columns=rename_map)
    # Convertir a numérico
    if 'total_programacion' in df.columns:
        df['total_programacion'] = pd.to_numeric(df['total_programacion'], errors='coerce')
    if 'torre' in df.columns:
        df['torre'] = pd.to_numeric(df['torre'], errors='coerce')
    if 'departamento' in df.columns:
        df['departamento'] = pd.to_numeric(df['departamento'], errors='coerce')
    return df

def leer_amortizacion(mes: str, anio: int):
    """Lee la hoja de amortización para el mes y año dados."""
    nombre_hoja = f"Amortización {mes} {anio}"
    spreadsheet = get_spreadsheet()
    try:
        worksheet = spreadsheet.worksheet(nombre_hoja)
    except gspread.exceptions.WorksheetNotFound:
        return pd.DataFrame()
    datos = worksheet.get_all_values()
    if len(datos) < 2:
        return pd.DataFrame()
    headers = datos[0]
    filas = datos[1:]
    df = pd.DataFrame(filas, columns=headers)
    # Limpiar nombres
    df.columns = df.columns.str.strip().str.replace('\n', ' ')
    # Renombrar columnas
    rename_map = {}
    for col in df.columns:
        if 'torre' in col.lower():
            rename_map[col] = 'torre'
        elif 'dpto' in col.lower() or 'departamento' in col.lower():
            rename_map[col] = 'departamento'
        elif 'amortizacion' in col.lower():
            rename_map[col] = 'amortizacion'
    df = df.rename(columns=rename_map)
    if 'torre' in df.columns:
        df['torre'] = pd.to_numeric(df['torre'], errors='coerce')
    if 'departamento' in df.columns:
        df['departamento'] = pd.to_numeric(df['departamento'], errors='coerce')
    if 'amortizacion' in df.columns:
        df['amortizacion'] = pd.to_numeric(df['amortizacion'], errors='coerce')
    return df

def leer_medidores(mes: str, anio: int):
    """Lee la hoja de medidores para el mes y año dados."""
    nombre_hoja = f"Medidor {mes} {anio}"
    spreadsheet = get_spreadsheet()
    try:
        worksheet = spreadsheet.worksheet(nombre_hoja)
    except gspread.exceptions.WorksheetNotFound:
        return pd.DataFrame()
    datos = worksheet.get_all_values()
    if len(datos) < 2:
        return pd.DataFrame()
    headers = datos[0]
    filas = datos[1:]
    df = pd.DataFrame(filas, columns=headers)
    df.columns = df.columns.str.strip().str.replace('\n', ' ')
    # Renombrar
    rename_map = {}
    for col in df.columns:
        if 'torre' in col.lower():
            rename_map[col] = 'torre'
        elif 'departamento' in col.lower():
            rename_map[col] = 'departamento'
        elif 'monto' in col.lower():
            rename_map[col] = 'monto'
    df = df.rename(columns=rename_map)
    if 'torre' in df.columns:
        df['torre'] = pd.to_numeric(df['torre'], errors='coerce')
    if 'departamento' in df.columns:
        df['departamento'] = pd.to_numeric(df['departamento'], errors='coerce')
    if 'monto' in df.columns:
        df['monto'] = pd.to_numeric(df['monto'], errors='coerce')
    return df

def leer_pagos_mes(mes: str, anio: int):
    """Lee la hoja de pagos para el mes y año dados y devuelve cada transacción individual."""
    nombre_hoja = f"Pagos {mes} {anio}"
    spreadsheet = get_spreadsheet()
    try:
        worksheet = spreadsheet.worksheet(nombre_hoja)
    except gspread.exceptions.WorksheetNotFound:
        return pd.DataFrame()
    datos = worksheet.get_all_values()
    if len(datos) < 2:
        return pd.DataFrame()
    headers = datos[0]
    filas = datos[1:]
    df = pd.DataFrame(filas, columns=headers)
    df.columns = df.columns.str.strip().str.replace('\n', ' ')
    # Renombrar columnas clave
    rename_map = {}
    for col in df.columns:
        if 'fecha' in col.lower():
            rename_map[col] = 'fecha'
        elif 'torre' in col.lower():
            rename_map[col] = 'torre'
        elif 'departamento' in col.lower() or 'dpto' in col.lower():
            rename_map[col] = 'departamento'
        elif 'ingresos' in col.lower() or 'pagos' in col.lower():
            rename_map[col] = 'ingresos'
        elif 'n_operacion' in col.lower() or 'operación' in col.lower():
            rename_map[col] = 'n_operacion'
    df = df.rename(columns=rename_map)
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
    if 'torre' in df.columns:
        df['torre'] = pd.to_numeric(df['torre'], errors='coerce')
    if 'departamento' in df.columns:
        df['departamento'] = pd.to_numeric(df['departamento'], errors='coerce')
    if 'ingresos' in df.columns:
        df['ingresos'] = pd.to_numeric(df['ingresos'], errors='coerce')
    # Ordenar por fecha
    df = df.sort_values('fecha')
    return df
