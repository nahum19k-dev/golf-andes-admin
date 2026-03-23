import streamlit as st
import pandas as pd
import re
import gsheets
from datetime import datetime

st.set_page_config(page_title="Pagos Bancos", layout="wide")

st.title("💰 Pagos - Registro de Depósitos Bancos")

tab1, tab2 = st.tabs(["📤 Subir y Procesar", "📊 Visualizar Pagos Ordenados"])

# ====================== TAB 1: SUBIR Y PROCESAR ======================
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        mes = st.selectbox("Mes", ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                                   "Julio","Agosto","Setiembre","Octubre","Noviembre","Diciembre"])
    with col2:
        anio = st.number_input("Año", min_value=2025, max_value=2035, value=2026, step=1)

    periodo_key = f"{mes.upper()}_{int(anio)}"

    uploaded_file = st.file_uploader(
        "Sube el archivo Excel de DATA BANCOS",
        type=["xlsx"]
    )

    if uploaded_file is not None:
        try:
            # === LECTURA DEL EXCEL ===
            df_raw = pd.read_excel(uploaded_file, sheet_name=0, header=0)

            # Eliminar columna vacía del principio y limpiar nombres
            df_raw = df_raw.iloc[:, 1:]                    # quita la primera columna NaN/Unnamed
            df_raw.columns = df_raw.columns.str.strip().str.replace('\n', ' ').str.replace('\r', '')

            # Renombrar columnas clave
            df = df_raw.rename(columns={
                'Fecha': 'fecha',
                'DESCRIPCION OPERACIONES': 'descripcion',
                'N°OPERACIÓN': 'n_operacion',
                'INGRESOS': 'ingresos'
            })

            # Extraer código (últimos 5 dígitos)
            def extraer_codigo(desc):
                if pd.isna(desc):
                    return None
                match = re.search(r'(\d{5})$', str(desc).strip())
                return match.group(1) if match else None

            df['codigo'] = df['descripcion'].apply(extraer_codigo)

            # Cargar propietarios
            prop = gsheets.leer_propietarios()
            if prop.empty:
                st.error("No se pudo cargar Propietarios")
                st.stop()

            # Detectar columna de departamento
            depto_col = None
            posibles_nombres = ['departamento', 'dpto', 'depto', 'N°DPTO', 'depto_numero']
            for col in prop.columns:
                if col.lower() in posibles_nombres or col.lower() in [p.lower() for p in posibles_nombres]:
                    depto_col = col
                    break
            if depto_col is None:
                st.error("No se encontró columna de departamento en Propietarios. Las columnas disponibles son: " + ", ".join(prop.columns))
                st.stop()

            # Detectar columna de código (puede ser 'codigo' o 'codigo_prop' etc.)
            codigo_col = 'codigo'
            if codigo_col not in prop.columns:
                for col in prop.columns:
                    if 'codigo' in col.lower():
                        codigo_col = col
                        break
                else:
                    st.error("No se encontró columna de código en Propietarios")
                    st.stop()

            # Seleccionar columnas necesarias para el merge
            columnas_merge = [codigo_col, 'torre', depto_col, 'nombre']
            dni_col = next((c for c in prop.columns if 'dni' in c.lower()), None)
            if dni_col:
                columnas_merge.append(dni_col)

            # Realizar merge
            df_merged = df.merge(prop[columnas_merge], left_on='codigo', right_on=codigo_col, how='left')

            # Renombrar columna de departamento para consistencia interna
            if depto_col != 'departamento':
                df_merged.rename(columns={depto_col: 'departamento'}, inplace=True)

            # Separar coincidentes y no coincidentes
            df_coinciden = df_merged[df_merged['torre'].notna()].copy()
            df_no_coinciden = df_merged[df_merged['torre'].isna()].copy()

            # Ordenar coincidentes
            for col in ['torre', 'departamento']:
                if col in df_coinciden.columns:
                    df_coinciden[col] = pd.to_numeric(df_coinciden[col], errors='coerce')

            df_coinciden = df_coinciden.sort_values(by=['torre', 'departamento', 'nombre'])

            # Mostrar resultados
            st.subheader("✅ Resultado del procesamiento")

            if not df_coinciden.empty:
                st.markdown("### Pagos que coincidieron")
                cols = ['fecha', 'descripcion', 'codigo', 'torre', 'departamento', 'nombre', 'ingresos']
                if dni_col:
                    cols.insert(6, dni_col)  # inserta DNI después de nombre
                st.dataframe(df_coinciden[cols].fillna(""), use_container_width=True, height=400)

            if not df_no_coinciden.empty:
                st.markdown("### Pagos sin coincidencia (revisar)")
                st.dataframe(df_no_coinciden[['fecha', 'descripcion', 'codigo', 'ingresos']].fillna(""),
                             use_container_width=True, height=300)

            # Botón guardar
            if st.button("💾 Guardar en Google Sheets", type="primary"):
                try:
                    # Verificar que la función existe en gsheets
                    if not hasattr(gsheets, 'crear_y_guardar_programacion'):
                        st.error("La función 'crear_y_guardar_programacion' no está definida en gsheets.py. Verifica el archivo.")
                    else:
                        nombre_hoja = gsheets.crear_y_guardar_programacion(
                            df=df_coinciden,
                            periodo_key=periodo_key,
                            mes=mes,
                            anio=int(anio)
                        )
                        st.success(f"Guardado en hoja: **{nombre_hoja}**")
                except Exception as e:
                    st.error(f"Error al guardar en Google Sheets: {str(e)}")

        except Exception as e:
            st.error(f"Error al procesar: {str(e)}")

# ====================== TAB 2: VISUALIZAR ORDENADO ======================
with tab2:
    st.subheader("📊 Visualizar Pagos Ordenados")

    # Si ya se procesó un archivo, usar df_coinciden
    if 'df_coinciden' in locals() and not df_coinciden.empty:
        df_viz = df_coinciden.copy()
        df_viz = df_viz.rename(columns={
            'fecha': 'FECHA',
            'torre': 'TORRE',
            'departamento': 'N°DPTO',
            'nombre': 'NOMBRES Y APELLIDOS',
            'ingresos': 'PAGOS',
            'n_operacion': 'N°OPERACIÓN'
        })
        if dni_col:
            df_viz = df_viz.rename(columns={dni_col: 'DNI'})

        df_viz['SITUACIÓN'] = "PROPIETARIO"

        # Filtro por fecha
        df_viz['FECHA'] = pd.to_datetime(df_viz['FECHA'], errors='coerce')
        fecha_min = st.date_input("Desde", value=df_viz['FECHA'].min().date() if not df_viz.empty else datetime(2026,1,1))
        fecha_max = st.date_input("Hasta", value=df_viz['FECHA'].max().date() if not df_viz.empty else datetime(2026,1,31))

        mask = (df_viz['FECHA'].dt.date >= fecha_min) & (df_viz['FECHA'].dt.date <= fecha_max)
        df_filtrado = df_viz[mask]

        # Mostrar tabla exacta
        columnas_final = ['FECHA', 'TORRE', 'N°DPTO', 'DNI', 'NOMBRES Y APELLIDOS', 'SITUACIÓN', 'PAGOS', 'N°OPERACIÓN']
        st.dataframe(df_filtrado[columnas_final].fillna(""), use_container_width=True, height=600)
    else:
        st.info("Primero sube un archivo en la pestaña 'Subir y Procesar' para visualizar los datos.")
