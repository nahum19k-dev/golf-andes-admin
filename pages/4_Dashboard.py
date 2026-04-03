import streamlit as st
import pandas as pd
import supabase_client as gsheets
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Dashboard de Cobranza", page_icon="📊", layout="wide")

st.title("📊 Dashboard de Gestión de Cobranza")
st.markdown("---")

# ========== FUNCIONES AUXILIARES ==========
@st.cache_data(ttl=600)
def cargar_propietarios():
    return gsheets.leer_propietarios()

@st.cache_data(ttl=600)
def obtener_datos_mes(anio, mes):
    """Obtiene los datos de saldos_mensuales y los combina con propietarios."""
    df_saldos = gsheets.leer_saldos_mensuales(anio, mes)
    if df_saldos.empty:
        return None, None
    df_prop = cargar_propietarios()
    if not df_prop.empty:
        df_prop['torre'] = pd.to_numeric(df_prop['torre'], errors='coerce')
        df_prop['departamento'] = pd.to_numeric(df_prop['dpto'], errors='coerce')
        df_prop = df_prop[['torre', 'departamento', 'nombre']].dropna()
        df_prop['torre'] = df_prop['torre'].astype(int)
        df_prop['departamento'] = df_prop['departamento'].astype(int)
        df_saldos = df_saldos.merge(df_prop, on=['torre', 'departamento'], how='left')
        df_saldos['nombre'] = df_saldos['nombre'].fillna("SIN REGISTRAR")
    else:
        df_saldos['nombre'] = "SIN REGISTRAR"
    return df_saldos, df_saldos[df_saldos['saldo_final'] > 0].copy()

# ========== SELECTOR DE MES Y AÑO ==========
meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
         "Julio","Agosto","Setiembre","Octubre","Noviembre","Diciembre"]
col1, col2 = st.columns(2)
with col1:
    mes_sel = st.selectbox("Mes", meses, index=0)
with col2:
    anio_sel = st.number_input("Año", min_value=2025, max_value=2035, value=2026, step=1)

# Botón para cargar
if st.button("Actualizar Dashboard", type="primary", use_container_width=True):
    with st.spinner("Cargando datos..."):
        df_total, df_deudores = obtener_datos_mes(anio_sel, mes_sel)
        if df_total is None or df_total.empty:
            st.warning(f"No hay datos de saldos para {mes_sel} {anio_sel}. Primero genera ese mes en la pestaña 'Detalle' de Operaciones.")
        else:
            # Guardar en session_state para evitar recargas en cada tab
            st.session_state['df_total'] = df_total
            st.session_state['df_deudores'] = df_deudores
            st.session_state['datos_cargados'] = True
else:
    if 'datos_cargados' not in st.session_state:
        st.session_state['datos_cargados'] = False

