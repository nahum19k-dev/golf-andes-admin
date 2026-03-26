import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import numpy as np

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

# ------------------- Programación -------------------
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

def leer_pagos_mes(mes: str, anio: int):
    """
    Lee la hoja de pagos y devuelve fecha, torre, departamento, n_operacion,
    mantenimiento, amortizacion, medidor e ingresos (suma de los tres conceptos).
    """
    nombre_base = f"Pagos {mes} {anio}"
    spreadsheet = get_spreadsheet()
    hojas = spreadsheet.worksheets()
    nombres_hojas = [hoja.title for hoja in hojas]
    coincidencias = [h for h in nombres_hojas if h.startswith(nombre_base)]
    if not coincidencias:
        return pd.DataFrame()
    nombre_hoja = coincidencias[0]
    worksheet = spreadsheet.worksheet(nombre_hoja)
    datos = worksheet.get_all_values()
    if len(datos) < 2:
        return pd.DataFrame()
    headers = datos[0]
    filas = datos[1:]
    df = pd.DataFrame(filas, columns=headers)
    df.columns = df.columns.str.strip().str.replace('\n', ' ')

    # Mapeo flexible
    col_fecha = next((c for c in df.columns if 'fecha' in c.lower()), None)
    col_torre = next((c for c in df.columns if 'torre' in c.lower()), None)
    col_dpto = next((c for c in df.columns if 'dpto' in c.lower() or 'departamento' in c.lower()), None)
    col_oper = next((c for c in df.columns if 'operación' in c.lower() or 'n_operacion' in c.lower()), None)
    col_mant = next((c for c in df.columns if 'mantenimiento' in c.lower()), None)
    col_amort = next((c for c in df.columns if 'amortizacion' in c.lower()), None)
    col_med = next((c for c in df.columns if 'medidor' in c.lower()), None)

    if not (col_fecha and col_torre and col_dpto):
        return pd.DataFrame()

    df_out = pd.DataFrame()
    df_out['fecha'] = pd.to_datetime(df[col_fecha], errors='coerce')
    df_out['torre'] = pd.to_numeric(df[col_torre], errors='coerce')
    df_out['departamento'] = pd.to_numeric(df[col_dpto], errors='coerce')
    df_out['n_operacion'] = df[col_oper].astype(str) if col_oper else ''
    df_out['mantenimiento'] = pd.to_numeric(df[col_mant], errors='coerce').fillna(0) if col_mant else 0
    df_out['amortizacion'] = pd.to_numeric(df[col_amort], errors='coerce').fillna(0) if col_amort else 0
    df_out['medidor'] = pd.to_numeric(df[col_med], errors='coerce').fillna(0) if col_med else 0
    df_out['ingresos'] = df_out['mantenimiento'] + df_out['amortizacion'] + df_out['medidor']

    df_out = df_out.sort_values('fecha')
    return df_out
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

# ------------------- Deuda Inicial -------------------
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
    return df

