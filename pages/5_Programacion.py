import streamlit as st
import pandas as pd
import numpy as np
import gsheets
import gspread          # <-- Importación necesaria para la excepción WorksheetNotFound
from datetime import datetime, timedelta

st.set_page_config(page_title="Programación", page_icon="📅", layout="wide")

st.title("📅 Programación Mensual - Subir desde Excel")

# Crear pestañas principales con nuevo orden
tab1, tab2, tab3, tab4 = st.tabs(["📊 Programación Mantenimiento", "💧 Medidores", "💰 Amortización", "📌 Otros"])

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
                df = pd.read_excel(uploaded_file, sheet_name=0, header=0)
                df.columns = df.columns.str.strip().str.replace('\n', ' ')
                df = df.dropna(axis=1, how='all')
                df = df.dropna(how='all')

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

                if col_torre is None or col_dpto is None or col_monto is None:
                    st.error("No se encontraron las columnas necesarias (TORRE, N°DPTO, MANTENIMIENTO). Verifica el archivo.")
                    st.stop()

                df_seleccionado = pd.DataFrame()
                df_seleccionado['torre'] = df[col_torre]
                df_seleccionado['departamento'] = df[col_dpto]
                df_seleccionado['Mantenimiento'] = df[col_monto]

                if col_codigo:
                    df_seleccionado['codigo'] = df[col_codigo]
                if col_dni:
                    df_seleccionado['dni'] = df[col_dni]
                if col_nombre:
                    df_seleccionado['nombre'] = df[col_nombre]

                df_seleccionado['torre'] = pd.to_numeric(df_seleccionado['torre'], errors='coerce')
                df_seleccionado['departamento'] = pd.to_numeric(df_seleccionado['departamento'], errors='coerce')
                df_seleccionado['Mantenimiento'] = pd.to_numeric(df_seleccionado['Mantenimiento'], errors='coerce')
                df_seleccionado = df_seleccionado.dropna(subset=['torre', 'departamento'])
                df_seleccionado['Mantenimiento'] = df_seleccionado['Mantenimiento'].fillna(0)

                st.success(f"Archivo leído: {len(df_seleccionado)} filas")
                st.write("Vista previa (primeras 8 filas):")
                st.dataframe(df_seleccionado.head(8))

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
                df_guardado = df_guardado.drop_duplicates(subset=['torre', 'departamento'], keep='first')

                prop = gsheets.leer_propietarios()
                if not prop.empty:
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
                        prop_sub = prop[[col_torre_prop, col_dpto_prop, 'nombre', 'dni']].copy()
                        prop_sub.rename(columns={col_torre_prop: 'torre', col_dpto_prop: 'departamento'}, inplace=True)
                        prop_sub['torre'] = pd.to_numeric(prop_sub['torre'], errors='coerce')
                        prop_sub['departamento'] = pd.to_numeric(prop_sub['departamento'], errors='coerce')
                        prop_sub = prop_sub.drop_duplicates(subset=['torre', 'departamento'], keep='first')
                        df_mostrar = df_guardado.merge(prop_sub, on=['torre', 'departamento'], how='left')
                else:
                    st.warning("No se pudo cargar la lista de propietarios. Se mostrarán solo torre y departamento.")
                    df_mostrar = df_guardado.copy()

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

                if 'Mantenimiento' in df_mostrar.columns:
                    df_mostrar['Mantenimiento'] = df_mostrar['Mantenimiento'].apply(formatear_numero)
                for col in ['torre', 'departamento']:
                    if col in df_mostrar.columns:
                        df_mostrar[col] = df_mostrar[col].apply(formatear_numero)

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

                st.metric("💰 Total de Mantenimiento", total_formateado)
                st.markdown("---")

                df_viz = df_viz.reset_index(drop=True)
                df_viz.index = df_viz.index + 1

                st.dataframe(df_viz.fillna(""), use_container_width=True, height=600)

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

