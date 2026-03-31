import streamlit as st
import pandas as pd
import re
import supabase_client as gsheets  # Cambiamos la importación para usar Supabase
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
            # Leer todas las celdas como string para evitar interpretaciones automáticas
            df_raw = pd.read_excel(uploaded_file, sheet_name=0, header=0, dtype=str)

            # Eliminar columna vacía del principio y limpiar nombres
            df_raw = df_raw.iloc[:, 1:]                    # quita la primera columna NaN/Unnamed
            df_raw.columns = df_raw.columns.str.strip().str.replace('\n', ' ').str.replace('\r', '')

            # Mapeo flexible de columnas (ampliamos para los nuevos conceptos)
            rename_map = {}
            for col in df_raw.columns:
                col_low = col.lower()
                if 'fecha' in col_low:
                    rename_map[col] = 'fecha'
                elif 'descripcion' in col_low or 'operaciones' in col_low:
                    rename_map[col] = 'descripcion'
                elif 'operación' in col_low or 'n°operación' in col_low:
                    rename_map[col] = 'n_operacion'
                elif 'mantenimiento' in col_low:
                    rename_map[col] = 'mantenimiento'
                elif 'amortizacion' in col_low:
                    rename_map[col] = 'amortizacion'
                elif 'medidor' in col_low:
                    rename_map[col] = 'medidor'
                elif 'cuota extraordinaria' in col_low or 'extraordinarias' in col_low:
                    rename_map[col] = 'cuota_extraordinaria'
                elif 'parrilla' in col_low:
                    rename_map[col] = 'alquiler_parrilla'
                elif 'garantia' in col_low or 'garantía' in col_low:
                    rename_map[col] = 'garantia'
                elif 'sala zoom' in col_low or 'zoom' in col_low:
                    rename_map[col] = 'sala_zoom'
                elif 'sillas' in col_low:
                    rename_map[col] = 'alquiler_sillas'
                elif 'tuberias' in col_low or 'tuberías' in col_low:
                    rename_map[col] = 'tuberias'

            df = df_raw.rename(columns=rename_map)

            # Lista de todos los conceptos posibles
            conceptos = ['mantenimiento', 'amortizacion', 'medidor',
                         'cuota_extraordinaria', 'alquiler_parrilla', 'garantia',
                         'sala_zoom', 'alquiler_sillas', 'tuberias']

            # Asegurar que existan todas las columnas de conceptos
            for col in conceptos:
                if col not in df.columns:
                    df[col] = 0

            # Convertir a números, reemplazar vacíos por 0
            for col in conceptos:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            # Calcular monto total como suma de todos los conceptos
            df['ingresos'] = df[conceptos].sum(axis=1)

            # Extraer código (últimos 5 dígitos) desde la descripción
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

            # Detectar columna de código
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

            # ========== MOSTRAR INDICADORES DE TOTALES ==========
            st.subheader("📊 Resumen de Pagos Procesados")
            # Calcular totales por concepto
            totales = {}
            for col in conceptos + ['ingresos']:
                if col in df_coinciden.columns:
                    totales[col] = df_coinciden[col].sum()
                else:
                    totales[col] = 0

            # Mostrar en columnas (agrupamos de a 3)
            conceptos_mostrar = conceptos + ['ingresos']
            nombres_mostrar = {
                'mantenimiento': 'Mantenimiento',
                'amortizacion': 'Amortización',
                'medidor': 'Medidor',
                'cuota_extraordinaria': 'Cuota Extraordinaria',
                'alquiler_parrilla': 'Alquiler Parrilla',
                'garantia': 'Garantía',
                'sala_zoom': 'Sala Zoom',
                'alquiler_sillas': 'Alquiler Sillas',
                'tuberias': 'Tuberías',
                'ingresos': 'TOTAL PAGADO'
            }
            # Filtrar solo los que tienen valor >0 o que queremos mostrar
            cols_mostrar = [c for c in conceptos_mostrar if totales.get(c, 0) != 0 or c == 'ingresos']
            # Distribuir en filas de 3 columnas
            for i in range(0, len(cols_mostrar), 3):
                cols = st.columns(3)
                for j, concepto in enumerate(cols_mostrar[i:i+3]):
                    with cols[j]:
                        st.metric(
                            label=nombres_mostrar.get(concepto, concepto.upper()),
                            value=f"S/ {totales[concepto]:,.2f}"
                        )
            st.markdown("---")
            # =============================================

            # Mostrar resultados
            st.subheader("✅ Resultado del procesamiento")

            if not df_coinciden.empty:
                st.markdown("### Pagos que coincidieron")
                cols_mostrar = ['fecha', 'descripcion', 'codigo', 'torre', 'departamento', 'nombre', 'mantenimiento', 'amortizacion', 'medidor', 'ingresos']
                if dni_col:
                    cols_mostrar.insert(6, dni_col)
                # Añadir los nuevos conceptos si existen
                for c in conceptos:
                    if c not in cols_mostrar and c in df_coinciden.columns:
                        cols_mostrar.append(c)
                df_mostrar = df_coinciden[cols_mostrar].copy()
                # Formatear números para mostrar con dos decimales
                for col in df_mostrar.columns:
                    if col in conceptos + ['ingresos']:
                        df_mostrar[col] = df_mostrar[col].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "")
                st.dataframe(df_mostrar.fillna(""), use_container_width=True, height=400)

            if not df_no_coinciden.empty:
                st.markdown("### Pagos sin coincidencia (revisar)")
                cols_no = ['fecha', 'descripcion', 'codigo', 'mantenimiento', 'amortizacion', 'medidor', 'ingresos']
                st.dataframe(df_no_coinciden[cols_no].fillna(""), use_container_width=True, height=300)

            # Botón guardar
            if st.button("💾 Guardar en Google Sheets", type="primary"):
                try:
                    # Seleccionar columnas a guardar
                    columnas_guardar = ['fecha', 'descripcion', 'codigo', 'torre', 'departamento', 'nombre', 'dni', 'n_operacion'] + conceptos
                    cols_existentes = [c for c in columnas_guardar if c in df_coinciden.columns]
                    df_guardar = df_coinciden[cols_existentes].copy()

                    st.info(f"📊 Se van a guardar **{len(df_guardar)}** filas coincidentes.")

                    # --- LIMPIEZA ROBUSTA ANTES DE GUARDAR ---
                    # 1. Limpiar espacios en columnas de texto
                    for col in ['descripcion', 'codigo', 'nombre', 'dni', 'n_operacion']:
                        if col in df_guardar.columns:
                            df_guardar[col] = df_guardar[col].astype(str).str.strip().fillna('')

                    # 2. FECHA: manejo de números de Excel y strings
                    if 'fecha' in df_guardar.columns:
                        def convert_fecha(val):
                            if pd.isna(val):
                                return None
                            if isinstance(val, (int, float)):
                                try:
                                    return pd.to_datetime(val, unit='D', origin='1899-12-30')
                                except:
                                    return None
                            s = str(val).strip()
                            for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y'):
                                try:
                                    return pd.to_datetime(s, format=fmt, errors='raise')
                                except:
                                    continue
                            try:
                                return pd.to_datetime(s, dayfirst=True, errors='coerce')
                            except:
                                return None

                        df_guardar['fecha_dt'] = df_guardar['fecha'].apply(convert_fecha)
                        invalid_mask = df_guardar['fecha_dt'].isna()
                        if invalid_mask.any():
                            st.warning(f"⚠️ {invalid_mask.sum()} filas tienen fecha inválida y se guardarán sin fecha.")
                            problematic = df_guardar[invalid_mask][['fecha']].head(10)
                            st.write("Ejemplos de valores no reconocidos:")
                            st.dataframe(problematic)
                        df_guardar['fecha'] = df_guardar['fecha_dt'].dt.strftime('%Y-%m-%d').fillna('')
                        df_guardar.drop('fecha_dt', axis=1, inplace=True)

                    # 3. Columnas numéricas: asegurar float y reemplazar NaN por 0
                    for col in conceptos:
                        if col in df_guardar.columns:
                            df_guardar[col] = pd.to_numeric(df_guardar[col], errors='coerce').fillna(0)

                    # 4. Asegurar que torre y departamento sean enteros
                    for col in ['torre', 'departamento']:
                        if col in df_guardar.columns:
                            df_guardar[col] = pd.to_numeric(df_guardar[col], errors='coerce').fillna(0).astype(int)

                    # Mostrar vista previa
                    st.write("**Vista previa de los datos a guardar (primeras 5 filas):**")
                    st.dataframe(df_guardar.head(5))

                    # Guardar en Supabase
                    nombre_hoja = gsheets.guardar_pagos(
                        df=df_guardar,
                        mes=mes,
                        anio=int(anio)
                    )
                    st.success(f"✅ Guardado en hoja: **{nombre_hoja}** (filas: {len(df_guardar)})")
                except Exception as e:
                    st.error(f"Error al guardar: {str(e)}")
                    st.error("Detalles para depuración:")
                    st.write("Columnas:", list(df_guardar.columns))
                    st.write("Tipos:\n", df_guardar.dtypes)
                    st.write("Primeras 3 filas:")
                    st.dataframe(df_guardar.head(3))

        except Exception as e:
            st.error(f"Error al procesar el archivo: {str(e)}")

