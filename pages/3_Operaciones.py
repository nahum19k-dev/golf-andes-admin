import streamlit as st
import pandas as pd
import gsheets
from datetime import datetime

st.set_page_config(page_title="Operaciones", page_icon="📊", layout="wide")

st.title("📊 Operaciones - Estado de Cuenta por Departamento")

col1, col2 = st.columns(2)
with col1:
    mes = st.selectbox("Mes", ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                               "Julio","Agosto","Setiembre","Octubre","Noviembre","Diciembre"])
with col2:
    anio = st.number_input("Año", min_value=2025, max_value=2035, value=2026, step=1)

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
                pagos_df = pd.DataFrame(columns=['fecha', 'torre', 'departamento', 'ingresos', 'n_operacion',
                                                 'mantenimiento', 'amortizacion', 'medidor'])
            else:
                for col in ['torre', 'departamento', 'ingresos', 'mantenimiento', 'amortizacion', 'medidor']:
                    if col in pagos_df.columns:
                        pagos_df[col] = pd.to_numeric(pagos_df[col], errors='coerce')
                # Asegurar que los conceptos existan
                for col in ['mantenimiento', 'amortizacion', 'medidor']:
                    if col not in pagos_df.columns:
                        pagos_df[col] = 0
                pagos_df = pagos_df[['fecha', 'torre', 'departamento', 'n_operacion', 'ingresos',
                                     'mantenimiento', 'amortizacion', 'medidor']].copy()
                pagos_df['ingresos'] = pagos_df['ingresos'].fillna(0)
                pagos_df['mantenimiento'] = pagos_df['mantenimiento'].fillna(0)
                pagos_df['amortizacion'] = pagos_df['amortizacion'].fillna(0)
                pagos_df['medidor'] = pagos_df['medidor'].fillna(0)

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

                # Fila de cargo (sin número de operación)
                movimientos.append({
                    'tipo': 'cargo',
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
                    'pago_mantenimiento': 0,
                    'pago_amortizacion': 0,
                    'pago_medidor': 0,
                    'total_pagado': 0,
                    'saldo': total_cargos
                })

                saldo = total_cargos
                for _, pago in pagos_dpto.iterrows():
                    saldo -= pago['ingresos']
                    movimientos.append({
                        'tipo': 'pago',
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
                        'pago_mantenimiento': pago['mantenimiento'],
                        'pago_amortizacion': pago['amortizacion'],
                        'pago_medidor': pago['medidor'],
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
                        'pago_mantenimiento', 'pago_amortizacion', 'pago_medidor', 'total_pagado', 'saldo']:
                if col in df_mov.columns:
                    df_mov[col] = df_mov[col].apply(fmt_num)

            # ========== PREPARAR DATOS PARA MOSTRAR ==========
            # Separar cargos y pagos
            df_cargos = df_mov[df_mov['tipo'] == 'cargo'].copy()
            df_pagos = df_mov[df_mov['tipo'] == 'pago'].copy()

            # Unir en una sola tabla pero con columnas separadas
            # Crear tabla final con el formato deseado
            # Primero, agregar una columna de índice para ordenar correctamente
            df_cargos['orden'] = range(1, len(df_cargos)+1)
            df_pagos['orden'] = range(1, len(df_pagos)+1)
            # Mezclar cargos y pagos por orden (esto no es necesario si queremos que los cargos aparezcan primero y luego pagos)
            # Pero como los pagos ya tienen fechas específicas, los mostraremos después del cargo.
            # Para que aparezcan en orden cronológico, podríamos unir y ordenar por fecha. Sin embargo, por ahora mantendremos:
            # - Primero el cargo (con fecha de emisión)
            # - Luego los pagos en orden de fecha
            # Esto ya está construido en la lista de movimientos: primero el cargo, luego los pagos en orden.
            # Entonces podemos usar df_mov directamente, pero para mostrar necesitamos las columnas correctas.

            # Construir el DataFrame de salida final
            # Seleccionamos columnas según el tipo
            final_rows = []
            for _, row in df_mov.iterrows():
                if row['tipo'] == 'cargo':
                    final_rows.append({
                        'fecha': row['fecha'],
                        'codigo': row['codigo'],
                        'dni': row['dni'],
                        'nombre': row['nombre'],
                        'deuda_inicial': row['deuda_inicial'],
                        'mantenimiento': row['mantenimiento'],
                        'amortizacion': row['amortizacion'],
                        'medidor': row['medidor'],
                        'total_programacion': row['total_programacion'],
                        'n_operacion': '',
                        'pago_mantenimiento': '',
                        'pago_amortizacion': '',
                        'pago_medidor': '',
                        'total_pagado': '',
                        'saldo': row['saldo']
                    })
                else:
                    final_rows.append({
                        'fecha': row['fecha'],
                        'codigo': row['codigo'],
                        'dni': row['dni'],
                        'nombre': row['nombre'],
                        'deuda_inicial': '',
                        'mantenimiento': '',
                        'amortizacion': '',
                        'medidor': '',
                        'total_programacion': '',
                        'n_operacion': row['n_operacion'],
                        'pago_mantenimiento': row['pago_mantenimiento'],
                        'pago_amortizacion': row['pago_amortizacion'],
                        'pago_medidor': row['pago_medidor'],
                        'total_pagado': row['total_pagado'],
                        'saldo': row['saldo']
                    })
            df_final = pd.DataFrame(final_rows)

            # Agregar columna de índice
            df_final.insert(0, '#', range(1, len(df_final)+1))

            # ========== GENERAR TABLA HTML CON DOS SECCIONES (PROGRAMACION y PAGOS) ==========
            col_names = list(df_final.columns)
            # Las columnas que van bajo "PROGRAMACION"
            group_cols_prog = ['deuda_inicial', 'mantenimiento', 'amortizacion', 'medidor', 'total_programacion']
            # Las columnas que van bajo "PAGOS"
            group_cols_pagos = ['pago_mantenimiento', 'pago_amortizacion', 'pago_medidor', 'total_pagado']

            # Encontrar índices
            prog_indices = [col_names.index(c) for c in group_cols_prog if c in col_names]
            first_prog = min(prog_indices) if prog_indices else 0
            last_prog = max(prog_indices) if prog_indices else 0
            span_prog = last_prog - first_prog + 1

            pagos_indices = [col_names.index(c) for c in group_cols_pagos if c in col_names]
            first_pago = min(pagos_indices) if pagos_indices else 0
            last_pago = max(pagos_indices) if pagos_indices else 0
            span_pago = last_pago - first_pago + 1

            # Construir HTML
            html = '<div style="overflow-x: auto;">'
            html += '<table style="width:100%; border-collapse: collapse; font-family: sans-serif;">'
            html += '<thead>'

            # Primera fila: PROGRAMACION y PAGOS
            html += ' hilab'
            # Celdas antes de PROGRAMACION
            for i in range(first_prog):
                html += '<th style="border: 1px solid #ddd; padding: 8px; background-color: #f0f2f6;"></th>'
            html += f'<th colspan="{span_prog}" style="text-align: center; font-weight: bold; background-color: #f0f2f6; border: 1px solid #ddd; padding: 8px;">PROGRAMACION</th>'
            # Celdas entre PROGRAMACION y PAGOS
            for i in range(last_prog+1, first_pago):
                html += '<th style="border: 1px solid #ddd; padding: 8px; background-color: #f0f2f6;"></th>'
            html += f'<th colspan="{span_pago}" style="text-align: center; font-weight: bold; background-color: #f0f2f6; border: 1px solid #ddd; padding: 8px;">PAGOS</th>'
            # Celdas después de PAGOS
            for i in range(last_pago+1, len(col_names)):
                html += '<th style="border: 1px solid #ddd; padding: 8px; background-color: #f0f2f6;"></th>'
            html += '</tr>'

            # Segunda fila: nombres de columnas
            html += '气'
            for col in col_names:
                # Personalizar nombres para mejor visualización
                if col == 'deuda_inicial':
                    display = 'DEUDA INICIAL'
                elif col == 'mantenimiento':
                    display = 'MANTENIMIENTO'
                elif col == 'amortizacion':
                    display = 'AMORTIZACIÓN CONVENIO'
                elif col == 'medidor':
                    display = 'MEDIDOR'
                elif col == 'total_programacion':
                    display = 'TOTAL PROGRAMACIÓN'
                elif col == 'pago_mantenimiento':
                    display = 'MANTENIMIENTO'
                elif col == 'pago_amortizacion':
                    display = 'AMORTIZACIÓN CONVENIO'
                elif col == 'pago_medidor':
                    display = 'MEDIDOR'
                elif col == 'total_pagado':
                    display = 'TOTAL PAGADO'
                elif col == 'saldo':
                    display = 'SALDO POR COBRAR ACTUAL'
                elif col == 'n_operacion':
                    display = 'N°OPERACIÓN'
                else:
                    display = col.upper()
                html += f'<th style="border: 1px solid #ddd; padding: 8px; background-color: #f0f2f6; text-align: left;">{display}</th>'
            html += '</tr>'
            html += '</thead><tbody>'

            # Filas de datos
            for _, row in df_final.iterrows():
                html += '气'
                for col in col_names:
                    val = row[col]
                    # Aplicar alineación derecha a números
                    if col in ['deuda_inicial', 'mantenimiento', 'amortizacion', 'medidor', 'total_programacion',
                               'pago_mantenimiento', 'pago_amortizacion', 'pago_medidor', 'total_pagado', 'saldo']:
                        align = 'right'
                    else:
                        align = 'left'
                    html += f'<td style="border: 1px solid #ddd; padding: 8px; text-align: {align};">{val}</td>'
                html += '</tr>'
            html += '</tbody></table></div>'

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
