import streamlit as st
import pandas as pd
import numpy as np
import gsheets
from datetime import datetime, timedelta

st.set_page_config(page_title="Programación", page_icon="📅", layout="wide")

st.title("📅 Programación Mensual - Subir desde Excel")

# Crear pestañas principales
tab1, tab2 = st.tabs(["📊 Programación Mantenimiento", "💰 Amortización"])

# ====================== TAB 1: PROGRAMACIÓN MANTENIMIENTO ======================
with tab1:
    # Sub‑pestañas dentro de Programación Mantenimiento
    subtab1, subtab2 = st.tabs(["📤 Subir y Procesar", "📊 Visualizar Programación"])

    # ---------- SUBTAB 1: SUBIR Y PROCESAR ----------
    with subtab1:
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

        mes_num = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Setiembre","Octubre","Noviembre","Diciembre"].index(mes) + 1
        fecha_emision_def = datetime(anio, mes_num, 23)
        fecha_venc_def = fecha_emision_def + timedelta(days=15)

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            fecha_emision = st.date_input("Fecha de Emisión", value=fecha_emision_def)
        with col_f2:
            fecha_vencimiento = st.date_input("Fecha de Vencimiento", value=fecha_venc_def)

        st.divider()
        st.subheader("Subir archivo Excel de mantenimiento mensual")
        uploaded_file = st.file_uploader(
            "Elige el archivo .xlsx (formato: TORRE, N°DPTO, CODIGO PROPIETARIO, DNI, APELLIDOS Y NOMBRES, MANTENIMIENTO)",
            type=["xlsx"],
            key="det_cuotas"
        )
        df = None

        if uploaded_file is not None:
            try:
                # Leer el archivo asumiendo que la primera fila contiene los encabezados
                df = pd.read_excel(uploaded_file, sheet_name=0, header=0)
                df.columns = df.columns.str.strip().str.replace('\n', ' ')

                # Eliminar columnas completamente vacías
                df = df.dropna(axis=1, how='all')
                # Eliminar filas vacías (opcional)
                df = df.dropna(how='all')

                # Mostrar las columnas detectadas para depuración (opcional, se puede comentar)
                # st.write("Columnas detectadas:", list(df.columns))

                # Buscar las columnas necesarias (insensible a mayúsculas)
                col_torre = None
                col_dpto = None
                col_codigo = None
                col_dni = None
                col_nombre = None
                col_monto = None

                for col in df.columns:
                    col_low = col.lower()
                    if 'torre' in col_low:
                        col_torre = col
                    elif 'dpto' in col_low or 'n°dpto' in col_low or 'departamento' in col_low:
                        col_dpto = col
                    elif 'codigo' in col_low:
                        col_codigo = col
                    elif 'dni' in col_low:
                        col_dni = col
                    elif 'apellidos' in col_low or 'nombre' in col_low:
                        col_nombre = col
                    elif 'mantenimiento' in col_low or 'monto' in col_low or 'total' in col_low:
                        col_monto = col

                # Verificar que se encontraron las columnas esenciales
                if col_torre is None or col_dpto is None or col_monto is None:
                    st.error("No se encontraron las columnas necesarias (TORRE, N°DPTO, MANTENIMIENTO). Verifica el archivo.")
                    st.stop()

                # Seleccionar y renombrar columnas
                df_seleccionado = pd.DataFrame()
                df_seleccionado['torre'] = df[col_torre]
                df_seleccionado['departamento'] = df[col_dpto]
                df_seleccionado['Mantenimiento'] = df[col_monto]

                # Si existen columnas de código, dni, nombre, también las guardamos (para referencia, aunque no se usarán en el guardado final)
                if col_codigo:
                    df_seleccionado['codigo'] = df[col_codigo]
                if col_dni:
                    df_seleccionado['dni'] = df[col_dni]
                if col_nombre:
                    df_seleccionado['nombre'] = df[col_nombre]

                # Convertir columnas numéricas
                df_seleccionado['torre'] = pd.to_numeric(df_seleccionado['torre'], errors='coerce')
                df_seleccionado['departamento'] = pd.to_numeric(df_seleccionado['departamento'], errors='coerce')
                df_seleccionado['Mantenimiento'] = pd.to_numeric(df_seleccionado['Mantenimiento'], errors='coerce')

                # Eliminar filas con torre o departamento NaN (inválidos)
                df_seleccionado = df_seleccionado.dropna(subset=['torre', 'departamento'])

                # Si hay filas con mantenimiento NaN, las dejamos (se rellenarán con 0 en el guardado)
                df_seleccionado['Mantenimiento'] = df_seleccionado['Mantenimiento'].fillna(0)

                st.success(f"Archivo leído: {len(df_seleccionado)} filas")
                st.write("Vista previa (primeras 8 filas):")
                st.dataframe(df_seleccionado.head(8))

                # Para guardar, usaremos solo torre, departamento, Mantenimiento
                df_guardar = df_seleccionado[['torre', 'departamento', 'Mantenimiento']].copy()

            except Exception as e:
                st.error(f"Error al leer el archivo: {e}")

        if df is not None:
            periodo_key = f"{mes.upper()}_{int(anio)}"
            if gsheets.existe_programacion(periodo_key):
                st.error(f"⚠️ Ya existe una programación para {mes} {anio}")
                st.info("Cambia el mes/año o elimina manualmente la hoja en Google Sheets si quieres sobrescribir.")
            else:
                if st.button("Guardar en Google Sheets", type="primary", key="guardar_det_cuotas"):
                    with st.spinner("Guardando..."):
                        try:
                            nombre_hoja = gsheets.crear_y_guardar_programacion(
                                df_guardar, periodo_key, mes, int(anio)
                            )
                            st.success(f"Guardado en hoja: **{nombre_hoja}**")
                        except Exception as e:
                            st.error(f"Error al guardar: {e}")

    # ---------- SUBTAB 2: VISUALIZAR PROGRAMACIÓN ----------
    with subtab2:
        st.subheader("Programaciones Guardadas")

        try:
            hojas_prog = gsheets.listar_hojas_programacion()
        except Exception as e:
            st.error(f"No se pudo conectar con Google Sheets: {e}")
            hojas_prog = []

        if hojas_prog:
            hoja_seleccionada = st.selectbox("Selecciona la programación:", hojas_prog, key="select_prog")
            df_guardado = gsheets.leer_hoja_programacion(hoja_seleccionada)

            if not df_guardado.empty:
                # Eliminar duplicados por torre/departamento (por si hubiera filas repetidas en la hoja)
                df_guardado = df_guardado.drop_duplicates(subset=['torre', 'departamento'], keep='first')

                # Cargar propietarios
                prop = gsheets.leer_propietarios()
                if not prop.empty:
                    # Detectar columnas de torre y departamento en prop
                    col_torre_prop = None
                    col_dpto_prop = None
                    for col in prop.columns:
                        if col.lower() == 'torre':
                            col_torre_prop = col
                        elif col.lower() in ['departamento', 'dpto', 'n°dpto']:
                            col_dpto_prop = col
                    if col_torre_prop is None or col_dpto_prop is None:
                        st.warning("No se pudieron identificar las columnas de torre y departamento en Propietarios. No se mostrarán nombres ni DNI.")
                        df_mostrar = df_guardado.copy()
                    else:
                        # Preparar propietarios para merge, eliminando duplicados
                        prop_sub = prop[[col_torre_prop, col_dpto_prop, 'nombre', 'dni']].copy()
                        prop_sub.rename(columns={col_torre_prop: 'torre', col_dpto_prop: 'departamento'}, inplace=True)
                        # Convertir a numérico para merge correcto
                        prop_sub['torre'] = pd.to_numeric(prop_sub['torre'], errors='coerce')
                        prop_sub['departamento'] = pd.to_numeric(prop_sub['departamento'], errors='coerce')
                        # 🔥 ELIMINAR DUPLICADOS EN PROPIETARIOS (misma torre/departamento)
                        prop_sub = prop_sub.drop_duplicates(subset=['torre', 'departamento'], keep='first')
                        # Realizar merge
                        df_mostrar = df_guardado.merge(prop_sub, on=['torre', 'departamento'], how='left')
                else:
                    st.warning("No se pudo cargar la lista de propietarios. Se mostrarán solo torre y departamento.")
                    df_mostrar = df_guardado.copy()

                # Función para formatear números con dos decimales (para la columna Mantenimiento)
                def formatear_numero(valor):
                    try:
                        if pd.isna(valor):
                            return ""
                        num = float(valor)
                        if num.is_integer():
                            return str(int(num))
                        else:
                            return f"{num:.2f}"
                    except (ValueError, TypeError):
                        return str(valor)

                # Aplicar formateo a la columna Mantenimiento (si existe)
                if 'Mantenimiento' in df_mostrar.columns:
                    df_mostrar['Mantenimiento'] = df_mostrar['Mantenimiento'].apply(formatear_numero)
                # Asegurar que torre y departamento sean strings (sin decimales)
                for col in ['torre', 'departamento']:
                    if col in df_mostrar.columns:
                        df_mostrar[col] = df_mostrar[col].apply(formatear_numero)

                # Renombrar columnas para visualización amigable
                mapeo = {
                    'torre': 'TORRE',
                    'departamento': 'N°DPTO',
                    'nombre': 'NOMBRES Y APELLIDOS',
                    'dni': 'DNI',
                    'Mantenimiento': 'MANTENIMIENTO (S/)'
                }
                df_viz = df_mostrar.rename(columns={col: mapeo[col] for col in df_mostrar.columns if col in mapeo})
                df_viz = df_viz.loc[:, ~df_viz.columns.duplicated()]

                columnas_final = ['TORRE', 'N°DPTO', 'NOMBRES Y APELLIDOS', 'DNI', 'MANTENIMIENTO (S/)']
                columnas_existentes = [col for col in columnas_final if col in df_viz.columns]
                if 'NOMBRES Y APELLIDOS' not in df_viz.columns:
                    columnas_existentes = ['TORRE', 'N°DPTO', 'MANTENIMIENTO (S/)']
                df_viz = df_viz[columnas_existentes]

                # ---------- CALCULAR TOTAL DE MANTENIMIENTO ----------
                def extraer_numero(val):
                    if pd.isna(val) or val == '':
                        return 0.0
                    s = str(val).strip()
                    s = s.replace(',', '').replace(' ', '').replace('S/', '').replace('$', '')
                    try:
                        return float(s)
                    except:
                        return 0.0

                total_mantenimiento = df_viz['MANTENIMIENTO (S/)'].apply(extraer_numero).sum()
                total_formateado = f"S/ {total_mantenimiento:,.2f}"

                # Mostrar indicador de total
                st.metric("💰 Total de Mantenimiento", total_formateado)
                st.markdown("---")

                # Índice empezando en 1
                df_viz = df_viz.reset_index(drop=True)
                df_viz.index = df_viz.index + 1

                st.dataframe(df_viz.fillna(""), use_container_width=True, height=600)

                # Botón de descarga
                import io
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_viz.to_excel(writer, index=False, sheet_name=hoja_seleccionada)
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
            st.info("No hay programaciones guardadas. Sube un archivo en la pestaña 'Subir y Procesar' para crear una.")