# ====================== FUNCIONES DE LECTURA PARA OPERACIONES ======================
def leer_programacion(mes: str, anio: int):
    nombre_hoja = f"Prog_{mes.upper()}_{anio}"
    spreadsheet = get_spreadsheet()
    try:
        worksheet = spreadsheet.worksheet(nombre_hoja)
    except gspread.exceptions.WorksheetNotFound:
        return pd.DataFrame()
    datos = worksheet.get_all_values()
    if len(datos) < 4:
        return pd.DataFrame()
    headers = datos[2]
    filas = datos[3:]
    df = pd.DataFrame(filas, columns=headers)
    df.columns = df.columns.str.strip().str.replace('\n', ' ')

    # 1. Buscar exactamente la columna "Torre"
    col_torre = None
    for col in df.columns:
        if col.lower() == 'torre':
            col_torre = col
            break
    if col_torre is None:
        for col in df.columns:
            if 'torre' in col.lower():
                col_torre = col
                break
        if col_torre is None:
            return pd.DataFrame()

    # 2. Buscar exactamente la columna "Departamento"
    col_dpto = None
    for col in df.columns:
        if col.lower() == 'departamento':
            col_dpto = col
            break
    if col_dpto is None:
        for col in df.columns:
            if 'departamento' in col.lower() or 'dpto' in col.lower():
                col_dpto = col
                break
        if col_dpto is None:
            return pd.DataFrame()

    # 3. Buscar la columna de total (mantenimiento)
    col_total = None
    # Primero buscar exactamente "Mantenimiento"
    for col in df.columns:
        if col.lower() == 'mantenimiento':
            col_total = col
            break
    if col_total is None:
        # Si no, buscar cualquier columna que contenga "total", "cuota", "pagar"
        for col in df.columns:
            col_low = col.lower()
            if 'total' in col_low or 'cuota' in col_low or 'pagar' in col_low:
                col_total = col
                break
    if col_total is None:
        return pd.DataFrame()

    # Crear DataFrame con las tres columnas
    df_out = df[[col_torre, col_dpto, col_total]].copy()
    df_out.columns = ['torre', 'departamento', 'Mantenimiento']

    # Convertir a numérico
    df_out['torre'] = pd.to_numeric(df_out['torre'], errors='coerce')
    df_out['departamento'] = pd.to_numeric(df_out['departamento'], errors='coerce')
    df_out['Mantenimiento'] = pd.to_numeric(df_out['Mantenimiento'], errors='coerce')

    # Eliminar filas donde torre o departamento sean NaN (no numéricos)
    df_out = df_out.dropna(subset=['torre', 'departamento'])

    # Convertir torre y departamento a enteros nullable para que coincidan con los propietarios
    df_out['torre'] = df_out['torre'].astype('Int64')
    df_out['departamento'] = df_out['departamento'].astype('Int64')

    return df_out

def leer_amortizacion(mes: str, anio: int):
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
    df.columns = df.columns.str.strip().str.replace('\n', ' ')
    col_torre = None
    col_dpto = None
    col_amort = None
    for col in df.columns:
        col_low = col.lower()
        if 'torre' in col_low:
            col_torre = col
        elif 'dpto' in col_low or 'departamento' in col_low:
            col_dpto = col
        elif 'amortizacion' in col_low:
            col_amort = col
    if not (col_torre and col_dpto and col_amort):
        return pd.DataFrame()
    df_out = pd.DataFrame()
    df_out['torre'] = pd.to_numeric(df[col_torre], errors='coerce')
    df_out['departamento'] = pd.to_numeric(df[col_dpto], errors='coerce')
    df_out['amortizacion'] = pd.to_numeric(df[col_amort], errors='coerce')
    return df_out

def leer_medidores(mes: str, anio: int):
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
    col_torre = None
    col_dpto = None
    col_monto = None
    for col in df.columns:
        col_low = col.lower()
        if 'torre' in col_low:
            col_torre = col
        elif 'dpto' in col_low or 'departamento' in col_low:
            col_dpto = col
        elif 'monto' in col_low:
            col_monto = col
    if not (col_torre and col_dpto and col_monto):
        return pd.DataFrame()
    df_out = pd.DataFrame()
    df_out['torre'] = pd.to_numeric(df[col_torre], errors='coerce')
    df_out['departamento'] = pd.to_numeric(df[col_dpto], errors='coerce')
    df_out['monto'] = pd.to_numeric(df[col_monto], errors='coerce')
    return df_out

def leer_deuda_inicial(anio: int):
    nombre_hoja = f"Deuda Inicial {anio}"
    df = leer_hoja_deuda(nombre_hoja)
    if df.empty and anio > 2020:
        nombre_hoja_anterior = f"Deuda Inicial {anio-1}"
        df = leer_hoja_deuda(nombre_hoja_anterior)
        if not df.empty:
            st.info(f"Usando deuda del año anterior ({anio-1}) porque no se encontró para {anio}.")
    return df

