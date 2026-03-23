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
    st.cache_resource.clear()  # ✅ limpia caché
    df = pd.read_excel(ruta_excel, dtype=str)
    df = df.fillna("")
    sheet = get_sheet("Propietarios")
    sheet.clear()
    sheet.update(
        [df.columns.tolist()] + df.values.tolist(),
        value_input_option="RAW"
    )
    return len(df)


# ────────────────────────────────────────────────
#           FUNCIONES PARA PROGRAMACIÓN MENSUAL
# ────────────────────────────────────────────────

@st.cache_resource
def get_spreadsheet():
    """Devuelve el objeto Spreadsheet completo (necesario para crear hojas nuevas)"""
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )
    client = gspread.authorize(creds)
    sheet_id = st.secrets["sheets"]["spreadsheet_id"]
    return client.open_by_key(sheet_id)


def existe_programacion(periodo_key: str) -> bool:
    """
    Verifica si ya existe una hoja para este período.
    Ejemplo: periodo_key = "MARZO_2026" → busca hoja "Prog_MARZO_2026"
    """
    nombre_hoja = f"Prog_{periodo_key.upper()}"
    spreadsheet = get_spreadsheet()
    try:
        spreadsheet.worksheet(nombre_hoja)
        return True
    except gspread.exceptions.WorksheetNotFound:
        return False


def crear_y_guardar_programacion(df: pd.DataFrame, periodo_key: str, mes: str, anio: int):
    """
    Crea hoja nueva si no existe y guarda el DataFrame ahí.
    Agrega título similar al de tu ejemplo de Excel.
    """
    nombre_hoja = f"Prog_{periodo_key.upper()}"
    
    if existe_programacion(periodo_key):
        raise ValueError(f"La hoja '{nombre_hoja}' ya existe. No se puede crear duplicado.")
    
    spreadsheet = get_spreadsheet()
    
    # Crear hoja nueva
    nueva_hoja = spreadsheet.add_worksheet(
        title=nombre_hoja,
        rows=700,
        cols=max(40, len(df.columns) + 10)
    )
    
    # Título principal
    titulo = f"DETERMINACION DE CUOTA MES DE {mes.upper()}-{anio} - CONJUNTO RESIDENCIAL GOLF LOS ANDES I"
    nueva_hoja.update("A1", [[titulo]])  # formato 2D obligatorio
    nueva_hoja.format("A1", {
        "textFormat": {"bold": True, "fontSize": 14},
        "horizontalAlignment": "CENTER"
    })
    nueva_hoja.merge_cells("A1:AG1")  # ajusta el rango si usas más columnas
    
    # Fila vacía (como en tu ejemplo)
    nueva_hoja.update("A2", [[""]])
    
    # Encabezados en fila 3
    encabezados = df.columns.tolist()
    nueva_hoja.update("A3", [encabezados])  # formato 2D
    
    # Datos desde fila 4
    datos = df.fillna("").values.tolist()
    if datos:
        nueva_hoja.update("A4", datos)
    
    # Limpiar caché para que se vea el cambio inmediatamente
    st.cache_resource.clear()
    
    return nombre_hoja
