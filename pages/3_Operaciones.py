import streamlit as st
import pandas as pd
import gsheets
from datetime import datetime

st.set_page_config(page_title="Operaciones", page_icon="📊", layout="wide")

st.title("📊 Operaciones - Estado de Cuenta por Departamento")

# ========== INICIALIZAR SESSION_STATE ==========
if 'df_final' not in st.session_state:
    st.session_state.df_final = None
if 'datos_cargados' not in st.session_state:
    st.session_state.datos_cargados = False
if 'mes_actual' not in st.session_state:
    st.session_state.mes_actual = None
if 'anio_actual' not in st.session_state:
    st.session_state.anio_actual = None
if 'fecha_emision' not in st.session_state:
    st.session_state.fecha_emision = None
if 'fecha_vencimiento' not in st.session_state:
    st.session_state.fecha_vencimiento = None

# ========== CREAR PESTAÑAS ==========
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
                        'torre': torre,
                        'departamento': dpto,
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
                            'torre': torre,
                            'departamento': dpto,
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

                # Seleccionar y ordenar columnas finales (incluyendo torre y departamento)
                columnas_orden = [
                    'fecha', 'torre', 'departamento', 'codigo', 'dni', 'nombre',
                    'deuda_inicial', 'mantenimiento', 'amortizacion', 'medidor', 'total_programacion',
                    'n_operacion', 'mantenimiento_pago', 'amortizacion_pago', 'medidor_pago', 'total_pagado', 'saldo'
                ]
                columnas_existentes = [c for c in columnas_orden if c in df_mov.columns]
                df_final = df_mov[columnas_existentes].copy()
                df_final = df_final.reset_index(drop=True)
                df_final.insert(0, '#', range(1, len(df_final)+1))

                # Guardar en session_state para la segunda pestaña
                st.session_state.df_final = df_final.copy()
                st.session_state.datos_cargados = True
                st.session_state.mes_actual = mes
                st.session_state.anio_actual = anio

                # Obtener y guardar las fechas del período (Mantenimiento como referencia)
                fecha_emi, fecha_ven = gsheets.obtener_fechas_programacion("Mantenimiento", mes, anio)
                st.session_state.fecha_emision = fecha_emi
                st.session_state.fecha_vencimiento = fecha_ven

                # Aplicar filtro por código si se especificó
                if codigo_filtro.strip():
                    mask = df_final['codigo'].astype(str).str.contains(codigo_filtro.strip(), case=False, na=False)
                    df_final = df_final[mask].copy()
                    if df_final.empty:
                        st.warning(f"No se encontraron movimientos para el código '{codigo_filtro}'")
                    else:
                        df_final = df_final.reset_index(drop=True)
                        df_final.index = df_final.index + 1
                        df_final['#'] = df_final.index

                # Mostrar rango de fechas si existe
                if fecha_emi and fecha_ven:
                    st.info(f"📅 **Período de programación:** {fecha_emi.strftime('%d/%m/%Y')} al {fecha_ven.strftime('%d/%m/%Y')}")
                else:
                    st.warning("⚠️ No se encontró información de fechas para este período en la hoja de control.")

                # ========== GENERAR TABLA HTML CON CABECERAS AGRUPADAS ==========
                col_names = list(df_final.columns)
                grupo_prog = ['deuda_inicial', 'mantenimiento', 'amortizacion', 'medidor', 'total_programacion']
                grupo_pagos = ['n_operacion', 'mantenimiento_pago', 'amortizacion_pago', 'medidor_pago', 'total_pagado', 'saldo']

                prog_indices = [i for i, col in enumerate(col_names) if col in grupo_prog]
                pagos_indices = [i for i, col in enumerate(col_names) if col in grupo_pagos]

                html = '<div style="overflow-x: auto; max-width: 100%;">\n'
                html += '<table style="width:100%; border-collapse: collapse; font-family: sans-serif; font-size: 12px;">\n'
                html += '<thead>\n'

                if prog_indices and pagos_indices:
                    prog_first = min(prog_indices)
                    prog_last = max(prog_indices)
                    prog_span = prog_last - prog_first + 1
                    pagos_first = min(pagos_indices)
                    pagos_last = max(pagos_indices)
                    pagos_span = pagos_last - pagos_first + 1

                    html += '    <tr>\n'
                    for i in range(prog_first):
                        html += '        <th style="border: 1px solid #ddd; padding: 4px 2px; background-color: #f0f2f6;"></th>\n'
                    html += f'        <th colspan="{prog_span}" style="text-align: center; font-weight: bold; background-color: #f0f2f6; border: 1px solid #ddd; padding: 4px 2px;">PROGRAMACION</th>\n'
                    for i in range(prog_last+1, pagos_first):
                        html += '        <th style="border: 1px solid #ddd; padding: 4px 2px; background-color: #f0f2f6;"></th>\n'
                    html += f'        <th colspan="{pagos_span}" style="text-align: center; font-weight: bold; background-color: #f0f2f6; border: 1px solid #ddd; padding: 4px 2px;">PAGOS</th>\n'
                    for i in range(pagos_last+1, len(col_names)):
                        html += '        <th style="border: 1px solid #ddd; padding: 4px 2px; background-color: #f0f2f6;"></th>\n'
                    html += '      </tr>\n'

                html += '      <tr>\n'
                for col in col_names:
                    html += f'        <th style="border: 1px solid #ddd; padding: 4px 2px; background-color: #f0f2f6; text-align: left;">{col}</th>\n'
                html += '      </tr>\n'
                html += '</thead>\n<tbody>\n'

                for _, row in df_final.iterrows():
                    html += '      <tr>\n'
                    for col in col_names:
                        val = row[col]
                        align = 'right' if col in grupo_prog + grupo_pagos else 'left'
                        html += f'        <td style="border: 1px solid #ddd; padding: 4px 2px; text-align: {align};">{val}</td>\n'
                    html += '      </tr>\n'
                html += '</tbody>\n</table>\n</div>'

                st.markdown(html, unsafe_allow_html=True)

                # Descarga a Excel
                import io
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_final.to_excel(writer, index=False, sheet_name=f"Operaciones_{mes}_{anio}")
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
            st.info(f"Datos cargados para {st.session_state.mes_actual} {st.session_state.anio_actual}. Puedes visualizar el resumen en la otra pestaña.")
            if st.session_state.fecha_emision and st.session_state.fecha_vencimiento:
                st.info(f"📅 Período: {st.session_state.fecha_emision.strftime('%d/%m/%Y')} al {st.session_state.fecha_vencimiento.strftime('%d/%m/%Y')}")
        else:
            st.info("Haz clic en 'Generar Estado de Cuenta' para cargar los datos.")

