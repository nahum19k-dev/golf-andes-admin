import streamlit as st
import pandas as pd
import re
import gsheets

st.set_page_config(page_title="Pagos Bancos", layout="wide")

st.title("💰 Pagos - Registro de Depósitos Bancos")

col1, col2 = st.columns(2)
with col1:
    mes = st.selectbox("Mes", ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                               "Julio", "Agosto", "Setiembre", "Octubre", "Noviembre", "Diciembre"])
with col2:
    anio = st.number_input("Año", min_value=2025, max_value=2035, value=2026, step=1)

periodo_key = f"{mes.upper()}_{int(anio)}"

uploaded_file = st.file_uploader(
    "Sube el archivo Excel de DATA BANCOS (hoja ENERO o similar)",
    type=["xlsx"]
)

if uploaded_file is not None:
    try:
        # Lectura corregida: saltar metadatos (5 filas)
        df_raw = pd.read_excel(
            uploaded_file,
            sheet_name=0,
            skiprows=5,
            header=0
        )

        # Limpieza de nombres de columnas
        df_raw.columns = df_raw.columns.str.strip().str.replace('\n', ' ').str.replace('\r', '')

        st.success(f"Archivo leído: {len(df_raw)} filas")

        # Mostrar columnas detectadas (para depuración)
        st.write("**Columnas detectadas después de skiprows:**")
        st.write(list(df_raw.columns))

        # Renombrar flexible
        rename_dict = {}
        for col in df_raw.columns:
            col_lower = col.lower().strip()
            if 'descripcion' in col_lower or 'operaciones' in col_lower:
                rename_dict[col] = 'descripcion'
            elif 'ingresos' in col_lower or 'monto' in col_lower:
                rename_dict[col] = 'ingresos'
            elif 'fecha' in col_lower:
                rename_dict[col] = 'fecha'
            elif 'n°' in col_lower or 'operación' in col_lower:
                rename_dict[col] = 'n_operacion'

        df = df_raw.rename(columns=rename_dict)

        # Verificaciones mínimas
        if 'descripcion' not in df.columns:
            st.error("No se encontró columna con 'DESCRIPCION' o 'OPERACIONES' después de procesar")
            st.stop()

        if 'ingresos' not in df.columns:
            st.warning("No se detectó columna 'INGRESOS'. Continuando sin totales precisos.")

        # Extraer código (últimos 5 dígitos de descripcion)
        def extraer_codigo(desc):
            if pd.isna(desc):
                return None
            match = re.search(r'(\d{5})$', str(desc).strip())
            return match.group(1) if match else None

        df['codigo'] = df['descripcion'].apply(extraer_codigo)

        # Cargar propietarios
        prop = gsheets.leer_propietarios()
        if prop.empty:
            st.error("No se pudo cargar la hoja 'Propietarios'")
            st.stop()

        # Merge
        df_merged = df.merge(
            prop[['codigo', 'torre', 'departamento', 'nombre']],
            on='codigo',
            how='left'
        )

        # DNI si existe
        dni_col = next((c for c in prop.columns if 'dni' in c.lower()), None)
        if dni_col:
            df_merged = df_merged.merge(prop[['codigo', dni_col]], on='codigo', how='left')

        # Convertir para ordenamiento
        for col in ['torre', 'departamento']:
            if col in df_merged.columns:
                df_merged[col] = pd.to_numeric(df_merged[col], errors='coerce')

        # Separar
        df_coinciden = df_merged[df_merged['torre'].notna()].copy()
        df_no_coinciden = df_merged[df_merged['torre'].isna()].copy()

        df_coinciden = df_coinciden.sort_values(by=['torre', 'departamento', 'nombre'], na_position='last')

        # Mostrar
        st.subheader(f"Pagos procesados - {mes} {anio}")

        cols_mostrar = ['fecha', 'descripcion', 'codigo', 'torre', 'departamento', 'nombre', 'ingresos']
        if dni_col:
            cols_mostrar.insert(6, dni_col)

        if not df_coinciden.empty:
            st.markdown("### Coincidencias")
            st.dataframe(df_coinciden[cols_mostrar].fillna(""), use_container_width=True, height=500)
            total = pd.to_numeric(df_coinciden['ingresos'], errors='coerce').sum()
            st.metric("Total coincidentes", f"S/ {total:,.2f}")

        if not df_no_coinciden.empty:
            st.markdown("### Sin coincidencia")
            st.dataframe(df_no_coinciden[['fecha', 'descripcion', 'codigo', 'ingresos']].fillna(""),
                         use_container_width=True, height=300)

        # Aquí puedes agregar el botón de guardar como en versiones anteriores

    except Exception as e:
        st.error(f"Error al procesar el archivo: {str(e)}")
        import traceback
        st.code(traceback.format_exc(), language="python")
