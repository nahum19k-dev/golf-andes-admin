import streamlit as st
import pandas as pd
import supabase_client as gsheets
from datetime import datetime, timedelta
import calendar
from fpdf import FPDF
import io

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

# ========== FUNCIONES AUXILIARES ==========
def obtener_mes_anterior(mes: str, anio: int):
    meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
             "Julio","Agosto","Setiembre","Octubre","Noviembre","Diciembre"]
    idx = meses.index(mes)
    if idx == 0:
        return "Diciembre", anio - 1
    else:
        return meses[idx - 1], anio

def limpiar_numero_general(x):
    if pd.isna(x):
        return 0.0
    s = str(x).strip()
    s = s.replace(',', '').replace(' ', '').replace('S/', '').replace('$', '')
    try:
        return float(s)
    except:
        return 0.0

def ultimo_dia_mes(mes: str, anio: int) -> int:
    """Devuelve el último día del mes (1-31)."""
    meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
             "Julio","Agosto","Setiembre","Octubre","Noviembre","Diciembre"]
    idx = meses.index(mes) + 1
    return calendar.monthrange(anio, idx)[1]

# ========== CACHÉ PARA PROPIETARIOS ==========
@st.cache_data(ttl=300)  # 5 minutos de caché
def cargar_propietarios():
    return gsheets.leer_propietarios()

