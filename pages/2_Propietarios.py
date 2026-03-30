import streamlit as st
import pandas as pd
import supabase_client
from datetime import datetime

st.set_page_config(page_title="Datos Propietarios", page_icon="📊", layout="wide")

# Sidebar styling
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
            mostrar = df[mask].copy()
        else:
            mostrar = df.copy()

        # Limpiar NaN y la cadena literal "nan"
        mostrar = mostrar.fillna('')
        # Reemplazar la cadena literal "nan" (independientemente de mayúsculas)
        mostrar = mostrar.applymap(lambda x: '' if isinstance(x, str) and x.lower() == 'nan' else x)

        st.markdown(f"Mostrando **{len(mostrar)}** propietarios")
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
    - Columnas requeridas: `TORRE`, `N°DPTO`, `CODIGO`, `NOMBRE`
    - El DNI es opcional; si no se proporciona, se genera automáticamente como COD1, COD2...
    - La combinación Torre + N°DPTO debe ser única.
    - Torre se guardará con dos dígitos (01, 02, … 19).  
    - Código se guardará con cinco dígitos (relleno con cero a la izquierda).  
    - DNI se formateará a 8 dígitos (si es numérico y tiene menos de 8). RUC (11 dígitos) se conserva.
    """)

    uploaded_file = st.file_uploader("Elige el archivo Excel o CSV de propietarios",
                                    type=["xlsx", "csv"],
                                    key="propietarios_file")

    if uploaded_file is not None:
        try:
            # Leer el archivo según su tipo
            if uploaded_file.name.endswith('.csv'):
                df_raw = pd.read_csv(uploaded_file, dtype=str)
            else:
                df_raw = pd.read_excel(uploaded_file, dtype=str)

            # Limpiar nombres de columnas
            df_raw.columns = df_raw.columns.str.strip().str.replace('\n', ' ')
            
            # --- DETECCIÓN EXACTA DE COLUMNAS ---
            col_mapping = {}
            for col in df_raw.columns:
                col_lc = col.lower().strip()
                if col_lc == 'torre':
                    col_mapping['torre'] = col
                elif col_lc in ['dpto', 'departamento', 'n°dpto']:
                    col_mapping['dpto'] = col
                elif col_lc == 'codigo':
                    col_mapping['codigo'] = col
                elif col_lc == 'dni':
                    col_mapping['dni'] = col
                elif col_lc in ['nombre', 'apellidos y nombres', 'nombres']:
                    col_mapping['nombre'] = col
                elif col_lc in ['direccion', 'dirección', 'dir']:
                    col_mapping['direccion'] = col
                elif col_lc in ['celular', 'telefono', 'tel']:
                    col_mapping['celular'] = col
                elif col_lc in ['correo', 'email', 'e-mail']:
                    col_mapping['correo'] = col
                elif col_lc in ['situacion', 'situación', 'estado']:
                    col_mapping['situacion'] = col

            # Verificar columnas obligatorias
            cols_req = ['torre', 'dpto', 'codigo', 'nombre']
            faltantes = [c for c in cols_req if c not in col_mapping]
            if faltantes:
                st.error(f"Faltan columnas obligatorias: {', '.join(faltantes)}")
                st.stop()

            # Crear DataFrame normalizado
            df = pd.DataFrame({
                'torre': df_raw[col_mapping['torre']].astype(str).str.strip(),
                'dpto': df_raw[col_mapping['dpto']].astype(str).str.strip(),
                'codigo': df_raw[col_mapping['codigo']].astype(str).str.strip(),
                'nombre': df_raw[col_mapping['nombre']].astype(str).str.strip(),
            })
            
            # Formatear torre a 2 dígitos (01, 02, ...)
            df['torre'] = df['torre'].str.zfill(2)
            
            # Formatear código a 5 dígitos (rellenar con cero a la izquierda)
            df['codigo'] = df['codigo'].str.zfill(5)

            # DNI (opcional)
            if 'dni' in col_mapping:
                df['dni'] = df_raw[col_mapping['dni']].astype(str).str.strip()
            else:
                df['dni'] = ""

            # Columnas opcionales
            for opt in ['celular', 'correo', 'situacion', 'direccion']:
                if opt in col_mapping:
                    df[opt] = df_raw[col_mapping[opt]].astype(str).str.strip()
                else:
                    df[opt] = ""

            # Eliminar columnas duplicadas (por si acaso)
            df = df.loc[:, ~df.columns.duplicated()]

            # --- FUNCIÓN PARA FORMATEAR DNI / RUC ---
            def formatear_dni(valor):
                if pd.isna(valor) or valor == '':
                    return valor
                valor = str(valor).strip()
                # Si es numérico y tiene 11 dígitos, se asume RUC, se deja igual
                if valor.isdigit() and len(valor) == 11:
                    return valor
                # Si es numérico y tiene 8 dígitos, ya está bien
                if valor.isdigit() and len(valor) == 8:
                    return valor
                # Si es numérico y tiene menos de 8 dígitos, rellenar con ceros a la izquierda
                if valor.isdigit() and len(valor) < 8:
                    return valor.zfill(8)
                # Si no es numérico (ej. COD123) se devuelve sin cambios
                return valor

            # Aplicar formateo a la columna DNI
            df['dni'] = df['dni'].apply(formatear_dni)

            # --- VALIDACIÓN DE DUPLICADOS INTERNOS ---
            df['key'] = df['torre'] + '_' + df['dpto']
            duplicados_internos = df[df.duplicated(subset=['key'], keep=False)]
            if not duplicados_internos.empty:
                st.error("🚨 Se encontraron departamentos duplicados en el archivo:")
                st.dataframe(duplicados_internos[['torre','dpto','codigo','nombre']], use_container_width=True)
                st.stop()

            # --- VALIDACIÓN CONTRA DATOS EXISTENTES ---
            try:
                existing = gsheets.leer_propietarios()
                if not existing.empty:
                    existing['key'] = existing['torre'].astype(str) + '_' + existing['dpto'].astype(str)
                    claves_existentes = set(existing['key'].tolist())
                    claves_nuevas = set(df['key'].tolist())
                    claves_dup = claves_nuevas & claves_existentes
                    if claves_dup:
                        st.error(f"🚨 {len(claves_dup)} departamentos ya existen en la base:")
                        duplicados_exist = existing[existing['key'].isin(claves_dup)][['torre','dpto','codigo','dni','nombre']]
                        st.dataframe(duplicados_exist, use_container_width=True)
                        st.stop()
            except:
                pass

            # --- GENERAR DNI AUTOMÁTICO SI NO TIENE ---
            try:
                spreadsheet = gsheets.get_spreadsheet()
                try:
                    control = spreadsheet.worksheet("Control_Codigos")
                    last_val = control.cell(1, 1).value
                    cod_counter = int(last_val) if last_val else 0
                except:
                    control = spreadsheet.add_worksheet(title="Control_Codigos", rows=10, cols=5)
                    control.update_cell(1, 1, "0")
                    cod_counter = 0
            except:
                cod_counter = 0

            nuevas_filas = []
            for _, fila in df.iterrows():
                dni = str(fila['dni']).strip()
                if not dni or dni.lower() == 'nan':
                    cod_counter += 1
                    dni = f"COD{cod_counter}"
                nuevas_filas.append({
                    'torre': fila['torre'],
                    'dpto': fila['dpto'],
                    'codigo': fila['codigo'],
                    'dni': dni,
                    'nombre': fila['nombre'],
                    'celular': fila.get('celular', ''),
                    'correo': fila.get('correo', ''),
                    'situacion': fila.get('situacion', ''),
                    'direccion': fila.get('direccion', '')
                })

            if cod_counter > 0:
                try:
                    control.update_cell(1, 1, str(cod_counter))
                except:
                    pass

            # Mostrar resumen
            st.success(f"✅ {len(nuevas_filas)} registro(s) listo(s) para subir.")
            df_preview = pd.DataFrame(nuevas_filas).fillna('')
            # Limpiar la cadena "nan"
            df_preview = df_preview.applymap(lambda x: '' if isinstance(x, str) and x.lower() == 'nan' else x)
            st.write("Vista previa:")
            st.dataframe(df_preview, use_container_width=True)

            if st.button("💾 Guardar en Google Sheets", type="primary"):
                with st.spinner("Guardando..."):
                    try:
                        df_upload = pd.DataFrame(nuevas_filas).fillna("")
                        total = gsheets.subir_excel_a_sheets(df_upload)
                        st.success(f"¡{total} propietarios guardados correctamente!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

        except Exception as e:
            st.error(f"Error al procesar el archivo: {e}")

# ====================== TAB 3: DEUDA INICIAL ======================
with tab3:
    st.header("💰 Deuda Inicial (al 31/12 del año anterior)")

    sub1, sub2 = st.tabs(["📤 Subir Deuda", "📊 Visualizar Deudas"])

    # ---------- SUBTAB 1: SUBIR DEUDA ----------
    with sub1:
        col1, col2 = st.columns(2)
        with col1:
            anio_deuda = st.number_input("Año de la deuda", min_value=2020, max_value=2030, value=2025, step=1)
        with col2:
            st.write("")

        st.info("""
        **Formato esperado del archivo Excel:**
        - Columnas: `TORRE`, `N°DPTO`, `CODIGO`, `DNI`, `APELLIDOS Y NOMBRES`, `DEUDA AL 31/12/2025`
        - La primera fila debe ser los encabezados.
        - Se eliminará automáticamente la fila de "TOTAL" si existe.
        """)

        uploaded_deuda = st.file_uploader("Elige el archivo Excel de deuda", type=["xlsx"], key="deuda_file")

        if uploaded_deuda is not None:
            try:
                df = pd.read_excel(uploaded_deuda, sheet_name=0, header=0)
                df.columns = df.columns.str.strip().str.replace('\n', ' ')

                # Eliminar fila TOTAL si existe
                if 'APELLIDOS  Y  NOMBRES' in df.columns:
                    df = df[~df['APELLIDOS  Y  NOMBRES'].astype(str).str.contains('TOTAL', case=False, na=False)]
                df = df.dropna(subset=['TORRE', 'N°DPTO'])

                col_deuda = 'DEUDA AL 31/12/2025'
                if col_deuda in df.columns:
                    deuda_numeric = pd.to_numeric(df[col_deuda], errors='coerce')
                    total_deuda = deuda_numeric.sum()
                    total_formateado = f"S/ {total_deuda:,.2f}" if not pd.isna(total_deuda) else "S/ 0.00"
                else:
                    total_formateado = "No disponible"

                df_vista = df.reset_index(drop=True)
                df_vista.index = df_vista.index + 1
                st.success(f"Archivo leído: {len(df)} filas válidas")
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
                col_deuda = 'DEUDA AL 31/12/2025'
                if col_deuda in df_deuda.columns:
                    deuda_numeric = pd.to_numeric(df_deuda[col_deuda], errors='coerce')
                    total_deuda = deuda_numeric.sum()
                    total_formateado = f"S/ {total_deuda:,.2f}" if not pd.isna(total_deuda) else "S/ 0.00"
                else:
                    total_formateado = "No disponible"

                # Limpiar NaN y la cadena literal "nan"
                df_deuda = df_deuda.fillna('')
                df_deuda = df_deuda.applymap(lambda x: '' if isinstance(x, str) and x.lower() == 'nan' else x)

                def formatear_numero(valor):
                    try:
                        if pd.isna(valor) or valor == '':
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

                df_deuda = df_deuda.reset_index(drop=True)
                df_deuda.index = df_deuda.index + 1

                st.metric("💰 Total Deuda", total_formateado)
                st.dataframe(df_deuda, use_container_width=True, height=600)

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