# ====================== TAB 2: MEDIDORES ======================
with tab2:
    # Sub‑pestañas dentro de Medidores
    subtab1, subtab2 = st.tabs(["📤 Subir y Procesar", "📊 Visualizar Medidores"])

    # ---------- SUBTAB 1: SUBIR Y PROCESAR ----------
    with subtab1:
        col1, col2 = st.columns(2)
        with col1:
            mes = st.selectbox("Mes", ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                                       "Julio","Agosto","Setiembre","Octubre","Noviembre","Diciembre"],
                               key="mes_medidor")
        with col2:
            anio = st.number_input("Año", min_value=2025, max_value=2035, value=2026, step=1,
                                   key="anio_medidor")

        uploaded_file = st.file_uploader("Sube el archivo Excel de MEDIDORES", type=["xlsx"],
                                         key="medidor_file")

        if uploaded_file is not None:
            try:
                # Leer archivo
                df_raw = pd.read_excel(uploaded_file, sheet_name=0, header=0)

                # Limpiar nombres de columnas
                df_raw.columns = df_raw.columns.str.strip().str.replace('\n', ' ').str.replace('\r', '')

                # Función para buscar columna con prioridad
                def find_column(priority_keywords, fallback_keywords=None):
                    for col in df_raw.columns:
                        col_lower = col.lower()
                        if any(pk.lower() in col_lower for pk in priority_keywords):
                            return col
                    if fallback_keywords:
                        for col in df_raw.columns:
                            col_lower = col.lower()
                            if any(fk.lower() in col_lower for fk in fallback_keywords):
                                return col
                    return None

                # Detectar columnas
                col_codigo = find_column(['codigo', 'código'])
                col_edificio = find_column(['edificio', 'torre'])
                col_dpto = find_column(['dpto', 'departamento'])
                col_med_inst = find_column(['medidor instalado'])  # solo esta
                col_n_med = find_column(['n°', 'nº', 'número'], fallback_keywords=['medidor'])
                col_monto = find_column(['monto a pagar', 'monto', 'pago'])

                # Crear DataFrame con nombres estandarizados
                df = pd.DataFrame()
                if col_codigo:
                    df['codigo_raw'] = df_raw[col_codigo].astype(str).str.strip()
                if col_edificio:
                    df['torre'] = df_raw[col_edificio]
                if col_dpto:
                    df['departamento'] = df_raw[col_dpto]
                if col_med_inst:
                    df['medidor_instalado'] = df_raw[col_med_inst].astype(str).str.strip()
                if col_n_med:
                    df['n_medidor'] = df_raw[col_n_med]
                if col_monto:
                    df['monto'] = df_raw[col_monto]

                # ========== FILTRADO ROBUSTO ==========
                # 1. Código: eliminar TOTAL, mantener 4-5 dígitos
                if 'codigo_raw' in df.columns:
                    df['codigo_raw'] = df['codigo_raw'].str.split('.').str[0]  # quitar decimales
                    df = df[~df['codigo_raw'].str.contains('TOTAL', case=False, na=False)]
                    df = df[df['codigo_raw'].str.match(r'^\d{4,5}$', na=False)]

                # 2. Torre y departamento numéricos > 0
                df['torre'] = pd.to_numeric(df['torre'], errors='coerce')
                df['departamento'] = pd.to_numeric(df['departamento'], errors='coerce')
                df = df.dropna(subset=['torre', 'departamento'])
                df = df[(df['torre'] > 0) & (df['departamento'] > 0)]

                # 3. Medidor instalado = "SI"
                if 'medidor_instalado' in df.columns:
                    df['medidor_instalado'] = df['medidor_instalado'].str.upper().str.strip()
                    df = df[df['medidor_instalado'] == 'SI']

                # 4. Número de medidor no vacío
                if 'n_medidor' in df.columns:
                    df['n_medidor'] = df['n_medidor'].astype(str).str.strip()
                    df = df[df['n_medidor'].notna() & (df['n_medidor'] != '') & (df['n_medidor'] != 'nan')]

                # 5. Monto > 0
                if 'monto' in df.columns:
                    df['monto'] = pd.to_numeric(df['monto'], errors='coerce')
                    df = df[df['monto'] > 0]

                if df.empty:
                    st.warning("No se encontraron filas válidas después de los filtros. Revisa el archivo.")
                    st.stop()

                st.info(f"✅ Filas válidas después de filtrar: {len(df)}")

                # Código de 5 dígitos para mostrar
                if 'codigo_raw' in df.columns:
                    df['codigo_5d'] = df['codigo_raw'].apply(lambda x: x.zfill(5) if len(x) == 4 else x)
                else:
                    df['codigo_5d'] = ""

                # Cargar propietarios
                prop = gsheets.leer_propietarios()
                if prop.empty:
                    st.error("No se pudo cargar Propietarios")
                    st.stop()

                # Detectar columna de departamento en prop
                depto_col_prop = None
                posibles = ['departamento', 'dpto', 'depto', 'N°DPTO']
                for col in prop.columns:
                    if col.lower() in posibles:
                        depto_col_prop = col
                        break
                if depto_col_prop is None:
                    st.error("No se encontró columna de departamento en Propietarios. Columnas: " + ", ".join(prop.columns))
                    st.stop()

                # Asegurar tipos numéricos en prop
                prop['torre'] = pd.to_numeric(prop['torre'], errors='coerce')
                prop[depto_col_prop] = pd.to_numeric(prop[depto_col_prop], errors='coerce')

                # Eliminar duplicados en prop (misma torre y departamento)
                prop = prop.drop_duplicates(subset=['torre', depto_col_prop], keep='first')

                # Merge
                df_merged = df.merge(
                    prop[['torre', depto_col_prop, 'nombre', 'dni', 'codigo']],
                    left_on=['torre', 'departamento'],
                    right_on=['torre', depto_col_prop],
                    how='left'
                )
                df_merged.rename(columns={'codigo': 'codigo_propietario'}, inplace=True)

                # Separar coincidentes y no coincidentes
                df_coinciden = df_merged[df_merged['nombre'].notna()].copy()
                df_no_coinciden = df_merged[df_merged['nombre'].isna()].copy()

                # Ordenar y resetear índice (empezar en 1)
                df_coinciden = df_coinciden.sort_values(by=['torre', 'departamento'])
                df_coinciden.reset_index(drop=True, inplace=True)
                df_coinciden.index = df_coinciden.index + 1
                df_no_coinciden.reset_index(drop=True, inplace=True)
                df_no_coinciden.index = df_no_coinciden.index + 1

                # Formatear números sin .0
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

                for col in ['codigo_5d', 'torre', 'departamento', 'n_medidor', 'monto']:
                    if col in df_coinciden.columns:
                        df_coinciden[col] = df_coinciden[col].apply(formatear_numero)
                    if col in df_no_coinciden.columns:
                        df_no_coinciden[col] = df_no_coinciden[col].apply(formatear_numero)

                # Mostrar resultados
                st.subheader("✅ Resultado del procesamiento")

                if not df_coinciden.empty:
                    st.markdown("### Medidores que coincidieron")
                    cols = ['codigo_5d', 'torre', 'departamento', 'nombre', 'dni', 'medidor_instalado', 'n_medidor', 'monto']
                    st.dataframe(df_coinciden[cols].fillna(""), use_container_width=True, height=400)

                if not df_no_coinciden.empty:
                    st.markdown("### Medidores sin coincidencia (revisar)")
                    cols_no = ['codigo_5d', 'torre', 'departamento', 'medidor_instalado', 'n_medidor', 'monto']
                    st.dataframe(df_no_coinciden[cols_no].fillna(""), use_container_width=True, height=300)

                # Botón guardar
                if st.button("💾 Guardar en Google Sheets", type="primary"):
                    try:
                        df_guardar = df_coinciden[['codigo_5d', 'torre', 'departamento', 'nombre', 'dni', 'medidor_instalado', 'n_medidor', 'monto']].copy()
                        for col in ['codigo_5d', 'torre', 'departamento', 'n_medidor', 'monto']:
                            if col in df_guardar.columns:
                                df_guardar[col] = pd.to_numeric(df_guardar[col], errors='coerce')
                        df_guardar.columns = ['codigo', 'torre', 'departamento', 'nombre', 'dni', 'medidor_instalado', 'n_medidor', 'monto']
                        nombre_hoja = gsheets.guardar_medidor(df=df_guardar, mes=mes, anio=int(anio))
                        st.success(f"Guardado en hoja: **{nombre_hoja}**")
                    except Exception as e:
                        st.error(f"Error al guardar: {str(e)}")

            except Exception as e:
                st.error(f"Error al procesar: {str(e)}")

    # ---------- SUBTAB 2: VISUALIZAR MEDIDORES ----------
    with subtab2:
        st.subheader("📊 Visualizar Medidores Guardados")

        try:
            hojas_medidor = gsheets.listar_hojas_medidor()
        except Exception as e:
            st.error(f"No se pudo conectar con Google Sheets: {e}")
            hojas_medidor = []

        if hojas_medidor:
            hoja_seleccionada = st.selectbox("Selecciona el período de medidores:", hojas_medidor,
                                             key="select_medidor_hoja")
            df_guardado = gsheets.leer_hoja_medidor(hoja_seleccionada)

            if not df_guardado.empty:
                # Función para formatear números sin .0 (igual que en la primera pestaña)
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

                for col in ['codigo', 'torre', 'departamento', 'n_medidor', 'monto']:
                    if col in df_guardado.columns:
                        df_guardado[col] = df_guardado[col].apply(formatear_numero)

                mapeo = {
                    'codigo': 'CÓDIGO',
                    'torre': 'TORRE',
                    'departamento': 'DPTO',
                    'nombre': 'PROPIETARIO',
                    'dni': 'DNI',
                    'medidor_instalado': 'MEDIDOR INSTALADO',
                    'n_medidor': 'N° MEDIDOR',
                    'monto': 'MONTO (S/)'
                }
                df_viz = df_guardado.rename(columns={col: mapeo[col] for col in df_guardado.columns if col in mapeo})

                # ---------- CALCULAR TOTAL DE MONTO ----------
                # Extraer valores numéricos de la columna MONTO (S/) y sumarlos
                # Primero convertir a número (ya están formateados como strings, pero podemos usar la función limpiar)
                def extraer_numero(val):
                    if pd.isna(val) or val == '':
                        return 0.0
                    # Eliminar caracteres no numéricos excepto punto decimal y signo menos
                    s = str(val).strip()
                    # Eliminar comas, espacios, símbolos de moneda
                    s = s.replace(',', '').replace(' ', '').replace('S/', '').replace('$', '')
                    try:
                        return float(s)
                    except:
                        return 0.0

                total_monto = df_viz['MONTO (S/)'].apply(extraer_numero).sum()
                total_formateado = f"S/ {total_monto:,.2f}"

                # Mostrar indicador de total
                st.metric("💰 Total de Monto a Pagar", total_formateado)
                st.markdown("---")

                # ---------- RESET INDEX PARA EMPEZAR EN 1 ----------
                df_viz = df_viz.reset_index(drop=True)
                df_viz.index = df_viz.index + 1

                # Mostrar tabla
                st.dataframe(df_viz, use_container_width=True, height=600)

                # Botón descarga
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
            st.info("No hay hojas de medidores guardadas. Sube un archivo en la pestaña 'Subir y Procesar' para crear una.")

