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
    """Reemplaza NaN por None (que se convierte a null en JSON) en DataFrames."""
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == 'float64':
            df[col] = df[col].fillna(0)
        elif df[col].dtype == 'object':
            df[col] = df[col].fillna('')
    return df

def limpiar_nombres_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """Solo limpia espacios al inicio/final, sin cambiar mayúsculas."""
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
def guardar_programacion(df: pd.DataFrame, mes: str, anio: int, fecha_emision, fecha_vencimiento) -> str:
    """Guarda una nueva hoja de programación, validando solapamiento de fechas."""
    supabase = get_supabase()
    nombre_hoja = f"Prog_{mes.upper()}_{anio}"

    # Validar solapamiento con otras programaciones del mismo tipo
    if existe_solapamiento_fechas("Mantenimiento", fecha_emision, fecha_vencimiento):
        raise ValueError(f"Las fechas {fecha_emision} - {fecha_vencimiento} se solapan con otra programación existente.")

    df_clean = limpiar_nan_para_json(df)
    datos = df_clean.to_dict(orient='records')
    supabase.table('programacion').insert({
        'nombre_hoja': nombre_hoja,
        'mes': mes,
        'anio': anio,
        'datos': datos
    }).execute()

    # Registrar las fechas para control de solapamiento
    registrar_fecha_programacion("Mantenimiento", nombre_hoja, fecha_emision, fecha_vencimiento)
    return nombre_hoja

def leer_programacion(mes: str, anio: int) -> pd.DataFrame:
    """
    Lee todas las programaciones del mes y año, concatena los datos y agrupa por departamento sumando Mantenimiento.
    """
    supabase = get_supabase()
    response = supabase.table('programacion').select('datos').eq('mes', mes).eq('anio', anio).execute()
    if not response.data:
        return pd.DataFrame(columns=['torre', 'departamento', 'Mantenimiento'])

    dfs = []
    for row in response.data:
        df = pd.DataFrame(row['datos'])
        df = limpiar_nombres_columnas(df)
        if 'torre' in df.columns and 'departamento' in df.columns and 'Mantenimiento' in df.columns:
            df['torre'] = pd.to_numeric(df['torre'], errors='coerce')
            df['departamento'] = pd.to_numeric(df['departamento'], errors='coerce')
            df['Mantenimiento'] = pd.to_numeric(df['Mantenimiento'], errors='coerce').fillna(0)
            dfs.append(df)

    if not dfs:
        return pd.DataFrame(columns=['torre', 'departamento', 'Mantenimiento'])

    df_all = pd.concat(dfs, ignore_index=True)
    df_all = df_all.dropna(subset=['torre', 'departamento'])
    df_sum = df_all.groupby(['torre', 'departamento'], as_index=False)['Mantenimiento'].sum()
    return df_sum[['torre', 'departamento', 'Mantenimiento']]

# ====================== PAGOS ======================
def guardar_pagos(df: pd.DataFrame, mes: str, anio: int) -> str:
    """Guarda una hoja de pagos (no se validan fechas para pagos)."""
    supabase = get_supabase()
    nombre_hoja = f"Pagos {mes} {anio}"

    # Calcular la columna ingresos si no existe
    if 'ingresos' not in df.columns:
        conceptos = ['mantenimiento', 'amortizacion', 'medidor', 'cuota_extraordinaria',
                     'alquiler_parrilla', 'garantia', 'sala_zoom', 'alquiler_sillas', 'tuberias']
        for c in conceptos:
            if c not in df.columns:
                df[c] = 0
        df['ingresos'] = df[conceptos].sum(axis=1)

    df_clean = limpiar_nan_para_json(df)
    datos = df_clean.to_dict(orient='records')
    supabase.table('pagos').insert({
        'nombre_hoja': nombre_hoja,
        'mes': mes,
        'anio': anio,
        'datos': datos
    }).execute()
    return nombre_hoja

def leer_pagos_mes(mes: str, anio: int) -> pd.DataFrame:
    """
    Lee todas las hojas de pagos del mes y año, concatena los datos y los devuelve sin agrupar.
    """
    supabase = get_supabase()
    response = supabase.table('pagos').select('datos').eq('mes', mes).eq('anio', anio).execute()
    if not response.data:
        return pd.DataFrame(columns=['fecha', 'torre', 'departamento', 'n_operacion', 'ingresos',
                                     'mantenimiento', 'amortizacion', 'medidor'])

    dfs = []
    for row in response.data:
        df = pd.DataFrame(row['datos'])
        df = limpiar_nombres_columnas(df)
        # Asegurar columnas numéricas
        conceptos = ['mantenimiento', 'amortizacion', 'medidor', 'cuota_extraordinaria',
                     'alquiler_parrilla', 'garantia', 'sala_zoom', 'alquiler_sillas', 'tuberias']
        for col in conceptos + ['torre', 'departamento', 'ingresos']:
            if col not in df.columns:
                df[col] = 0
            else:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        if 'ingresos' not in df.columns or df['ingresos'].sum() == 0:
            df['ingresos'] = df[conceptos].sum(axis=1)
        if 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
        dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    df_all = pd.concat(dfs, ignore_index=True)
    return df_all.sort_values('fecha')

