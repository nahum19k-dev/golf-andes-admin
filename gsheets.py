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
    """
    Lee la hoja de programación (creada con crear_y_guardar_programacion)
    y devuelve torre, departamento y Mantenimiento.
    """
    nombre_hoja = f"Prog_{mes.upper()}_{anio}"
    spreadsheet = get_spreadsheet()
    try:
        worksheet = spreadsheet.worksheet(nombre_hoja)
    except gspread.exceptions.WorksheetNotFound:
        return pd.DataFrame()
    datos = worksheet.get_all_values()
    if len(datos) < 4:
        return pd.DataFrame()
    # encabezados en fila 3 (índice 2), datos desde fila 4 (índice 3)
    headers = datos[2]
    filas = datos[3:]
    df = pd.DataFrame(filas, columns=headers)
    df.columns = df.columns.str.strip().str.replace('\n', ' ')
    # Buscar columna de total (mantenimiento)
    col_total = None
    for col in df.columns:
        col_low = col.lower()
        if 'total' in col_low or 'mantenimiento' in col_low or 'cuota' in col_low or 'pagar' in col_low:
            col_total = col
            break
    if col_total is None:
        return pd.DataFrame()
    # Buscar columnas de torre y departamento
    col_torre = None
    col_dpto = None
    for col in df.columns:
        col_low = col.lower()
        if 'torre' in col_low:
            col_torre = col
        elif 'departamento' in col_low or 'dpto' in col_low:
            col_dpto = col
    if not (col_torre and col_dpto):
        return pd.DataFrame()
    df_out = pd.DataFrame()
    df_out['torre'] = pd.to_numeric(df[col_torre], errors='coerce')
    df_out['departamento'] = pd.to_numeric(df[col_dpto], errors='coerce')
    df_out['Mantenimiento'] = pd.to_numeric(df[col_total], errors='coerce')
    return df_out

def leer_amortizacion(mes: str, anio: int):
    """
    Lee la hoja de amortización y devuelve solo torre, departamento, amortizacion.
    """
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
    # Buscar columnas
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
    """
    Lee la hoja de medidores y devuelve solo torre, departamento, monto.
    """
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

def leer_pagos_mes(mes: str, anio: int):
    """
    Lee la hoja de pagos y devuelve fecha, torre, departamento, ingresos, n_operacion.
    """
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
    col_fecha = None
    col_torre = None
    col_dpto = None
    col_ing = None
    col_oper = None
    for col in df.columns:
        col_low = col.lower()
        if 'fecha' in col_low:
            col_fecha = col
        elif 'torre' in col_low:
            col_torre = col
        elif 'dpto' in col_low or 'departamento' in col_low:
            col_dpto = col
        elif 'ingresos' in col_low or 'pagos' in col_low:
            col_ing = col
        elif 'operación' in col_low or 'n_operacion' in col_low:
            col_oper = col
    if not (col_fecha and col_torre and col_dpto and col_ing):
        return pd.DataFrame()
    df_out = pd.DataFrame()
    df_out['fecha'] = pd.to_datetime(df[col_fecha], errors='coerce')
    df_out['torre'] = pd.to_numeric(df[col_torre], errors='coerce')
    df_out['departamento'] = pd.to_numeric(df[col_dpto], errors='coerce')
    df_out['ingresos'] = pd.to_numeric(df[col_ing], errors='coerce')
    df_out['n_operacion'] = df[col_oper].astype(str) if col_oper else ''
    df_out = df_out.sort_values('fecha')
    return df_out

def leer_deuda_inicial(anio: int):
    """
    Busca primero la deuda del año exacto. Si no existe, intenta con el año anterior.
    """
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
    """
    Lee una hoja de programación (creada con crear_y_guardar_programacion)
    y devuelve DataFrame con columnas: torre, departamento, Mantenimiento.
    """
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.worksheet(nombre_hoja)
    datos = worksheet.get_all_values()
    if len(datos) < 4:
        st.warning(f"La hoja {nombre_hoja} tiene menos de 4 filas.")
        return pd.DataFrame()

    # Los encabezados están en la fila 3 (índice 2)
    headers = datos[2]
    filas = datos[3:]

    # Eliminar filas completamente vacías (opcional)
    filas = [f for f in filas if any(cell for cell in f)]

    if not filas:
        st.warning("No hay filas de datos en la hoja.")
        return pd.DataFrame()

    df = pd.DataFrame(filas, columns=headers)
    # Limpiar nombres de columnas: quitar espacios, saltos de línea, etc.
    df.columns = df.columns.str.strip().str.replace('\n', ' ').str.replace('\r', '')

    # --- Depuración (puedes eliminar después) ---
    st.write("**Columnas encontradas en la hoja:**", list(df.columns))

    # 1. Buscar la columna "Torre" (exacta, insensible a mayúsculas)
    col_torre = None
    for col in df.columns:
        if col.lower() == 'torre':
            col_torre = col
            break
    # Si no, buscar con variantes
    if col_torre is None:
        for col in df.columns:
            if col.lower() in ['torre', 'edificio']:
                col_torre = col
                break
    if col_torre is None:
        st.error(f"No se encontró columna 'Torre'. Columnas disponibles: {list(df.columns)}")
        return pd.DataFrame()

    # 2. Buscar la columna "Departamento" (exacta, insensible a mayúsculas)
    col_dpto = None
    for col in df.columns:
        if col.lower() == 'departamento' or col.lower() == 'dpto' or col.lower() == 'n°dpto':
            col_dpto = col
            break
    if col_dpto is None:
        st.error(f"No se encontró columna 'Departamento'. Columnas disponibles: {list(df.columns)}")
        return pd.DataFrame()

    # 3. Buscar la columna "Mantenimiento" (puede llamarse "Mantenimiento" o "Total" o similar)
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
        st.error(f"No se encontró columna de monto (Mantenimiento/Total).")
        return pd.DataFrame()

    st.write(f"**Columna Torre:** {col_torre}")
    st.write(f"**Columna Departamento:** {col_dpto}")
    st.write(f"**Columna Monto:** {col_monto}")

    # Crear DataFrame con solo las tres columnas necesarias
    df_out = df[[col_torre, col_dpto, col_monto]].copy()
    df_out.columns = ['torre', 'departamento', 'Mantenimiento']

    # Convertir a numérico (reemplazar comas, puntos, etc.)
    for col in ['torre', 'departamento', 'Mantenimiento']:
        # Primero, eliminar espacios en blanco
        df_out[col] = df_out[col].astype(str).str.strip()
        # Reemplazar comas por puntos (para números decimales)
        df_out[col] = df_out[col].str.replace(',', '.')
        # Convertir a numérico, forzando errores a NaN
        df_out[col] = pd.to_numeric(df_out[col], errors='coerce')

    # Eliminar filas donde torre o departamento sean NaN
    df_out = df_out.dropna(subset=['torre', 'departamento'])

    # Opcional: eliminar filas donde Mantenimiento sea NaN (si se quiere)
    # df_out = df_out.dropna(subset=['Mantenimiento'])

    st.write(f"**DataFrame final shape:** {df_out.shape}")
    st.write("**Muestra:**")
    st.dataframe(df_out.head(10))

    # Eliminar columnas duplicadas por si acaso
    df_out = df_out.loc[:, ~df_out.columns.duplicated()]

    return df_out