# ====================== TAB 2: VISUALIZAR PAGOS ORDENADOS ======================
with tab2:
    st.subheader("📊 Visualizar Pagos Ordenados")

    try:
        hojas_pagos = gsheets.listar_hojas_pagos()
    except Exception as e:
        st.error(f"No se pudo conectar con Supabase: {e}")
        hojas_pagos = []

    if hojas_pagos:
        hoja_seleccionada = st.selectbox("Selecciona el período de pagos:", hojas_pagos)
        df_guardado = gsheets.leer_hoja_pagos(hoja_seleccionada)

        if not df_guardado.empty:
            # Convertir columnas a tipos adecuados
            conceptos = ['mantenimiento', 'amortizacion', 'medidor', 'cuota_extraordinaria',
                         'alquiler_parrilla', 'garantia', 'sala_zoom', 'alquiler_sillas', 'tuberias']
            # Asegurar que existan
            for col in conceptos:
                if col not in df_guardado.columns:
                    df_guardado[col] = 0
            # Convertir a numérico
            for col in conceptos:
                df_guardado[col] = pd.to_numeric(df_guardado[col], errors='coerce').fillna(0)
            # Calcular ingresos si no existe
            if 'ingresos' not in df_guardado.columns:
                df_guardado['ingresos'] = df_guardado[conceptos].sum(axis=1)

            # Mapeo de nombres de columna al formato deseado
            mapeo = {
                'fecha': 'FECHA',
                'torre': 'TORRE',
                'departamento': 'N°DPTO',
                'nombre': 'NOMBRES Y APELLIDOS',
                'ingresos': 'PAGOS',
                'n_operacion': 'N°OPERACIÓN',
                'dni': 'DNI',
                'mantenimiento': 'MANTENIMIENTO',
                'amortizacion': 'AMORTIZACIÓN',
                'medidor': 'MEDIDOR',
                'cuota_extraordinaria': 'CUOTA EXTRAORDINARIA',
                'alquiler_parrilla': 'ALQUILER PARRILLA',
                'garantia': 'GARANTÍA',
                'sala_zoom': 'SALA ZOOM',
                'alquiler_sillas': 'ALQUILER SILLAS',
                'tuberias': 'TUBERÍAS'
            }
            df_viz = df_guardado.rename(columns={col: mapeo.get(col, col) for col in df_guardado.columns})

            # Agregar columnas faltantes
            if 'DNI' not in df_viz.columns:
                df_viz['DNI'] = ""
            if 'SITUACIÓN' not in df_viz.columns:
                df_viz['SITUACIÓN'] = "PROPIETARIO"

            # Convertir fechas a datetime para filtrar
            if 'FECHA' in df_viz.columns:
                df_viz['FECHA'] = pd.to_datetime(df_viz['FECHA'], errors='coerce')

            # Filtro por rango de fechas
            if 'FECHA' in df_viz.columns and not df_viz['FECHA'].isna().all():
                col_fecha, col_fecha2 = st.columns(2)
                with col_fecha:
                    fecha_min = st.date_input("Desde", value=df_viz['FECHA'].min().date())
                with col_fecha2:
                    fecha_max = st.date_input("Hasta", value=df_viz['FECHA'].max().date())
                mask = (df_viz['FECHA'].dt.date >= fecha_min) & (df_viz['FECHA'].dt.date <= fecha_max)
                df_filtrado = df_viz[mask].copy()
            else:
                df_filtrado = df_viz.copy()

            # ========== MOSTRAR INDICADORES DE TOTALES ==========
            st.subheader("📊 Resumen del Período Seleccionado")
            # Calcular totales por concepto
            totales = {}
            for col in conceptos + ['ingresos']:
                col_norm = col
                # Buscar el nombre de columna real en df_filtrado (puede estar ya mapeado)
                col_real = next((c for c in df_filtrado.columns if c.lower() == col_norm.lower() or c == mapeo.get(col_norm, col_norm)), None)
                if col_real and col_real in df_filtrado.columns:
                    totales[col_norm] = pd.to_numeric(df_filtrado[col_real], errors='coerce').sum()
                else:
                    totales[col_norm] = 0

            nombres_mostrar = {
                'mantenimiento': 'Mantenimiento',
                'amortizacion': 'Amortización',
                'medidor': 'Medidor',
                'cuota_extraordinaria': 'Cuota Extraordinaria',
                'alquiler_parrilla': 'Alquiler Parrilla',
                'garantia': 'Garantía',
                'sala_zoom': 'Sala Zoom',
                'alquiler_sillas': 'Alquiler Sillas',
                'tuberias': 'Tuberías',
                'ingresos': 'TOTAL PAGADO'
            }
            # Mostrar en filas de 3 columnas
            cols_mostrar = [c for c in conceptos + ['ingresos'] if totales.get(c, 0) != 0 or c == 'ingresos']
            for i in range(0, len(cols_mostrar), 3):
                cols = st.columns(3)
                for j, concepto in enumerate(cols_mostrar[i:i+3]):
                    with cols[j]:
                        st.metric(
                            label=nombres_mostrar.get(concepto, concepto.upper()),
                            value=f"S/ {totales[concepto]:,.2f}"
                        )
            st.markdown("---")
            # =============================================

            # Formateo de fechas
            if 'FECHA' in df_filtrado.columns and not df_filtrado['FECHA'].isna().all():
                df_filtrado['FECHA'] = df_filtrado['FECHA'].dt.strftime('%Y-%m-%d')

            # Función para formatear números sin decimales si son enteros
            def formatear_numero(valor):
                try:
                    if pd.isna(valor):
                        return ""
                    num = float(valor)
                    if num.is_integer():
                        return str(int(num))
                    else:
                        return str(num)
                except (ValueError, TypeError):
                    return str(valor)

            # Aplicar formateo a columnas numéricas
            for col in df_filtrado.columns:
                if col in ['TORRE', 'N°DPTO', 'PAGOS', 'N°OPERACIÓN', 'MANTENIMIENTO',
                           'AMORTIZACIÓN', 'MEDIDOR', 'CUOTA EXTRAORDINARIA',
                           'ALQUILER PARRILLA', 'GARANTÍA', 'SALA ZOOM',
                           'ALQUILER SILLAS', 'TUBERÍAS']:
                    df_filtrado[col] = df_filtrado[col].apply(formatear_numero)

            # Orden de columnas deseado
            columnas_final = ['FECHA', 'TORRE', 'N°DPTO', 'DNI', 'NOMBRES Y APELLIDOS', 'SITUACIÓN',
                              'MANTENIMIENTO', 'AMORTIZACIÓN', 'MEDIDOR', 'CUOTA EXTRAORDINARIA',
                              'ALQUILER PARRILLA', 'GARANTÍA', 'SALA ZOOM', 'ALQUILER SILLAS',
                              'TUBERÍAS', 'PAGOS', 'N°OPERACIÓN']
            columnas_existentes = [col for col in columnas_final if col in df_filtrado.columns]

            # Índice empezando en 1
            df_filtrado = df_filtrado.reset_index(drop=True)
            df_filtrado.index = df_filtrado.index + 1

            st.dataframe(df_filtrado[columnas_existentes].fillna(""), use_container_width=True, height=600)

            # Botón de descarga a Excel
            import io
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_filtrado[columnas_existentes].to_excel(writer, index=False, sheet_name=hoja_seleccionada)
            excel_data = output.getvalue()

            st.download_button(
                label="📥 Descargar como Excel",
                data=excel_data,
                file_name=f"{hoja_seleccionada}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # Botón eliminar
            st.markdown("---")
            if st.button("🗑️ Eliminar esta hoja de pagos", type="secondary", key=f"del_pagos_{hoja_seleccionada}"):
                nombre_parts = hoja_seleccionada.replace("Pagos ", "").split()
                if len(nombre_parts) >= 2:
                    mes_eliminado = nombre_parts[0]
                    anio_eliminado = nombre_parts[1]
                    mensaje = f"Eliminado: {mes_eliminado} {anio_eliminado}"
                else:
                    mensaje = f"Eliminado: {hoja_seleccionada}"

                if gsheets.eliminar_programacion(hoja_seleccionada):
                    st.success(f"✅ {mensaje}")
                    st.cache_resource.clear()
                    st.rerun()
                else:
                    st.error("No se pudo eliminar la hoja (puede que ya no exista).")
        else:
            st.info("La hoja seleccionada está vacía.")
    else:
        st.info("No hay hojas de pagos guardadas. Sube un archivo en la pestaña 'Subir y Procesar' para crear una.")
