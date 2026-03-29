import streamlit as st
import pandas as pd
import gsheetsfrom datetime import datetime

s.set_page_config(page_title="Operaciones", page_icon="📊", layout="wide")

s.title("📊 Operaciones - Estado de Cuenta por Departamento")

# ========== INICIALIZAR SESSION_STATE ==========
if 'df_final' not in s.session_state:
    s.session_state.df_final = None
if 'datos_cargados' not in s.session_state:
    s.session_state.datos_cargados = False
if 'mes_actual' not in s.session_state:
    s.session_state.mes_actual = None
if 'anio_actual' not in s.session_state:
    s.session_state.anio_actual = None
if 'fecha_emision' not in s.session_state:
    s.session_state.fecha_emision = None
if 'fecha_vencimiento' not in s.session_state:
    s.session_state.fecha_vencimiento = None# ========== CREAR PESTAÑAS ==========
tab1, tab2, tab3 = s.tabs(["📋 Detalle por Departamento", "🏢 Resumen por Torres", "📊 Reporte"])

# ====================== TAB 1: DETALLE POR DEPARTAMENTO ======================
with tab1:
    # ... (código existente de la primera pestaña) ...

# ====================== TAB 2: RESUMEN POR TORRES ======================
with tab2:
    # ... (código existente de la segunda pestaña) ...

