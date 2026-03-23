import streamlit as st
import pandas as pd
import re
import gsheets
from datetime import datetime

st.set_page_config(page_title="Medidores de Agua", layout="wide")

st.title("💧 Medidores - Registro de Instalación y Pagos")

tab1, tab2 = st.tabs(["📤 Subir y Procesar", "📊 Visualizar Medidores"])

# ====================== TAB 1: SUBIR Y PROCESAR ======================
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        mes = st.selectbox("Mes", ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                                   "Julio","Agosto","Setiembre","Octubre","Noviembre","Diciembre"])
    with col2:
        anio = st.number_input("Año", min_value=2025, max_value=2035, value=2026, step=1)

    uploaded_file = st.file_uploader(
        "Sube el archivo Excel de MEDIDORES",
        type=["xlsx"]
    )

    if uploaded_file is not None:
        try:
            # Leer archivo
            df_raw = pd.read_excel(uploaded_file, sheet_name=0, header=0)

            # Limpiar nombres de columnas (quitar espacios, saltos de línea)
            df_raw.columns = df_raw.columns.str.strip().str.replace('\n', ' ').str.replace('\r', '')

            # Eliminar fila de total (si existe)
            # Buscar en la columna de MONTO A PAGAR si la última fila contiene "SUM" o "="
            col_monto = next((c for c in df_raw.columns if 'MONTO' in c.upper()), None)
            if col_monto:
                last_val = str(df_raw[col_monto].iloc[-1])
                if 'SUM' in last_val.upper() or '=' in last_val:
                    df_raw = df_raw.iloc[:-1].copy()

            # Renombrar columnas a nombres internos (usando nombres exactos que salen del Excel)
            renombres = {
                'CODIGO': 'codigo_raw',
                'EDIFICIO': 'torre',
                'DPTO': 'departamento',
                'MEDIDOR INSTALADO': 'medidor_instalado',
                'N° DE MEDIDOR': 'n_medidor',
                'MONTO A PAGAR': 'monto'
            }
            # Renombrar solo las columnas que existen
            for old, new in renombres.items():
                if old in df_raw.columns:
                    df_raw.rename(columns={old: new}, inplace=True)

            df = df_raw.copy()

            # Convertir torre y departamento a números
            df['torre'] = pd.to_numeric(df['torre'], errors='coerce')
            df['departamento'] = pd.to_numeric(df['departamento'], errors='coerce')

            # Procesar código para 5 dígitos (solo para mostrar)
            if 'codigo_raw' in df.columns:
                df['codigo_raw'] = df['codigo_raw'].astype(str).str.strip()
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
                st.error("No se encontró columna de departamento en Propietarios. Las columnas disponibles son: " + ", ".join(prop.columns))
                st.stop()

            # Asegurar que las columnas de torre y departamento sean numéricas en prop
            prop['torre'] = pd.to_numeric(prop['torre'], errors='coerce')
            prop[depto_col_prop] = pd.to_numeric(prop[depto_col_prop], errors='coerce')

            # Merge usando torre y departamento (prop tiene columna depto con nombre detectado)
            df_merged = df.merge(
                prop[['torre', depto_col_prop, 'nombre', 'dni', 'codigo']],
                left_on=['torre', 'departamento'],
                right_on=['torre', depto_col_prop],
                how='left'
            )

            # Renombrar la columna de código del propietario para evitar confusión
            df_merged.rename(columns={'codigo': 'codigo_propietario'}, inplace=True)

            # Separar coincidentes y no coincidentes
            df_coinciden = df_merged[df_merged['nombre'].notna()].copy()
            df_no_coinciden = df_merged[df_merged['nombre'].isna()].copy()

            # Ordenar
            df_coinciden = df_coinciden.sort_values(by=['torre', 'departamento'])

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
                    # Preparar DataFrame para guardar
                    df_guardar = df_coinciden[['codigo_5d', 'torre', 'departamento', 'nombre', 'dni', 'medidor_instalado', 'n_medidor', 'monto']].copy()
                    df_guardar.columns = ['codigo', 'torre', 'departamento', 'nombre', 'dni', 'medidor_instalado', 'n_medidor', 'monto']
                    nombre_hoja = gsheets.guardar_medidor(
                        df=df_guardar,
                        mes=mes,
                        anio=int(anio)
                    )
                    st.success(f"Guardado en hoja: **{nombre_hoja}**")
                except Exception as e:
                    st.error(f"Error al guardar: {str(e)}")

        except Exception as e:
            st.error(f"Error al procesar: {str(e)}")

# ====================== TAB 2: VISUALIZAR MEDIDORES ======================
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
            # Renombrar columnas para visualización amigable
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

            # Orden de columnas deseado
            columnas_final = ['CÓDIGO', 'TORRE', 'DPTO', 'PROPIETARIO', 'DNI', 'MEDIDOR INSTALADO', 'N° MEDIDOR', 'MONTO (S/)']
            columnas_existentes = [col for col in columnas_final if col in df_viz.columns]
            st.dataframe(df_viz[columnas_existentes].fillna(""), use_container_width=True, height=600)

            # Botón de descarga
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
