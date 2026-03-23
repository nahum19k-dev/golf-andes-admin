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
    st.cache_resource.clear() # ✅ limpia caché
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
#           NUEVAS FUNCIONES - PROGRAMACIÓN MENSUAL
# ────────────────────────────────────────────────

@st.cache_resource
def get_spreadsheet():
    """
    Devuelve el objeto Spreadsheet completo (necesario para crear hojas nuevas)
    """
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
    Ej: periodo_key = "MARZO_2026" → busca "Prog_MARZO_2026"
    Retorna True si la hoja ya existe (no se puede subir duplicado)
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
    Crea una hoja nueva automáticamente si no existe y guarda los datos del DataFrame.
    
    - Agrega título similar al de tu Excel de ejemplo
    - Escribe encabezados y datos
    - Retorna el nombre de la hoja creada
    
    Uso recomendado:
    nombre_hoja = crear_y_guardar_programacion(df, "MARZO_2026", "Marzo", 2026)
    """
    nombre_hoja = f"Prog_{periodo_key.upper()}"
    
    if existe_programacion(periodo_key):
        raise ValueError(f"La hoja '{nombre_hoja}' ya existe. No se puede crear duplicado.")
    
    spreadsheet = get_spreadsheet()
    
    # Crear hoja nueva con dimensiones razonables
    nueva_hoja = spreadsheet.add_worksheet(
        title=nombre_hoja,
        rows=700,               # suficiente para 380+ dptos + totales + encabezados
        cols=max(40, len(df.columns) + 10)
    )
    
    # Título principal (similar a tu Excel)
    titulo = f"DETERMINACION DE CUOTA MES DE {mes.upper()}-{anio} - CONJUNTO RESIDENCIAL GOLF LOS ANDES I"
    nueva_hoja.update("A1", titulo)
    nueva_hoja.format("A1", {
        "textFormat": {"bold": True, "fontSize": 14},
        "horizontalAlignment": "CENTER"
    })
    # Merge para que se vea bien (ajusta el rango según cuántas columnas uses)
    nueva_hoja.merge_cells("A1:AG1")  # AG ≈ columna 33, ajusta si necesitas más
    
    # Fila 2 vacía (como en tu ejemplo)
    nueva_hoja.update("A2", "")
    
    # Encabezados en fila 3
    encabezados = df.columns.tolist()
    nueva_hoja.update("A3", [encabezados])
    nueva_hoja.format("A3:AG3", {"textFormat": {"bold": True}})
    
    # Datos desde fila 4
    datos = df.fillna("").values.tolist()  # evita NaN que rompen gspread
    if datos:
        nueva_hoja.update("A4", datos)
    
    # Limpiar caché para que futuras lecturas vean los cambios
    st.cache_resource.clear()
    
    return nombre_hoja
