import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import numpy as np
from datetime import datetime

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

def subir_excel_a_sheets(df_upload):
    """
    Sube el DataFrame de propietarios a Google Sheets.
    Valida unicidad y maneja códigos COD automáticamente.
    """
    # NOTA: El cache se limpia desde la UI (pages/2_Propietarios.py)

    # Obtener datos existentes para validación de unicidad
    try:
        existing = leer_propietarios()
        existing['combinacion'] = existing['torre'].astype(str) + '_' + existing['dpto'].astype(str) + '_' + existing['dni'].astype(str)
        combos_existentes = set(existing['combinacion'].tolist())
    except:
        combos_existentes = set()

    # Contador de COD - buscar en Google Sheets o iniciar en 0
    spreadsheet = get_spreadsheet()
    try:
        # Intentar leer el contador desde la hoja de control
        try:
            control = spreadsheet.worksheet("Control_Codigos")
            contador_row = control.cell(1, 1).value
            last_cod_num = int(contador_row) if contador_row else 0
        except:
            # Si no existe, crear hoja de control
            try:
                control = spreadsheet.add_worksheet(title="Control_Codigos", rows=10, cols=5)
                control.cell(1, 1, "0")
                last_cod_num = 0
            except:
                last_cod_num = 0
    except:
        last_cod_num = 0

    # Procesar filas
    filas_validas = []
    duplicados = []
    cod_counter = last_cod_num

    for _, row in df_upload.iterrows():
        torre = str(row.get('torre', '')).strip()
        dpto = str(row.get('dpto', '')).strip()
        dni = str(row.get('dni', '')).strip()
        nombre = str(row.get('nombre', '')).strip()
        codigo = str(row.get('codigo', '')).strip()

        # Si no hay DNI, usar COD
        if not dni or dni == 'nan':
            cod_counter += 1
            dni = f"COD{cod_counter}"

        # Validar unicidad
        combinacion = f"{torre}_{dpto}_{dni}"
        if combinacion in combos_existentes:
            duplicados.append({'torre': torre, 'dpto': dpto, 'dni': dni})
        else:
            filas_validas.append({
                'torre': torre,
                'dpto': dpto,
                'codigo': codigo,
                'dni': dni,
                'nombre': nombre,
                'celular': str(row.get('celular', '')).strip(),
                'correo': str(row.get('correo', '')).strip(),
                'situacion': str(row.get('situacion', '')).strip()
            })
            combos_existentes.add(combinacion)

    # Guardar estado del contador si hay nuevos CODs
    if cod_counter > last_cod_num:
        try:
            control = spreadsheet.worksheet("Control_Codigos")
            control.cell(1, 1, str(cod_counter))
        except:
            pass

    # Reportar duplicados (dejar que la UI maneje la presentación)
    if duplicados:
        # Devolver información de duplicados a través de excepción
        raise ValueError(f"Duplicados detectados: {len(duplicados)} registros")

    # Subir solo las filas válidas
    df_final = pd.DataFrame(filas_validas)
    df_final = df_final.fillna("")

    sheet = get_sheet("Propietarios")
    sheet.clear()
    sheet.update(
        "A1",  # Rango donde empezar a escribir
        [df_final.columns.tolist()] + df_final.values.tolist(),
        value_input_option="RAW"
    )
    return len(df_final)

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
    spreadsheet = get_spreadsheet()
    # Limpiar NaN antes de subir
    df_clean = df.copy()
    for col in df_clean.columns:
        if df_clean[col].dtype == 'float64':
            df_clean[col] = df_clean[col].fillna(0)
        else:
            df_clean[col] = df_clean[col].fillna('')
    # Eliminar la hoja si ya existe
    try:
        worksheet = spreadsheet.worksheet(nombre_hoja)
        spreadsheet.del_worksheet(worksheet)
    except gspread.exceptions.WorksheetNotFound:
        pass
    # Crear nueva hoja y subir datos
    worksheet = spreadsheet.add_worksheet(title=nombre_hoja, rows="1000", cols="20")
    worksheet.update("A1", [df_clean.columns.values.tolist()] + df_clean.values.tolist())
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

