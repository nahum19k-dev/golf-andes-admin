import streamlit as st
import pandas as pd
from supabase_client import leer_propietarios, agregar_propietario, eliminar_propietario_por_id

st.set_page_config(page_title="Buscar Propietario", page_icon="🔍", layout="wide")

st.markdown("""
<style>
[data-testid="stSidebar"] { background: linear-gradient(180deg, #1b5e20 0%, #2e7d32 100%); }
[data-testid="stSidebar"] * { color: white !important; }
div[data-testid="column"]:nth-child(1) .stButton > button { background:#2e7d32 !important; color:white !important; font-weight:800 !important; border-radius:8px !important; }
div[data-testid="column"]:nth-child(2) .stButton > button { background:#1565c0 !important; color:white !important; font-weight:800 !important; border-radius:8px !important; }
div[data-testid="column"]:nth-child(3) .stButton > button { background:#b71c1c !important; color:white !important; font-weight:800 !important; border-radius:8px !important; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=60)
def cargar_datos():
    return leer_propietarios()

try:
    if "df" not in st.session_state:
        st.session_state.df = cargar_datos()
    df = st.session_state.df

    st.markdown("### Buscar Propietario")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Propietarios", len(df))
    c2.metric("Con Torre/Dpto", df[df["torre"].str.strip()!=""].shape[0])
    c3.metric("En Alquiler", df[df["situacion"].astype(str).str.lower().str.contains("alquil", na=False)].shape[0])
    c4.metric("Sin DNI", df[df["dni"]==""].shape[0])
    st.markdown("---")

    col_dni, col_cod, col_nom = st.columns([2,2,3])
    with col_dni:
        buscar_dni = st.text_input("DNI:", placeholder="Ej: 08165632")
    with col_cod:
        buscar_cod = st.text_input("Codigo (Torre+Dpto):", placeholder="Ej: 01101")
    with col_nom:
        buscar_nom = st.text_input("Nombres:", placeholder="Ingrese nombre...")

    b1,b2,b3 = st.columns(3)
    with b1: btn_buscar   = st.button("BUSCAR",   use_container_width=True)
    with b2: btn_agregar  = st.button("AGREGAR",  use_container_width=True)
    with b3: btn_eliminar = st.button("ELIMINAR", use_container_width=True)

    resultado = df.copy()
    if buscar_dni: resultado = resultado[resultado["dni"].str.contains(buscar_dni.strip(), na=False)]
    if buscar_cod: resultado = resultado[resultado["codigo"].str.contains(buscar_cod.strip(), na=False)]
    if buscar_nom: resultado = resultado[resultado["nombre"].astype(str).str.upper().str.contains(buscar_nom.upper(), na=False)]
    hay_busqueda = buscar_dni or buscar_cod or buscar_nom or btn_buscar

    if btn_agregar:
        st.session_state["modo_agregar"] = True

    if st.session_state.get("modo_agregar"):
        st.markdown("---")
        st.markdown("#### Agregar Nuevo Propietario")
        with st.form("form_agregar"):
            fa1,fa2,fa3 = st.columns(3)
            with fa1:
                n_torre  = st.text_input("Torre")
                n_dpto   = st.text_input("N Dpto")
                n_dni    = st.text_input("DNI (8 digitos)", max_chars=8)
            with fa2:
                n_nombre = st.text_input("Nombres y Apellidos")
                n_cel    = st.text_input("Celular")
                n_sit    = st.selectbox("Situacion", ["","PROPIETARIO","ALQUILER","DESOCUPADO"])
            with fa3:
                n_dir    = st.text_input("Direccion")
                n_correo = st.text_input("Correo")
            cg,cc = st.columns(2)
            with cg: guardar  = st.form_submit_button("GUARDAR",  use_container_width=True)
            with cc: cancelar = st.form_submit_button("CANCELAR", use_container_width=True)

        if guardar:
            if n_dni and len(n_dni.strip()) != 8:
                st.error("El DNI debe tener exactamente 8 digitos")
            elif not n_nombre:
                st.error("El nombre es obligatorio")
            else:
                dni_val = n_dni.strip().zfill(8) if n_dni.strip() else ""
                t = str(int(n_torre)).zfill(2) if n_torre else ""
                d = str(int(n_dpto)).zfill(3)  if n_dpto  else ""
                cod = t + d if t and d else ""
                nuevo = {
                    "codigo": cod,
                    "torre": t,
                    "dpto": d,
                    "dni": dni_val,
                    "nombre": n_nombre.upper(),
                    "direccion": n_dir,
                    "celular": n_cel,
                    "correo": n_correo,
                    "situacion": n_sit
                }
                if agregar_propietario(nuevo):
                    st.cache_data.clear()
                    st.session_state.df = cargar_datos()
                    st.success("Propietario agregado correctamente!")
                    st.session_state["modo_agregar"] = False
                    st.rerun()
                else:
                    st.error("Error al guardar en Supabase.")
        if cancelar:
            st.session_state["modo_agregar"] = False
            st.rerun()

    if btn_eliminar:
        if hay_busqueda and len(resultado) == 1:
            p = resultado.iloc[0]
            st.warning("Eliminar a " + p["nombre"] + " (DNI: " + str(p["dni"]) + ")? No se puede deshacer.")
            ce1,ce2 = st.columns(2)
            with ce1:
                if st.button("SI, ELIMINAR", key="confirm_del"):
                    if eliminar_propietario_por_id(p['id']):
                        st.cache_data.clear()
                        st.session_state.df = cargar_datos()
                        st.success("Eliminado correctamente")
                        st.rerun()
                    else:
                        st.error("Error al eliminar en Supabase.")
            with ce2:
                if st.button("CANCELAR", key="cancel_del"):
                    st.rerun()
        else:
            st.warning("Busca primero un propietario específico para eliminar")

    if hay_busqueda and not st.session_state.get("modo_agregar"):
        st.markdown("**Se encontraron " + str(len(resultado)) + " resultado(s)**")
        if len(resultado) > 0:
            tabla = resultado[["codigo","dni","nombre","torre","dpto","celular","situacion"]].copy()
            tabla.columns = ["Codigo","DNI","Nombres y Apellidos","Torre","N Dpto","Celular","Situacion"]
            st.dataframe(tabla.reset_index(drop=True), use_container_width=True, hide_index=True)
            if len(resultado) == 1:
                p = resultado.iloc[0]
                st.markdown("---")
                st.markdown("#### Detalle del Propietario")
                d1,d2,d3 = st.columns(3)
                with d1:
                    st.info("Codigo: " + str(p["codigo"] or ""))
                    st.info("DNI: " + str(p["dni"] or ""))
                    st.info("Torre: " + str(p["torre"] or "") + " | Dpto: " + str(p["dpto"] or ""))
                with d2:
                    st.info("Nombre: " + str(p["nombre"]))
                    st.info("Celular: " + str(p["celular"] or ""))
                    st.info("Situacion: " + str(p["situacion"] or ""))
                with d3:
                    st.info("Correo: " + str(p["correo"] or ""))
                    st.info("Direccion: " + str(p["direccion"] or ""))
        else:
            st.warning("No se encontraron resultados.")
    elif not hay_busqueda and not st.session_state.get("modo_agregar"):
        st.info("Ingresa DNI, Codigo o Nombre para buscar")

except Exception as e:
    st.error(f"Error conectando con Supabase: {e}")
