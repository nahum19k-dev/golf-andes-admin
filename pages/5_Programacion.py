import streamlit as st
import pandas as pd
import gsheets  # tu módulo que ya actualizamos

st.set_page_config(page_title="Programación", page_icon="📅", layout="wide")

st.title("📅 Programación Mensual - Subir desde Excel")

# 1. Selección del período (obligatorio)
col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    mes = st.selectbox(
        "Mes a programar",
        ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
         "Julio", "Agosto", "Setiembre", "Octubre", "Noviembre", "Diciembre"]
    )

with col2:
    anio = st.number_input("Año", min_value=2025, max_value=2035, value=2026, step=1)

with col3:
    n_deptos = st.number_input("N° Departamentos (divisor)", min_value=300, max_value=500, value=380, step=1)

# Fechas sugeridas (el usuario puede cambiarlas)
from datetime import datetime, timedelta
mes_num = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Setiembre","Octubre","Noviembre","Diciembre"].index(mes) + 1
fecha_emision_def = datetime(anio, mes_num, 23)
fecha_venc_def = fecha_emision_def + timedelta(days=15)

col_f1, col_f2 = st.columns(2)
with col_f1:
    fecha_emision = st.date_input("Fecha de Emisión", value=fecha_emision_def)
with col_f2:
    fecha_vencimiento = st.date_input("Fecha de Vencimiento", value=fecha_venc_def)

# 2. Subir el archivo
st.divider()
st.subheader("Subir archivo Excel de determinación de cuotas")

uploaded_file = st.file_uploader("Elige el archivo .xlsx", type=["xlsx"])

df = None

if uploaded_file is not None:
    try:
        # Leer sin encabezados iniciales (tu Excel tiene varias filas de título)
        df_raw = pd.read_excel(uploaded_file, sheet_name=0, header=None)

        # Buscar la fila donde aparece "Lote" (o ajusta según tu Excel)
        start_row = None
        for i in range(len(df_raw)):
            if "Lote" in df_raw.iloc[i].values:
                start_row = i
                break

        if start_row is None:
            st.error("No encontré la fila con encabezados (buscando 'Lote'). Verifica el formato del Excel.")
        else:
            # Leer desde esa fila como encabezados
            df = pd.read_excel(uploaded_file, sheet_name=0, skiprows=start_row)
            df.columns = df.columns.str.strip().str.replace('\n', ' ')  # limpiar nombres

            st.success(f"Archivo leído: {len(df)} filas detectadas")
            st.write("Vista previa (primeras 8 filas):")
            st.dataframe(df.head(8))

    except Exception as e:
        st.error(f"Error al leer el Excel: {str(e)}")

# 3. Botón de guardar (solo aparece si hay datos y no existe ya)
if df is not None:
    periodo_key = f"{mes.upper()}_{int(anio)}"

    if gsheets.existe_programacion(periodo_key):
        st.error(f"⚠️ Ya existe una programación para {mes} {anio}")
        st.info("Cambia el mes/año o elimina manualmente la hoja en Google Sheets si quieres sobrescribir.")
    else:
        if st.button("Guardar en Google Sheets", type="primary"):
            with st.spinner("Creando hoja y guardando..."):
                try:
                    nombre_hoja = gsheets.crear_y_guardar_programacion(
                        df=df,
                        periodo_key=periodo_key,
                        mes=mes,
                        anio=int(anio)
                    )
                    st.success("¡Guardado correctamente!")
                    st.markdown(f"Hoja creada en Google Sheets: **{nombre_hoja}**")
                except Exception as e:
                    st.error(f"Error al guardar: {str(e)}")