# ====================== MEDIDORES ======================
def guardar_medidor(df: pd.DataFrame, mes: str, anio: int, fecha_emision, fecha_vencimiento) -> str:
    """Guarda una hoja de medidores con validación de solapamiento."""
    supabase = get_supabase()
    nombre_hoja = f"Medidor {mes} {anio}"

    if existe_solapamiento_fechas("Medidores", fecha_emision, fecha_vencimiento):
        raise ValueError(f"Las fechas {fecha_emision} - {fecha_vencimiento} se solapan con otra hoja de medidores existente.")

    df_clean = limpiar_nan_para_json(df)
    datos = df_clean.to_dict(orient='records')
    supabase.table('medidores').insert({
        'nombre_hoja': nombre_hoja,
        'mes': mes,
        'anio': anio,
        'datos': datos
    }).execute()

    registrar_fecha_programacion("Medidores", nombre_hoja, fecha_emision, fecha_vencimiento)
    return nombre_hoja

def leer_medidores(mes: str, anio: int) -> pd.DataFrame:
    """
    Lee todas las hojas de medidores del mes y año, concatena y agrupa por departamento sumando monto.
    """
    supabase = get_supabase()
    response = supabase.table('medidores').select('datos').eq('mes', mes).eq('anio', anio).execute()
    if not response.data:
        return pd.DataFrame(columns=['torre', 'departamento', 'monto'])

    dfs = []
    for row in response.data:
        df = pd.DataFrame(row['datos'])
        df = limpiar_nombres_columnas(df)
        if 'torre' in df.columns and 'departamento' in df.columns and 'monto' in df.columns:
            df['torre'] = pd.to_numeric(df['torre'], errors='coerce')
            df['departamento'] = pd.to_numeric(df['departamento'], errors='coerce')
            df['monto'] = pd.to_numeric(df['monto'], errors='coerce').fillna(0)
            dfs.append(df)

    if not dfs:
        return pd.DataFrame(columns=['torre', 'departamento', 'monto'])

    df_all = pd.concat(dfs, ignore_index=True)
    df_all = df_all.dropna(subset=['torre', 'departamento'])
    df_sum = df_all.groupby(['torre', 'departamento'], as_index=False)['monto'].sum()
    return df_sum[['torre', 'departamento', 'monto']]

# ====================== AMORTIZACIÓN ======================
def guardar_amortizacion(df: pd.DataFrame, mes: str, anio: int, fecha_emision, fecha_vencimiento) -> str:
    """Guarda una hoja de amortización con validación de solapamiento."""
    supabase = get_supabase()
    nombre_hoja = f"Amortización {mes} {anio}"

    if existe_solapamiento_fechas("Amortización", fecha_emision, fecha_vencimiento):
        raise ValueError(f"Las fechas {fecha_emision} - {fecha_vencimiento} se solapan con otra hoja de amortización existente.")

    df_clean = limpiar_nan_para_json(df)
    datos = df_clean.to_dict(orient='records')
    supabase.table('amortizacion').insert({
        'nombre_hoja': nombre_hoja,
        'mes': mes,
        'anio': anio,
        'datos': datos
    }).execute()

    registrar_fecha_programacion("Amortización", nombre_hoja, fecha_emision, fecha_vencimiento)
    return nombre_hoja

def leer_amortizacion(mes: str, anio: int) -> pd.DataFrame:
    """
    Lee todas las hojas de amortización del mes y año, concatena y agrupa por departamento sumando amortizacion.
    """
    supabase = get_supabase()
    response = supabase.table('amortizacion').select('datos').eq('mes', mes).eq('anio', anio).execute()
    if not response.data:
        return pd.DataFrame(columns=['torre', 'departamento', 'amortizacion'])

    dfs = []
    for row in response.data:
        df = pd.DataFrame(row['datos'])
        df = limpiar_nombres_columnas(df)
        if 'torre' in df.columns and 'departamento' in df.columns and 'amortizacion' in df.columns:
            df['torre'] = pd.to_numeric(df['torre'], errors='coerce')
            df['departamento'] = pd.to_numeric(df['departamento'], errors='coerce')
            df['amortizacion'] = pd.to_numeric(df['amortizacion'], errors='coerce').fillna(0)
            dfs.append(df)

    if not dfs:
        return pd.DataFrame(columns=['torre', 'departamento', 'amortizacion'])

    df_all = pd.concat(dfs, ignore_index=True)
    df_all = df_all.dropna(subset=['torre', 'departamento'])
    df_sum = df_all.groupby(['torre', 'departamento'], as_index=False)['amortizacion'].sum()
    return df_sum[['torre', 'departamento', 'amortizacion']]

