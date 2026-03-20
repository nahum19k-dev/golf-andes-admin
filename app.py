import streamlit as st
import json
import pandas as pd

# ── Configuración de página ─────────────────────────────────────────────────
st.set_page_config(
    page_title="Golf Los Andes - Administración",
    page_icon="🏌️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Estilos CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700;800;900&display=swap');

/* Header principal */
.header-container {
    background: linear-gradient(135deg, #1b5e20 0%, #2e7d32 50%, #388e3c 100%);
    padding: 24px 32px;
    border-radius: 12px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 20px;
    box-shadow: 0 4px 20px rgba(46,125,50,0.3);
}

.header-title {
    font-family: 'Montserrat', sans-serif;
    font-size: 36px;
    font-weight: 900;
    color: white;
    margin: 0;
    line-height: 1;
}

.header-title span { color: #a5d6a7; }

.header-sub {
    font-family: 'Montserrat', sans-serif;
    font-size: 12px;
    font-weight: 700;
    color: #a5d6a7;
    letter-spacing: 4px;
    text-transform: uppercase;
    margin-top: 4px;
}

/* Tarjetas de stats */
.stat-card {
    background: white;
    border-radius: 10px;
    padding: 16px 20px;
    border-left: 4px solid #2e7d32;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    text-align: center;
}

/* Tabla */
.stDataFrame { border-radius: 8px; overflow: hidden; }

/* Botón buscar */
.stButton > button {
    background: linear-gradient(135deg, #2e7d32, #1b5e20) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    padding: 10px 30px !important;
    font-size: 15px !important;
    width: 100%;
}

/* Badge situación */
.badge-prop { background:#e8f5e9; color:#1b5e20; padding:2px 10px; border-radius:12px; font-size:12px; font-weight:700; }
.badge-alq  { background:#fff3e0; color:#e65100; padding:2px 10px; border-radius:12px; font-size:12px; font-weight:700; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1b5e20 0%, #2e7d32 100%);
}

[data-testid="stSidebar"] * { color: white !important; }
[data-testid="stSidebar"] .stRadio label { color: white !important; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ── Cargar datos ─────────────────────────────────────────────────────────────
@st.cache_data
def cargar_datos():
    with open("propietarios.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return pd.DataFrame(data)

df = cargar_datos()

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="header-container">
    <div style="font-size:52px">🏌️</div>
    <div>
        <div class="header-title">Residencial <span>Golf</span>Andes</div>
        <div class="header-sub">Sistema de Administración</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Sidebar - Menú ────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📋 Menú")
    st.markdown("---")
    pagina = st.radio(
        "",
        ["🔍 Buscar Propietario", "📊 Datos Propietarios", "💰 Operaciones", "📈 Dashboard"],
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.markdown(f"**Total propietarios:** {len(df)}")
    st.markdown(f"**Torres:** 1 al 19")

# ── PÁGINA: BUSCAR PROPIETARIO ────────────────────────────────────────────────
if pagina == "🔍 Buscar Propietario":

    st.markdown("### 🔍 Buscar Cliente")

    # Stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Propietarios", len(df))
    with col2:
        con_torre = df[df['torre'].str.strip() != ''].shape[0]
        st.metric("Con Torre/Dpto", con_torre)
    with col3:
        alquiler = df[df['situacion'].str.lower().str.contains('alquil', na=False)].shape[0]
        st.metric("En Alquiler", alquiler)
    with col4:
        sin_dni = df[df['dni'] == ''].shape[0]
        st.metric("Sin DNI", sin_dni)

    st.markdown("---")

    # Formulario de búsqueda
    col_dni, col_nombre, col_btn = st.columns([2, 3, 1])
    with col_dni:
        buscar_dni = st.text_input("**DNI:**", placeholder="Ingrese DNI...", key="inp_dni")
    with col_nombre:
        buscar_nombre = st.text_input("**Nombres:**", placeholder="Ingrese nombres...", key="inp_nombre")
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        buscar_btn = st.button("🔍 BUSCAR")

    # Filtrar
    resultado = df.copy()
    if buscar_dni:
        resultado = resultado[resultado['dni'].str.contains(buscar_dni, case=False, na=False)]
    if buscar_nombre:
        resultado = resultado[resultado['nombre'].str.contains(buscar_nombre, case=False, na=False)]

    if buscar_dni or buscar_nombre or buscar_btn:
        st.markdown(f"**Se encontraron {len(resultado)} resultado(s)**")

        if len(resultado) > 0:
            # Mostrar tabla
            tabla = resultado[['dni','nombre','torre','dpto','celular','correo','situacion']].copy()
            tabla.columns = ['DNI','Nombres y Apellidos','Torre','N° Dpto','N° Celular','Correo','Situación']
            tabla = tabla.reset_index(drop=True)
            st.dataframe(
                tabla,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "DNI": st.column_config.TextColumn("DNI", width=100),
                    "Nombres y Apellidos": st.column_config.TextColumn("Nombres y Apellidos", width=250),
                    "Torre": st.column_config.TextColumn("Torre", width=60),
                    "N° Dpto": st.column_config.TextColumn("N° Dpto", width=70),
                    "Situación": st.column_config.TextColumn("Situación", width=110),
                }
            )

            # Detalle al seleccionar
            if len(resultado) == 1:
                p = resultado.iloc[0]
                st.markdown("---")
                st.markdown("#### 📋 Detalle del Propietario")
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.info(f"**DNI:** {p['dni'] or '—'}")
                    st.info(f"**Torre:** {p['torre'] or '—'}  |  **Dpto:** {p['dpto'] or '—'}")
                with c2:
                    st.info(f"**Celular:** {p['celular'] or '—'}")
                    st.info(f"**Situación:** {p['situacion'] or '—'}")
                with c3:
                    st.info(f"**Correo:** {p['correo'] or '—'}")
                    st.info(f"**Dirección:** {p['direccion'] or '—'}")
        else:
            st.warning("No se encontraron resultados.")

    else:
        st.info("👆 Ingresa un DNI o nombre para buscar")

# ── PÁGINA: DATOS PROPIETARIOS ────────────────────────────────────────────────
elif pagina == "📊 Datos Propietarios":

    st.markdown("### 📊 Datos Propietarios")

    # Filtro rápido
    filtro = st.text_input("🔍 Buscar (DNI, nombre, torre, dpto):", placeholder="Escriba para filtrar...")

    if filtro:
        mask = (
            df['dni'].str.contains(filtro, case=False, na=False) |
            df['nombre'].str.contains(filtro, case=False, na=False) |
            df['torre'].str.contains(filtro, case=False, na=False) |
            df['dpto'].str.contains(filtro, case=False, na=False)
        )
        mostrar = df[mask]
    else:
        mostrar = df

    st.markdown(f"Mostrando **{len(mostrar)}** propietarios")

    tabla = mostrar[['torre','dpto','dni','nombre','celular','correo','situacion']].copy()
    tabla.columns = ['Torre','N° Dpto','DNI','Nombres y Apellidos','Celular','Correo','Situación']
    tabla = tabla.reset_index(drop=True)

    st.dataframe(
        tabla,
        use_container_width=True,
        hide_index=True,
        height=500
    )

    # Exportar
    csv = tabla.to_csv(index=False).encode('utf-8')
    st.download_button(
        "⬇️ Descargar como CSV",
        csv,
        "propietarios_golf_andes.csv",
        "text/csv"
    )

# ── PÁGINA: OPERACIONES ───────────────────────────────────────────────────────
elif pagina == "💰 Operaciones":
    st.markdown("### 💰 Operaciones")
    st.info("🚧 Módulo en desarrollo — próximamente disponible")

    st.markdown("""
    **Este módulo incluirá:**
    - 📥 Carga del extracto BCP
    - ✅ Asignación automática de pagos por DNI
    - 📋 Registro manual de pagos
    - 📊 Reporte de deudas por propietario
    """)

# ── PÁGINA: DASHBOARD ─────────────────────────────────────────────────────────
elif pagina == "📈 Dashboard":
    st.markdown("### 📈 Dashboard")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Propietarios por Torre")
        por_torre = df[df['torre'].str.strip() != ''].groupby('torre').size().reset_index(name='cantidad')
        por_torre['torre'] = por_torre['torre'].apply(lambda x: f"Torre {x}")
        por_torre = por_torre.sort_values('torre')
        st.bar_chart(por_torre.set_index('torre'))

    with col2:
        st.markdown("#### Situación de Departamentos")
        sit = df['situacion'].replace('', 'Sin datos').fillna('Sin datos')
        sit_count = sit.value_counts().reset_index()
        sit_count.columns = ['Situación', 'Cantidad']
        st.dataframe(sit_count, hide_index=True, use_container_width=True)

    st.markdown("---")
    st.markdown("#### Resumen General")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Propietarios", len(df))
    c2.metric("Torres", 19)
    c3.metric("Con correo registrado", df[df['correo'].str.strip() != ''].shape[0])
    c4.metric("Con celular registrado", df[df['celular'].str.strip() != ''].shape[0])