# ========== CREAR PESTAÑAS ==========
tab1, tab2, tab3 = st.tabs(["📋 Detalle por Departamento", "🏢 Resumen por Torres", "📄 Reporte de Deudas (PDF)"])

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
                # ========== PROPIETARIOS (con caché) ==========
                prop = cargar_propietarios()
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
                base['torre'] = base['torre'].fillna(0).astype(int)
                base['departamento'] = base['departamento'].fillna(0).astype(int)

                # ========== DEUDA INICIAL DEL MES ==========
                if mes == "Enero":
                    deuda_almacenada = gsheets.leer_deuda_inicial(anio)
                    if deuda_almacenada.empty:
                        st.warning(f"No se encontró 'Deuda Inicial {anio}'. Se usará 0 como deuda inicial.")
                        deuda_df = pd.DataFrame(columns=['torre', 'departamento', 'deuda_inicial'])
                    else:
                        col_t = None; col_d = None; col_dd = None
                        for col in deuda_almacenada.columns:
                            col_low = col.lower()
                            if 'torre' in col_low: col_t = col
                            elif 'dpto' in col_low or 'departamento' in col_low: col_d = col
                            elif 'deuda' in col_low: col_dd = col
                        if col_t and col_d and col_dd:
                            deuda_df = deuda_almacenada[[col_t, col_d, col_dd]].copy()
                            deuda_df.rename(columns={col_t: 'torre', col_d: 'departamento', col_dd: 'deuda_inicial'}, inplace=True)
                            deuda_df['torre'] = pd.to_numeric(deuda_df['torre'], errors='coerce')
                            deuda_df['departamento'] = pd.to_numeric(deuda_df['departamento'], errors='coerce')
                            deuda_df['deuda_inicial'] = pd.to_numeric(deuda_df['deuda_inicial'], errors='coerce').fillna(0)
                        else:
                            st.warning("No se identificaron columnas de deuda. Se usará 0.")
                            deuda_df = pd.DataFrame(columns=['torre', 'departamento', 'deuda_inicial'])
                else:
                    # Leer saldos del mes anterior desde saldos_mensuales
                    mes_anterior, anio_anterior = obtener_mes_anterior(mes, anio)
                    saldos_anteriores = gsheets.leer_saldos_mensuales(anio_anterior, mes_anterior)
                    if saldos_anteriores.empty:
                        st.error(f"❌ No se puede generar {mes} {anio} porque no existen saldos guardados para {mes_anterior} {anio_anterior}.\n\n"
                                 f"Por favor, genera primero el reporte del mes anterior.")
                        st.stop()
                    else:
                        deuda_df = saldos_anteriores[['torre', 'departamento', 'saldo_final']].rename(
                            columns={'saldo_final': 'deuda_inicial'}
                        )
                        st.info(f"Deuda inicial obtenida de los saldos guardados de {mes_anterior} {anio_anterior}.")

                # ========== PROGRAMACIÓN ==========
                prog_df = gsheets.leer_programacion(mes, anio)
                if prog_df.empty:
                    st.warning(f"No se encontró programación para {mes} {anio}. Mantenimiento = 0.")
                    prog_df = pd.DataFrame(columns=['torre', 'departamento', 'Mantenimiento'])
                else:
                    prog_df = prog_df[['torre', 'departamento', 'Mantenimiento']].copy()
                    prog_df['Mantenimiento'] = prog_df['Mantenimiento'].fillna(0)

                # ========== AMORTIZACIÓN ==========
                amort_df = gsheets.leer_amortizacion(mes, anio)
                if amort_df.empty:
                    st.warning(f"No se encontró amortización para {mes} {anio}. Amortización = 0.")
                    amort_df = pd.DataFrame(columns=['torre', 'departamento', 'amortizacion'])
                else:
                    amort_df = amort_df[['torre', 'departamento', 'amortizacion']].copy()
                    amort_df['amortizacion'] = amort_df['amortizacion'].fillna(0)

                # ========== MEDIDORES ==========
                med_df = gsheets.leer_medidores(mes, anio)
                if med_df.empty:
                    st.warning(f"No se encontraron medidores para {mes} {anio}. Medidor = 0.")
                    med_df = pd.DataFrame(columns=['torre', 'departamento', 'monto'])
                else:
                    med_df = med_df[['torre', 'departamento', 'monto']].copy()
                    med_df['monto'] = med_df['monto'].fillna(0)

                # ========== OTROS ==========
                otros_df = gsheets.leer_otros_mes(mes, anio)
                if otros_df.empty:
                    st.warning(f"No se encontraron otros ingresos para {mes} {anio}. Otros = 0.")
                    otros_df = pd.DataFrame(columns=['torre', 'departamento', 'otros'])
                else:
                    otros_df = otros_df[['torre', 'departamento', 'otros']].copy()
                    otros_df['otros'] = otros_df['otros'].fillna(0)

                # ========== PAGOS (optimizado) ==========
                pagos_df = gsheets.leer_pagos_mes(mes, anio)
                if pagos_df.empty:
                    st.warning(f"No se encontraron pagos para {mes} {anio}.")
                    pagos_df = pd.DataFrame(columns=['fecha', 'torre', 'departamento', 'n_operacion', 'ingresos',
                                                     'mantenimiento', 'amortizacion', 'medidor'])
                else:
                    # Asegurar columnas numéricas
                    for col in ['torre', 'departamento', 'ingresos', 'mantenimiento', 'amortizacion', 'medidor']:
                        if col not in pagos_df.columns:
                            pagos_df[col] = 0
                        else:
                            pagos_df[col] = pd.to_numeric(pagos_df[col], errors='coerce').fillna(0)
                    pagos_df = pagos_df.sort_values('fecha')

                # ========== UNIR TABLAS ==========
                base = base.merge(deuda_df, on=['torre', 'departamento'], how='left').fillna(0)
                base = base.merge(prog_df, on=['torre', 'departamento'], how='left').fillna(0)
                base = base.merge(amort_df, on=['torre', 'departamento'], how='left').fillna(0)
                base = base.merge(med_df, on=['torre', 'departamento'], how='left').fillna(0)
                base = base.merge(otros_df, on=['torre', 'departamento'], how='left').fillna(0)

                # ========== OPTIMIZACIÓN: DICCIONARIO DE PAGOS POR DEPARTAMENTO ==========
                pagos_por_departamento = {}
                for _, pago in pagos_df.iterrows():
                    key = (pago['torre'], pago['departamento'])
                    if key not in pagos_por_departamento:
                        pagos_por_departamento[key] = []
                    pagos_por_departamento[key].append(pago)

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
                    otros = row['otros']
                    total_cargos = deuda + mantenimiento + amort + med + otros

                    pagos_dpto = pagos_por_departamento.get((torre, dpto), [])
                    pagos_dpto.sort(key=lambda x: x['fecha'] if pd.notna(x['fecha']) else datetime.min)

                    # Movimiento de cargo
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
                        'otros': otros,
                        'total_programacion': total_cargos,
                        'n_operacion': '',
                        'mantenimiento_pago': 0,
                        'amortizacion_pago': 0,
                        'medidor_pago': 0,
                        'otros_pago': 0,
                        'total_pagado': 0,
                        'saldo': total_cargos
                    })

                    saldo = total_cargos
                    for pago in pagos_dpto:
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
                            'otros': '',
                            'total_programacion': '',
                            'n_operacion': pago['n_operacion'],
                            'mantenimiento_pago': pago['mantenimiento'],
                            'amortizacion_pago': pago['amortizacion'],
                            'medidor_pago': pago['medidor'],
                            'otros_pago': pago.get('otros', 0),
                            'total_pagado': pago['ingresos'],
                            'saldo': saldo
                        })

                df_mov = pd.DataFrame(movimientos)

                # ========== GUARDAR AGREGADOS EN SALDOS_MENSUALES (ANTES DE FORMATEAR) ==========
                agregados = df_mov.groupby(['torre', 'departamento']).agg({
                    'deuda_inicial': 'first',
                    'mantenimiento': 'first',
                    'amortizacion': 'first',
                    'medidor': 'first',
                    'otros': 'first',
                    'total_pagado': 'sum',
                    'saldo': 'last'
                }).reset_index()
                agregados.rename(columns={'saldo': 'saldo_final'}, inplace=True)
                agregados['anio'] = anio
                agregados['mes'] = mes
                gsheets.guardar_saldos_mensuales(agregados)

                # ========== FORMATEAR NÚMEROS PARA MOSTRAR ==========
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

                for col in ['deuda_inicial', 'mantenimiento', 'amortizacion', 'medidor', 'otros', 'total_programacion',
                            'mantenimiento_pago', 'amortizacion_pago', 'medidor_pago', 'otros_pago', 'total_pagado', 'saldo']:
                    if col in df_mov.columns:
                        df_mov[col] = df_mov[col].apply(fmt_num)

                columnas_orden = [
                    'fecha', 'torre', 'departamento', 'codigo', 'dni', 'nombre',
                    'deuda_inicial', 'mantenimiento', 'amortizacion', 'medidor', 'otros', 'total_programacion',
                    'n_operacion', 'mantenimiento_pago', 'amortizacion_pago', 'medidor_pago', 'otros_pago', 'total_pagado', 'saldo'
                ]
                columnas_existentes = [c for c in columnas_orden if c in df_mov.columns]
                df_final = df_mov[columnas_existentes].copy()
                df_final = df_final.reset_index(drop=True)
                df_final.insert(0, '#', range(1, len(df_final)+1))

                # ========== GUARDAR REPORTE COMPLETO ==========
                gsheets.guardar_reporte_mensual(anio, mes, df_final)
                st.success(f"✅ Reporte de {mes} {anio} guardado correctamente.")

                st.session_state.df_final = df_final.copy()
                st.session_state.datos_cargados = True
                st.session_state.mes_actual = mes
                st.session_state.anio_actual = anio

                fecha_emi, fecha_ven = gsheets.obtener_fechas_programacion("Mantenimiento", mes, anio)
                st.session_state.fecha_emision = fecha_emi
                st.session_state.fecha_vencimiento = fecha_ven

                if codigo_filtro.strip():
                    mask = df_final['codigo'].astype(str).str.contains(codigo_filtro.strip(), case=False, na=False)
                    df_final = df_final[mask].copy()
                    if df_final.empty:
                        st.warning(f"No se encontraron movimientos para el código '{codigo_filtro}'")
                    else:
                        df_final = df_final.reset_index(drop=True)
                        df_final.index = df_final.index + 1
                        df_final['#'] = df_final.index

                if fecha_emi and fecha_ven:
                    st.info(f"📅 **Período de programación:** {fecha_emi.strftime('%d/%m/%Y')} al {fecha_ven.strftime('%d/%m/%Y')}")
                else:
                    st.warning("⚠️ No se encontró información de fechas para este período en la hoja de control.")

                # Mostrar tabla HTML
                col_names = list(df_final.columns)
                grupo_prog = ['deuda_inicial', 'mantenimiento', 'amortizacion', 'medidor', 'otros', 'total_programacion']
                grupo_pagos = ['n_operacion', 'mantenimiento_pago', 'amortizacion_pago', 'medidor_pago', 'otros_pago', 'total_pagado', 'saldo']

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

                    html += '                   <tr>\n'
                    for i in range(prog_first):
                        html += '        <th style="border: 1px solid #ddd; padding: 4px 2px; background-color: #f0f2f6;"></th>\n'
                    html += f'        <th colspan="{prog_span}" style="text-align: center; font-weight: bold; background-color: #f0f2f6; border: 1px solid #ddd; padding: 4px 2px;">PROGRAMACION</th>\n'
                    for i in range(prog_last+1, pagos_first):
                        html += '        <th style="border: 1px solid #ddd; padding: 4px 2px; background-color: #f0f2f6;"></th>\n'
                    html += f'        <th colspan="{pagos_span}" style="text-align: center; font-weight: bold; background-color: #f0f2f6; border: 1px solid #ddd; padding: 4px 2px;">PAGOS</th>\n'
                    for i in range(pagos_last+1, len(col_names)):
                        html += '        <th style="border: 1px solid #ddd; padding: 4px 2px; background-color: #f0f2f6;"></th>\n'
                    html += '                   </tr>\n'

                html += '                   <tr>\n'
                for col in col_names:
                    html += f'        <th style="border: 1px solid #ddd; padding: 4px 2px; background-color: #f0f2f6; text-align: left;">{col}</th>\n'
                html += '                   </tr>\n'
                html += '</thead>\n<tbody>\n'

                for _, row in df_final.iterrows():
                    html += '                   <tr>\n'
                    for col in col_names:
                        val = row[col]
                        align = 'right' if col in grupo_prog + grupo_pagos else 'left'
                        html += f'        <td style="border: 1px solid #ddd; padding: 4px 2px; text-align: {align};">{val}</td>\n'
                    html += '                   </tr>\n'
                html += '</tbody>\n</table>\n</div>'

                st.markdown(html, unsafe_allow_html=True)

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

        # Limpieza de columnas
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
            elif 'otros' in col and 'pago' not in col:
                col_mapping['otros'] = col
            elif 'total_pagado' in col:
                col_mapping['total_pagado'] = col

        esenciales = ['torre', 'departamento', 'codigo', 'dni', 'nombre',
                      'deuda_inicial', 'mantenimiento', 'amortizacion', 'medidor', 'otros', 'total_pagado']
        faltan = [col for col in esenciales if col not in col_mapping]
        if faltan:
            st.error(f"Faltan columnas esenciales: {faltan}. Columnas disponibles: {list(df_resumen.columns)}")
            st.stop()

        df_resumen = df_resumen.rename(columns={col_mapping[k]: k for k in esenciales})
        df_resumen = df_resumen[esenciales]

        for col in ['deuda_inicial', 'mantenimiento', 'amortizacion', 'medidor', 'otros', 'total_pagado']:
            df_resumen[col] = df_resumen[col].apply(limpiar_numero_general)

        df_resumen['torre'] = pd.to_numeric(df_resumen['torre'], errors='coerce').fillna(0).astype(int)
        df_resumen['departamento'] = pd.to_numeric(df_resumen['departamento'], errors='coerce').fillna(0).astype(int)

        df_resumen['clave'] = df_resumen['torre'].astype(str) + '_' + df_resumen['departamento'].astype(str)

        grupo = df_resumen.groupby('clave')

        primer_registro = grupo.first().reset_index()
        if 'total_pagado' in primer_registro.columns:
            primer_registro = primer_registro.drop(columns=['total_pagado'])

        primer_registro['total_programacion'] = (
            primer_registro['mantenimiento'] +
            primer_registro['amortizacion'] +
            primer_registro['medidor'] +
            primer_registro['otros']
        )
        primer_registro['total_deuda'] = (
            primer_registro['deuda_inicial'] +
            primer_registro['mantenimiento'] +
            primer_registro['amortizacion'] +
            primer_registro['medidor'] +
            primer_registro['otros']
        )

        total_pagado_por_clave = grupo['total_pagado'].sum().reset_index()
        resumen = primer_registro.merge(total_pagado_por_clave, on='clave', how='left')
        resumen['total_pagado'] = resumen['total_pagado'].fillna(0)

        resumen['saldo_a_pagar'] = resumen['total_deuda'] - resumen['total_pagado']

        resumen = resumen.sort_values(['torre', 'saldo_a_pagar'], ascending=[True, False])

        # Formateo de moneda
        def formatear_moneda(valor):
            return f"S/ {valor:,.2f}"

        resumen['TOTAL PROGRAMACIÓN'] = resumen['total_programacion'].apply(formatear_moneda)
        resumen['TOTAL DEUDA'] = resumen['total_deuda'].apply(formatear_moneda)
        resumen['TOTAL PAGADO'] = resumen['total_pagado'].apply(formatear_moneda)
        resumen['SALDO A PAGAR'] = resumen['saldo_a_pagar'].apply(formatear_moneda)

        columnas_finales = ['torre', 'departamento', 'codigo', 'dni', 'nombre',
                            'TOTAL PROGRAMACIÓN', 'TOTAL DEUDA', 'TOTAL PAGADO', 'SALDO A PAGAR']
        columnas_existentes = [c for c in columnas_finales if c in resumen.columns]
        resumen_final = resumen[columnas_existentes].copy()
        resumen_final.columns = ['TORRE', 'N°DPTO', 'CÓDIGO', 'DNI', 'APELLIDOS Y NOMBRES',
                                 'TOTAL PROGRAMACIÓN', 'TOTAL DEUDA', 'TOTAL PAGADO', 'SALDO A PAGAR']

        # ---------- TOTALES GENERALES ----------
        total_deuda_inicial_gral = resumen['deuda_inicial'].sum()
        total_prog_gral = resumen['total_programacion'].sum()
        total_deuda_gral = resumen['total_deuda'].sum()
        total_pag_gral = resumen['total_pagado'].sum()
        total_saldo_gral = resumen['saldo_a_pagar'].sum()

        st.markdown(
            """
            <style>
            .metric-card {
                background-color: #f0f2f6;
                border-radius: 0.5rem;
                padding: 0.75rem 0.5rem;
                text-align: center;
                margin: 0 0.25rem;
                box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            }
            .metric-label {
                font-size: 0.9rem;
                font-weight: 500;
                color: #4a5b6e;
                margin-bottom: 0.5rem;
            }
            .metric-value {
                font-size: 1.25rem;
                font-weight: 600;
                color: #1e4663;
                white-space: normal;
                word-wrap: break-word;
                overflow-wrap: break-word;
                line-height: 1.3;
            }
            @media (max-width: 640px) {
                .metric-value { font-size: 1rem; }
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        cols = st.columns(5)
        with cols[0]:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">💰 Deuda Inicial</div>'
                f'<div class="metric-value">S/ {total_deuda_inicial_gral:,.2f}</div></div>',
                unsafe_allow_html=True
            )
        with cols[1]:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">📊 Total Programación</div>'
                f'<div class="metric-value">S/ {total_prog_gral:,.2f}</div></div>',
                unsafe_allow_html=True
            )
        with cols[2]:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">💸 Total Deuda</div>'
                f'<div class="metric-value">S/ {total_deuda_gral:,.2f}</div></div>',
                unsafe_allow_html=True
            )
        with cols[3]:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">🏦 Total Pagado</div>'
                f'<div class="metric-value">S/ {total_pag_gral:,.2f}</div></div>',
                unsafe_allow_html=True
            )
        with cols[4]:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">⚖️ Saldo a Pagar</div>'
                f'<div class="metric-value">S/ {total_saldo_gral:,.2f}</div></div>',
                unsafe_allow_html=True
            )

        st.markdown("---")

        busqueda = st.text_input("Buscar por código o nombre", placeholder="Ej. 01101 o nombre")
        if busqueda:
            mask = (resumen_final['CÓDIGO'].astype(str).str.contains(busqueda, case=False, na=False) |
                    resumen_final['APELLIDOS Y NOMBRES'].astype(str).str.contains(busqueda, case=False, na=False))
            resumen_final = resumen_final[mask].copy()
            if resumen_final.empty:
                st.warning("No se encontraron resultados.")

        column_config = {
            "TOTAL PROGRAMACIÓN": st.column_config.TextColumn("TOTAL PROGRAMACIÓN", width="medium"),
            "TOTAL DEUDA": st.column_config.TextColumn("TOTAL DEUDA", width="medium"),
            "TOTAL PAGADO": st.column_config.TextColumn("TOTAL PAGADO", width="medium"),
            "SALDO A PAGAR": st.column_config.TextColumn("SALDO A PAGAR", width="medium")
        }
        st.dataframe(resumen_final, use_container_width=True, height=600, column_config=column_config)

        st.subheader("Subtotales por Torre")
        subtotales_num = resumen.groupby('torre').agg({
            'total_programacion': 'sum',
            'total_deuda': 'sum',
            'total_pagado': 'sum',
            'saldo_a_pagar': 'sum'
        }).reset_index()
        subtotales_num.columns = ['TORRE', 'TOTAL PROGRAMACIÓN', 'TOTAL DEUDA', 'TOTAL PAGADO', 'SALDO A PAGAR']
        for col in ['TOTAL PROGRAMACIÓN', 'TOTAL DEUDA', 'TOTAL PAGADO', 'SALDO A PAGAR']:
            subtotales_num[col] = subtotales_num[col].apply(formatear_moneda)
        st.dataframe(subtotales_num, use_container_width=True)

        import io
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            resumen_final.to_excel(writer, index=False, sheet_name=f"Resumen_Torres_{st.session_state.mes_actual}_{st.session_state.anio_actual}")
            subtotales_num.to_excel(writer, index=False, sheet_name="Subtotales")
        excel_data = output.getvalue()
        st.download_button(
            label="📥 Descargar Resumen en Excel",
            data=excel_data,
            file_name=f"Resumen_Torres_{st.session_state.mes_actual}_{st.session_state.anio_actual}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# ====================== TAB 3: REPORTE DE DEUDAS (PDF) ======================
with tab3:
    st.subheader("Generar Reporte de Deudas por Torre")

    # Selectores de mes y año (por defecto el último generado)
    meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
             "Julio","Agosto","Setiembre","Octubre","Noviembre","Diciembre"]
    default_mes_index = meses.index(st.session_state.mes_actual) if st.session_state.mes_actual in meses else 0
    default_anio = st.session_state.anio_actual if st.session_state.anio_actual else 2026

    col1, col2 = st.columns(2)
    with col1:
        mes_reporte = st.selectbox("Mes", meses, index=default_mes_index)
    with col2:
        anio_reporte = st.number_input("Año", min_value=2025, max_value=2035, value=default_anio, step=1)

    if st.button("Generar PDF", type="primary"):
        with st.spinner("Generando reporte..."):
            try:
                # 1. Obtener saldos del mes seleccionado
                df_saldos = gsheets.leer_saldos_mensuales(anio_reporte, mes_reporte)
                if df_saldos.empty:
                    st.warning(f"No hay datos de saldos para {mes_reporte} {anio_reporte}. Primero genera ese mes en la pestaña 'Detalle'.")
                    st.stop()

                # 2. Filtrar solo deudores (saldo_final > 0)
                df_deudores = df_saldos[df_saldos['saldo_final'] > 0].copy()
                if df_deudores.empty:
                    st.info("No hay deudores en el período seleccionado.")
                    st.stop()

                # 3. Obtener datos de propietarios
                df_prop = cargar_propietarios()
                if df_prop.empty:
                    st.error("No se pudieron cargar los datos de propietarios.")
                    st.stop()

                # 4. Unir con propietarios para obtener nombres y DNI
                df_prop['torre'] = pd.to_numeric(df_prop['torre'], errors='coerce')
                df_prop['departamento'] = pd.to_numeric(df_prop['dpto'], errors='coerce')
                df_prop = df_prop[['torre', 'departamento', 'codigo', 'dni', 'nombre']].dropna()
                df_prop['torre'] = df_prop['torre'].astype(int)
                df_prop['departamento'] = df_prop['departamento'].astype(int)

                df_deudores['torre'] = df_deudores['torre'].astype(int)
                df_deudores['departamento'] = df_deudores['departamento'].astype(int)

                df_final = df_deudores.merge(df_prop, on=['torre', 'departamento'], how='left')
                # Si falta algún nombre, usar placeholder
                df_final['nombre'] = df_final['nombre'].fillna("SIN REGISTRAR")
                df_final['dni'] = df_final['dni'].fillna("")

                # 5. Ordenar por torre y departamento
                df_final = df_final.sort_values(['torre', 'departamento'])

                # 6. Calcular el último día del mes para el encabezado
                dia = ultimo_dia_mes(mes_reporte, anio_reporte)
                fecha_corte = f"{dia} DE {mes_reporte.upper()} DEL {anio_reporte}"

                # 7. Crear PDF con fpdf2
                class PDF(FPDF):
                    def header(self):
                        self.set_font('Helvetica', 'B', 12)
                        self.cell(0, 6, "JUNTA DE PROPIETARIOS DEL CONJUNTO RESIDENCIAL GOLF LOS ANDES", ln=True, align='C')
                        self.set_font('Helvetica', 'B', 11)
                        self.cell(0, 6, f"RELACION DE DEUDAS AL {fecha_corte}", ln=True, align='C')
                        self.ln(8)

                pdf = PDF('P', 'mm', 'A4')
                pdf.set_auto_page_break(auto=True, margin=15)
                pdf.set_font('Helvetica', '', 10)

                # Agrupar por torre
                total_general = 0.0
                for torre in sorted(df_final['torre'].unique()):
                    df_torre = df_final[df_final['torre'] == torre].copy()
                    df_torre = df_torre.reset_index(drop=True)
                    df_torre['item'] = df_torre.index + 1

                    pdf.add_page()
                    # Título de la torre
                    pdf.set_font('Helvetica', 'B', 12)
                    pdf.cell(0, 8, f"TORRE N° {torre}", ln=True, align='L')
                    pdf.set_font('Helvetica', '', 9)
                    pdf.ln(4)

                    # Cabecera de tabla
                    cabeceras = ["ITEM", "TORRE", "N°DPTO", "DNI", "APELLIDOS Y NOMBRES", "DEUDA (S/)"]
                    col_widths = [12, 15, 20, 30, 70, 30]
                    pdf.set_font('Helvetica', 'B', 9)
                    for i, cab in enumerate(cabeceras):
                        pdf.cell(col_widths[i], 7, cab, border=1, align='C')
                    pdf.ln()

                    # Filas de datos
                    pdf.set_font('Helvetica', '', 9)
                    subtotal_torre = 0.0
                    for _, row in df_torre.iterrows():
                        pdf.cell(col_widths[0], 6, str(row['item']), border=1, align='R')
                        pdf.cell(col_widths[1], 6, str(int(row['torre'])), border=1, align='C')
                        pdf.cell(col_widths[2], 6, str(int(row['departamento'])), border=1, align='C')
                        pdf.cell(col_widths[3], 6, str(row['dni']), border=1, align='L')
                        # Recortar nombre si es muy largo
                        nombre = row['nombre'][:40] if len(row['nombre']) > 40 else row['nombre']
                        pdf.cell(col_widths[4], 6, nombre, border=1, align='L')
                        deuda = row['saldo_final']
                        subtotal_torre += deuda
                        pdf.cell(col_widths[5], 6, f"{deuda:,.2f}".replace(',', '.'), border=1, align='R')
                        pdf.ln()

                    # Subtítulo de subtotal torre
                    pdf.set_font('Helvetica', 'B', 9)
                    pdf.cell(sum(col_widths) - col_widths[-1], 6, f"SUB-TOTAL DEUDA TORRE N°{torre}", border=0, align='R')
                    pdf.cell(col_widths[-1], 6, f"{subtotal_torre:,.2f}".replace(',', '.'), border=1, align='R')
                    pdf.ln(8)

                    total_general += subtotal_torre

                # Total general al final (última página)
                pdf.add_page()
                pdf.set_font('Helvetica', 'B', 10)
                pdf.cell(0, 10, f"TOTAL GENERAL DE TODAS LAS TORRES: S/ {total_general:,.2f}".replace(',', '.'), ln=True, align='R')

                # Guardar PDF en memoria
                pdf_output = io.BytesIO()
                pdf.output(pdf_output)
                pdf_data = pdf_output.getvalue()

                # Nombre del archivo
                nombre_archivo = f"DEUDAS_TORRE_{dia:02d}_{mes_reporte.upper()}_{anio_reporte}.pdf"
                st.download_button(
                    label="📥 Descargar PDF",
                    data=pdf_data,
                    file_name=nombre_archivo,
                    mime="application/pdf"
                )

            except Exception as e:
                st.error(f"Error al generar el PDF: {str(e)}")