# ====================== TAB 3: AMORTIZACIÓN ======================
with tab3:
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
                    df_amort = df_amort.loc[:, ~df_amort.columns.str.contains('^Unnamed', case=False)]
                    if 'ITEM' in df_amort.columns:
                        df_amort = df_amort[~df_amort['ITEM'].astype(str).str.contains('TOTAL', case=False, na=False)]
                    if 'APELLIDOS  Y  NOMBRES' in df_amort.columns:
                        df_amort = df_amort[~df_amort['APELLIDOS  Y  NOMBRES'].astype(str).str.contains('TOTAL', case=False, na=False)]
                    if 'TORRE' in df_amort.columns:
                        df_amort = df_amort.dropna(subset=['TORRE'])
                    if 'N°DPTO' in df_amort.columns:
                        df_amort = df_amort.dropna(subset=['N°DPTO'])
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

                st.metric("💰 Total de Amortización por Convenio", total_formateado)
                st.markdown("---")

                df_guardado = df_guardado.reset_index(drop=True)
                df_guardado.index = df_guardado.index + 1

                st.dataframe(df_guardado.fillna(""), use_container_width=True, height=600)

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

# ====================== TAB 4: OTROS (INGRESOS EXTRAORDINARIOS) ======================
with tab4:
    # Sub‑pestañas dentro de Otros
    subtab1, subtab2 = st.tabs(["📤 Subir y Procesar", "📊 Visualizar Otros"])

    # ---------- SUBTAB 1: SUBIR Y PROCESAR ----------
    with subtab1:
        col1, col2 = st.columns(2)
        with col1:
            mes_otros = st.selectbox(
                "Mes",
                ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                 "Julio","Agosto","Setiembre","Octubre","Noviembre","Diciembre"],
                key="mes_otros"
            )
        with col2:
            anio_otros = st.number_input("Año", min_value=2025, max_value=2035, value=2026, step=1, key="anio_otros")

        with st.expander("ℹ️ Formato esperado del archivo Excel"):
            st.info("""
            El archivo debe contener las siguientes columnas (en cualquier orden):
            - TORRE
            - N°DPTO
            - CODIGO (opcional)
            - DNI (opcional)
            - APELLIDOS Y NOMBRES (opcional)
            - CUOTA EXTRAORDINARIAS
            - ALQUILER PARRILLA
            - GARANTIA
            - SALA ZOOM
            - ALQUILER DE SILLAS

            La primera fila debe ser los encabezados.
            """)

        uploaded_file_otros = st.file_uploader("Elige el archivo Excel de ingresos extraordinarios", type=["xlsx"], key="otros_file")

        df_otros = None

        if uploaded_file_otros is not None:
            try:
                # Leer archivo asumiendo encabezados en primera fila
                df = pd.read_excel(uploaded_file_otros, sheet_name=0, header=0)
                df.columns = df.columns.str.strip().str.replace('\n', ' ').str.replace('\r', '')
                df = df.dropna(axis=1, how='all')
                df = df.dropna(how='all')

                # Buscar las columnas necesarias
                col_torre = None
                col_dpto = None
                col_codigo = None
                col_dni = None
                col_nombre = None

                # Columnas de montos (conceptos)
                conceptos = {
                    'CUOTA_EXTRAORDINARIAS': ['extraordinarias', 'cuota extraordinaria', 'extra'],
                    'ALQUILER_PARRILLA': ['parrilla', 'alquiler parrilla'],
                    'GARANTIA': ['garantia', 'garantía'],
                    'SALA_ZOOM': ['sala zoom', 'zoom'],
                    'ALQUILER_SILLAS': ['sillas', 'alquiler de sillas']
                }
                columnas_montos = {k: None for k in conceptos.keys()}

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
                    # Detección más flexible para nombres (acepta espacios, guiones, etc.)
                    elif 'apellidos' in col_low or 'nombre' in col_low:
                        col_nombre = col
                    else:
                        # Buscar entre los conceptos
                        for key, keywords in conceptos.items():
                            if any(kw in col_low for kw in keywords):
                                columnas_montos[key] = col
                                break

                if col_torre is None or col_dpto is None:
                    st.error("No se encontraron las columnas necesarias: TORRE y N°DPTO. Verifica el archivo.")
                    st.stop()

                # Si no se encontró ninguna columna de monto, mostrar advertencia
                if all(v is None for v in columnas_montos.values()):
                    st.warning("No se detectaron columnas de ingresos extraordinarios. Se creará un registro vacío.")

                # Seleccionar y renombrar columnas
                df_seleccionado = pd.DataFrame()
                df_seleccionado['torre'] = df[col_torre]
                df_seleccionado['departamento'] = df[col_dpto]

                # Añadir columnas de montos
                for key, col_monto in columnas_montos.items():
                    if col_monto is not None:
                        df_seleccionado[key] = df[col_monto]
                    else:
                        df_seleccionado[key] = 0  # si no existe la columna, asignar 0

                # Añadir columnas opcionales
                if col_codigo:
                    df_seleccionado['codigo'] = df[col_codigo]
                if col_dni:
                    df_seleccionado['dni'] = df[col_dni]
                if col_nombre:
                    df_seleccionado['nombre'] = df[col_nombre]

                # Convertir columnas numéricas
                df_seleccionado['torre'] = pd.to_numeric(df_seleccionado['torre'], errors='coerce')
                df_seleccionado['departamento'] = pd.to_numeric(df_seleccionado['departamento'], errors='coerce')
                for key in conceptos.keys():
                    df_seleccionado[key] = pd.to_numeric(df_seleccionado[key], errors='coerce')

                # Eliminar filas sin torre o departamento
                df_seleccionado = df_seleccionado.dropna(subset=['torre', 'departamento'])

                # Rellenar NaN con 0
                for key in conceptos.keys():
                    df_seleccionado[key] = df_seleccionado[key].fillna(0)

                st.success(f"Archivo leído: {len(df_seleccionado)} filas")

                # --- REORDENAR COLUMNAS PARA LA VISTA PREVIA Y GUARDADO ---
                # Definir el orden deseado de columnas
                columnas_orden_deseado = [
                    'torre', 'departamento', 'codigo', 'dni', 'nombre',
                    'CUOTA_EXTRAORDINARIAS', 'ALQUILER_PARRILLA', 'GARANTIA', 'SALA_ZOOM', 'ALQUILER_SILLAS'
                ]
                # Seleccionar solo las que existen en df_seleccionado
                columnas_existentes = [col for col in columnas_orden_deseado if col in df_seleccionado.columns]
                # Crear una copia ordenada para mostrar
                df_mostrar = df_seleccionado[columnas_existentes].copy()
                st.write("Vista previa (primeras 8 filas):")
                st.dataframe(df_mostrar.head(8))

                # Para guardar, usaremos las columnas que deben ir a la hoja
                # (incluyendo todas las que se hayan detectado, en el orden deseado)
                df_guardar = df_seleccionado[columnas_existentes].copy()
                df_otros = df_seleccionado  # Para usar después si se necesita

            except Exception as e:
                st.error(f"Error al leer el archivo: {e}")

        if df_otros is not None:
            # Verificar si ya existe una hoja con ese nombre
            nombre_hoja = f"Otros {mes_otros} {anio_otros}"
            spreadsheet = gsheets.get_spreadsheet()
            try:
                spreadsheet.worksheet(nombre_hoja)
                existe = True
            except gspread.exceptions.WorksheetNotFound:
                existe = False

            if existe:
                st.error(f"⚠️ Ya existe una hoja para {mes_otros} {anio_otros}")
                st.info("Cambia el mes/año o elimina manualmente la hoja en Google Sheets si quieres sobrescribir.")
            else:
                if st.button("Guardar en Google Sheets (Otros)", type="primary", key="guardar_otros"):
                    with st.spinner("Guardando..."):
                        try:
                            nombre_hoja = gsheets.guardar_otros(
                                df_guardar, mes_otros, int(anio_otros)
                            )
                            st.success(f"Guardado en hoja: **{nombre_hoja}**")
                        except Exception as e:
                            st.error(f"Error al guardar: {str(e)}")

    # ---------- SUBTAB 2: VISUALIZAR OTROS ----------
    with subtab2:
        st.subheader("Otros Guardados")

        try:
            hojas_otros = gsheets.listar_hojas_otros()
        except Exception as e:
            st.error(f"No se pudo conectar con Google Sheets: {e}")
            hojas_otros = []

        if hojas_otros:
            hoja_seleccionada = st.selectbox("Selecciona el período:", hojas_otros, key="select_otros")
            df_guardado = gsheets.leer_hoja_otros(hoja_seleccionada)

            if not df_guardado.empty:
                # Cargar propietarios para obtener nombre y DNI si no estaban en el archivo original
                prop = gsheets.leer_propietarios()
                if not prop.empty and 'nombre' not in df_guardado.columns:
                    col_torre_prop = None
                    col_dpto_prop = None
                    for col in prop.columns:
                        if col.lower() == 'torre':
                            col_torre_prop = col
                        elif col.lower() in ['departamento', 'dpto', 'n°dpto']:
                            col_dpto_prop = col
                    if col_torre_prop is not None and col_dpto_prop is not None:
                        prop_sub = prop[[col_torre_prop, col_dpto_prop, 'nombre', 'dni']].copy()
                        prop_sub.rename(columns={col_torre_prop: 'torre', col_dpto_prop: 'departamento'}, inplace=True)
                        prop_sub['torre'] = pd.to_numeric(prop_sub['torre'], errors='coerce')
                        prop_sub['departamento'] = pd.to_numeric(prop_sub['departamento'], errors='coerce')
                        prop_sub = prop_sub.drop_duplicates(subset=['torre', 'departamento'], keep='first')
                        df_guardado = df_guardado.merge(prop_sub, on=['torre', 'departamento'], how='left')
                    else:
                        st.warning("No se pudieron identificar las columnas de torre y departamento en Propietarios. No se mostrarán nombres ni DNI.")
                elif 'nombre' in df_guardado.columns:
                    # Ya tiene los datos, no hacemos nada
                    pass
                else:
                    st.warning("No se pudo cargar la lista de propietarios. Se mostrarán solo torre y departamento.")

                # Formatear números
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

                # Identificar las columnas de montos (conceptos)
                conceptos_viz = {
                    'CUOTA_EXTRAORDINARIAS': 'CUOTA EXTRAORDINARIA',
                    'ALQUILER_PARRILLA': 'ALQUILER PARRILLA',
                    'GARANTIA': 'GARANTÍA',
                    'SALA_ZOOM': 'SALA ZOOM',
                    'ALQUILER_SILLAS': 'ALQUILER DE SILLAS'
                }

                # Renombrar columnas para visualización
                mapeo = {
                    'torre': 'TORRE',
                    'departamento': 'N°DPTO',
                    'codigo': 'CÓDIGO',
                    'dni': 'DNI',
                    'nombre': 'APELLIDOS Y NOMBRES'
                }
                # Añadir los conceptos al mapeo
                for key, label in conceptos_viz.items():
                    if key in df_guardado.columns:
                        mapeo[key] = label

                # Aplicar renombrado
                df_viz = df_guardado.rename(columns={col: mapeo[col] for col in df_guardado.columns if col in mapeo})
                df_viz = df_viz.loc[:, ~df_viz.columns.duplicated()]

                # Formatear columnas numéricas
                for col in df_viz.columns:
                    if col in conceptos_viz.values():
                        df_viz[col] = df_viz[col].apply(formatear_numero)

                # Asegurar que torre y departamento sean strings sin decimales
                for col in ['TORRE', 'N°DPTO']:
                    if col in df_viz.columns:
                        df_viz[col] = df_viz[col].apply(formatear_numero)

                # Orden de columnas (priorizar torre, dpto, código, nombre, luego conceptos)
                columnas_orden = ['TORRE', 'N°DPTO', 'CÓDIGO', 'DNI', 'APELLIDOS Y NOMBRES'] + list(conceptos_viz.values())
                columnas_existentes = [col for col in columnas_orden if col in df_viz.columns]

                # Calcular totales por concepto
                def extraer_numero(val):
                    if pd.isna(val) or val == '':
                        return 0.0
                    s = str(val).strip()
                    s = s.replace(',', '').replace(' ', '').replace('S/', '').replace('$', '')
                    try:
                        return float(s)
                    except:
                        return 0.0

                # Mostrar totales en métricas (en filas de columnas)
                st.subheader("📊 Resumen de Ingresos")
                # Dividir en grupos de hasta 3 métricas por fila
                conceptos_list = [label for label in conceptos_viz.values() if label in df_viz.columns]
                for i in range(0, len(conceptos_list), 3):
                    cols = st.columns(3)
                    for j, concepto in enumerate(conceptos_list[i:i+3]):
                        total = df_viz[concepto].apply(extraer_numero).sum()
                        with cols[j]:
                            st.metric(label=concepto, value=f"S/ {total:,.2f}")

                st.markdown("---")

                # Índice empezando en 1
                df_viz = df_viz[columnas_existentes].reset_index(drop=True)
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
            st.info("No hay hojas de ingresos extraordinarios guardadas. Sube un archivo en la pestaña 'Subir y Procesar' para crear una.")