# ====================== FUNCIONES DE CONTROL DE FECHAS ======================
def registrar_fecha_programacion(tipo: str, nombre_hoja: str, fecha_emision, fecha_vencimiento):
    """
    Registra en la hoja 'Control_Fechas' el rango de fechas de una programación.
    """
    spreadsheet = get_spreadsheet()
    try:
        worksheet = spreadsheet.worksheet("Control_Fechas")
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title="Control_Fechas", rows="1000", cols="10")
        worksheet.update("A1", [["TIPO", "NOMBRE_HOJA", "FECHA_EMISION", "FECHA_VENCIMIENTO"]])

    registros = worksheet.get_all_values()
    if len(registros) > 1:
        for i, row in enumerate(registros[1:], start=2):
            if len(row) >= 2 and row[1] == nombre_hoja:
                worksheet.update(f"C{i}", [[fecha_emision.strftime('%Y-%m-%d')]])
                worksheet.update(f"D{i}", [[fecha_vencimiento.strftime('%Y-%m-%d')]])
                return
    worksheet.append_row([
        tipo,
        nombre_hoja,
        fecha_emision.strftime('%Y-%m-%d'),
        fecha_vencimiento.strftime('%Y-%m-%d')
    ])

def existe_solapamiento_fechas(tipo: str, nueva_emision, nueva_vencimiento) -> bool:
    """
    Retorna True si ya existe una programación del mismo tipo con un rango que solapa.
    """
    spreadsheet = get_spreadsheet()
    try:
        worksheet = spreadsheet.worksheet("Control_Fechas")
    except gspread.exceptions.WorksheetNotFound:
        return False

    registros = worksheet.get_all_values()
    if len(registros) <= 1:
        return False

    for row in registros[1:]:
        if len(row) < 4:
            continue
        if row[0] != tipo:
            continue
        try:
            emision_existente = datetime.strptime(row[2], '%Y-%m-%d').date()
            venc_existente = datetime.strptime(row[3], '%Y-%m-%d').date()
        except:
            continue
        if nueva_emision <= venc_existente and nueva_vencimiento >= emision_existente:
            return True
    return False

def obtener_fechas_programacion(tipo: str, mes: str, anio: int):
    """
    Obtiene las fechas de emisión y vencimiento registradas para una programación.
    tipo: "Mantenimiento", "Medidores", "Amortización", "Otros"
    mes: nombre del mes (ej. "Enero")
    anio: año (int)
    Retorna: (fecha_emision, fecha_vencimiento) como objetos date, o (None, None) si no se encuentra.
    """
    # Construir nombre de hoja según el tipo
    if tipo == "Mantenimiento":
        nombre_hoja = f"Prog_{mes.upper()}_{anio}"
    elif tipo == "Medidores":
        nombre_hoja = f"Medidor {mes} {anio}"
    elif tipo == "Amortización":
        nombre_hoja = f"Amortización {mes} {anio}"
    elif tipo == "Otros":
        nombre_hoja = f"Otros {mes} {anio}"
    else:
        return (None, None)

    spreadsheet = get_spreadsheet()
    try:
        worksheet = spreadsheet.worksheet("Control_Fechas")
    except gspread.exceptions.WorksheetNotFound:
        return (None, None)

    registros = worksheet.get_all_values()
    if len(registros) <= 1:
        return (None, None)

    for row in registros[1:]:
        if len(row) < 4:
            continue
        if row[0] == tipo and row[1] == nombre_hoja:
            try:
                fecha_emi = datetime.strptime(row[2], '%Y-%m-%d').date()
                fecha_ven = datetime.strptime(row[3], '%Y-%m-%d').date()
                return (fecha_emi, fecha_ven)
            except:
                return (None, None)
    return (None, None)

# ====================== NUEVA FUNCIÓN PARA ELIMINAR ======================
def eliminar_programacion(nombre_hoja: str) -> bool:
    """
    Elimina una hoja del spreadsheet y su registro en Control_Fechas.
    Retorna True si se eliminó correctamente, False si no se encontró la hoja.
    """
    spreadsheet = get_spreadsheet()
    eliminada = False

    # 1. Eliminar la hoja si existe
    try:
        worksheet = spreadsheet.worksheet(nombre_hoja)
        spreadsheet.del_worksheet(worksheet)
        eliminada = True
    except gspread.exceptions.WorksheetNotFound:
        pass

    # 2. Eliminar el registro en Control_Fechas (si existe)
    try:
        control = spreadsheet.worksheet("Control_Fechas")
        registros = control.get_all_values()
        if len(registros) > 1:
            # Buscar la fila que tenga nombre_hoja en la columna B (índice 1)
            for i, row in enumerate(registros[1:], start=2):
                if len(row) >= 2 and row[1] == nombre_hoja:
                    control.delete_rows(i)
                    break
    except gspread.exceptions.WorksheetNotFound:
        pass

    return eliminada