# ====================== TAB 3: REPORTE ======================
with tab3:
    s.subheader("📊 Reporte de Estado de Cuentas")

    if not s.session_state.datos_cargados or s.session_state.df_final is None:
        s.info("Primero genera los datos en la pestaña 'Detalle por Departamento'.")
    else:
        # ------------------- COPIA DE LA LÓGICA DE RESUMEN -------------------
        df_resumen = s.session_state.df_final.copy()

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
            s.error(f"Faltan columnas esenciales: {faltan}. Columnas disponibles: {list(df_resumen.columns)}")
            s.stop()

        df_resumen = df_resumen.rename(columns={col_mapping[k]: k for k in esenciales})
        df_resumen = df_resumen[esenciales]

        # ---------- FUNCIÓN PARA LIMPIAR NÚMEROS ----------
        def limpiar_numero(x):
            if pd.isna(x):
                return 0.0
            s_str = str(x).strip()
            s_str = s_str.replace(',', '').replace(' ', '').replace('S/', '').replace('$', '')
            try:
                return float(s_str)
            except:
                return 0.0

        for col in ['deuda_inicial', 'mantenimiento', 'amortizacion', 'medidor', 'total_pagado']:
            df_resumen[col] = df_resumen[col].apply(limpiar_numero)

        # ---------- AGREGACIÓN POR TORRE+DEPARTAMENTO ----------
        df_resumen['torre'] = pd.to_numeric(df_resumen['torre'], errors='coerce')
        df_resumen['departamento'] = pd.to_numeric(df_resumen['departamento'], errors='coerce')
        # Fill missing values with 0 and convert to int to avoid dropping rows
        df_resumen['torre'] = df_resumen['torre'].fillna(0).astype(int)
        df_resumen['departamento'] = df_resumen['departamento'].fillna(0).astype(int)

        df_resumen['clave'] = df_resumen['torre'].astype(str) + '_' + df_resumen['departamento'].astype(str)
        grupo = df_resumen.groupby('clave')

        primer_registro = grupo.first().reset_index()
        if 'total_pagado' in primer_registro.columns:
            primer_registro = primer_registro.drop(columns=['total_pagado'])

        primer_registro['total_programacion'] = (
            primer_registro['mantenimiento'] +
            primer_registro['amortizacion'] +
            primer_registro['medidor']
        )
        primer_registro['total_deuda'] = (
            primer_registro['deuda_inicial'] +
            primer_registro['mantenimiento'] +
            primer_registro['amortizacion'] +
            primer_registro['medidor']
        )

        total_pagado_por_clave = grupo['total_pagado'].sum().reset_index()
        resumen = primer_registro.merge(total_pagado_por_clave, on='clave', how='left')
        resumen['total_pagado'] = resumen['total_pagado'].fillna(0)
        resumen['saldo_a_pagar'] = resumen['total_deuda'] - resumen['total_pagado']
        resumen = resumen.sort_values(['torre', 'saldo_a_pagar'], ascending=[True, False])

        # ---------- FORMATEO ----------
        resumen['TOTAL PROGRAMACIÓN'] = resumen['total_programacion'].apply(lambda x: f"{x:,.2f}")
        resumen['TOTAL DEUDA'] = resumen['total_deuda'].apply(lambda x: f"{x:,.2f}")
        resumen['TOTAL PAGADO'] = resumen['total_pagado'].apply(lambda x: f"{x:,.2f}")
        resumen['SALDO A PAGAR'] = resumen['saldo_a_pagar'].apply(lambda x: f"{x:,.2f}")

        columnas_finales = ['torre', 'departamento', 'codigo', 'dni', 'nombre',
                            'TOTAL PROGRAMACIÓN', 'TOTAL DEUDA', 'TOTAL PAGADO', 'SALDO A PAGAR']
        columnas_existentes = [c for c in columnas_finales if c in resumen.columns]
        resumen_final = resumen[columnas_existentes].copy()
        resumen_final.columns = ['TORRE', 'N°DPTO', 'CÓDIGO', 'DNI', 'APELLIDOS Y NOMBRES',
                                 'TOTAL PROGRAMACIÓN', 'TOTAL DEUDA', 'TOTAL PAGADO', 'SALDO A PAGAR']

        # ------------------- MÉTRICAS Y BUSCADOR -------------------
        total_prog_gral = resumen['TOTAL PROGRAMACIÓN'].apply(lambda x: float(x.replace(',', '').replace('.', ''))).sum()
        total_deuda_gral = resumen['TOTAL DEUDA'].apply(lambda x: float(x.replace(',', '').replace('.', ''))).sum()
        total_pag_gral = resumen['TOTAL PAGADO'].apply(lambda x: float(x.replace(',', '').replace('.', ''))).sum()
        total_saldo_gral = resumen['SALDO A PAGAR'].apply(lambda x: float(x.replace(',', '').replace('.', ''))).sum()

        s.subheader("Totales generales")
        col1, col2, col3, col4 = s.columns(4)
        with col1:
            s.metric("💰 Total Programación", f"S/ {total_prog_gral:,.2f}")
        with col2:
            s.metric("📊 Total Deuda", f"S/ {total_deuda_gral:,.2f}")
        with col3:
            s.metric("💸 Total Pagado", f"S/ {total_pag_gral:,.2f}")
        with col4:
            s.metric("🏦 Total Saldo a Pagar", f"S/ {total_saldo_gral:,.2f}")
        s.markdown("---")

        # Buscador
        busqueda = s.text_input("Buscar por código o nombre", placeholder="Ej. 01101 o nombre")
        if busqueda:
            mask = (resumen_final['CÓDIGO'].astype(str).str.contains(busqueda, case=False, na=False) |
                    resumen_final['APELLIDOS Y NOMBRES'].astype(str).str.contains(busqueda, case=False, na=False))
            resumen_final = resumen_final[mask].copy()
            if resumen_final.empty:
                s.warning("No se encontraron resultados.")

        # Mostrar tabla
        s.dataframe(resumen_final, use_container_width=True, height=600)

        # Subtotales por torre
        s.subheader("Subtotales por Torre")
        subtotales = resumen_final.groupby('TORRE')[['TOTAL PROGRAMACIÓN', 'TOTAL DEUDA', 'TOTAL PAGADO', 'SALDO A PAGAR']].agg(
            lambda x: sum(limpiar_numero(v) for v in x)
        ).reset_index()
        for col in ['TOTAL PROGRAMACIÓN', 'TOTAL DEUDA', 'TOTAL PAGADO', 'SALDO A PAGAR']:
            subtotales[col] = subtotales[col].apply(lambda x: f"{x:,.2f}")
        s.dataframe(subtotales, use_container_width=True)

        # Descarga a Excel
        import io
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            resumen_final.to_excel(writer, index=False, sheet_name=f"Resumen_Torres_{s.session_state.mes_actual}_{s.session_state.anio_actual}")
            subtotales.to_excel(writer, index=False, sheet_name="Subtotales")
        excel_data = output.getvalue()
        s.download_button(
            label="📥 Descargar Reporte en Excel",
            data=excel_data,
            file_name=f"Resumen_Torres_{s.session_state.mes_actual}_{s.session_state.anio_actual}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )