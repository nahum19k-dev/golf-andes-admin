import streamlit as st
import pandas as pd
import gsheets
from datetime import datetime

st.set_page_config(page_title="Operaciones", page_icon="📊", layout="wide")

st.title("📊 Operaciones - Estado de Cuenta por Departamento")

# Selección del período
col1, col2 = st.columns(2)
with col1:
    mes = st.selectbox("Mes", ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                               "Julio","Agosto","Setiembre","Octubre","Noviembre","Diciembre"])
with col2:
    anio = st.number_input("Año", min_value=2025, max_value=2035, value=2026, step=1)

if st.button("Generar Estado de Cuenta", type="primary"):
    with st.spinner("Cargando datos..."):
        try:
            # ---------- 1. Propietarios (base) ----------
            prop = gsheets.leer_propietarios()
            st.write("🔍 Columnas en Propietarios:", list(prop.columns))  # LOG
            if prop.empty:
                st.error("No se pudo cargar la lista de propietarios.")
                st.stop()

            # Detectar columnas en prop
            col_torre_prop = None
            col_depto_prop = None
            col_codigo_prop = None
            col_dni_prop = None
            col_nombre_prop = None

            for col in prop.columns:
                col_low = col.lower()
                if 'torre' in col_low:
                    col_torre_prop = col
                if 'departamento' in col_low or 'dpto' in col_low or 'n°dpto' in col_low:
                    col_depto_prop = col
                if 'codigo' in col_low or 'código' in col_low:
                    col_codigo_prop = col
                if 'dni' in col_low:
                    col_dni_prop = col
                if 'nombre' in col_low or 'apellidos' in col_low:
                    col_nombre_prop = col

            if col_torre_prop is None or col_depto_prop is None:
                st.error("No se encontraron las columnas 'torre' y 'departamento' en propietarios.")
                st.stop()
            if col_codigo_prop is None:
                st.error("No se encontró la columna 'codigo' en propietarios.")
                st.stop()
            if col_dni_prop is None:
                st.warning("No se encontró columna 'dni' en propietarios. Se usará vacío.")
                col_dni_prop = None
            if col_nombre_prop is None:
                st.error("No se encontró columna 'nombre' en propietarios.")
                st.stop()

            # Seleccionar columnas necesarias
            cols_to_use = [col_torre_prop, col_depto_prop, col_codigo_prop]
            if col_dni_prop:
                cols_to_use.append(col_dni_prop)
            if col_nombre_prop:
                cols_to_use.append(col_nombre_prop)

            base = prop[cols_to_use].copy()
            base.rename(columns={
                col_torre_prop: 'torre',
                col_depto_prop: 'departamento',
                col_codigo_prop: 'codigo',
                col_dni_prop: 'dni' if col_dni_prop else 'dni',
                col_nombre_prop: 'nombre'
            }, inplace=True)

            # Asegurar tipos numéricos
            base['torre'] = pd.to_numeric(base['torre'], errors='coerce')
            base['departamento'] = pd.to_numeric(base['departamento'], errors='coerce')
            base = base.dropna(subset=['torre', 'departamento'])

            st.write("✅ Base (propietarios) lista, filas:", len(base))
            st.write("Muestra base:", base.head(3))

            # ---------- 2. Deuda inicial ----------
            deuda_df = gsheets.leer_deuda_inicial(anio)
            st.write("🔍 Deuda inicial shape:", deuda_df.shape)
            st.write("Columnas deuda:", list(deuda_df.columns))
            if deuda_df.empty:
                st.warning(f"No se encontró hoja 'Deuda Inicial {anio}'. Se usará deuda cero para todos.")
                deuda_df = pd.DataFrame(columns=['torre', 'departamento', 'deuda_inicial'])
            else:
                # Detectar columnas en deuda
                col_torre = None
                col_depto = None
                col_deuda = None
                for col in deuda_df.columns:
                    col_low = col.lower()
                    if 'torre' in col_low:
                        col_torre = col
                    if 'dpto' in col_low or 'departamento' in col_low or 'n°dpto' in col_low:
                        col_depto = col
                    if 'deuda' in col_low:
                        col_deuda = col
                if col_torre is None or col_depto is None:
                    st.warning("No se pudieron identificar columnas de torre/departamento en deuda. Se usará deuda cero.")
                    deuda_df = pd.DataFrame(columns=['torre', 'departamento', 'deuda_inicial'])
                else:
                    deuda_df = deuda_df[[col_torre, col_depto, col_deuda]].copy()
                    deuda_df.rename(columns={col_torre: 'torre', col_depto: 'departamento', col_deuda: 'deuda_inicial'}, inplace=True)
                    deuda_df['torre'] = pd.to_numeric(deuda_df['torre'], errors='coerce')
                    deuda_df['departamento'] = pd.to_numeric(deuda_df['departamento'], errors='coerce')
                    deuda_df['deuda_inicial'] = pd.to_numeric(deuda_df['deuda_inicial'], errors='coerce').fillna(0)

            # ---------- 3. Programación ----------
            prog_df = gsheets.leer_programacion(mes, anio)
            st.write("🔍 Programación shape:", prog_df.shape)
            st.write("Columnas programación:", list(prog_df.columns))
            if prog_df.empty:
                st.warning(f"No se encontró programación para {mes} {anio}. Mantenimiento = 0.")
                prog_df = pd.DataFrame(columns=['torre', 'departamento', 'total_programacion'])
            # prog_df ya tiene las columnas renombradas por la función de lectura

            # ---------- 4. Amortización ----------
            amort_df = gsheets.leer_amortizacion(mes, anio)
            st.write("🔍 Amortización shape:", amort_df.shape)
            st.write("Columnas amortización:", list(amort_df.columns))
            if amort_df.empty:
                st.warning(f"No se encontró amortización para {mes} {anio}. Amortización = 0.")
                amort_df = pd.DataFrame(columns=['torre', 'departamento', 'amortizacion'])

            # ---------- 5. Medidores ----------
            med_df = gsheets.leer_medidores(mes, anio)
            st.write("🔍 Medidores shape:", med_df.shape)
            st.write("Columnas medidores:", list(med_df.columns))
            if med_df.empty:
                st.warning(f"No se encontraron medidores para {mes} {anio}. Medidor = 0.")
                med_df = pd.DataFrame(columns=['torre', 'departamento', 'monto'])

            # ---------- 6. Pagos ----------
            pagos_df = gsheets.leer_pagos_mes(mes, anio)
            st.write("🔍 Pagos shape:", pagos_df.shape)
            st.write("Columnas pagos:", list(pagos_df.columns))
            if pagos_df.empty:
                st.warning(f"No se encontraron pagos para {mes} {anio}. Se mostrarán solo los cargos.")
                pagos_df = pd.DataFrame(columns=['fecha', 'torre', 'departamento', 'ingresos', 'n_operacion'])

            # ---------- 7. Unir ----------
            # Merge de deuda
            base = base.merge(deuda_df, on=['torre', 'departamento'], how='left')
            base['deuda_inicial'] = base['deuda_inicial'].fillna(0)

            base = base.merge(prog_df, on=['torre', 'departamento'], how='left')
            base['total_programacion'] = base['total_programacion'].fillna(0)

            base = base.merge(amort_df, on=['torre', 'departamento'], how='left')
            base['amortizacion'] = base['amortizacion'].fillna(0)

            base = base.merge(med_df, on=['torre', 'departamento'], how='left')
            base['monto'] = base['monto'].fillna(0)

            # Construir movimientos
            movimientos = []
            for _, row in base.iterrows():
                torre = row['torre']
                dpto = row['departamento']
                codigo = row['codigo']
                dni = row.get('dni', '')
                nombre = row['nombre']
                deuda_inicial = row['deuda_inicial']
                mantenimiento = row['total_programacion']
                amortizacion = row['amortizacion']
                medidor = row['monto']

                total_cargos = deuda_inicial + mantenimiento + amortizacion + medidor

                # Pagos del departamento
                pagos_dpto = pagos_df[(pagos_df['torre'] == torre) & (pagos_df['departamento'] == dpto)].copy()
                pagos_dpto = pagos_dpto.sort_values('fecha') if 'fecha' in pagos_dpto.columns else pagos_dpto

                # Fila de cargos
                movimientos.append({
                    'fecha': f"01/{mes[:3]}/{anio}",
                    'torre': torre,
                    'departamento': dpto,
                    'codigo': codigo,
                    'dni': dni,
                    'nombre': nombre,
                    'deuda_inicial': deuda_inicial,
                    'mantenimiento': mantenimiento,
                    'amortizacion': amortizacion,
                    'medidor': medidor,
                    'total_programacion': total_cargos,
                    'n_operacion': '',
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
                        'n_operacion': pago.get('n_operacion', ''),
                        'total_pagado': pago['ingresos'],
                        'saldo': saldo
                    })

            df_movimientos = pd.DataFrame(movimientos)

            # Formatear números
            def fmt_num(valor):
                try:
                    if pd.isna(valor) or valor == '':
                        return ''
                    num = float(valor)
                    if num.is_integer():
                        return f"{int(num):,.0f}"
                    else:
                        return f"{num:,.2f}"
                except:
                    return valor

            for col in ['deuda_inicial', 'mantenimiento', 'amortizacion', 'medidor', 'total_programacion', 'total_pagado', 'saldo']:
                if col in df_movimientos.columns:
                    df_movimientos[col] = df_movimientos[col].apply(fmt_num)

            # Reordenar columnas
            columnas = ['fecha', 'torre', 'departamento', 'dni', 'nombre', 'deuda_inicial',
                        'mantenimiento', 'amortizacion', 'medidor', 'total_programacion',
                        'n_operacion', 'total_pagado', 'saldo']
            columnas_existentes = [c for c in columnas if c in df_movimientos.columns]
            df_final = df_movimientos[columnas_existentes]

            st.subheader(f"Estado de Cuenta - {mes} {anio}")
            st.dataframe(df_final, use_container_width=True, height=600)

            # Botón descarga
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
            import traceback
            st.code(traceback.format_exc())
