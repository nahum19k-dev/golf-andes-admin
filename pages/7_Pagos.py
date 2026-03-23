import streamlit as st
import pandas as pd
import re
import gsheets

st.set_page_config(page_title="Pagos Bancos", layout="wide")

st.title("💰 Pagos - Registro de Depósitos Bancos")

# Selección de período
col1, col2 = st.columns(2)
with col1:
    mes = st.selectbox(
        "Mes",
        ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
         "Julio", "Agosto", "Setiembre", "Octubre", "Noviembre", "Diciembre"]
    )
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

        # Renombrar columnas clave (ajusta si tu Excel varía)
        rename_map = {
            'DESCRIPCION OPERACIONES': 'descripcion',
            'INGRESOS': 'ingresos',
            'Fecha': 'fecha'
        }
        df = df_raw.rename(columns=rename_map)

        # Extraer lote (últimos 5 dígitos de descripción)
        def extraer_lote(desc):
            if pd.isna(desc):
                return None
            match = re.search(r'(\d{5})$', str(desc).strip())
            return match.group(1) if match else None

        df['codigo'] = df['descripcion'].apply(extraer_lote)

        # Cargar propietarios
        prop = gsheets.leer_propietarios()

        if prop.empty:
            st.error("No se pudo cargar la hoja 'Propietarios'")
            st.stop()

        # Merge con propietarios usando 'codigo'
        df_merged = df.merge(
            prop[['codigo', 'torre', 'departamento', 'nombre']],
            on='codigo',
            how='left'
        )

        # Agregar DNI si existe (ajusta nombre de columna si es diferente)
        dni_col = None
        for col in ['dni', 'DNI', 'Dni']:
            if col in prop.columns:
                dni_col = col
                break
        if dni_col:
            df_merged = df_merged.merge(
                prop[['codigo', dni_col]],
                on='codigo',
                how='left'
            )

        # Convertir columnas numéricas para ordenamiento
        for col in ['torre', 'departamento']:
            if col in df_merged.columns:
                df_merged[col] = pd.to_numeric(df_merged[col], errors='coerce')

        # ==================== Separar coincidencias y no coincidencias ====================
        df_coinciden = df_merged[df_merged['torre'].notna()].copy()
        df_no_coinciden = df_merged[df_merged['torre'].isna()].copy()

        # Ordenar los que sí coinciden
        sort_cols = ['torre', 'departamento', 'nombre']
        df_coinciden = df_coinciden.sort_values(by=sort_cols, na_position='last')

        # ==================== Mostrar resultados ====================
        st.subheader(f"📋 Pagos procesados y ordenados - {mes} {anio}")

        columnas_mostrar = ['fecha', 'descripcion', 'codigo', 'torre', 'departamento', 'nombre', 'ingresos']
        if dni_col:
            columnas_mostrar.insert(6, dni_col)

        if not df_coinciden.empty:
            st.markdown("### Coincidencias con propietarios")
            st.dataframe(
                df_coinciden[columnas_mostrar].fillna(""),
                use_container_width=True,
                height=400
            )
            total_coinciden = pd.to_numeric(df_coinciden['ingresos'], errors='coerce').sum()
            st.metric("Total ingresos coincidentes", f"S/ {total_coinciden:,.2f}")
        else:
            st.info("No se encontraron coincidencias con propietarios.")

        if not df_no_coinciden.empty:
            st.markdown("### Pagos sin coincidencia (revisar descripción o código)")
            st.dataframe(
                df_no_coinciden[['fecha', 'descripcion', 'codigo', 'ingresos']].fillna(""),
                use_container_width=True,
                height=300
            )
            total_no = pd.to_numeric(df_no_coinciden['ingresos'], errors='coerce').sum()
            st.metric("Total ingresos sin coincidencia", f"S/ {total_no:,.2f}")
        else:
            st.success("Todos los pagos coincidieron con propietarios.")

        # ==================== Guardar en Google Sheets ====================
        if st.button("💾 Guardar Pagos Procesados en Google Sheets", type="primary"):
            if gsheets.existe_programacion(periodo_key):  # Reutilizamos la función (cambia nombre si prefieres)
                st.error(f"Ya existe una hoja para {mes} {anio}. Cambia el período o elimina la hoja manualmente.")
            else:
                with st.spinner("Creando hoja y guardando..."):
                    try:
                        # Preparar DF para guardar (solo columnas útiles + período)
                        df_guardar = df_coinciden.copy()
                        df_guardar['periodo'] = periodo_key
                        df_guardar['mes'] = mes
                        df_guardar['anio'] = anio

                        # Guardar usando la misma lógica de programación (ajusta si quieres hoja diferente)
                        nombre_hoja = gsheets.crear_y_guardar_programacion(
                            df=df_guardar,
                            periodo_key=periodo_key,
                            mes=mes,
                            anio=int(anio)
                        )
                        st.success(f"Guardado correctamente en: **{nombre_hoja}**")
                    except Exception as e:
                        st.error(f"Error al guardar: {str(e)}")

    except Exception as e:
        st.error(f"Error general al procesar: {str(e)}")