# ====================== FUNCIONES PARA VISUALIZAR PROGRAMACIÓN ======================
def listar_hojas_programacion():
    spreadsheet = get_spreadsheet()
    hojas = spreadsheet.worksheets()
    nombres = [hoja.title for hoja in hojas if hoja.title.startswith("Prog_")]
    nombres.sort(reverse=True)
    return nombres

def leer_hoja_programacion(nombre_hoja):
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.worksheet(nombre_hoja)
    datos = worksheet.get_all_values()
    if len(datos) < 4:
        return pd.DataFrame()
    headers = datos[2]
    filas = datos[3:]
    filas = [f for f in filas if any(cell for cell in f)]
    if not filas:
        return pd.DataFrame()
    df = pd.DataFrame(filas, columns=headers)
    df.columns = df.columns.str.strip().str.replace('\n', ' ').str.replace('\r', '')
    col_torre = None
    for col in df.columns:
        if col.lower() == 'torre':
            col_torre = col
            break
    if col_torre is None:
        for col in df.columns:
            if col.lower() in ['torre', 'edificio']:
                col_torre = col
                break
    if col_torre is None:
        return pd.DataFrame()
    col_dpto = None
    for col in df.columns:
        if col.lower() in ['departamento', 'dpto', 'n°dpto']:
            col_dpto = col
            break
    if col_dpto is None:
        return pd.DataFrame()
    col_monto = None
    for col in df.columns:
        if col.lower() == 'mantenimiento':
            col_monto = col
            break
    if col_monto is None:
        for col in df.columns:
            if 'total' in col.lower() or 'cuota' in col.lower() or 'pagar' in col.lower():
                col_monto = col
                break
    if col_monto is None:
        return pd.DataFrame()
    df_out = df[[col_torre, col_dpto, col_monto]].copy()
    df_out.columns = ['torre', 'departamento', 'Mantenimiento']
    def clean_number(x):
        if pd.isna(x):
            return np.nan
        s = str(x).strip()
        s = s.replace('S/', '').replace('$', '').replace(' ', '').replace(',', '.')
        try:
            return float(s)
        except:
            return np.nan
    df_out['Mantenimiento'] = df_out['Mantenimiento'].apply(clean_number)
    df_out['torre'] = pd.to_numeric(df_out['torre'], errors='coerce')
    df_out['departamento'] = pd.to_numeric(df_out['departamento'], errors='coerce')
    df_out = df_out.dropna(subset=['torre', 'departamento'])
    df_out = df_out.loc[:, ~df_out.columns.duplicated()]
    return df_out
# ------------------- Otros (Ingresos Extraordinarios) -------------------
def guardar_otros(df, mes, anio):
    nombre_hoja = f"Otros {mes} {anio}"
    # Eliminar la hoja si existe
    try:
        worksheet = spreadsheet.worksheet(nombre_hoja)
        spreadsheet.del_worksheet(worksheet)
    except gspread.exceptions.WorksheetNotFound:
        pass
    # Crear nueva hoja y subir datos
    worksheet = spreadsheet.add_worksheet(title=nombre_hoja, rows="1000", cols="20")
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())
    return nombre_hoja

def listar_hojas_otros():
    spreadsheet = get_spreadsheet()
    hojas = spreadsheet.worksheets()
    nombres = [hoja.title for hoja in hojas if hoja.title.startswith("Otros")]
    nombres.sort(reverse=True)
    return nombres

def leer_hoja_otros(nombre_hoja):
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.worksheet(nombre_hoja)
    datos = worksheet.get_all_values()
    if len(datos) < 2:
        return pd.DataFrame()
    headers = datos[0]
    filas = datos[1:]
    df = pd.DataFrame(filas, columns=headers)
    return df
