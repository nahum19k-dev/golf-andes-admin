import streamlit as st

def check_auth():
    """Llamar al inicio de cada página para verificar login"""
    if not st.session_state.get("autenticado"):
        st.warning("⚠️ Debes iniciar sesión primero")
        st.switch_page("app.py")
        st.stop()
