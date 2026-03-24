import streamlit as st
import pandas as pd
import gsheets
from datetime import datetime, timedelta

st.set_page_config(page_title="Programación", page_icon="📅", layout="wide")

st.title("📅 Programación Mensual - Subir desde Excel")

# Crear pestañas
tab1, tab2 = st.tabs(["📊 Determinación de Cuotas", "💰 Amortización"])

# ====================== TAB 1: DETERMINACIÓN DE CUOTAS (original) ======================
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

    # Fechas sugeridas
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

            # Buscar fila con "Lote" (o ajusta según tu Excel)
            start_row = None
            for i in range(len(df_raw)):
                if "Lote" in df_raw.iloc[i].values:
                    start_row = i
                    break

            if start_row is None:
                st.error("No encontré la fila con encabezados (buscando 'Lote'). Verifica el formato del Excel.")
            else:
                df = pd.read_excel(uploaded_file, sheet_name=0, skiprows=start_row)
                df.columns = df.columns.str.strip().str.replace('\n', ' ')

                st.success(f"Archivo leído: {len(df)} filas detectadas")
                st.write("Vista previa (primeras 8 filas):")
                st.dataframe(df.head(8))

        except Exception as e:
            st.error(f"Error al leer el Excel: {str(e)}")

    if df is not None:
        periodo_key = f"{mes.upper()}_{int(anio)}"

        if gsheets.existe_programacion(periodo_key):
            st.error(f"⚠️ Ya existe una programación para {mes} {anio}")
            st.info("Cambia el mes/año o elimina manualmente la hoja en Google Sheets si quieres sobrescribir.")
        else:
            if st.button("Guardar en Google Sheets", type="primary", key="guardar_det_cuotas"):
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

# ====================== TAB 2: AMORTIZACIÓN (nueva) ======================
with tab2:
    st.subheader("Subir archivo Excel de Amortización")

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

    uploaded_file_amort = st.file_uploader("Elige el archivo Excel de amortización", type=["xlsx"], key="amort_file")

    df_amort = None

    if uploaded_file_amort is not None:
        try:
            # Leer el archivo asumiendo que los encabezados están en la primera fila
            df_amort = pd.read_excel(uploaded_file_amort, sheet_name=0, header=0)
            df_amort.columns = df_amort.columns.str.strip().str.replace('\n', ' ')

            # Limpiar: eliminar fila de total (si existe)
            # Buscar si la última fila tiene "TOTAL" en la columna ITEM o APELLIDOS
            if 'ITEM' in df_amort.columns:
                df_amort = df_amort[~df_amort['ITEM'].astype(str).str.contains('TOTAL', case=False, na=False)]
            if 'APELLIDOS  Y  NOMBRES' in df_amort.columns:
                df_amort = df_amort[~df_amort['APELLIDOS  Y  NOMBRES'].astype(str).str.contains('TOTAL', case=False, na=False)]

            # Opcional: eliminar filas con NaN en TORRE o N°DPTO (si las hubiera)
            df_amort = df_amort.dropna(subset=['TORRE', 'N°DPTO'])

            st.success(f"Archivo leído: {len(df_amort)} filas válidas")
            st.write("Vista previa (primeras 8 filas):")
            st.dataframe(df_amort.head(8))

        except Exception as e:
            st.error(f"Error al leer el Excel: {str(e)}")

    if df_amort is not None:
        if st.button("Guardar en Google Sheets (Amortización)", type="primary", key="guardar_amort"):
            with st.spinner("Guardando datos de amortización..."):
                try:
                    nombre_hoja = gsheets.guardar_amortizacion(
                        df=df_amort,
                        mes=mes_amort,
                        anio=int(anio_amort)
                    )
                    st.success(f"¡Guardado correctamente en hoja: **{nombre_hoja}**!")
                except Exception as e:
                    st.error(f"Error al guardar: {str(e)}")