# ====================== TAB 2: RESUMEN POR TORRES ======================
with tab2:
    st.subheader("Resumen de Saldos por Departamento")

    if not st.session_state.datos_cargados or st.session_state.df_final is None:
        st.info("Primero genera los datos en la pestaña 'Detalle por Departamento'.")
    else:
        df_resumen = st.session_state.df_final.copy()

        # ---------- LIMPIEZA DE COLUMNAS ----------
        if isinstance(df_resumen.columns, pd.MultiIndex):
            df_resumen.columns = [col[1] if col[1] else col[0] for col in df_resumen.columns]

        df_resumen.columns = [col.lower() for col in df_resumen.columns]

        col_mapping = {}
        for col in df_resumen.columns:
            if 'torre' in col:
                col_mapping['torre'] = col
            elif 'departamento' in col or 'dpto' in col:
                col_mapping['departamento'] = col
            elif 'codigo' in col:
                col_mapping['codigo'] = col
            elif 'dni' in col:
                col_mapping['dni'] = col
            elif 'nombre' in col:
                col_mapping['nombre'] = col
            elif 'deuda_inicial' in col:
                col_mapping['deuda_inicial'] = col
            elif 'mantenimiento' in col and 'pago' not in col:
                col_mapping['mantenimiento'] = col
            elif 'amortizacion' in col and 'pago' not in col:
                col_mapping['amortizacion'] = col
            elif 'medidor' in col and 'pago' not in col:
                col_mapping['medidor'] = col
            elif 'total_pagado' in col:
                col_mapping['total_pagado'] = col

        esenciales = ['torre', 'departamento', 'codigo', 'dni', 'nombre',
                      'deuda_inicial', 'mantenimiento', 'amortizacion', 'medidor', 'total_pagado']
        faltan = [col for col in esenciales if col not in col_mapping]
        if faltan:
            st.error(f"Faltan columnas esenciales: {faltan}. Columnas disponibles: {list(df_resumen.columns)}")
            st.stop()

        df_resumen = df_resumen.rename(columns={col_mapping[k]: k for k in esenciales})
        df_resumen = df_resumen[esenciales]

        # ---------- FUNCIÓN PARA LIMPIAR NÚMEROS ----------
        def limpiar_numero(x):
            if pd.isna(x):
                return 0.0
            s = str(x).strip()
            s = s.replace(',', '').replace(' ', '').replace('S/', '').replace('$', '')
            try:
                return float(s)
            except:
                return 0.0

        for col in ['deuda_inicial', 'mantenimiento', 'amortizacion', 'medidor', 'total_pagado']:
            df_resumen[col] = df_resumen[col].apply(limpiar_numero)

        # ---------- AGREGACIÓN POR TORRE+DEPARTAMENTO ----------
        # Asegurar que torre y departamento sean numéricos (ya lo están, pero por si acaso)
        df_resumen['torre'] = pd.to_numeric(df_resumen['torre'], errors='coerce')
        df_resumen['departamento'] = pd.to_numeric(df_resumen['departamento'], errors='coerce')
        # Eliminar filas con torre o departamento NaN (no debería haber, pero por seguridad)
        df_resumen = df_resumen.dropna(subset=['torre', 'departamento'])

        # Crear clave única combinando torre y departamento
        df_resumen['clave'] = df_resumen['torre'].astype(str) + '_' + df_resumen['departamento'].astype(str)

        # Agrupar por clave
        grupo = df_resumen.groupby('clave')

        # Tomar el primer registro (los cargos) de cada grupo
        primer_registro = grupo.first().reset_index(drop=True)
        # Eliminar la columna 'total_pagado' del primer registro (son los cargos, pagado=0)
        if 'total_pagado' in primer_registro.columns:
            primer_registro = primer_registro.drop(columns=['total_pagado'])

        # Calcular Total Programación = mantenimiento + amortizacion + medidor
        primer_registro['total_programacion'] = (
            primer_registro['mantenimiento'] +
            primer_registro['amortizacion'] +
            primer_registro['medidor']
        )
        # Calcular Total Deuda = deuda_inicial + mantenimiento + amortizacion + medidor
        primer_registro['total_deuda'] = (
            primer_registro['deuda_inicial'] +
            primer_registro['mantenimiento'] +
            primer_registro['amortizacion'] +
            primer_registro['medidor']
        )

        # Sumar total pagado por clave (torre+departamento)
        total_pagado_por_clave = grupo['total_pagado'].sum().reset_index(name='total_pagado')
        # Asegurar que la columna de clave se llame 'clave'
        if 'index' in total_pagado_por_clave.columns:
            total_pagado_por_clave.rename(columns={'index': 'clave'}, inplace=True)
        # Si ya tiene 'clave', está bien
        if 'clave' not in total_pagado_por_clave.columns:
            # Si por alguna razón no está, la creamos desde el índice
            total_pagado_por_clave = total_pagado_por_clave.reset_index().rename(columns={'index': 'clave'})

        # Combinar cargos y pagos
        resumen = primer_registro.merge(total_pagado_por_clave, on='clave', how='left')
        resumen['total_pagado'] = resumen['total_pagado'].fillna(0)

        # Saldo a Pagar = Total Deuda - Total Pagado
        resumen['saldo_a_pagar'] = resumen['total_deuda'] - resumen['total_pagado']

        # Ordenar por torre y saldo
        resumen = resumen.sort_values(['torre', 'saldo_a_pagar'], ascending=[True, False])

        # Formatear para mostrar
        resumen['TOTAL PROGRAMACIÓN'] = resumen['total_programacion'].apply(lambda x: f"{x:,.2f}")
        resumen['TOTAL DEUDA'] = resumen['total_deuda'].apply(lambda x: f"{x:,.2f}")
        resumen['TOTAL PAGADO'] = resumen['total_pagado'].apply(lambda x: f"{x:,.2f}")
        resumen['SALDO A PAGAR'] = resumen['saldo_a_pagar'].apply(lambda x: f"{x:,.2f}")

        # Seleccionar columnas finales
        resumen_final = resumen[['torre', 'departamento', 'codigo', 'dni', 'nombre',
                                  'TOTAL PROGRAMACIÓN', 'TOTAL DEUDA', 'TOTAL PAGADO', 'SALDO A PAGAR']].copy()
        resumen_final.columns = ['TORRE', 'N°DPTO', 'CÓDIGO', 'DNI', 'APELLIDOS Y NOMBRES',
                                 'TOTAL PROGRAMACIÓN', 'TOTAL DEUDA', 'TOTAL PAGADO', 'SALDO A PAGAR']

        # ---------- TOTALES GENERALES ----------
        total_prog_gral = resumen['total_programacion'].sum()
        total_deuda_gral = resumen['total_deuda'].sum()
        total_pag_gral = resumen['total_pagado'].sum()
        total_saldo_gral = resumen['saldo_a_pagar'].sum()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("💰 Total Programación", f"S/ {total_prog_gral:,.2f}")
        with col2:
            st.metric("📊 Total Deuda", f"S/ {total_deuda_gral:,.2f}")
        with col3:
            st.metric("💸 Total Pagado", f"S/ {total_pag_gral:,.2f}")
        with col4:
            st.metric("🏦 Total Saldo a Pagar", f"S/ {total_saldo_gral:,.2f}")
        st.markdown("---")

        # Buscador
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
        subtotales = resumen_final.groupby('TORRE')[['TOTAL PROGRAMACIÓN', 'TOTAL DEUDA', 'TOTAL PAGADO', 'SALDO A PAGAR']].agg(
            lambda x: sum(limpiar_numero(v) for v in x)
        ).reset_index()
        for col in ['TOTAL PROGRAMACIÓN', 'TOTAL DEUDA', 'TOTAL PAGADO', 'SALDO A PAGAR']:
            subtotales[col] = subtotales[col].apply(lambda x: f"{x:,.2f}")
        st.dataframe(subtotales, use_container_width=True)

        # Descarga a Excel
        import io
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            resumen_final.to_excel(writer, index=False, sheet_name=f"Resumen_Torres_{st.session_state.mes_actual}_{st.session_state.anio_actual}")
            subtotales.to_excel(writer, index=False, sheet_name="Subtotales")
        excel_data = output.getvalue()
        st.download_button(
            label="📥 Descargar Resumen en Excel",
            data=excel_data,
            file_name=f"Resumen_Torres_{st.session_state.mes_actual}_{st.session_state.anio_actual}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
