import streamlit as st
import pandas as pd
import re
import gsheets
from datetime import datetime

st.set_page_config(page_title="Medidores de Agua", layout="wide")

st.title("💧 Medidores - Registro de Instalación y Pagos")

# Mostrar información sobre el código de 5 dígitos
with st.expander("ℹ️ Información sobre el código de 5 dígitos", expanded=False):
    st.info("""
    - En el archivo Excel, la columna **CODIGO** corresponde a un número de **5 dígitos** que combina torre y departamento.
    - Ejemplo: **01102** = Torre 1, Departamento 102.  
    - Si el archivo muestra solo 4 dígitos (ej. 1102), automáticamente se agregará un **0** al inicio para completar 5 dígitos.
    - Para el cruce con la lista de propietarios, se usan las columnas **EDIFICIO** y **DPTO** directamente, por lo que el formato del código no afecta.
    """)

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

            # Limpiar nombres de columnas
            df_raw.columns = df_raw.columns.str.strip()

            # Eliminar fila de total (si existe)
            if 'MONTO A PAGAR' in df_raw.columns:
                last_val = str(df_raw['MONTO A PAGAR'].iloc[-1])
                if 'SUM' in last_val.upper() or '=' in last_val:
                    df_raw = df_raw.iloc[:-1].copy()

            # Renombrar columnas a nombres internos
            renombres = {
                'CODIGO': 'codigo_raw',
                'EDIFICIO': 'torre',
                'DPTO': 'departamento',
                'MEDIDOR INSTALADO': 'medidor_instalado',
                'N° DE MEDIDOR': 'n_medidor',
                'MONTO A PAGAR': 'monto'
            }
            df = df_raw.rename(columns={col: renombres[col] for col in df_raw.columns if col in renombres})

            # Procesar código para que tenga 5 dígitos (rellenar con cero a la izquierda)
            df['codigo_raw'] = df['codigo_raw'].astype(str).str.strip()
            df['codigo_5d'] = df['codigo_raw'].apply(lambda x: x.zfill(5) if len(x) == 4 else x)
            # Nota: este código se usa solo para mostrar, no para el merge

            # Convertir torre y departamento a números
            df['torre'] = pd.to_numeric(df['torre'], errors='coerce')
            df['departamento'] = pd.to_numeric(df['departamento'], errors='coerce')

            # Cargar propietarios
            prop = gsheets.leer_propietarios()
            if prop.empty:
                st.error("No se pudo cargar Propietarios")
                st.stop()

            # Asegurar que las columnas en prop sean numéricas para el merge
            prop['torre'] = pd.to_numeric(prop['torre'], errors='coerce')
            prop['departamento'] = pd.to_numeric(prop['departamento'], errors='coerce')

            # Merge usando torre y departamento
            df_merged = df.merge(
                prop[['torre', 'departamento', 'nombre', 'dni', 'codigo']],
                on=['torre', 'departamento'],
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
                st.dataframe(df_no_coinciden[['codigo_5d', 'torre', 'departamento', 'medidor_instalado', 'n_medidor', 'monto']].fillna(""),
                             use_container_width=True, height=300)

            # Botón guardar
            if st.button("💾 Guardar en Google Sheets", type="primary"):
                try:
                    # Preparar DataFrame para guardar (usamos columnas útiles)
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
