import streamlit as st

st.set_page_config(page_title="Operaciones", page_icon="💰", layout="wide")
st.markdown("""<style>
[data-testid="stSidebar"] { background: linear-gradient(180deg, #1b5e20 0%, #2e7d32 100%); }
[data-testid="stSidebar"] * { color: white !important; }
</style>""", unsafe_allow_html=True)

st.markdown("### Operaciones - Extracto BCP")
st.info("Modulo en desarrollo - proximamente disponible")
st.markdown("""
**Este modulo incluira:**
- Carga del extracto BCP (Hoja1)
- Asignacion automatica de pagos por DNI
- Registro manual de pagos
- Reporte de deudas por propietario
""")
