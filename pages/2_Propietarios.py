import streamlit as st
import pandas as pd
import gsheets
from datetime import datetime

st.set_page_config(page_title="Datos Propietarios", page_icon="📊", layout="wide")

# Sidebar styling (lo mantienes)
st.markdown("""<style>
[data-testid="stSidebar"] { background: linear-gradient(180deg, #1b5e20 0%, #2e7d32 100%); }
[data-testid="stSidebar"] * { color: white !important; }
</style>""", unsafe_allow_html=True)

st.title("🏠 Gestión de Propietarios y Deuda Inicial")

# Crear pestañas principales
tab1, tab2, tab3 = st.tabs(["📋 Visualizar Propietarios", "📤 Subir Propietarios", "💰 Deuda Inicial"])

# ====================== TAB 1: VISUALIZAR PROPIETARIOS ======================
with tab1:
    @st.cache_data(ttl=60)
    def cargar():
        return gsheets.leer_propietarios()

    try:
        df = cargar()
        st.markdown("### Datos Propietarios")
        filtro = st.text_input("Filtrar (DNI, nombre, código, torre):")
        if filtro:
            mask = (df["dni"].astype(str).str.contains(filtro, case=False, na=False) |
                    df["nombre"].astype(str).str.contains(filtro, case=False, na=False) |
                    df["codigo"].astype(str).str.contains(filtro, case=False, na=False) |
                    df["torre"].astype(str).str.contains(filtro, case=False, na=False))
            mostrar = df[mask]
        else:
            mostrar = df
        st.markdown("Mostrando **" + str(len(mostrar)) + "** propietarios")
        tabla = mostrar[["codigo","torre","dpto","dni","nombre","celular","correo","situacion"]].copy()
        tabla.columns = ["Código","Torre","N° Dpto","DNI","Nombres y Apellidos","Celular","Correo","Situación"]
        st.dataframe(tabla.reset_index(drop=True), use_container_width=True, hide_index=True, height=500)
        csv = tabla.to_csv(index=False).encode("utf-8")
        st.download_button("Descargar CSV", csv, "propietarios.csv", "text/csv")
    except Exception as e:
        st.error(f"Error conectando con Google Sheets: {e}")

