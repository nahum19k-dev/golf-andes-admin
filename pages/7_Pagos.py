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
        df_raw = pd.read_excel(uploaded_file, sheet_name=0)
        df_raw.columns = df_raw.columns.str.strip()

        st.success(f"Archivo leído: {len(df_raw)} filas")

        # Diagnóstico: mostrar columnas reales detectadas
        st.write("**Columnas detectadas en el Excel:**")
        st.write(list(df_raw.columns))

        # Renombrar flexible para 'descripcion'
        descripcion_col = None
        for col in df_raw.columns:
            col_lower = str(col).lower().strip()
            if 'descripcion' in col_lower or 'operaciones' in col_lower:
                descripcion_col = col
                break

        if not descripcion_col:
            st.error("No se encontró columna que contenga 'DESCRIPCION' o 'OPERACIONES'")
            st.stop()

        df = df_raw.rename(columns={descripcion_col: 'descripcion'})

        # Renombrar ingresos y fecha (similar)
        for orig, nuevo in [
            ('INGRESOS', 'ingresos'),
            ('Ingresos', 'ingresos'),
            ('MONTO', 'ingresos'),  # por si acaso
            ('Fecha', 'fecha'),
            ('FECHA', 'fecha')
        ]:
            if orig in df.columns:
                df = df.rename(columns={orig: nuevo})

        # Verificar que existan las columnas mínimas
        if 'descripcion' not in df.columns:
            st.error("Columna 'descripcion' no pudo ser creada")
            st.stop()
        if 'ingresos' not in df.columns:
            st.warning("No se encontró columna de 'INGRESOS'. Se intentará continuar sin ella.")

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
            st.error("No se pudo cargar la hoja 'Propietarios'")
            st.stop()

        # Merge usando 'codigo'
        df_merged = df.merge(
            prop[['codigo', 'torre', 'departamento', 'nombre']],
            on='codigo',
            how='left'
        )

        # DNI si existe
        dni_col = next((c for c in prop.columns if 'dni' in c.lower()), None)
        if dni_col:
            df_merged = df_merged.merge(
                prop[['codigo', dni_col]],
                on='codigo',
                how='left'
            )

        # Convertir a numérico para orden
        for col in ['torre', 'departamento']:
            if col in df_merged.columns:
                df_merged[col] = pd.to_numeric(df_merged[col], errors='coerce')

        # Separar coinciden / no coinciden
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
            st.markdown("### Sin coincidencia (revisar)")
            st.dataframe(df_no_coinciden[['fecha', 'descripcion', 'codigo', 'ingresos']].fillna(""),
                         use_container_width=True, height=300)

        # Guardar botón (ya lo tienes implementado en versiones anteriores)

    except Exception as e:
        st.error(f"Error general al procesar: {str(e)}")
        import traceback
        st.code(traceback.format_exc(), language="python")