# ====================== OTROS ======================
def guardar_otros(df: pd.DataFrame, mes: str, anio: int, fecha_emision, fecha_vencimiento) -> str:
    """Guarda una hoja de otros conceptos con validación de solapamiento."""
    supabase = get_supabase()
    nombre_hoja = f"Otros {mes} {anio}"

    if existe_solapamiento_fechas("Otros", fecha_emision, fecha_vencimiento):
        raise ValueError(f"Las fechas {fecha_emision} - {fecha_vencimiento} se solapan con otra hoja de otros conceptos existente.")

    df_clean = limpiar_nan_para_json(df)
    datos = df_clean.to_dict(orient='records')
    supabase.table('otros').insert({
        'nombre_hoja': nombre_hoja,
        'mes': mes,
        'anio': anio,
        'datos': datos
    }).execute()

    registrar_fecha_programacion("Otros", nombre_hoja, fecha_emision, fecha_vencimiento)
    return nombre_hoja

def leer_otros_mes(mes: str, anio: int) -> pd.DataFrame:
    """
    Lee todas las hojas de otros conceptos del mes y año, concatena y agrupa por departamento sumando otros.
    """
    supabase = get_supabase()
    response = supabase.table('otros').select('datos').eq('mes', mes).eq('anio', anio).execute()
    if not response.data:
        return pd.DataFrame(columns=['torre', 'departamento', 'otros'])

    dfs = []
    for row in response.data:
        df = pd.DataFrame(row['datos'])
        df = limpiar_nombres_columnas(df)
        df.columns = df.columns.str.strip().str.lower()
        conceptos = ['cuota_extraordinarias', 'alquiler_parrilla', 'garantia', 'sala_zoom', 'alquiler_sillas', 'tuberias']
        for c in conceptos:
            if c not in df.columns:
                df[c] = 0
        for c in conceptos:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        df['otros'] = df[conceptos].sum(axis=1)

        if 'torre' in df.columns and 'departamento' in df.columns:
            df['torre'] = pd.to_numeric(df['torre'], errors='coerce')
            df['departamento'] = pd.to_numeric(df['departamento'], errors='coerce')
            dfs.append(df[['torre', 'departamento', 'otros']].copy())

    if not dfs:
        return pd.DataFrame(columns=['torre', 'departamento', 'otros'])

    df_all = pd.concat(dfs, ignore_index=True)
    df_all = df_all.dropna(subset=['torre', 'departamento'])
    df_sum = df_all.groupby(['torre', 'departamento'], as_index=False)['otros'].sum()
    return df_sum[['torre', 'departamento', 'otros']]

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

def leer_deuda_inicial(anio: int):
    nombre_hoja = f"Deuda Inicial {anio}"
    supabase = get_supabase()
    response = supabase.table('deuda_inicial').select('datos').eq('anio', anio).execute()
    if response.data:
        df = pd.DataFrame(response.data[0]['datos'])
        df = limpiar_nombres_columnas(df)
        return df
    # Fallback al año anterior
    if anio > 2020:
        response_ant = supabase.table('deuda_inicial').select('datos').eq('anio', anio-1).execute()
        if response_ant.data:
            st.info(f"Usando deuda del año anterior ({anio-1}) porque no se encontró para {anio}.")
            df = pd.DataFrame(response_ant.data[0]['datos'])
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
    # Como ahora puede haber múltiples hojas, se devuelve el rango más amplio? 
    # Por simplicidad, seguimos devolviendo el de la primera que encontremos.
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

# ====================== REPORTES MENSUALES ======================
def guardar_reporte_mensual(anio: int, mes: str, df: pd.DataFrame) -> None:
    supabase = get_supabase()
    datos_json = df.to_json(orient='records', date_format='iso')
    supabase.table('reportes_mensuales').upsert(
        {'anio': anio, 'mes': mes, 'datos_json': datos_json},
        on_conflict='anio, mes'
    ).execute()

def leer_reporte_mensual(anio: int, mes: str) -> pd.DataFrame:
    supabase = get_supabase()
    response = supabase.table('reportes_mensuales')\
        .select('datos_json')\
        .eq('anio', anio)\
        .eq('mes', mes)\
        .execute()
    if response.data:
        df = pd.read_json(response.data[0]['datos_json'], orient='records')
        for col in df.columns:
            if col not in ['fecha', 'n_operacion']:
                df[col] = pd.to_numeric(df[col], errors='ignore')
        return df
    return pd.DataFrame()

def existe_reporte_mensual(anio: int, mes: str) -> bool:
    supabase = get_supabase()
    response = supabase.table('reportes_mensuales')\
        .select('id')\
        .eq('anio', anio)\
        .eq('mes', mes)\
        .execute()
    return len(response.data) > 0

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