# ====================== TAB 2: SUBIR PROPIETARIOS ======================
with tab2:
    st.info("""
    **Formato esperado del archivo Excel/CSV:**
    - Columnas requeridas: `TORRE`, `N°DPTO`, `CODIGO`, `DNI`, `NOMBRE`
    - Si no se proporciona DNI, se generará automáticamente un código COD1, COD2, etc.
    - La combinación Torre + N°DPTO + DNI/COD debe ser única
    """)

    uploaded_file = st.file_uploader("Elige el archivo Excel o CSV de propietarios",
                                    type=["xlsx", "csv"],
                                    key="propietarios_file")

    if uploaded_file is not None:
        try:
            # Leer el archivo según su tipo
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file, dtype=str)
            else:
                df = pd.read_excel(uploaded_file, dtype=str)

            # Limpiar nombres de columnas
            df.columns = df.columns.str.strip().str.replace('\n', ' ')

            # Mapeo flexible de columnas
            col_mapping = {}
            for col in df.columns:
                col_lower = col.lower()
                if 'torre' in col_lower:
                    col_mapping['torre'] = col
                elif 'dpto' in col_lower or 'departamento' in col_lower or 'n°dpto' in col_lower:
                    col_mapping['dpto'] = col
                elif 'codigo' in col_lower:
                    col_mapping['codigo'] = col
                elif 'dni' in col_lower:
                    col_mapping['dni'] = col
                elif 'nombre' in col_lower or 'apellido' in col_lower:
                    col_mapping['nombre'] = col

            # Verificar columnas requeridas
            required_cols = ['torre', 'dpto', 'codigo', 'nombre']
            missing_cols = [col for col in required_cols if col not in col_mapping]

            if missing_cols:
                st.error(f"Faltan columnas requeridas: {missing_cols}")
                st.stop()

            # Renombrar columnas
            df_renamed = df[list(col_mapping.values())].copy()
            df_renamed.columns = ['torre', 'dpto', 'codigo', 'nombre']

            # Validar unicidad y generar COD si no hay DNI
            duplicates = []
            existing_data = []

            try:
                # Obtener datos existentes
                existing = gsheets.leer_propietarios()
                if not existing.empty:
                    existing = existing[['torre', 'dpto', 'dni', 'codigo']].dropna(subset=['torre', 'dpto'])
                    existing_data = existing
            except:
                existing_data = pd.DataFrame()

            # Procesar cada fila
            new_rows = []
            cod_counter = 1

            for index, row in df_renamed.iterrows():
                torre = str(row['torre']).strip()
                dpto = str(row['dpto']).strip()
                nombre = str(row['nombre']).strip()
                codigo = str(row['codigo']).strip()
                dni = str(row.get('dni', '')).strip()

                # Si no hay DNI, usar COD
                if not dni or dni.lower() == 'nan':
                    dni = f"COD{cod_counter}"
                    cod_counter += 1

                # Validar combinación única
                if not existing_data.empty:
                    duplicate_mask = (
                        (existing_data['torre'].astype(str) == torre) &
                        (existing_data['dpto'].astype(str) == dpto) &
                        ((existing_data['dni'].astype(str) == dni) |
                         (existing_data['codigo'].astype(str) == codigo))
                    )
                    if duplicate_mask.any():
                        duplicates.append({
                            'torre': torre,
                            'dpto': dpto,
                            'dni': dni,
                            'codigo': codigo
                        })
                        continue  # Saltar a siguiente fila

                # Añadir fila válida
                new_row = row.to_dict()
                new_row['dni'] = dni
                # Incluir columnas opcionales si existen en la fila original
                for opt in ['celular', 'correo', 'situacion']:
                    if opt in row:
                        new_row[opt] = str(row[opt]).strip()
                    else:
                        new_row[opt] = ""
                new_rows.append(new_row)

            # Mostrar resultados del procesamiento
            st.success(f"✅ Procesado: {len(df_renamed)} filas del archivo")
            if duplicates:
                st.warning(f"🚫 Duplicados detectados: {len(duplicates)}")
                st.write("**Duplicados encontrados:**")
                dup_df = pd.DataFrame(duplicates)
                st.dataframe(dup_df, use_container_width=True)
            st.info(f"Filas válidas para subir: {len(new_rows)}")

            if new_rows:
                df_preview = pd.DataFrame(new_rows)
                st.write("Vista previa de datos a subir:")
                st.dataframe(df_preview, use_container_width=True)

                if st.button("Guardar Propietarios en Google Sheets", type="primary"):
                    with st.spinner("Guardando..."):
                        try:
                            df_upload = pd.DataFrame(new_rows).fillna("")
                            total_subidos = gsheets.subir_excel_a_sheets(df_upload)
                            st.success(f"¡{total_subidos} propietarios guardados correctamente!")
                            # Limpiar cache y recargar
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al guardar: {e}")

        except Exception as e:
            st.error(f"Error al procesar el archivo: {e}")

