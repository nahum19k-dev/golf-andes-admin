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
                    cols.insert(6, dni_col)
                st.dataframe(df_coinciden[cols].fillna(""), use_container_width=True, height=400)

            if not df_no_coinciden.empty:
                st.markdown("### Pagos sin coincidencia (revisar)")
                st.dataframe(df_no_coinciden[['fecha', 'descripcion', 'codigo', 'ingresos']].fillna(""),
                             use_container_width=True, height=300)

            # Botón guardar (usa la nueva función guardar_pagos)
            if st.button("💾 Guardar en Google Sheets", type="primary"):
                try:
                    nombre_hoja = gsheets.guardar_pagos(
                        df=df_coinciden,
                        mes=mes,
                        anio=int(anio)
                    )
                    st.success(f"Guardado en hoja: **{nombre_hoja}**")
                except Exception as e:
                    st.error(f"Error al guardar: {str(e)}")

        except Exception as e:
            st.error(f"Error al procesar: {str(e)}")
# ====================== TAB 2: VISUALIZAR PAGOS ORDENADOS ======================
with tab2:
    st.subheader("📊 Visualizar Pagos Ordenados")

    try:
        hojas_pagos = gsheets.listar_hojas_pagos()
    except Exception as e:
        st.error(f"No se pudo conectar con Google Sheets: {e}")
        hojas_pagos = []

    if hojas_pagos:
        hoja_seleccionada = st.selectbox("Selecciona el período de pagos:", hojas_pagos)
        df_guardado = gsheets.leer_hoja_pagos(hoja_seleccionada)

        if not df_guardado.empty:
            # Mapeo de nombres de columna al formato deseado
            mapeo = {
                'fecha': 'FECHA',
                'torre': 'TORRE',
                'departamento': 'N°DPTO',
                'nombre': 'NOMBRES Y APELLIDOS',
                'ingresos': 'PAGOS',
                'n_operacion': 'N°OPERACIÓN',
                'dni': 'DNI'
            }
            df_viz = df_guardado.rename(columns={col: mapeo[col] for col in df_guardado.columns if col in mapeo})

            if 'DNI' not in df_viz.columns:
                df_viz['DNI'] = ""
            if 'SITUACIÓN' not in df_viz.columns:
                df_viz['SITUACIÓN'] = "PROPIETARIO"

            # Filtro por fecha
            if 'FECHA' in df_viz.columns:
                df_viz['FECHA'] = pd.to_datetime(df_viz['FECHA'], errors='coerce')
                if not df_viz['FECHA'].isna().all():
                    col_fecha, col_fecha2 = st.columns(2)
                    with col_fecha:
                        fecha_min = st.date_input("Desde", value=df_viz['FECHA'].min().date())
                    with col_fecha2:
                        fecha_max = st.date_input("Hasta", value=df_viz['FECHA'].max().date())
                    mask = (df_viz['FECHA'].dt.date >= fecha_min) & (df_viz['FECHA'].dt.date <= fecha_max)
                    df_filtrado = df_viz[mask]
                else:
                    df_filtrado = df_viz
            else:
                df_filtrado = df_viz

            # Orden de columnas deseado
            columnas_final = ['FECHA', 'TORRE', 'N°DPTO', 'DNI', 'NOMBRES Y APELLIDOS', 'SITUACIÓN', 'PAGOS', 'N°OPERACIÓN']
            columnas_existentes = [col for col in columnas_final if col in df_filtrado.columns]
            st.dataframe(df_filtrado[columnas_existentes].fillna(""), use_container_width=True, height=600)

            # --- Botón de descarga (corregido) ---
            # Convertir DataFrame a bytes en memoria
            import io
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_filtrado.to_excel(writer, index=False, sheet_name=hoja_seleccionada)
            excel_data = output.getvalue()

            st.download_button(
                label="📥 Descargar como Excel",
                data=excel_data,
                file_name=f"{hoja_seleccionada}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("La hoja seleccionada está vacía.")
    else:
        st.info("No hay hojas de pagos guardadas. Sube un archivo en la pestaña 'Subir y Procesar' para crear una.")

