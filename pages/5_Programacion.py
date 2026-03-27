import streamlit as st
import pandas as pd
import numpy as np
import gsheets
import gspread
from datetime import datetime, timedelta

st.set_page_config(page_title="Programación", page_icon="📅", layout="wide")

st.title("📅 Programación Mensual - Subir desde Excel")

# ====================== FUNCIÓN AUXILIAR ======================
def validar_mes_vencimiento(mes_seleccionado: str, fecha_vencimiento):
    """
    Verifica que el mes de la fecha de vencimiento coincida con el mes seleccionado.
    Retorna (es_valido, mes_real)
    """
    meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
             "Julio","Agosto","Setiembre","Octubre","Noviembre","Diciembre"]
    mes_real = meses[fecha_vencimiento.month - 1]
    if mes_seleccionado != mes_real:
        return False, mes_real
    return True, mes_real

# Crear pestañas principales
tab1, tab2, tab3, tab4 = st.tabs(["📊 Programación Mantenimiento", "💧 Medidores", "💰 Amortización", "📌 Otros"])

# ====================== TAB 1: PROGRAMACIÓN MANTENIMIENTO ======================
with tab1:
    # Sub‑pestañas dentro de Programación Mantenimiento
    subtab1, subtab2 = st.tabs(["📤 Subir y Procesar", "📊 Visualizar Programación"])

    # ---------- SUBTAB 1: SUBIR Y PROCESAR ----------
    with subtab1:
        col1, col2 = st.columns(2)
        with col1:
            mes = st.selectbox(
                "Mes a programar",
                ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                 "Julio", "Agosto", "Setiembre", "Octubre", "Noviembre", "Diciembre"]
            )
        with col2:
            anio = st.number_input("Año", min_value=2025, max_value=2035, value=2026, step=1)

        mes_num = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Setiembre","Octubre","Noviembre","Diciembre"].index(mes) + 1
        fecha_emision_def = datetime(anio, mes_num, 23)
        fecha_venc_def = fecha_emision_def + timedelta(days=15)

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            fecha_emision = st.date_input("Fecha de Emisión", value=fecha_emision_def, key="fec_emision_mant")
        with col_f2:
            fecha_vencimiento = st.date_input("Fecha de Vencimiento", value=fecha_venc_def, key="fec_venc_mant")

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

                columnas_a_guardar = ['torre', 'departamento', 'Mantenimiento']
                if 'codigo' in df_seleccionado.columns:
                    columnas_a_guardar.insert(2, 'codigo')
                if 'dni' in df_seleccionado.columns:
                    columnas_a_guardar.insert(3, 'dni')
                if 'nombre' in df_seleccionado.columns:
                    columnas_a_guardar.insert(4, 'nombre')
                df_guardar = df_seleccionado[columnas_a_guardar].copy()

            except Exception as e:
                st.error(f"Error al leer el archivo: {e}")

        if df is not None:
            valido, mes_real = validar_mes_vencimiento(mes, fecha_vencimiento)
            if not valido:
                st.error(f"❌ El mes seleccionado ({mes}) no coincide con el mes de la fecha de vencimiento ({mes_real}). Debes seleccionar el mes correspondiente al vencimiento.")
            else:
                periodo_key = f"{mes_real.upper()}_{int(fecha_vencimiento.year)}"
                if gsheets.existe_programacion(periodo_key):
                    st.error(f"⚠️ Ya existe una programación para {mes_real} {fecha_vencimiento.year}")
                    st.info("Cambia el mes/año o elimina manualmente la hoja en Google Sheets si quieres sobrescribir.")
                else:
                    if st.button("Guardar en Google Sheets", type="primary", key="guardar_det_cuotas"):
                        if gsheets.existe_solapamiento_fechas("Mantenimiento", fecha_emision, fecha_vencimiento):
                            st.error("❌ Ya existe una programación de Mantenimiento con un rango de fechas que se solapa con este. No se puede guardar.")
                        else:
                            with st.spinner("Guardando..."):
                                try:
                                    nombre_hoja = gsheets.crear_y_guardar_programacion(
                                        df_guardar, periodo_key, mes_real, int(fecha_vencimiento.year)
                                    )
                                    gsheets.registrar_fecha_programacion("Mantenimiento", nombre_hoja, fecha_emision, fecha_vencimiento)
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

                # Preparar tabla de propietarios
                if not prop.empty:
                    col_torre_prop = None
                    col_dpto_prop = None
                    for col in prop.columns:
                        if col.lower() == 'torre':
                            col_torre_prop = col
                        if col.lower() in ['departamento', 'dpto', 'n°dpto']:
                            col_dpto_prop = col
                    if col_torre_prop is not None and col_dpto_prop is not None:
                        columnas_seleccion = [col_torre_prop, col_dpto_prop]
                        col_codigo_prop = None
                        for col in prop.columns:
                            if col.lower() == 'codigo':
                                col_codigo_prop = col
                                break
                        if col_codigo_prop:
                            columnas_seleccion.append(col_codigo_prop)
                        col_dni_prop = None
                        for col in prop.columns:
                            if col.lower() == 'dni':
                                col_dni_prop = col
                                break
                        if col_dni_prop:
                            columnas_seleccion.append(col_dni_prop)
                        col_nombre_prop = None
                        for col in prop.columns:
                            if col.lower() in ['nombre', 'apellidos y nombres']:
                                col_nombre_prop = col
                                break
                        if col_nombre_prop:
                            columnas_seleccion.append(col_nombre_prop)

                        prop_sub = prop[columnas_seleccion].copy()
                        rename_map = {}
                        if col_torre_prop:
                            rename_map[col_torre_prop] = 'torre'
                        if col_dpto_prop:
                            rename_map[col_dpto_prop] = 'departamento'
                        if col_codigo_prop:
                            rename_map[col_codigo_prop] = 'codigo'
                        if col_dni_prop:
                            rename_map[col_dni_prop] = 'dni'
                        if col_nombre_prop:
                            rename_map[col_nombre_prop] = 'nombre'
                        prop_sub.rename(columns=rename_map, inplace=True)
                        prop_sub['torre'] = pd.to_numeric(prop_sub['torre'], errors='coerce')
                        prop_sub['departamento'] = pd.to_numeric(prop_sub['departamento'], errors='coerce')
                        prop_sub = prop_sub.drop_duplicates(subset=['torre', 'departamento'], keep='first')
                    else:
                        prop_sub = None
                        st.warning("No se pudieron identificar las columnas de torre y departamento en Propietarios.")
                else:
                    prop_sub = None
                    st.warning("No se pudo cargar la lista de propietarios.")

                # Completar datos faltantes
                df_mostrar = df_guardado.copy()
                if prop_sub is not None:
                    columnas_guardado = df_guardado.columns.tolist()
                    if 'codigo' not in columnas_guardado and 'codigo' in prop_sub.columns:
                        df_mostrar = df_mostrar.merge(prop_sub[['torre', 'departamento', 'codigo']],
                                                       on=['torre', 'departamento'], how='left')
                    if 'dni' not in columnas_guardado and 'dni' in prop_sub.columns:
                        df_mostrar = df_mostrar.merge(prop_sub[['torre', 'departamento', 'dni']],
                                                       on=['torre', 'departamento'], how='left')
                    if 'nombre' not in columnas_guardado and 'nombre' in prop_sub.columns:
                        df_mostrar = df_mostrar.merge(prop_sub[['torre', 'departamento', 'nombre']],
                                                       on=['torre', 'departamento'], how='left')
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

                if 'Mantenimiento' in df_mostrar.columns:
                    df_mostrar['Mantenimiento'] = df_mostrar['Mantenimiento'].apply(formatear_numero)
                for col in ['torre', 'departamento']:
                    if col in df_mostrar.columns:
                        df_mostrar[col] = df_mostrar[col].apply(formatear_numero)

                mapeo = {
                    'torre': 'TORRE',
                    'departamento': 'N°DPTO',
                    'codigo': 'CÓDIGO',
                    'dni': 'DNI',
                    'nombre': 'NOMBRES Y APELLIDOS',
                    'Mantenimiento': 'MANTENIMIENTO (S/)'
                }
                df_viz = df_mostrar.rename(columns={col: mapeo[col] for col in df_mostrar.columns if col in mapeo})
                df_viz = df_viz.loc[:, ~df_viz.columns.duplicated()]

                columnas_final = ['TORRE', 'N°DPTO', 'CÓDIGO', 'DNI', 'NOMBRES Y APELLIDOS', 'MANTENIMIENTO (S/)']
                columnas_existentes = [col for col in columnas_final if col in df_viz.columns]
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

                # Botón eliminar
                st.markdown("---")
                if st.button("🗑️ Eliminar esta programación", type="secondary", key=f"del_{hoja_seleccionada}"):
                    if gsheets.eliminar_programacion(hoja_seleccionada):
                        st.success(f"Se eliminó la hoja '{hoja_seleccionada}' correctamente.")
                        st.cache_resource.clear()
                        st.rerun()
                    else:
                        st.error("No se pudo eliminar la hoja (puede que ya no exista).")
            else:
                st.info("La hoja seleccionada está vacía.")
        else:
            st.info("No hay programaciones guardadas. Sube un archivo en la pestaña 'Subir y Procesar' para crear una.")

# ====================== TAB 2: MEDIDORES ======================
with tab2:
    subtab1, subtab2 = st.tabs(["📤 Subir y Procesar", "📊 Visualizar Medidores"])

    with subtab1:
        col1, col2 = st.columns(2)
        with col1:
            mes = st.selectbox("Mes", ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                                       "Julio","Agosto","Setiembre","Octubre","Noviembre","Diciembre"],
                               key="mes_medidor")
        with col2:
            anio = st.number_input("Año", min_value=2025, max_value=2035, value=2026, step=1,
                                   key="anio_medidor")

        mes_num = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Setiembre","Octubre","Noviembre","Diciembre"].index(mes) + 1
        fecha_emision_def = datetime(anio, mes_num, 23)
        fecha_venc_def = fecha_emision_def + timedelta(days=15)

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            fecha_emision = st.date_input("Fecha de Emisión", value=fecha_emision_def, key="fec_emision_med")
        with col_f2:
            fecha_vencimiento = st.date_input("Fecha de Vencimiento", value=fecha_venc_def, key="fec_venc_med")

        st.divider()
        uploaded_file = st.file_uploader("Sube el archivo Excel de MEDIDORES", type=["xlsx"],
                                         key="medidor_file")

        if uploaded_file is not None:
            try:
                df_raw = pd.read_excel(uploaded_file, sheet_name=0, header=0)
                df_raw.columns = df_raw.columns.str.strip().str.replace('\n', ' ').str.replace('\r', '')

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

                col_codigo = find_column(['codigo', 'código'])
                col_edificio = find_column(['edificio', 'torre'])
                col_dpto = find_column(['dpto', 'departamento'])
                col_med_inst = find_column(['medidor instalado'])
                col_n_med = find_column(['n°', 'nº', 'número'], fallback_keywords=['medidor'])
                col_monto = find_column(['monto a pagar', 'monto', 'pago'])

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

                if 'codigo_raw' in df.columns:
                    df['codigo_raw'] = df['codigo_raw'].str.split('.').str[0]
                    df = df[~df['codigo_raw'].str.contains('TOTAL', case=False, na=False)]
                    df = df[df['codigo_raw'].str.match(r'^\d{4,5}$', na=False)]

                df['torre'] = pd.to_numeric(df['torre'], errors='coerce')
                df['departamento'] = pd.to_numeric(df['departamento'], errors='coerce')
                df = df.dropna(subset=['torre', 'departamento'])
                df = df[(df['torre'] > 0) & (df['departamento'] > 0)]

                if 'medidor_instalado' in df.columns:
                    df['medidor_instalado'] = df['medidor_instalado'].str.upper().str.strip()
                    df = df[df['medidor_instalado'] == 'SI']

                if 'n_medidor' in df.columns:
                    df['n_medidor'] = df['n_medidor'].astype(str).str.strip()
                    df = df[df['n_medidor'].notna() & (df['n_medidor'] != '') & (df['n_medidor'] != 'nan')]

                if 'monto' in df.columns:
                    df['monto'] = pd.to_numeric(df['monto'], errors='coerce')
                    df = df[df['monto'] > 0]

                if df.empty:
                    st.warning("No se encontraron filas válidas después de los filtros. Revisa el archivo.")
                    st.stop()

                st.info(f"✅ Filas válidas después de filtrar: {len(df)}")

                if 'codigo_raw' in df.columns:
                    df['codigo_5d'] = df['codigo_raw'].apply(lambda x: x.zfill(5) if len(x) == 4 else x)
                else:
                    df['codigo_5d'] = ""

                prop = gsheets.leer_propietarios()
                if prop.empty:
                    st.error("No se pudo cargar Propietarios")
                    st.stop()

                depto_col_prop = None
                posibles = ['departamento', 'dpto', 'depto', 'N°DPTO']
                for col in prop.columns:
                    if col.lower() in posibles:
                        depto_col_prop = col
                        break
                if depto_col_prop is None:
                    st.error("No se encontró columna de departamento en Propietarios. Columnas: " + ", ".join(prop.columns))
                    st.stop()

                prop['torre'] = pd.to_numeric(prop['torre'], errors='coerce')
                prop[depto_col_prop] = pd.to_numeric(prop[depto_col_prop], errors='coerce')
                prop = prop.drop_duplicates(subset=['torre', depto_col_prop], keep='first')

                df_merged = df.merge(
                    prop[['torre', depto_col_prop, 'nombre', 'dni', 'codigo']],
                    left_on=['torre', 'departamento'],
                    right_on=['torre', depto_col_prop],
                    how='left'
                )
                df_merged.rename(columns={'codigo': 'codigo_propietario'}, inplace=True)

                df_coinciden = df_merged[df_merged['nombre'].notna()].copy()
                df_no_coinciden = df_merged[df_merged['nombre'].isna()].copy()

                df_coinciden = df_coinciden.sort_values(by=['torre', 'departamento'])
                df_coinciden.reset_index(drop=True, inplace=True)
                df_coinciden.index = df_coinciden.index + 1
                df_no_coinciden.reset_index(drop=True, inplace=True)
                df_no_coinciden.index = df_no_coinciden.index + 1

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

                st.subheader("✅ Resultado del procesamiento")

                if not df_coinciden.empty:
                    st.markdown("### Medidores que coincidieron")
                    cols = ['codigo_5d', 'torre', 'departamento', 'nombre', 'dni', 'medidor_instalado', 'n_medidor', 'monto']
                    st.dataframe(df_coinciden[cols].fillna(""), use_container_width=True, height=400)

                if not df_no_coinciden.empty:
                    st.markdown("### Medidores sin coincidencia (revisar)")
                    cols_no = ['codigo_5d', 'torre', 'departamento', 'medidor_instalado', 'n_medidor', 'monto']
                    st.dataframe(df_no_coinciden[cols_no].fillna(""), use_container_width=True, height=300)

                valido, mes_real = validar_mes_vencimiento(mes, fecha_vencimiento)
                if not valido:
                    st.error(f"❌ El mes seleccionado ({mes}) no coincide con el mes de la fecha de vencimiento ({mes_real}). Debes seleccionar el mes correspondiente al vencimiento.")
                else:
                    if st.button("💾 Guardar en Google Sheets", type="primary"):
                        if gsheets.existe_solapamiento_fechas("Medidores", fecha_emision, fecha_vencimiento):
                            st.error("❌ Ya existe una programación de Medidores con un rango de fechas que se solapa con este. No se puede guardar.")
                        else:
                            try:
                                df_guardar = df_coinciden[['codigo_5d', 'torre', 'departamento', 'nombre', 'dni', 'medidor_instalado', 'n_medidor', 'monto']].copy()
                                for col in ['codigo_5d', 'torre', 'departamento', 'n_medidor', 'monto']:
                                    if col in df_guardar.columns:
                                        df_guardar[col] = pd.to_numeric(df_guardar[col], errors='coerce')
                                df_guardar.columns = ['codigo', 'torre', 'departamento', 'nombre', 'dni', 'medidor_instalado', 'n_medidor', 'monto']
                                nombre_hoja = gsheets.guardar_medidor(df=df_guardar, mes=mes_real, anio=int(fecha_vencimiento.year))
                                gsheets.registrar_fecha_programacion("Medidores", nombre_hoja, fecha_emision, fecha_vencimiento)
                                st.success(f"Guardado en hoja: **{nombre_hoja}**")
                            except Exception as e:
                                st.error(f"Error al guardar: {str(e)}")

            except Exception as e:
                st.error(f"Error al procesar: {str(e)}")

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

                def extraer_numero(val):
                    if pd.isna(val) or val == '':
                        return 0.0
                    s = str(val).strip()
                    s = s.replace(',', '').replace(' ', '').replace('S/', '').replace('$', '')
                    try:
                        return float(s)
                    except:
                        return 0.0

                total_monto = df_viz['MONTO (S/)'].apply(extraer_numero).sum()
                total_formateado = f"S/ {total_monto:,.2f}"

                st.metric("💰 Total de Monto a Pagar", total_formateado)
                st.markdown("---")

                df_viz = df_viz.reset_index(drop=True)
                df_viz.index = df_viz.index + 1

                st.dataframe(df_viz, use_container_width=True, height=600)

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

                # Botón eliminar
                st.markdown("---")
                if st.button("🗑️ Eliminar esta programación", type="secondary", key=f"del_med_{hoja_seleccionada}"):
                    if gsheets.eliminar_programacion(hoja_seleccionada):
                        st.success(f"Se eliminó la hoja '{hoja_seleccionada}' correctamente.")
                        st.cache_resource.clear()
                        st.rerun()
                    else:
                        st.error("No se pudo eliminar la hoja.")
            else:
                st.info("La hoja seleccionada está vacía.")
        else:
            st.info("No hay hojas de medidores guardadas. Sube un archivo en la pestaña 'Subir y Procesar' para crear una.")

# ====================== TAB 3: AMORTIZACIÓN ======================
with tab3:
    subtab1, subtab2 = st.tabs(["📤 Subir y Procesar", "📊 Visualizar Amortización"])

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

        mes_num = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Setiembre","Octubre","Noviembre","Diciembre"].index(mes_amort) + 1
        fecha_emision_def = datetime(anio_amort, mes_num, 23)
        fecha_venc_def = fecha_emision_def + timedelta(days=15)

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            fecha_emision = st.date_input("Fecha de Emisión", value=fecha_emision_def, key="fec_emision_amort")
        with col_f2:
            fecha_vencimiento = st.date_input("Fecha de Vencimiento", value=fecha_venc_def, key="fec_venc_amort")

        st.divider()
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
            valido, mes_real = validar_mes_vencimiento(mes_amort, fecha_vencimiento)
            if not valido:
                st.error(f"❌ El mes seleccionado ({mes_amort}) no coincide con el mes de la fecha de vencimiento ({mes_real}). Debes seleccionar el mes correspondiente al vencimiento.")
            else:
                if st.button("Guardar en Google Sheets (Amortización)", type="primary", key="guardar_amort"):
                    if gsheets.existe_solapamiento_fechas("Amortización", fecha_emision, fecha_vencimiento):
                        st.error("❌ Ya existe una programación de Amortización con un rango de fechas que se solapa con este. No se puede guardar.")
                    else:
                        with st.spinner("Guardando datos de amortización..."):
                            try:
                                nombre_hoja = gsheets.guardar_amortizacion(
                                    df_amort, mes_real, int(fecha_vencimiento.year)
                                )
                                gsheets.registrar_fecha_programacion("Amortización", nombre_hoja, fecha_emision, fecha_vencimiento)
                                st.success(f"¡Guardado correctamente en hoja: **{nombre_hoja}**!")
                            except Exception as e:
                                st.error(f"Error al guardar: {str(e)}")
        elif df_amort is not None and df_amort.empty:
            st.warning("No se encontraron datos válidos después de filtrar. Verifica el archivo.")

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

                # Botón eliminar
                st.markdown("---")
                if st.button("🗑️ Eliminar esta programación", type="secondary", key=f"del_amort_{hoja_seleccionada}"):
                    if gsheets.eliminar_programacion(hoja_seleccionada):
                        st.success(f"Se eliminó la hoja '{hoja_seleccionada}' correctamente.")
                        st.cache_resource.clear()
                        st.rerun()
                    else:
                        st.error("No se pudo eliminar la hoja.")
            else:
                st.info("La hoja seleccionada está vacía.")
        else:
            st.info("No hay hojas de amortización guardadas. Sube un archivo en la pestaña 'Subir y Procesar' para crear una.")

# ====================== TAB 4: OTROS (INGRESOS EXTRAORDINARIOS) ======================
with tab4:
    subtab1, subtab2 = st.tabs(["📤 Subir y Procesar", "📊 Visualizar Otros"])

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

        mes_num = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Setiembre","Octubre","Noviembre","Diciembre"].index(mes_otros) + 1
        fecha_emision_def = datetime(anio_otros, mes_num, 23)
        fecha_venc_def = fecha_emision_def + timedelta(days=15)

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            fecha_emision = st.date_input("Fecha de Emisión", value=fecha_emision_def, key="fec_emision_otros")
        with col_f2:
            fecha_vencimiento = st.date_input("Fecha de Vencimiento", value=fecha_venc_def, key="fec_venc_otros")

        st.divider()
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
                df = pd.read_excel(uploaded_file_otros, sheet_name=0, header=0)
                df.columns = df.columns.str.strip().str.replace('\n', ' ').str.replace('\r', '')
                df = df.dropna(axis=1, how='all')
                df = df.dropna(how='all')

                col_torre = None
                col_dpto = None
                col_codigo = None
                col_dni = None
                col_nombre = None

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
                    elif 'apellidos' in col_low or 'nombre' in col_low:
                        col_nombre = col
                    else:
                        for key, keywords in conceptos.items():
                            if any(kw in col_low for kw in keywords):
                                columnas_montos[key] = col
                                break

                if col_torre is None or col_dpto is None:
                    st.error("No se encontraron las columnas necesarias: TORRE y N°DPTO. Verifica el archivo.")
                    st.stop()

                if all(v is None for v in columnas_montos.values()):
                    st.warning("No se detectaron columnas de ingresos extraordinarios. Se creará un registro vacío.")

                df_seleccionado = pd.DataFrame()
                df_seleccionado['torre'] = df[col_torre]
                df_seleccionado['departamento'] = df[col_dpto]

                for key, col_monto in columnas_montos.items():
                    if col_monto is not None:
                        df_seleccionado[key] = df[col_monto]
                    else:
                        df_seleccionado[key] = 0

                if col_codigo:
                    df_seleccionado['codigo'] = df[col_codigo]
                if col_dni:
                    df_seleccionado['dni'] = df[col_dni]
                if col_nombre:
                    df_seleccionado['nombre'] = df[col_nombre]

                df_seleccionado['torre'] = pd.to_numeric(df_seleccionado['torre'], errors='coerce')
                df_seleccionado['departamento'] = pd.to_numeric(df_seleccionado['departamento'], errors='coerce')
                for key in conceptos.keys():
                    df_seleccionado[key] = pd.to_numeric(df_seleccionado[key], errors='coerce')

                df_seleccionado = df_seleccionado.dropna(subset=['torre', 'departamento'])

                for key in conceptos.keys():
                    df_seleccionado[key] = df_seleccionado[key].fillna(0)

                st.success(f"Archivo leído: {len(df_seleccionado)} filas")

                columnas_orden_deseado = [
                    'torre', 'departamento', 'codigo', 'dni', 'nombre',
                    'CUOTA_EXTRAORDINARIAS', 'ALQUILER_PARRILLA', 'GARANTIA', 'SALA_ZOOM', 'ALQUILER_SILLAS'
                ]
                columnas_existentes = [col for col in columnas_orden_deseado if col in df_seleccionado.columns]
                df_mostrar = df_seleccionado[columnas_existentes].copy()
                st.write("Vista previa (primeras 8 filas):")
                st.dataframe(df_mostrar.head(8))

                df_guardar = df_seleccionado[columnas_existentes].copy()

                for col in ['CUOTA_EXTRAORDINARIAS', 'ALQUILER_PARRILLA', 'GARANTIA', 'SALA_ZOOM', 'ALQUILER_SILLAS']:
                    if col in df_guardar.columns:
                        df_guardar[col] = df_guardar[col].fillna(0)
                for col in ['codigo', 'dni', 'nombre']:
                    if col in df_guardar.columns:
                        df_guardar[col] = df_guardar[col].fillna('')

                df_guardar['torre'] = df_guardar['torre'].astype('Int64')
                df_guardar['departamento'] = df_guardar['departamento'].astype('Int64')

                df_otros = df_seleccionado

            except Exception as e:
                st.error(f"Error al leer el archivo: {e}")

        if df_otros is not None:
            valido, mes_real = validar_mes_vencimiento(mes_otros, fecha_vencimiento)
            if not valido:
                st.error(f"❌ El mes seleccionado ({mes_otros}) no coincide con el mes de la fecha de vencimiento ({mes_real}). Debes seleccionar el mes correspondiente al vencimiento.")
            else:
                nombre_hoja = f"Otros {mes_real} {fecha_vencimiento.year}"
                spreadsheet = gsheets.get_spreadsheet()
                try:
                    spreadsheet.worksheet(nombre_hoja)
                    existe = True
                except gspread.exceptions.WorksheetNotFound:
                    existe = False

                if existe:
                    st.error(f"⚠️ Ya existe una hoja para {mes_real} {fecha_vencimiento.year}")
                    st.info("Cambia el mes/año o elimina manualmente la hoja en Google Sheets si quieres sobrescribir.")
                else:
                    if st.button("Guardar en Google Sheets (Otros)", type="primary", key="guardar_otros"):
                        if gsheets.existe_solapamiento_fechas("Otros", fecha_emision, fecha_vencimiento):
                            st.error("❌ Ya existe una programación de Otros con un rango de fechas que se solapa con este. No se puede guardar.")
                        else:
                            with st.spinner("Guardando..."):
                                try:
                                    nombre_hoja = gsheets.guardar_otros(
                                        df_guardar, mes_real, int(fecha_vencimiento.year)
                                    )
                                    gsheets.registrar_fecha_programacion("Otros", nombre_hoja, fecha_emision, fecha_vencimiento)
                                    st.success(f"Guardado en hoja: **{nombre_hoja}**")
                                except Exception as e:
                                    st.error(f"Error al guardar: {str(e)}")

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
                        columnas_seleccion = [col_torre_prop, col_dpto_prop]
                        col_nombre_prop = None
                        for col in prop.columns:
                            if col.lower() in ['nombre', 'apellidos y nombres']:
                                col_nombre_prop = col
                                break
                        if col_nombre_prop:
                            columnas_seleccion.append(col_nombre_prop)
                        col_dni_prop = None
                        for col in prop.columns:
                            if col.lower() == 'dni':
                                col_dni_prop = col
                                break
                        if col_dni_prop:
                            columnas_seleccion.append(col_dni_prop)
                        prop_sub = prop[columnas_seleccion].copy()
                        rename_map = {}
                        if col_torre_prop:
                            rename_map[col_torre_prop] = 'torre'
                        if col_dpto_prop:
                            rename_map[col_dpto_prop] = 'departamento'
                        if col_nombre_prop:
                            rename_map[col_nombre_prop] = 'nombre'
                        if col_dni_prop:
                            rename_map[col_dni_prop] = 'dni'
                        prop_sub.rename(columns=rename_map, inplace=True)
                        prop_sub['torre'] = pd.to_numeric(prop_sub['torre'], errors='coerce')
                        prop_sub['departamento'] = pd.to_numeric(prop_sub['departamento'], errors='coerce')
                        prop_sub = prop_sub.drop_duplicates(subset=['torre', 'departamento'], keep='first')
                        df_guardado = df_guardado.merge(prop_sub, on=['torre', 'departamento'], how='left')
                    else:
                        st.warning("No se pudieron identificar las columnas de torre y departamento en Propietarios. No se mostrarán nombres ni DNI.")
                elif 'nombre' in df_guardado.columns:
                    pass
                else:
                    st.warning("No se pudo cargar la lista de propietarios. Se mostrarán solo torre y departamento.")

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

                conceptos_viz = {
                    'CUOTA_EXTRAORDINARIAS': 'CUOTA EXTRAORDINARIA',
                    'ALQUILER_PARRILLA': 'ALQUILER PARRILLA',
                    'GARANTIA': 'GARANTÍA',
                    'SALA_ZOOM': 'SALA ZOOM',
                    'ALQUILER_SILLAS': 'ALQUILER DE SILLAS'
                }

                mapeo = {
                    'torre': 'TORRE',
                    'departamento': 'N°DPTO',
                    'codigo': 'CÓDIGO',
                    'dni': 'DNI',
                    'nombre': 'APELLIDOS Y NOMBRES'
                }
                for key, label in conceptos_viz.items():
                    if key in df_guardado.columns:
                        mapeo[key] = label

                df_viz = df_guardado.rename(columns={col: mapeo[col] for col in df_guardado.columns if col in mapeo})
                df_viz = df_viz.loc[:, ~df_viz.columns.duplicated()]

                for col in df_viz.columns:
                    if col in conceptos_viz.values():
                        df_viz[col] = df_viz[col].apply(formatear_numero)

                for col in ['TORRE', 'N°DPTO']:
                    if col in df_viz.columns:
                        df_viz[col] = df_viz[col].apply(formatear_numero)

                columnas_orden = ['TORRE', 'N°DPTO', 'CÓDIGO', 'DNI', 'APELLIDOS Y NOMBRES'] + list(conceptos_viz.values())
                columnas_existentes = [col for col in columnas_orden if col in df_viz.columns]

                def extraer_numero(val):
                    if pd.isna(val) or val == '':
                        return 0.0
                    s = str(val).strip()
                    s = s.replace(',', '').replace(' ', '').replace('S/', '').replace('$', '')
                    try:
                        return float(s)
                    except:
                        return 0.0

                st.subheader("📊 Resumen de Ingresos")
                conceptos_list = [label for label in conceptos_viz.values() if label in df_viz.columns]
                for i in range(0, len(conceptos_list), 3):
                    cols = st.columns(3)
                    for j, concepto in enumerate(conceptos_list[i:i+3]):
                        total = df_viz[concepto].apply(extraer_numero).sum()
                        with cols[j]:
                            st.metric(label=concepto, value=f"S/ {total:,.2f}")

                st.markdown("---")

                df_viz = df_viz[columnas_existentes].reset_index(drop=True)
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

                # Botón eliminar
                st.markdown("---")
                if st.button("🗑️ Eliminar esta programación", type="secondary", key=f"del_otros_{hoja_seleccionada}"):
                    if gsheets.eliminar_programacion(hoja_seleccionada):
                        st.success(f"Se eliminó la hoja '{hoja_seleccionada}' correctamente.")
                        st.cache_resource.clear()
                        st.rerun()
                    else:
                        st.error("No se pudo eliminar la hoja.")
            else:
                st.info("La hoja seleccionada está vacía.")
        else:
            st.info("No hay hojas de ingresos extraordinarios guardadas. Sube un archivo en la pestaña 'Subir y Procesar' para crear una.")