# ====================== TAB 2: AMORTIZACIÓN ======================
with tab2:
    # Sub‑pestañas dentro de Amortización
    subtab1, subtab2 = st.tabs(["📤 Subir y Procesar", "📊 Visualizar Amortización"])

    # ---------- SUBTAB 1: SUBIR Y PROCESAR ----------
    with subtab1:
        col1, col2 = st.columns(2)
        with col1:
            mes_amort = st.selectbox(
                "Mes",
                ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                 "Julio","Agosto","Setiembre","Octubre","Noviembre","Diciembre"],
                key="mes_amort"
            )
        with col2:
            anio_amort = st.number_input("Año", min_value=2025, max_value=2035, value=2026, step=1, key="anio_amort")

        with st.expander("ℹ️ Formato esperado del archivo Excel"):
            st.info("""
            El archivo debe contener las siguientes columnas (en cualquier orden):
            - ITEM (opcional)
            - TORRE
            - N°DPTO
            - CODIGO
            - DNI
            - APELLIDOS Y NOMBRES
            - AMORTIZACION CONVENIO

            El sistema buscará automáticamente la fila que contiene los encabezados y eliminará las filas de total.
            """)

        uploaded_file_amort = st.file_uploader("Elige el archivo Excel de amortización", type=["xlsx"], key="amort_file")

        df_amort = None

        if uploaded_file_amort is not None:
            try:
                df_raw = pd.read_excel(uploaded_file_amort, sheet_name=0, header=None)

                start_row = None
                for i in range(len(df_raw)):
                    row_str = ' '.join(df_raw.iloc[i].astype(str))
                    if 'TORRE' in row_str or 'N°DPTO' in row_str or 'ITEM' in row_str:
                        start_row = i
                        break

                if start_row is None:
                    st.error("No se encontró la fila con encabezados (buscando 'TORRE' o 'N°DPTO').")
                else:
                    df_amort = pd.read_excel(uploaded_file_amort, sheet_name=0, skiprows=start_row)
                    df_amort.columns = df_amort.columns.str.strip().str.replace('\n', ' ')
                    # Eliminar columnas Unnamed
                    df_amort = df_amort.loc[:, ~df_amort.columns.str.contains('^Unnamed', case=False)]
                    # Eliminar filas con TOTAL
                    if 'ITEM' in df_amort.columns:
                        df_amort = df_amort[~df_amort['ITEM'].astype(str).str.contains('TOTAL', case=False, na=False)]
                    if 'APELLIDOS  Y  NOMBRES' in df_amort.columns:
                        df_amort = df_amort[~df_amort['APELLIDOS  Y  NOMBRES'].astype(str).str.contains('TOTAL', case=False, na=False)]
                    # Eliminar filas sin torre o departamento
                    if 'TORRE' in df_amort.columns:
                        df_amort = df_amort.dropna(subset=['TORRE'])
                    if 'N°DPTO' in df_amort.columns:
                        df_amort = df_amort.dropna(subset=['N°DPTO'])
                    # Resetear índice para que empiece en 1
                    df_amort = df_amort.reset_index(drop=True)
                    df_amort.index = df_amort.index + 1
                    st.success(f"Archivo leído correctamente: {len(df_amort)} filas válidas")
                    st.write("Vista previa (primeras 10 filas):")
                    st.dataframe(df_amort.head(10))

            except Exception as e:
                st.error(f"Error al leer el archivo: {str(e)}")

        if df_amort is not None and not df_amort.empty:
            if st.button("Guardar en Google Sheets (Amortización)", type="primary", key="guardar_amort"):
                with st.spinner("Guardando datos de amortización..."):
                    try:
                        nombre_hoja = gsheets.guardar_amortizacion(
                            df_amort, mes_amort, int(anio_amort)
                        )
                        st.success(f"¡Guardado correctamente en hoja: **{nombre_hoja}**!")
                    except Exception as e:
                        st.error(f"Error al guardar: {str(e)}")
        elif df_amort is not None and df_amort.empty:
            st.warning("No se encontraron datos válidos después de filtrar. Verifica el archivo.")

    # ---------- SUBTAB 2: VISUALIZAR AMORTIZACIÓN ----------
    with subtab2:
        st.subheader("Amortizaciones Guardadas")

        try:
            hojas_amort = gsheets.listar_hojas_amortizacion()
        except Exception as e:
            st.error(f"No se pudo conectar con Google Sheets: {e}")
            hojas_amort = []

        if hojas_amort:
            hoja_seleccionada = st.selectbox("Selecciona el período de amortización:", hojas_amort, key="select_amort")
            df_guardado = gsheets.leer_hoja_amortizacion(hoja_seleccionada)

            if not df_guardado.empty:
                # Función para formatear números sin .0
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

                for col in ['TORRE', 'N°DPTO', 'CODIGO', 'AMORTIZACION CONVENIO']:
                    if col in df_guardado.columns:
                        df_guardado[col] = df_guardado[col].apply(formatear_numero)

                # ---------- CALCULAR TOTAL DE AMORTIZACIÓN ----------
                def extraer_numero(val):
                    if pd.isna(val) or val == '':
                        return 0.0
                    s = str(val).strip()
                    s = s.replace(',', '').replace(' ', '').replace('S/', '').replace('$', '')
                    try:
                        return float(s)
                    except:
                        return 0.0

                total_amort = df_guardado['AMORTIZACION CONVENIO'].apply(extraer_numero).sum()
                total_formateado = f"S/ {total_amort:,.2f}"

                # Mostrar indicador de total
                st.metric("💰 Total de Amortización por Convenio", total_formateado)
                st.markdown("---")

                # Índice empezando en 1
                df_guardado = df_guardado.reset_index(drop=True)
                df_guardado.index = df_guardado.index + 1

                st.dataframe(df_guardado.fillna(""), use_container_width=True, height=600)

                # Botón de descarga
                import io
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_guardado.to_excel(writer, index=False, sheet_name=hoja_seleccionada)
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
            st.info("No hay hojas de amortización guardadas. Sube un archivo en la pestaña 'Subir y Procesar' para crear una.")