if st.session_state.get('datos_cargados', False):
    df_total = st.session_state['df_total']
    df_deudores = st.session_state['df_deudores']

    # ========== KPI PRINCIPALES ==========
    total_saldo_positivo = df_deudores['saldo_final'].sum()
    total_pagado = df_total['total_pagado'].sum()
    num_deudores = len(df_deudores)
    total_programacion = (df_total['mantenimiento'].sum() +
                          df_total['amortizacion'].sum() +
                          df_total['medidor'].sum() +
                          df_total['otros'].sum())
    deuda_inicial_total = df_total['deuda_inicial'].sum()
    tasa_morosidad = (total_saldo_positivo / (deuda_inicial_total + total_programacion)) * 100 if (deuda_inicial_total + total_programacion) > 0 else 0

    # CSS para tarjetas
    st.markdown("""
    <style>
    .kpi-card {
        background: linear-gradient(135deg, #1e4663 0%, #2c5a82 100%);
        border-radius: 20px;
        padding: 1rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        text-align: center;
        color: white;
        margin-bottom: 1rem;
    }
    .kpi-number {
        font-size: 2.2rem;
        font-weight: bold;
    }
    .kpi-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    </style>
    """, unsafe_allow_html=True)

    col_kpi1, col_kpi2, col_kpi3, col_kpi4, col_kpi5 = st.columns(5)
    with col_kpi1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-number">S/ {total_saldo_positivo:,.2f}</div>
            <div class="kpi-label">💰 Saldo a Pagar</div>
        </div>
        """, unsafe_allow_html=True)
    with col_kpi2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-number">S/ {total_pagado:,.2f}</div>
            <div class="kpi-label">💵 Total Pagado</div>
        </div>
        """, unsafe_allow_html=True)
    with col_kpi3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-number">{num_deudores}</div>
            <div class="kpi-label">🏢 N° Deudores</div>
        </div>
        """, unsafe_allow_html=True)
    with col_kpi4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-number">{tasa_morosidad:.1f}%</div>
            <div class="kpi-label">📉 Morosidad</div>
        </div>
        """, unsafe_allow_html=True)
    with col_kpi5:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-number">S/ {total_programacion:,.2f}</div>
            <div class="kpi-label">📋 Programación</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ========== PESTAÑAS INTERNAS PARA GRÁFICOS ==========
    tab_resumen, tab_torres, tab_deudores, tab_evolucion = st.tabs(
        ["📈 Resumen General", "🏢 Deuda por Torre", "👥 Top Deudores", "📅 Evolución Mensual"]
    )

    with tab_resumen:
        # Gráfico de composición de la deuda (Waterfall)
        st.subheader("Análisis de Deuda: Inicial + Programación - Pagos = Saldo Final")
        data_waterfall = {
            'Concepto': ['Deuda Inicial', 'Programación', 'Pagos', 'Saldo Final (Deudores)'],
            'Monto': [deuda_inicial_total, total_programacion, -total_pagado, total_saldo_positivo],
            'Medida': ['relative', 'relative', 'relative', 'total']
        }
        df_water = pd.DataFrame(data_waterfall)
        fig_wf = go.Figure(go.Waterfall(
            name="Movimientos",
            orientation="v",
            measure=df_water['Medida'],
            x=df_water['Concepto'],
            y=df_water['Monto'],
            textposition="outside",
            text=[f"S/ {v:,.2f}" if v != -total_pagado else f"-S/ {abs(v):,.2f}" for v in df_water['Monto']],
            connector={"line": {"color": "rgb(63,63,63)"}},
            increasing={"marker": {"color": "#2c5a82"}},
            decreasing={"marker": {"color": "#d9534f"}},
            totals={"marker": {"color": "#5cb85c"}}
        ))
        fig_wf.update_layout(height=500, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig_wf, use_container_width=True)

        # Gráfico de distribución de deudores por rango de deuda
        bins = [0, 500, 1000, 5000, 10000, 50000, float('inf')]
        labels = ['< S/500', 'S/500-1000', 'S/1000-5000', 'S/5000-10000', 'S/10000-50000', '> S/50000']
        df_deudores['rango'] = pd.cut(df_deudores['saldo_final'], bins=bins, labels=labels, right=False)
        rango_counts = df_deudores['rango'].value_counts().reset_index()
        rango_counts.columns = ['Rango', 'Cantidad']
        fig_pie = px.pie(rango_counts, values='Cantidad', names='Rango', 
                         title='Distribución de Deudores por Monto Adeudado',
                         color_discrete_sequence=px.colors.sequential.Blues_r)
        st.plotly_chart(fig_pie, use_container_width=True)

    with tab_torres:
        st.subheader("Deuda Pendiente por Torre")
        deuda_torre = df_deudores.groupby('torre')['saldo_final'].sum().reset_index()
        deuda_torre = deuda_torre.sort_values('saldo_final', ascending=False)
        fig_bar = px.bar(deuda_torre, x='torre', y='saldo_final', 
                         title="Saldo a Pagar por Torre (S/)",
                         labels={'torre': 'Torre', 'saldo_final': 'Saldo (S/)'},
                         color='saldo_final', color_continuous_scale='Blues')
        fig_bar.update_layout(height=500)
        st.plotly_chart(fig_bar, use_container_width=True)

        # Tabla de detalle por torre
        st.subheader("Detalle por Torre")
        tabla_torre = deuda_torre.copy()
        tabla_torre.columns = ['Torre', 'Saldo a Pagar (S/)']
        tabla_torre['Saldo a Pagar (S/)'] = tabla_torre['Saldo a Pagar (S/)'].apply(lambda x: f"S/ {x:,.2f}")
        st.dataframe(tabla_torre, use_container_width=True)

    with tab_deudores:
        st.subheader("Top 10 Deudores")
        top10 = df_deudores.nlargest(10, 'saldo_final')[['nombre', 'saldo_final', 'torre', 'departamento']]
        top10['nombre_corto'] = top10['nombre'].apply(lambda x: x[:25] + '...' if len(x) > 25 else x)
        top10['label'] = top10['nombre_corto'] + f" (T{top10['torre']}-{top10['departamento']})"
        fig_top = px.bar(top10, x='saldo_final', y='label', orientation='h',
                         title='Top 10 Deudores',
                         labels={'saldo_final': 'Saldo (S/)', 'label': 'Propietario'},
                         color='saldo_final', color_continuous_scale='Reds')
        fig_top.update_layout(height=500, margin=dict(l=0, r=0))
        st.plotly_chart(fig_top, use_container_width=True)

        # Mostrar tabla completa de deudores (opcional)
        with st.expander("Ver todos los deudores"):
            todos = df_deudores[['torre', 'departamento', 'nombre', 'saldo_final']].copy()
            todos.columns = ['Torre', 'N°DPTO', 'Propietario', 'Saldo Pendiente']
            todos['Saldo Pendiente'] = todos['Saldo Pendiente'].apply(lambda x: f"S/ {x:,.2f}")
            st.dataframe(todos, use_container_width=True)

    with tab_evolucion:
        st.subheader("Evolución de Indicadores (últimos 6 meses)")
        # Necesitamos datos históricos de saldos_mensuales
        # Vamos a consultar los últimos 6 meses disponibles
        meses_num = list(range(anio_sel-1, anio_sel+1))
        # Obtener meses previos
        evol_data = []
        for i in range(5, -1, -1):
            # Calcular mes y año correspondientes
            nuevo_mes_num = meses.index(mes_sel) + 1 - i
            nuevo_anio = anio_sel
            if nuevo_mes_num <= 0:
                nuevo_mes_num += 12
                nuevo_anio -= 1
            if nuevo_anio < 2025:
                continue
            mes_nombre = meses[nuevo_mes_num-1]
            df_hist, _ = obtener_datos_mes(nuevo_anio, mes_nombre)
            if df_hist is not None and not df_hist.empty:
                saldo_pos = df_hist[df_hist['saldo_final'] > 0]['saldo_final'].sum()
                pagado = df_hist['total_pagado'].sum()
                deudores = len(df_hist[df_hist['saldo_final'] > 0])
                evol_data.append({
                    'Mes': f"{mes_nombre[:3]}-{nuevo_anio}",
                    'Saldo a Pagar': saldo_pos,
                    'Total Pagado': pagado,
                    'N° Deudores': deudores
                })
        if evol_data:
            df_evol = pd.DataFrame(evol_data)
            fig_line = px.line(df_evol, x='Mes', y=['Saldo a Pagar', 'Total Pagado'], 
                               title='Evolución de Saldo y Pagos',
                               labels={'value': 'Soles', 'variable': 'Indicador'},
                               markers=True)
            st.plotly_chart(fig_line, use_container_width=True)

            fig_deudores = px.bar(df_evol, x='Mes', y='N° Deudores', 
                                  title='Evolución del Número de Deudores',
                                  text_auto=True, color_discrete_sequence=['#2c5a82'])
            st.plotly_chart(fig_deudores, use_container_width=True)
        else:
            st.info("No hay datos suficientes para mostrar evolución (genera meses anteriores).")
else:
    st.info("Selecciona un mes y año y haz clic en 'Actualizar Dashboard' para comenzar.")
