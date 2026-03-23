import streamlit as st
import pandas as pd
import gsheets
from datetime import datetime

st.set_page_config(page_title="Medidores de Agua", layout="wide")

st.title("💧 Medidores - Registro de Instalación y Pagos")

tab1, tab2 = st.tabs(["📤 Subir y Procesar", "📊 Visualizar Medidores"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        mes = st.selectbox("Mes", ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                                   "Julio","Agosto","Setiembre","Octubre","Noviembre","Diciembre"])
    with col2:
        anio = st.number_input("Año", min_value=2025, max_value=2035, value=2026, step=1)

    uploaded_file = st.file_uploader("Sube el archivo Excel de MEDIDORES", type=["xlsx"])

    if uploaded_file is not None:
        try:
            # Leer archivo
            df_raw = pd.read_excel(uploaded_file, sheet_name=0, header=0)

            # Limpiar nombres de columnas
            df_raw.columns = df_raw.columns.str.strip().str.replace('\n', ' ').str.replace('\r', '')
            st.write("📋 Columnas detectadas en el archivo:", list(df_raw.columns))

            # Función para buscar columna por palabras clave
            def find_column(keywords):
                for col in df_raw.columns:
                    col_lower = col.lower()
                    if any(kw.lower() in col_lower for kw in keywords):
                        return col
                return None

            # Mapeo flexible
            col_codigo = find_column(['codigo', 'código'])
            col_edificio = find_column(['edificio', 'torre'])
            col_dpto = find_column(['dpto', 'departamento'])
            col_med_inst = find_column(['medidor instalado', 'instalado'])
            col_n_med = find_column(['n° de medidor', 'nº de medidor', 'numero de medidor', 'medidor'])
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

            st.write("Columnas estandarizadas:", list(df.columns))
            st.write("Filas iniciales:", len(df))

            # Filtro 1: código (sin TOTAL, solo 4-5 dígitos)
            if 'codigo_raw' in df.columns:
                df['codigo_raw'] = df['codigo_raw'].str.split('.').str[0]  # quitar decimales
                df = df[~df['codigo_raw'].str.contains('TOTAL', case=False, na=False)]
                df = df[df['codigo_raw'].str.match(r'^\d{4,5}$', na=False)]
                st.write("Después de filtrar código:", len(df))

            # Filtro 2: torre y departamento numéricos > 0
            df['torre'] = pd.to_numeric(df['torre'], errors='coerce')
            df['departamento'] = pd.to_numeric(df['departamento'], errors='coerce')
            df = df.dropna(subset=['torre', 'departamento'])
            df = df[(df['torre'] > 0) & (df['departamento'] > 0)]
            st.write("Después de filtrar torre/departamento:", len(df))

            # Filtro 3: medidor instalado = "SI"
            if 'medidor_instalado' in df.columns:
                df['medidor_instalado'] = df['medidor_instalado'].str.upper().str.strip()
                df = df[df['medidor_instalado'] == 'SI']
                st.write("Después de filtrar medidor_instalado:", len(df))

            # Filtro 4: número de medidor no vacío
            if 'n_medidor' in df.columns:
                df['n_medidor'] = df['n_medidor'].astype(str).str.strip()
                df = df[df['n_medidor'].notna() & (df['n_medidor'] != '') & (df['n_medidor'] != 'nan')]
                st.write("Después de filtrar n_medidor:", len(df))

            # Filtro 5: monto > 0
            if 'monto' in df.columns:
                df['monto'] = pd.to_numeric(df['monto'], errors='coerce')
                df = df[df['monto'] > 0]
                st.write("Después de filtrar monto:", len(df))

            if df.empty:
                st.warning("No se encontraron filas válidas después de los filtros. Revisa el archivo.")
                st.stop()

            st.info(f"✅ Filas válidas después de filtrar: {len(df)}")

            # Procesar código para 5 dígitos (solo para mostrar)
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

            prop['torre'] = pd.to_numeric(prop['torre'], errors='coerce')
            prop[depto_col_prop] = pd.to_numeric(prop[depto_col_prop], errors='coerce')

            # Merge
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

            # Formatear números
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

with tab2:
    st.subheader("📊 Visualizar Medidores Guardados")

    try:
        hojas_medidor = gsheets.listar_hojas_medidor()
    except Exception as e:
        st.error(f"No se pudo conectar con Google Sheets: {e}")
        hojas_medidor = []

    if hojas_medidor:
        hoja_seleccionada = st.selectbox("Selecciona el período de medidores:", hojas_medidor)
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

            columnas_final = ['CÓDIGO', 'TORRE', 'DPTO', 'PROPIETARIO', 'DNI', 'MEDIDOR INSTALADO', 'N° MEDIDOR', 'MONTO (S/)']
            columnas_existentes = [col for col in columnas_final if col in df_viz.columns]
            st.dataframe(df_viz[columnas_existentes].fillna(""), use_container_width=True, height=600)

            import io
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_viz[columnas_existentes].to_excel(writer, index=False, sheet_name=hoja_seleccionada)
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
