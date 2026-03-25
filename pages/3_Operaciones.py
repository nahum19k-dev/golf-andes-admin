import streamlit as st
import pandas as pd
import gsheets
from datetime import datetime

st.set_page_config(page_title="Operaciones", page_icon="📊", layout="wide")

st.title("📊 Operaciones - Estado de Cuenta por Departamento")

# Inicializar session_state para almacenar los datos cargados
if 'df_final' not in st.session_state:
    st.session_state.df_final = None
if 'datos_cargados' not in st.session_state:
    st.session_state.datos_cargados = False

# Crear pestañas
tab1, tab2 = st.tabs(["📋 Detalle por Departamento", "🏢 Resumen por Torres"])

# ====================== TAB 1: DETALLE POR DEPARTAMENTO ======================
with tab1:
    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        mes = st.selectbox("Mes", ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                                   "Julio","Agosto","Setiembre","Octubre","Noviembre","Diciembre"])
    with col2:
        anio = st.number_input("Año", min_value=2025, max_value=2035, value=2026, step=1)
    with col3:
        codigo_filtro = st.text_input("Buscar por código (ej. 01101)", placeholder="Dejar en blanco para mostrar todos")

    if st.button("Generar Estado de Cuenta", type="primary"):
        with st.spinner("Cargando datos..."):
            try:
                # ========== PROPIETARIOS ==========
                prop = gsheets.leer_propietarios()
                if prop.empty:
                    st.error("No se pudo cargar la lista de propietarios.")
                    st.stop()

                col_torre_prop = None
                col_depto_prop = None
                for col in prop.columns:
                    col_low = col.lower()
                    if 'torre' in col_low:
                        col_torre_prop = col
                    if 'departamento' in col_low or 'dpto' in col_low or 'n°dpto' in col_low:
                        col_depto_prop = col
                if col_torre_prop is None or col_depto_prop is None:
                    st.error("No se encontraron columnas 'torre' y 'departamento' en propietarios.")
                    st.stop()

                base = prop[[col_torre_prop, col_depto_prop, 'codigo', 'dni', 'nombre']].copy()
                base.rename(columns={col_torre_prop: 'torre', col_depto_prop: 'departamento'}, inplace=True)
                base['torre'] = pd.to_numeric(base['torre'], errors='coerce')
                base['departamento'] = pd.to_numeric(base['departamento'], errors='coerce')
                base = base.dropna(subset=['torre', 'departamento'])

                # ========== DEUDA INICIAL ==========
                deuda_df = gsheets.leer_deuda_inicial(anio)
                if deuda_df.empty:
                    st.warning(f"No se encontró 'Deuda Inicial {anio}'. Deuda = 0.")
                    deuda_df = pd.DataFrame(columns=['torre', 'departamento', 'deuda_inicial'])
                else:
                    col_t = None; col_d = None; col_dd = None
                    for col in deuda_df.columns:
                        col_low = col.lower()
                        if 'torre' in col_low: col_t = col
                        elif 'dpto' in col_low or 'departamento' in col_low: col_d = col
                        elif 'deuda' in col_low: col_dd = col
                    if col_t and col_d and col_dd:
                        deuda_df = deuda_df[[col_t, col_d, col_dd]].copy()
                        deuda_df.rename(columns={col_t: 'torre', col_d: 'departamento', col_dd: 'deuda_inicial'}, inplace=True)
                        deuda_df['torre'] = pd.to_numeric(deuda_df['torre'], errors='coerce')
                        deuda_df['departamento'] = pd.to_numeric(deuda_df['departamento'], errors='coerce')
                        deuda_df['deuda_inicial'] = pd.to_numeric(deuda_df['deuda_inicial'], errors='coerce').fillna(0)
                    else:
                        st.warning("No se identificaron columnas de deuda. Se usará 0.")
                        deuda_df = pd.DataFrame(columns=['torre', 'departamento', 'deuda_inicial'])

                # ========== PROGRAMACIÓN ==========
                prog_df = gsheets.leer_programacion(mes, anio)
                if prog_df.empty:
                    st.warning(f"No se encontró programación para {mes} {anio}. Mantenimiento = 0.")
                    prog_df = pd.DataFrame(columns=['torre', 'departamento', 'Mantenimiento'])
                else:
                    if 'Mantenimiento' not in prog_df.columns:
                        col_mant = None
                        for col in prog_df.columns:
                            if 'total' in col.lower() or 'mantenimiento' in col.lower() or 'cuota' in col.lower():
                                col_mant = col
                                break
                        if col_mant:
                            prog_df.rename(columns={col_mant: 'Mantenimiento'}, inplace=True)
                        else:
                            prog_df['Mantenimiento'] = 0
                    prog_df = prog_df[['torre', 'departamento', 'Mantenimiento']].copy()
                    for col in ['torre', 'departamento', 'Mantenimiento']:
                        if col in prog_df.columns:
                            prog_df[col] = pd.to_numeric(prog_df[col], errors='coerce')
                    prog_df['Mantenimiento'] = prog_df['Mantenimiento'].fillna(0)

                # ========== AMORTIZACIÓN ==========
                amort_df = gsheets.leer_amortizacion(mes, anio)
                if amort_df.empty:
                    st.warning(f"No se encontró amortización para {mes} {anio}. Amortización = 0.")
                    amort_df = pd.DataFrame(columns=['torre', 'departamento', 'amortizacion'])
                else:
                    for col in ['torre', 'departamento', 'amortizacion']:
                        if col in amort_df.columns:
                            amort_df[col] = pd.to_numeric(amort_df[col], errors='coerce')
                    amort_df = amort_df[['torre', 'departamento', 'amortizacion']].copy()
                    amort_df['amortizacion'] = amort_df['amortizacion'].fillna(0)

                # ========== MEDIDORES ==========
                med_df = gsheets.leer_medidores(mes, anio)
                if med_df.empty:
                    st.warning(f"No se encontraron medidores para {mes} {anio}. Medidor = 0.")
                    med_df = pd.DataFrame(columns=['torre', 'departamento', 'monto'])
                else:
                    for col in ['torre', 'departamento', 'monto']:
                        if col in med_df.columns:
                            med_df[col] = pd.to_numeric(med_df[col], errors='coerce')
                    med_df = med_df[['torre', 'departamento', 'monto']].copy()
                    med_df['monto'] = med_df['monto'].fillna(0)

                # ========== PAGOS ==========
                pagos_df = gsheets.leer_pagos_mes(mes, anio)
                if pagos_df.empty:
                    st.warning(f"No se encontraron pagos para {mes} {anio}.")
                    pagos_df = pd.DataFrame(columns=['fecha', 'torre', 'departamento', 'n_operacion', 'ingresos',
                                                     'mantenimiento', 'amortizacion', 'medidor'])
                else:
                    for col in ['torre', 'departamento', 'ingresos', 'mantenimiento', 'amortizacion', 'medidor']:
                        if col in pagos_df.columns:
                            pagos_df[col] = pd.to_numeric(pagos_df[col], errors='coerce').fillna(0)
                    pagos_df = pagos_df[['fecha', 'torre', 'departamento', 'n_operacion', 'ingresos',
                                         'mantenimiento', 'amortizacion', 'medidor']].copy()
                    pagos_df = pagos_df.sort_values('fecha')

                # ========== UNIR TABLAS ==========
                base = base.merge(deuda_df, on=['torre', 'departamento'], how='left').fillna(0)
                base = base.merge(prog_df, on=['torre', 'departamento'], how='left').fillna(0)
                base = base.merge(amort_df, on=['torre', 'departamento'], how='left').fillna(0)
                base = base.merge(med_df, on=['torre', 'departamento'], how='left').fillna(0)

                # ========== CONSTRUIR MOVIMIENTOS ==========
                movimientos = []
                for _, row in base.iterrows():
                    torre = row['torre']
                    dpto = row['departamento']
                    codigo = row['codigo']
                    dni = row['dni']
                    nombre = row['nombre']
                    deuda = row['deuda_inicial']
                    mantenimiento = row['Mantenimiento']
                    amort = row['amortizacion']
                    med = row['monto']
                    total_cargos = deuda + mantenimiento + amort + med

                    pagos_dpto = pagos_df[(pagos_df['torre'] == torre) & (pagos_df['departamento'] == dpto)].copy()
                    pagos_dpto = pagos_dpto.sort_values('fecha')

                    movimientos.append({
                        'fecha': f"01/{mes[:3]}/{anio}",
                        'codigo': codigo,
                        'dni': dni,
                        'nombre': nombre,
                        'deuda_inicial': deuda,
                        'mantenimiento': mantenimiento,
                        'amortizacion': amort,
                        'medidor': med,
                        'total_programacion': total_cargos,
                        'n_operacion': '',
                        'mantenimiento_pago': 0,
                        'amortizacion_pago': 0,
                        'medidor_pago': 0,
                        'total_pagado': 0,
                        'saldo': total_cargos
                    })

                    saldo = total_cargos
                    for _, pago in pagos_dpto.iterrows():
                        saldo -= pago['ingresos']
                        movimientos.append({
                            'fecha': pago['fecha'].strftime('%d/%m/%Y') if pd.notna(pago['fecha']) else '',
                            'codigo': codigo,
                            'dni': dni,
                            'nombre': nombre,
                            'deuda_inicial': '',
                            'mantenimiento': '',
                            'amortizacion': '',
                            'medidor': '',
                            'total_programacion': '',
                            'n_operacion': pago['n_operacion'],
                            'mantenimiento_pago': pago['mantenimiento'],
                            'amortizacion_pago': pago['amortizacion'],
                            'medidor_pago': pago['medidor'],
                            'total_pagado': pago['ingresos'],
                            'saldo': saldo
                        })

                df_mov = pd.DataFrame(movimientos)

                # Formateo numérico
                def fmt_num(val):
                    try:
                        if pd.isna(val) or val == '':
                            return ''
                        num = float(val)
                        if num.is_integer():
                            return f"{int(num):,.0f}"
                        else:
                            return f"{num:,.2f}"
                    except:
                        return val

                for col in ['deuda_inicial', 'mantenimiento', 'amortizacion', 'medidor', 'total_programacion',
                            'mantenimiento_pago', 'amortizacion_pago', 'medidor_pago', 'total_pagado', 'saldo']:
                    if col in df_mov.columns:
                        df_mov[col] = df_mov[col].apply(fmt_num)

                # Seleccionar y ordenar columnas finales
                columnas_orden = [
                    'fecha', 'codigo', 'dni', 'nombre',
                    'deuda_inicial', 'mantenimiento', 'amortizacion', 'medidor', 'total_programacion',
                    'n_operacion', 'mantenimiento_pago', 'amortizacion_pago', 'medidor_pago', 'total_pagado', 'saldo'
                ]
                columnas_existentes = [c for c in columnas_orden if c in df_mov.columns]
                df_final = df_mov[columnas_existentes].copy()
                df_final = df_final.reset_index(drop=True)
                df_final.insert(0, '#', range(1, len(df_final)+1))

                # Guardar en session_state para usar en la segunda pestaña
                st.session_state.df_final = df_final
                st.session_state.datos_cargados = True
                st.session_state.mes = mes
                st.session_state.anio = anio

                # Aplicar filtro por código
                if codigo_filtro.strip():
                    mask = df_final['codigo'].astype(str).str.contains(codigo_filtro.strip(), case=False, na=False)
                    df_final_filtrado = df_final[mask].copy()
                    if df_final_filtrado.empty:
                        st.warning(f"No se encontraron movimientos para el código '{codigo_filtro}'")
                    else:
                        df_final_filtrado = df_final_filtrado.reset_index(drop=True)
                        df_final_filtrado.index = df_final_filtrado.index + 1
                        df_final_filtrado['#'] = df_final_filtrado.index
                    df_final_mostrar = df_final_filtrado
                else:
                    df_final_mostrar = df_final

                # Mostrar tabla con MultiIndex
                grupos = {
                    '': ['#', 'fecha', 'codigo', 'dni', 'nombre'],
                    'PROGRAMACION': ['deuda_inicial', 'mantenimiento', 'amortizacion', 'medidor', 'total_programacion'],
                    'PAGOS': ['n_operacion', 'mantenimiento_pago', 'amortizacion_pago', 'medidor_pago', 'total_pagado', 'saldo']
                }
                niveles = []
                for grupo, cols in grupos.items():
                    for col in cols:
                        if col in df_final_mostrar.columns:
                            niveles.append((grupo, col))
                if niveles:
                    orden = list(df_final_mostrar.columns)
                    niveles_ordenados = [n for n in niveles if n[1] in orden]
                    df_final_mostrar.columns = pd.MultiIndex.from_tuples(niveles_ordenados)
                    df_final_mostrar = df_final_mostrar[[(g, c) for g, c in niveles_ordenados]]
                st.dataframe(df_final_mostrar, use_container_width=True, height=600)

                # Descarga a Excel
                import io
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_export = df_final.copy()
                    df_export.columns = [col[1] for col in df_export.columns] if isinstance(df_export.columns, pd.MultiIndex) else df_export.columns
                    df_export.to_excel(writer, index=False, sheet_name=f"Operaciones_{mes}_{anio}")
                excel_data = output.getvalue()
                st.download_button(
                    label="📥 Descargar Excel",
                    data=excel_data,
                    file_name=f"Operaciones_{mes}_{anio}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            except Exception as e:
                st.error(f"Error al generar el estado de cuenta: {str(e)}")
    else:
        if st.session_state.datos_cargados:
            st.info("Datos ya cargados. Puedes visualizar el resumen en la otra pestaña.")
        else:
            st.info("Haz clic en 'Generar Estado de Cuenta' para cargar los datos.")

# ====================== TAB 2: RESUMEN POR TORRES ======================
with tab2:
    st.subheader("Resumen de Saldos por Departamento")

    if not st.session_state.datos_cargados or st.session_state.df_final is None:
        st.info("Primero genera los datos en la pestaña 'Detalle por Departamento'.")
    else:
        df_final = st.session_state.df_final.copy()
        mes = st.session_state.mes
        anio = st.session_state.anio

        # Obtener el último saldo por departamento (el que tiene la mayor fecha o el último registro)
        # Asumimos que los registros están ordenados por fecha y que el último es el saldo final.
        # Agrupamos por código y tomamos el último registro (por índice).
        # Para asegurar orden, ordenamos por código y luego por índice (el último es el más reciente).
        # Pero en df_final los registros ya están en orden cronológico, y cada departamento tiene varios registros.
        # Tomamos el último registro de cada grupo (el de mayor índice).
        df_final['codigo_str'] = df_final['codigo'].astype(str)
        ultimos_saldos = df_final.groupby('codigo_str').last().reset_index(drop=True)
        # Seleccionar columnas relevantes
        resumen = ultimos_saldos[['torre', 'departamento', 'codigo', 'dni', 'nombre', 'saldo']].copy()
        # Convertir saldo a numérico (ya está formateado con comas, pero podemos convertir)
        # Primero limpiar el saldo (quitar comas y convertir a float)
        resumen['saldo_num'] = resumen['saldo'].astype(str).str.replace(',', '').str.replace(' ', '').astype(float)
        # Ordenar por torre y luego por saldo descendente
        resumen = resumen.sort_values(['torre', 'saldo_num'], ascending=[True, False])
        # Formatear saldo para mostrar
        resumen['SALDO A PAGAR'] = resumen['saldo_num'].apply(lambda x: f"{x:,.2f}")
        # Seleccionar y renombrar columnas
        resumen_final = resumen[['torre', 'departamento', 'codigo', 'dni', 'nombre', 'SALDO A PAGAR']].copy()
        resumen_final.columns = ['TORRE', 'N°DPTO', 'CÓDIGO', 'DNI', 'APELLIDOS Y NOMBRES', 'SALDO A PAGAR']

        # Añadir buscador
        busqueda = st.text_input("Buscar por código o nombre", placeholder="Ej. 01101 o nombre")
        if busqueda:
            mask = (resumen_final['CÓDIGO'].astype(str).str.contains(busqueda, case=False, na=False) |
                    resumen_final['APELLIDOS Y NOMBRES'].astype(str).str.contains(busqueda, case=False, na=False))
            resumen_final = resumen_final[mask].copy()
            if resumen_final.empty:
                st.warning("No se encontraron resultados.")

        # Mostrar tabla
        st.dataframe(resumen_final, use_container_width=True, height=600)

        # Subtotales por torre
        st.subheader("Subtotales por Torre")
        subtotales = resumen_final.groupby('TORRE')['SALDO A PAGAR'].agg(
            lambda x: sum(float(v.replace(',', '')) for v in x)
        ).reset_index()
        subtotales['SALDO A PAGAR'] = subtotales['SALDO A PAGAR'].apply(lambda x: f"{x:,.2f}")
        st.dataframe(subtotales, use_container_width=True)

        # Descarga a Excel
        import io
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            resumen_final.to_excel(writer, index=False, sheet_name=f"Resumen_Torres_{mes}_{anio}")
            subtotales.to_excel(writer, index=False, sheet_name="Subtotales")
        excel_data = output.getvalue()
        st.download_button(
            label="📥 Descargar Resumen en Excel",
            data=excel_data,
            file_name=f"Resumen_Torres_{mes}_{anio}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
