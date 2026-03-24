import streamlit as st
import pandas as pd
import gsheets
from datetime import datetime, timedelta

st.set_page_config(page_title="Programación", page_icon="📅", layout="wide")

st.title("📅 Programación Mensual - Subir desde Excel")

# Crear pestañas principales
tab1, tab2 = st.tabs(["📊 Determinación de Cuotas", "💰 Amortización"])

# ====================== TAB 1: DETERMINACIÓN DE CUOTAS ======================
with tab1:
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
    st.subheader("Subir archivo Excel de determinación de cuotas")
    uploaded_file = st.file_uploader("Elige el archivo .xlsx", type=["xlsx"], key="det_cuotas")
    df = None
    if uploaded_file is not None:
        try:
            df_raw = pd.read_excel(uploaded_file, sheet_name=0, header=None)
            start_row = None
            for i in range(len(df_raw)):
                if "Lote" in df_raw.iloc[i].values:
                    start_row = i
                    break
            if start_row is None:
                st.error("No encontré la fila con encabezados (buscando 'Lote').")
            else:
                df = pd.read_excel(uploaded_file, sheet_name=0, skiprows=start_row)
                df.columns = df.columns.str.strip().str.replace('\n', ' ')
                df = df.reset_index(drop=True)
                df.index = df.index + 1
                st.success(f"Archivo leído: {len(df)} filas")
                st.dataframe(df.head(8))
        except Exception as e:
            st.error(f"Error al leer: {e}")

    if df is not None:
        periodo_key = f"{mes.upper()}_{int(anio)}"
        if gsheets.existe_programacion(periodo_key):
            st.error(f"⚠️ Ya existe una programación para {mes} {anio}")
        else:
            if st.button("Guardar en Google Sheets", type="primary", key="guardar_det_cuotas"):
                with st.spinner("Guardando..."):
                    try:
                        nombre_hoja = gsheets.crear_y_guardar_programacion(
                            df, periodo_key, mes, int(anio)
                        )
                        st.success(f"Guardado en hoja: **{nombre_hoja}**")
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")

# ====================== TAB 2: AMORTIZACIÓN ======================
with tab2:
    # Sub‑pestañas dentro de Amortización
    subtab1, subtab2 = st.tabs(["📤 Subir y Procesar", "📊 Visualizar Amortización"])

    # ------------------- SUBTAB 1: SUBIR Y PROCESAR -------------------
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

    # ------------------- SUBTAB 2: VISUALIZAR AMORTIZACIÓN -------------------
    with subtab2:
        st.subheader("Amortizaciones Guardadas")

        try:
            hojas_amort = gsheets.listar_hojas_amortizacion()
        except Exception as e:
            st.error(f"No se pudo conectar con Google Sheets: {e}")
            hojas_amort = []

        if hojas_amort:
            hoja_seleccionada = st.selectbox("Selecciona el período de amortización:", hojas_amort)
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

                # Aplicar formateo a columnas numéricas
                for col in ['TORRE', 'N°DPTO', 'CODIGO', 'AMORTIZACION CONVENIO']:
                    if col in df_guardado.columns:
                        df_guardado[col] = df_guardado[col].apply(formatear_numero)

                # 🔧 Hacer que el índice empiece en 1
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
