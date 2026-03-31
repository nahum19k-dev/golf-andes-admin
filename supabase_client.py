import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import json

@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

# ====================== FUNCIÓN AUXILIAR ======================
def limpiar_nan_para_json(df: pd.DataFrame) -> pd.DataFrame:
    """
    Reemplaza NaN por None (que se convierte a null en JSON) en DataFrames.
    También convierte valores numéricos infinitos a 0.
    """
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == 'float64':
            df[col] = df[col].fillna(0)
        elif df[col].dtype == 'object':
            df[col] = df[col].fillna('')
    return df

def limpiar_nombres_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Solo limpia espacios al inicio/final, sin cambiar mayúsculas.
    """
    df.columns = df.columns.str.strip()
    return df

# ====================== PROPIETARIOS ======================
def leer_propietarios() -> pd.DataFrame:
    supabase = get_supabase()
    response = supabase.table('propietarios').select('*').execute()
    if response.data:
        df = pd.DataFrame(response.data)
        df = limpiar_nombres_columnas(df)
        columnas_esperadas = ['id', 'codigo', 'torre', 'dpto', 'dni', 'nombre', 'celular', 'correo', 'situacion', 'direccion']
        for col in columnas_esperadas:
            if col not in df.columns:
                if col == 'id':
                    df[col] = 0
                else:
                    df[col] = ''
        return df[columnas_esperadas]
    return pd.DataFrame()

def subir_excel_a_sheets(df: pd.DataFrame) -> int:
    supabase = get_supabase()
    supabase.table('propietarios').delete().neq('id', 0).execute()
    df_clean = limpiar_nan_para_json(df)
    records = df_clean.to_dict(orient='records')
    response = supabase.table('propietarios').insert(records).execute()
    return len(response.data)

def agregar_propietario(registro: dict) -> bool:
    supabase = get_supabase()
    try:
        supabase.table('propietarios').insert(registro).execute()
        return True
    except Exception as e:
        print(f"Error al insertar: {e}")
        return False

def eliminar_propietario_por_id(record_id: int) -> bool:
    supabase = get_supabase()
    try:
        supabase.table('propietarios').delete().eq('id', record_id).execute()
        return True
    except Exception as e:
        print(f"Error al eliminar: {e}")
        return False

# ====================== PROGRAMACIÓN ======================
def existe_programacion(periodo_key: str) -> bool:
    supabase = get_supabase()
    nombre_hoja = f"Prog_{periodo_key.upper()}"
    response = supabase.table('programacion').select('id').eq('nombre_hoja', nombre_hoja).execute()
    return len(response.data) > 0

def crear_y_guardar_programacion(df: pd.DataFrame, periodo_key: str, mes: str, anio: int) -> str:
    nombre_hoja = f"Prog_{periodo_key.upper()}"
    if existe_programacion(periodo_key):
        raise ValueError(f"La hoja '{nombre_hoja}' ya existe.")
    supabase = get_supabase()
    df_clean = limpiar_nan_para_json(df)
    datos = df_clean.to_dict(orient='records')
    supabase.table('programacion').insert({
        'nombre_hoja': nombre_hoja,
        'mes': mes,
        'anio': anio,
        'datos': datos
    }).execute()
    return nombre_hoja

def listar_hojas_programacion():
    supabase = get_supabase()
    response = supabase.table('programacion').select('nombre_hoja').execute()
    nombres = [row['nombre_hoja'] for row in response.data]
    nombres.sort(reverse=True)
    return nombres

def leer_hoja_programacion(nombre_hoja):
    supabase = get_supabase()
    response = supabase.table('programacion').select('datos').eq('nombre_hoja', nombre_hoja).execute()
    if response.data:
        df = pd.DataFrame(response.data[0]['datos'])
        df = limpiar_nombres_columnas(df)  # solo quita espacios
        return df
    return pd.DataFrame()

# ====================== PAGOS ======================
def guardar_pagos(df: pd.DataFrame, mes: str, anio: int) -> str:
    supabase = get_supabase()
    nombre_base = f"Pagos {mes} {anio}"
    resp = supabase.table('pagos').select('nombre_hoja').eq('nombre_hoja', nombre_base).execute()
    if resp.data:
        contador = 2
        while True:
            nuevo_nombre = f"{nombre_base} ({contador})"
            resp2 = supabase.table('pagos').select('nombre_hoja').eq('nombre_hoja', nuevo_nombre).execute()
            if not resp2.data:
                nombre_hoja = nuevo_nombre
                break
            contador += 1
    else:
        nombre_hoja = nombre_base

    df_clean = limpiar_nan_para_json(df)
    datos = df_clean.to_dict(orient='records')
    supabase.table('pagos').insert({
        'nombre_hoja': nombre_hoja,
        'mes': mes,
        'anio': anio,
        'datos': datos
    }).execute()
    return nombre_hoja

def listar_hojas_pagos():
    supabase = get_supabase()
    response = supabase.table('pagos').select('nombre_hoja').execute()
    nombres = [row['nombre_hoja'] for row in response.data]
    nombres.sort(reverse=True)
    return nombres

def leer_hoja_pagos(nombre_hoja):
    supabase = get_supabase()
    response = supabase.table('pagos').select('datos').eq('nombre_hoja', nombre_hoja).execute()
    if response.data:
        df = pd.DataFrame(response.data[0]['datos'])
        df = limpiar_nombres_columnas(df)
        return df
    return pd.DataFrame()
def leer_pagos_mes(mes: str, anio: int):
    supabase = get_supabase()
    response = supabase.table('pagos').select('datos').eq('mes', mes).eq('anio', anio).execute()
    if response.data:
        df = pd.DataFrame(response.data[0]['datos'])
        df = limpiar_nombres_columnas(df)
        # Ya no hacemos un rename fijo, solo devolvemos el DataFrame completo
        # Convertir columnas numéricas (detecta automáticamente)
        for col in df.columns:
            if col in ['torre', 'departamento', 'mantenimiento', 'amortizacion', 'medidor',
                       'cuota_extraordinaria', 'alquiler_parrilla', 'garantia',
                       'sala_zoom', 'alquiler_sillas', 'tuberias', 'ingresos']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        if 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
        return df.sort_values('fecha')
    return pd.DataFrame()

# ====================== MEDIDORES ======================
def guardar_medidor(df: pd.DataFrame, mes: str, anio: int) -> str:
    supabase = get_supabase()
    nombre_base = f"Medidor {mes} {anio}"
    resp = supabase.table('medidores').select('nombre_hoja').eq('nombre_hoja', nombre_base).execute()
    if resp.data:
        contador = 2
        while True:
            nuevo_nombre = f"{nombre_base} ({contador})"
            resp2 = supabase.table('medidores').select('nombre_hoja').eq('nombre_hoja', nuevo_nombre).execute()
            if not resp2.data:
                nombre_hoja = nuevo_nombre
                break
            contador += 1
    else:
        nombre_hoja = nombre_base

    df_clean = limpiar_nan_para_json(df)
    datos = df_clean.to_dict(orient='records')
    supabase.table('medidores').insert({
        'nombre_hoja': nombre_hoja,
        'mes': mes,
        'anio': anio,
        'datos': datos
    }).execute()
    return nombre_hoja

def listar_hojas_medidor():
    supabase = get_supabase()
    response = supabase.table('medidores').select('nombre_hoja').execute()
    nombres = [row['nombre_hoja'] for row in response.data]
    nombres.sort(reverse=True)
    return nombres

def leer_hoja_medidor(nombre_hoja):
    supabase = get_supabase()
    response = supabase.table('medidores').select('datos').eq('nombre_hoja', nombre_hoja).execute()
    if response.data:
        df = pd.DataFrame(response.data[0]['datos'])
        df = limpiar_nombres_columnas(df)
        return df
    return pd.DataFrame()

# ====================== AMORTIZACIÓN ======================
def guardar_amortizacion(df: pd.DataFrame, mes: str, anio: int) -> str:
    supabase = get_supabase()
    nombre_base = f"Amortización {mes} {anio}"
    resp = supabase.table('amortizacion').select('nombre_hoja').eq('nombre_hoja', nombre_base).execute()
    if resp.data:
        contador = 2
        while True:
            nuevo_nombre = f"{nombre_base} ({contador})"
            resp2 = supabase.table('amortizacion').select('nombre_hoja').eq('nombre_hoja', nuevo_nombre).execute()
            if not resp2.data:
                nombre_hoja = nuevo_nombre
                break
            contador += 1
    else:
        nombre_hoja = nombre_base

    df_clean = limpiar_nan_para_json(df)
    datos = df_clean.to_dict(orient='records')
    supabase.table('amortizacion').insert({
        'nombre_hoja': nombre_hoja,
        'mes': mes,
        'anio': anio,
        'datos': datos
    }).execute()
    return nombre_hoja

def listar_hojas_amortizacion():
    supabase = get_supabase()
    response = supabase.table('amortizacion').select('nombre_hoja').execute()
    nombres = [row['nombre_hoja'] for row in response.data]
    nombres.sort(reverse=True)
    return nombres

def leer_hoja_amortizacion(nombre_hoja):
    supabase = get_supabase()
    response = supabase.table('amortizacion').select('datos').eq('nombre_hoja', nombre_hoja).execute()
    if response.data:
        df = pd.DataFrame(response.data[0]['datos'])
        df = limpiar_nombres_columnas(df)
        return df
    return pd.DataFrame()

# ====================== OTROS ======================
def guardar_otros(df: pd.DataFrame, mes: str, anio: int) -> str:
    supabase = get_supabase()
    nombre_base = f"Otros {mes} {anio}"
    resp = supabase.table('otros').select('nombre_hoja').eq('nombre_hoja', nombre_base).execute()
    if resp.data:
        contador = 2
        while True:
            nuevo_nombre = f"{nombre_base} ({contador})"
            resp2 = supabase.table('otros').select('nombre_hoja').eq('nombre_hoja', nuevo_nombre).execute()
            if not resp2.data:
                nombre_hoja = nuevo_nombre
                break
            contador += 1
    else:
        nombre_hoja = nombre_base

    df_clean = limpiar_nan_para_json(df)
    datos = df_clean.to_dict(orient='records')
    supabase.table('otros').insert({
        'nombre_hoja': nombre_hoja,
        'mes': mes,
        'anio': anio,
        'datos': datos
    }).execute()
    return nombre_hoja

def listar_hojas_otros():
    supabase = get_supabase()
    response = supabase.table('otros').select('nombre_hoja').execute()
    nombres = [row['nombre_hoja'] for row in response.data]
    nombres.sort(reverse=True)
    return nombres

def leer_hoja_otros(nombre_hoja):
    supabase = get_supabase()
    response = supabase.table('otros').select('datos').eq('nombre_hoja', nombre_hoja).execute()
    if response.data:
        df = pd.DataFrame(response.data[0]['datos'])
        df = limpiar_nombres_columnas(df)
        return df
    return pd.DataFrame()

# ====================== DEUDA INICIAL ======================
def guardar_deuda_inicial(df: pd.DataFrame, anio: int) -> str:
    supabase = get_supabase()
    supabase.table('deuda_inicial').delete().eq('anio', anio).execute()
    df_clean = limpiar_nan_para_json(df)
    datos = df_clean.to_dict(orient='records')
    supabase.table('deuda_inicial').insert({
        'anio': anio,
        'datos': datos
    }).execute()
    return f"Deuda Inicial {anio}"

def listar_hojas_deuda():
    supabase = get_supabase()
    response = supabase.table('deuda_inicial').select('anio').execute()
    nombres = [f"Deuda Inicial {row['anio']}" for row in response.data]
    nombres.sort(reverse=True)
    return nombres

def leer_hoja_deuda(nombre_hoja):
    try:
        anio = int(nombre_hoja.split()[-1])
    except:
        return pd.DataFrame()
    supabase = get_supabase()
    response = supabase.table('deuda_inicial').select('datos').eq('anio', anio).execute()
    if response.data:
        df = pd.DataFrame(response.data[0]['datos'])
        df = limpiar_nombres_columnas(df)
        return df
    return pd.DataFrame()

# ====================== CONTROL DE FECHAS ======================
def registrar_fecha_programacion(tipo: str, nombre_hoja: str, fecha_emision, fecha_vencimiento):
    supabase = get_supabase()
    supabase.table('control_fechas').delete().eq('nombre_hoja', nombre_hoja).execute()
    supabase.table('control_fechas').insert({
        'tipo': tipo,
        'nombre_hoja': nombre_hoja,
        'fecha_emision': fecha_emision.isoformat(),
        'fecha_vencimiento': fecha_vencimiento.isoformat()
    }).execute()

def existe_solapamiento_fechas(tipo: str, nueva_emision, nueva_vencimiento) -> bool:
    supabase = get_supabase()
    response = supabase.table('control_fechas').select('*').eq('tipo', tipo).execute()
    for row in response.data:
        emision = datetime.fromisoformat(row['fecha_emision']).date()
        venc = datetime.fromisoformat(row['fecha_vencimiento']).date()
        if nueva_emision <= venc and nueva_vencimiento >= emision:
            return True
    return False

def obtener_fechas_programacion(tipo: str, mes: str, anio: int):
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
    supabase = get_supabase()
    response = supabase.table('control_fechas').select('fecha_emision,fecha_vencimiento').eq('tipo', tipo).eq('nombre_hoja', nombre_hoja).execute()
    if response.data:
        emision = datetime.fromisoformat(response.data[0]['fecha_emision']).date()
        venc = datetime.fromisoformat(response.data[0]['fecha_vencimiento']).date()
        return (emision, venc)
    return (None, None)

# ====================== ELIMINAR ======================
def eliminar_programacion(nombre_hoja: str) -> bool:
    supabase = get_supabase()
    eliminada = False
    for tabla in ['programacion', 'pagos', 'medidores', 'amortizacion', 'otros']:
        try:
            resp = supabase.table(tabla).delete().eq('nombre_hoja', nombre_hoja).execute()
            if resp.data:
                eliminada = True
        except:
            pass
    supabase.table('control_fechas').delete().eq('nombre_hoja', nombre_hoja).execute()
    return eliminada

# ====================== LECTURAS ESPECÍFICAS PARA OPERACIONES ======================
def leer_programacion(mes: str, anio: int):
    nombre_hoja = f"Prog_{mes.upper()}_{anio}"
    df = leer_hoja_programacion(nombre_hoja)
    if df.empty:
        return df
    # Convertir a numérico las columnas que corresponden
    for col in ['torre', 'departamento', 'Mantenimiento']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=['torre', 'departamento'])
    return df[['torre', 'departamento', 'Mantenimiento']]

def leer_amortizacion(mes: str, anio: int):
    nombre_hoja = f"Amortización {mes} {anio}"
    df = leer_hoja_amortizacion(nombre_hoja)
    if df.empty:
        return df
    for col in ['torre', 'departamento', 'amortizacion']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df[['torre', 'departamento', 'amortizacion']]

def leer_medidores(mes: str, anio: int):
    nombre_hoja = f"Medidor {mes} {anio}"
    df = leer_hoja_medidor(nombre_hoja)
    if df.empty:
        return df
    for col in ['torre', 'departamento', 'monto']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df[['torre', 'departamento', 'monto']]

def leer_deuda_inicial(anio: int):
    nombre_hoja = f"Deuda Inicial {anio}"
    df = leer_hoja_deuda(nombre_hoja)
    if df.empty and anio > 2020:
        df_ant = leer_hoja_deuda(f"Deuda Inicial {anio-1}")
        if not df_ant.empty:
            st.info(f"Usando deuda del año anterior ({anio-1}) porque no se encontró para {anio}.")
            return df_ant
    return df

# ====================== CONTROL DE CÓDIGOS ======================
def obtener_ultimo_codigo() -> int:
    supabase = get_supabase()
    response = supabase.table('control_codigos').select('ultimo_codigo').execute()
    if response.data:
        return response.data[0]['ultimo_codigo']
    else:
        supabase.table('control_codigos').insert({'ultimo_codigo': 0}).execute()
        return 0

def obtener_siguiente_codigo() -> int:
    supabase = get_supabase()
    response = supabase.table('control_codigos').select('id', 'ultimo_codigo').execute()
    if response.data:
        registro = response.data[0]
        nuevo = registro['ultimo_codigo'] + 1
        supabase.table('control_codigos').update({'ultimo_codigo': nuevo}).eq('id', registro['id']).execute()
        return nuevo
    else:
        supabase.table('control_codigos').insert({'ultimo_codigo': 1}).execute()
        return 1
