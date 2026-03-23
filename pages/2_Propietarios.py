import streamlit as st
import pandas as pd
from gsheets import leer_propietarios

st.set_page_config(page_title="Datos Propietarios", page_icon="📊", layout="wide")
st.markdown("""<style>
[data-testid="stSidebar"] { background: linear-gradient(180deg, #1b5e20 0%, #2e7d32 100%); }
[data-testid="stSidebar"] * { color: white !important; }
</style>""", unsafe_allow_html=True)

@st.cache_data(ttl=60)
def cargar():
    return leer_propietarios()

try:
    df = cargar()
    st.markdown("### Datos Propietarios")
    filtro = st.text_input("Filtrar (DNI, nombre, codigo, torre):")
    if filtro:
        mask = (df["dni"].astype(str).str.contains(filtro, case=False, na=False) |
                df["nombre"].astype(str).str.contains(filtro, case=False, na=False) |
                df["codigo"].astype(str).str.contains(filtro, case=False, na=False) |
                df["torre"].astype(str).str.contains(filtro, case=False, na=False))
        mostrar = df[mask]
    else:
        mostrar = df
    st.markdown("Mostrando **" + str(len(mostrar)) + "** propietarios")
    tabla = mostrar[["codigo","torre","dpto","dni","nombre","celular","correo","situacion"]].copy()
    tabla.columns = ["Codigo","Torre","N Dpto","DNI","Nombres y Apellidos","Celular","Correo","Situacion"]
    st.dataframe(tabla.reset_index(drop=True), use_container_width=True, hide_index=True, height=500)
    csv = tabla.to_csv(index=False).encode("utf-8")
    st.download_button("Descargar CSV", csv, "propietarios.csv", "text/csv")
except Exception as e:
    st.error(f"Error conectando con Google Sheets: {e}")
