import streamlit as st
import pandas as pd
import supabase_client as gsheets
from datetime import datetime, timedelta

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

def leer_otros_mes(mes: str, anio: int):
    nombre_hoja = f"Otros {mes} {anio}"
    df_otros = gsheets.leer_hoja_otros(nombre_hoja)
    if df_otros.empty:
        return pd.DataFrame(columns=['torre', 'departamento', 'otros'])

    df_otros.columns = df_otros.columns.str.strip().str.lower()
    conceptos = ['cuota_extraordinarias', 'alquiler_parrilla', 'garantia', 'sala_zoom', 'alquiler_sillas', 'tuberias']
    for c in conceptos:
        if c not in df_otros.columns:
            df_otros[c] = 0
    for c in conceptos:
        df_otros[c] = pd.to_numeric(df_otros[c], errors='coerce').fillna(0)
    df_otros['otros'] = df_otros[conceptos].sum(axis=1)

    df_otros['torre'] = pd.to_numeric(df_otros['torre'], errors='coerce')
    df_otros['departamento'] = pd.to_numeric(df_otros['departamento'], errors='coerce')
    df_otros = df_otros.dropna(subset=['torre', 'departamento'])
    return df_otros[['torre', 'departamento', 'otros']].copy()

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
                base['torre'] = base['torre'].fillna(0).astype(int)
                base['departamento'] = base['departamento'].fillna(0).astype(int)

                # ========== DEUDA INICIAL DEL MES ==========
                if mes == "Enero":
                    # Enero: leer deuda almacenada
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
                    # Meses siguientes: obtener deuda inicial del reporte del mes anterior
                    mes_anterior, anio_anterior = obtener_mes_anterior(mes, anio)
                    df_reporte_anterior = gsheets.leer_reporte_mensual(anio_anterior, mes_anterior)
                    if df_reporte_anterior.empty:
                        st.error(f"❌ No se puede generar {mes} {anio} porque no existe el reporte de {mes_anterior} {anio_anterior}.\n\n"
                                 f"Por favor, genera primero el reporte del mes anterior.")
                        st.stop()
                    else:
                        # Extraer último saldo por departamento
                        def limpiar_numero(x):
                            if pd.isna(x):
                                return 0.0
                            s = str(x).strip()
                            s = s.replace(',', '').replace(' ', '').replace('S/', '').replace('$', '')
                            try:
                                return float(s)
                            except:
                                return 0.0
                        df_reporte_anterior['saldo_clean'] = df_reporte_anterior['saldo'].apply(limpiar_numero)
                        ultimo_saldo = df_reporte_anterior.groupby(['torre', 'departamento'])['saldo_clean'].last().reset_index()
                        deuda_df = ultimo_saldo.rename(columns={'saldo_clean': 'deuda_inicial'})
                        st.info(f"Deuda inicial obtenida del reporte guardado de {mes_anterior} {anio_anterior}.")

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

                # ========== OTROS ==========
                otros_df = leer_otros_mes(mes, anio)
                if otros_df.empty:
                    st.warning(f"No se encontraron otros ingresos para {mes} {anio}. Otros = 0.")
                    otros_df = pd.DataFrame(columns=['torre', 'departamento', 'otros'])
                else:
                    otros_df['otros'] = pd.to_numeric(otros_df['otros'], errors='coerce').fillna(0)

                # ========== PAGOS ==========
                pagos_df = gsheets.leer_pagos_mes(mes, anio)
                if pagos_df.empty:
                    st.warning(f"No se encontraron pagos para {mes} {anio}.")
                    pagos_df = pd.DataFrame(columns=['fecha', 'torre', 'departamento', 'n_operacion', 'ingresos',
                                                     'mantenimiento', 'amortizacion', 'medidor'])
                else:
                    columnas_numericas = ['torre', 'departamento', 'ingresos', 'mantenimiento', 'amortizacion', 'medidor']
                    for col in columnas_numericas:
                        if col in pagos_df.columns:
                            pagos_df[col] = pd.to_numeric(pagos_df[col], errors='coerce').fillna(0)
                        else:
                            pagos_df[col] = 0
                    if 'ingresos' not in pagos_df.columns:
                        pagos_df['ingresos'] = 0
                    pagos_df = pagos_df[['fecha', 'torre', 'departamento', 'n_operacion', 'ingresos',
                                         'mantenimiento', 'amortizacion', 'medidor']].copy()
                    pagos_df = pagos_df.sort_values('fecha')

                # ========== UNIR TABLAS ==========
                base = base.merge(deuda_df, on=['torre', 'departamento'], how='left').fillna(0)
                base = base.merge(prog_df, on=['torre', 'departamento'], how='left').fillna(0)
                base = base.merge(amort_df, on=['torre', 'departamento'], how='left').fillna(0)
                base = base.merge(med_df, on=['torre', 'departamento'], how='left').fillna(0)
                base = base.merge(otros_df, on=['torre', 'departamento'], how='left').fillna(0)

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

                # ========== GUARDAR REPORTE COMPLETO (SOBRESCRIBIR) ==========
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

                    html += '              <tr>\n'
                    for i in range(prog_first):
                        html += '        <th style="border: 1px solid #ddd; padding: 4px 2px; background-color: #f0f2f6;"></th>\n'
                    html += f'        <th colspan="{prog_span}" style="text-align: center; font-weight: bold; background-color: #f0f2f6; border: 1px solid #ddd; padding: 4px 2px;">PROGRAMACION</th>\n'
                    for i in range(prog_last+1, pagos_first):
                        html += '        <th style="border: 1px solid #ddd; padding: 4px 2px; background-color: #f0f2f6;"></th>\n'
                    html += f'        <th colspan="{pagos_span}" style="text-align: center; font-weight: bold; background-color: #f0f2f6; border: 1px solid #ddd; padding: 4px 2px;">PAGOS</th>\n'
                    for i in range(pagos_last+1, len(col_names)):
                        html += '        <th style="border: 1px solid #ddd; padding: 4px 2px; background-color: #f0f2f6;"></th>\n'
                    html += '              </tr>\n'

                html += '              <tr>\n'
                for col in col_names:
                    html += f'        <th style="border: 1px solid #ddd; padding: 4px 2px; background-color: #f0f2f6; text-align: left;">{col}</th>\n'
                html += '              </tr>\n'
                html += '</thead>\n<tbody>\n'

                for _, row in df_final.iterrows():
                    html += '              <tr>\n'
                    for col in col_names:
                        val = row[col]
                        align = 'right' if col in grupo_prog + grupo_pagos else 'left'
                        html += f'        <td style="border: 1px solid #ddd; padding: 4px 2px; text-align: {align};">{val}</td>\n'
                    html += '              </tr>\n'
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

        def limpiar_numero(x):
            if pd.isna(x):
                return 0.0
            s = str(x).strip()
            s = s.replace(',', '').replace(' ', '').replace('S/', '').replace('$', '')
            try:
                return float(s)
            except:
                return 0.0

        for col in ['deuda_inicial', 'mantenimiento', 'amortizacion', 'medidor', 'otros', 'total_pagado']:
            df_resumen[col] = df_resumen[col].apply(limpiar_numero)

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

        # Presentación personalizada de los 5 totales sin truncamiento
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

        # Buscador
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

        # Subtotales por torre
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

        # Descarga a Excel
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
