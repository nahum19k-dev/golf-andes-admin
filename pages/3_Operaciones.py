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
            # 1. Cargar propietarios
            prop = gsheets.leer_propietarios()
            if prop.empty:
                st.error("No se pudo cargar la lista de propietarios.")
                st.stop()

            # 2. Deuda inicial del año actual
            deuda_df = gsheets.leer_deuda_inicial(anio)
            if deuda_df.empty:
                st.warning(f"No se encontró hoja 'Deuda Inicial {anio}'. Se usará deuda cero para todos.")
                deuda_df = pd.DataFrame(columns=['TORRE', 'N°DPTO', 'DNI', 'APELLIDOS  Y  NOMBRES', 'DEUDA AL 31/12/2025'])
            # Renombrar columnas de deuda para consistencia
            deuda_df = deuda_df.rename(columns={
                'TORRE': 'torre',
                'N°DPTO': 'departamento',
                'DNI': 'dni',
                'APELLIDOS  Y  NOMBRES': 'nombre',
                'DEUDA AL 31/12/2025': 'deuda_inicial'
            })
            deuda_df['torre'] = pd.to_numeric(deuda_df['torre'], errors='coerce')
            deuda_df['departamento'] = pd.to_numeric(deuda_df['departamento'], errors='coerce')
            deuda_df['deuda_inicial'] = pd.to_numeric(deuda_df['deuda_inicial'], errors='coerce').fillna(0)

            # 3. Programación del mes
            prog_df = gsheets.leer_programacion(mes, anio)
            if prog_df.empty:
                st.warning(f"No se encontró programación para {mes} {anio}. Mantenimiento = 0.")
                prog_df = pd.DataFrame(columns=['torre', 'departamento', 'total_programacion'])
            prog_df = prog_df[['torre', 'departamento', 'total_programacion']].copy()
            prog_df['total_programacion'] = pd.to_numeric(prog_df['total_programacion'], errors='coerce').fillna(0)

            # 4. Amortización del mes
            amort_df = gsheets.leer_amortizacion(mes, anio)
            if amort_df.empty:
                st.warning(f"No se encontró amortización para {mes} {anio}. Amortización = 0.")
                amort_df = pd.DataFrame(columns=['torre', 'departamento', 'amortizacion'])
            amort_df = amort_df[['torre', 'departamento', 'amortizacion']].copy()
            amort_df['amortizacion'] = pd.to_numeric(amort_df['amortizacion'], errors='coerce').fillna(0)

            # 5. Medidores del mes
            med_df = gsheets.leer_medidores(mes, anio)
            if med_df.empty:
                st.warning(f"No se encontraron medidores para {mes} {anio}. Medidor = 0.")
                med_df = pd.DataFrame(columns=['torre', 'departamento', 'monto'])
            med_df = med_df[['torre', 'departamento', 'monto']].copy()
            med_df['monto'] = pd.to_numeric(med_df['monto'], errors='coerce').fillna(0)

            # 6. Pagos del mes
            pagos_df = gsheets.leer_pagos_mes(mes, anio)
            if pagos_df.empty:
                st.warning(f"No se encontraron pagos para {mes} {anio}. Se mostrarán solo los cargos.")
                pagos_df = pd.DataFrame(columns=['fecha', 'torre', 'departamento', 'ingresos', 'n_operacion'])
            else:
                pagos_df['ingresos'] = pd.to_numeric(pagos_df['ingresos'], errors='coerce').fillna(0)

            # 7. Unir todos los datos por departamento
            # Primero obtener todos los departamentos únicos de propietarios (o de las otras tablas)
            # Usaremos prop como base
            base = prop[['codigo', 'torre', 'departamento', 'dni', 'nombre']].copy()
            base['torre'] = pd.to_numeric(base['torre'], errors='coerce')
            base['departamento'] = pd.to_numeric(base['departamento'], errors='coerce')
            base = base.dropna(subset=['torre', 'departamento'])

            # Merge de deuda
            base = base.merge(deuda_df, on=['torre', 'departamento'], how='left')
            base['deuda_inicial'] = base['deuda_inicial'].fillna(0)

            # Merge de programación
            base = base.merge(prog_df, on=['torre', 'departamento'], how='left')
            base['total_programacion'] = base['total_programacion'].fillna(0)

            # Merge de amortización
            base = base.merge(amort_df, on=['torre', 'departamento'], how='left')
            base['amortizacion'] = base['amortizacion'].fillna(0)

            # Merge de medidores
            base = base.merge(med_df, on=['torre', 'departamento'], how='left')
            base['monto'] = base['monto'].fillna(0)

            # Ahora, por cada departamento, construir la secuencia de movimientos
            movimientos = []
            for _, row in base.iterrows():
                torre = row['torre']
                dpto = row['departamento']
                codigo = row['codigo']
                dni = row['dni']
                nombre = row['nombre']
                deuda_inicial = row['deuda_inicial']
                mantenimiento = row['total_programacion']
                amortizacion = row['amortizacion']
                medidor = row['monto']

                total_cargos = deuda_inicial + mantenimiento + amortizacion + medidor

                # Obtener pagos de este departamento
                pagos_dpto = pagos_df[(pagos_df['torre'] == torre) & (pagos_df['departamento'] == dpto)].copy()
                pagos_dpto = pagos_dpto.sort_values('fecha')

                # Fila de cargo inicial
                movimientos.append({
                    'fecha': f"01/{mes}/{anio}",  # fecha de emisión de cargos (podríamos usar fecha de programación si existiera)
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
                        'n_operacion': pago['n_operacion'],
                        'total_pagado': pago['ingresos'],
                        'saldo': saldo
                    })

            df_movimientos = pd.DataFrame(movimientos)

            # Formatear números (eliminar .0 y usar separadores)
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
            # Usar solo las que existen
            columnas_existentes = [c for c in columnas if c in df_movimientos.columns]
            df_final = df_movimientos[columnas_existentes]

            # Mostrar
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