# ====================== TAB 3: DEUDA INICIAL ======================
with tab3:
    st.header("💰 Deuda Inicial (al 31/12 del año anterior)")

    # Sub-pestañas dentro de Deuda
    sub1, sub2 = st.tabs(["📤 Subir Deuda", "📊 Visualizar Deudas"])

    # ---------- SUBTAB 1: SUBIR DEUDA ----------
    with sub1:
        col1, col2 = st.columns(2)
        with col1:
            anio_deuda = st.number_input("Año de la deuda", min_value=2020, max_value=2030, value=2025, step=1)
        with col2:
            st.write("")  # espacio

        st.info("""
        **Formato esperado del archivo Excel:**
        - Columnas: `TORRE`, `N°DPTO`, `CODIGO`, `DNI`, `APELLIDOS Y NOMBRES`, `DEUDA AL 31/12/2025`
        - La primera fila debe ser los encabezados.
        - Se eliminará automáticamente la fila de "TOTAL" si existe.
        """)

        uploaded_deuda = st.file_uploader("Elige el archivo Excel de deuda", type=["xlsx"], key="deuda_file")

        if uploaded_deuda is not None:
            try:
                # Leer asumiendo encabezados en primera fila
                df = pd.read_excel(uploaded_deuda, sheet_name=0, header=0)
                df.columns = df.columns.str.strip().str.replace('\n', ' ')

                # Eliminar fila de total
                if 'APELLIDOS  Y  NOMBRES' in df.columns:
                    df = df[~df['APELLIDOS  Y  NOMBRES'].astype(str).str.contains('TOTAL', case=False, na=False)]
                # Quitar filas sin torre o departamento
                df = df.dropna(subset=['TORRE', 'N°DPTO'])

                # Calcular total de la deuda
                col_deuda = 'DEUDA AL 31/12/2025'
                if col_deuda in df.columns:
                    # Convertir a numérico, manejar errores
                    deuda_numeric = pd.to_numeric(df[col_deuda], errors='coerce')
                    total_deuda = deuda_numeric.sum()
                    total_formateado = f"S/ {total_deuda:,.2f}" if not pd.isna(total_deuda) else "S/ 0.00"
                else:
                    total_formateado = "No disponible"

                # Vista previa con índice desde 1
                df_vista = df.reset_index(drop=True)
                df_vista.index = df_vista.index + 1
                st.success(f"Archivo leído: {len(df)} filas válidas")

                # Mostrar total de deuda
                st.metric("💰 Total Deuda", total_formateado)

                st.write("Vista previa (primeras 10 filas):")
                st.dataframe(df_vista.head(10), use_container_width=True)

                if st.button("Guardar Deuda en Google Sheets", type="primary", key="guardar_deuda"):
                    with st.spinner("Guardando..."):
                        try:
                            nombre_hoja = gsheets.guardar_deuda_inicial(df, int(anio_deuda))
                            st.success(f"¡Guardado correctamente en hoja: **{nombre_hoja}**!")
                        except Exception as e:
                            st.error(f"Error al guardar: {e}")
            except Exception as e:
                st.error(f"Error al leer el archivo: {e}")

    # ---------- SUBTAB 2: VISUALIZAR DEUDAS GUARDADAS ----------
    with sub2:
        try:
            hojas_deuda = gsheets.listar_hojas_deuda()
        except Exception as e:
            st.error(f"No se pudo conectar con Google Sheets: {e}")
            hojas_deuda = []

        if hojas_deuda:
            hoja_seleccionada = st.selectbox("Selecciona el período de deuda:", hojas_deuda)
            df_deuda = gsheets.leer_hoja_deuda(hoja_seleccionada)

            if not df_deuda.empty:
                # Asegurar que la columna de deuda sea numérica
                col_deuda = 'DEUDA AL 31/12/2025'
                if col_deuda in df_deuda.columns:
                    deuda_numeric = pd.to_numeric(df_deuda[col_deuda], errors='coerce')
                    total_deuda = deuda_numeric.sum()
                    total_formateado = f"S/ {total_deuda:,.2f}" if not pd.isna(total_deuda) else "S/ 0.00"
                else:
                    total_formateado = "No disponible"

                # Formatear números (eliminar .0)
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

                for col in ['TORRE', 'N°DPTO', 'CODIGO']:
                    if col in df_deuda.columns:
                        df_deuda[col] = df_deuda[col].apply(formatear_numero)
                if col_deuda in df_deuda.columns:
                    df_deuda[col_deuda] = deuda_numeric.apply(formatear_numero)

                # Índice empezando en 1
                df_deuda = df_deuda.reset_index(drop=True)
                df_deuda.index = df_deuda.index + 1

                # Mostrar total de deuda
                st.metric("💰 Total Deuda", total_formateado)

                st.dataframe(df_deuda.fillna(""), use_container_width=True, height=600)

                # Descarga a Excel
                import io
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_deuda.to_excel(writer, index=False, sheet_name=hoja_seleccionada)
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
            st.info("No hay hojas de deuda guardadas. Sube un archivo en la pestaña 'Subir Deuda' para crear una.")
