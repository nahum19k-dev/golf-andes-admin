import streamlit as st
import hashlib
from ui_common import apply_global_css

st.set_page_config(
    page_title="Golf Los Andes - Login",
    page_icon="🏌️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Aplicar estilos globales
apply_global_css()

# Ocultar sidebar en login
st.markdown("""
<style>
[data-testid="stSidebar"] { display: none; }
[data-testid="collapsedControl"] { display: none; }
.block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)

# ── Logo centrado y más grande ──────────────────────────────────────────────
col1, col2, col3 = st.columns([1, 3, 1])
with col2:
    try:
        # Aumentar el tamaño a 400 píxeles de ancho
        st.image("assets/logo.png", width=400)
    except:
        st.markdown("<p style='text-align:center;'>Logo no encontrado</p>", unsafe_allow_html=True)

# Card de login con borde dorado
st.markdown("""
<div style="
    background:white;
    border-radius:16px;
    padding:32px 40px;
    box-shadow:0 8px 24px rgba(0,0,0,0.12);
    border-top:4px solid #D4AF37;
    max-width:420px;
    margin:0 auto;
">
    <h2 style="text-align:center;color:#2C5F2D;font-family:'Montserrat',sans-serif;margin-bottom:8px">
        Iniciar Sesión
    </h2>
    <p style="text-align:center;color:#666;font-size:14px;margin-bottom:24px">
        Sistema de Administración<br>Residencial Jolfandes
    </p>
</div>
""", unsafe_allow_html=True)

# ── Usuarios y contraseñas ────────────────────────────────────────────────
USUARIOS = {
    "admin":     hashlib.sha256("golf2026".encode()).hexdigest(),
    "nahum":     hashlib.sha256("andes2026".encode()).hexdigest(),
    "operador":  hashlib.sha256("operador123".encode()).hexdigest(),
}

def verificar(usuario, password):
    if usuario in USUARIOS:
        return USUARIOS[usuario] == hashlib.sha256(password.encode()).hexdigest()
    return False

# Formulario
with st.form("login_form"):
    st.markdown("<br>", unsafe_allow_html=True)
    usuario  = st.text_input("👤  Usuario:", placeholder="Ingrese su usuario")
    password = st.text_input("🔒  Contraseña:", type="password", placeholder="Ingrese su contraseña")
    
    # Opciones adicionales
    col1, col2 = st.columns(2)
    with col1:
        recordar = st.checkbox("Recordar usuario")
    with col2:
        st.markdown("""
        <div style="text-align: right;">
            <a href="#" style="color:#2C5F2D; text-decoration: none;">Olvidé mi contraseña</a>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    submit = st.form_submit_button("🔐  INGRESAR", use_container_width=True)

    if submit:
        if not usuario or not password:
            st.error("⚠️ Ingrese usuario y contraseña")
        elif verificar(usuario.strip().lower(), password):
            st.session_state["autenticado"] = True
            st.session_state["usuario"]     = usuario.strip().lower()
            if recordar:
                st.info("La opción 'Recordar usuario' estará disponible próximamente.")
            st.success("✅ Acceso correcto!")
            st.switch_page("pages/1_Buscar.py")
        else:
            st.error("❌ Usuario o contraseña incorrectos")

st.markdown("""
<p style="text-align:center;color:#aaa;font-size:12px;margin-top:20px">
    Residencial Golf Los Andes © 2026
</p>
""", unsafe_allow_html=True)
