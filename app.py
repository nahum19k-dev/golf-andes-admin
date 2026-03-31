import streamlit as st
import hashlib

st.set_page_config(
    page_title="Golf Los Andes - Login",
    page_icon="🏌️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ── ESTILOS MODERNOS ─────────────────────────────────────────────
st.markdown("""
<style>

/* Fondo degradado */
.stApp {
    background: linear-gradient(135deg, #1e7f5c, #4dbb9e);
}

/* Ocultar sidebar */
[data-testid="stSidebar"], [data-testid="collapsedControl"] {
    display: none;
}

/* Centrado vertical */
.block-container {
    padding-top: 5vh;
}

/* Card glass */
.login-card {
    backdrop-filter: blur(18px);
    background: rgba(255,255,255,0.15);
    border-radius: 20px;
    padding: 40px;
    max-width: 420px;
    margin: auto;
    box-shadow: 0 10px 30px rgba(0,0,0,0.25);
    color: white;
}

/* Título */
.title {
    text-align: center;
    font-size: 32px;
    font-weight: 700;
    margin-bottom: 5px;
}

/* Subtítulo */
.subtitle {
    text-align: center;
    font-size: 14px;
    opacity: 0.8;
    margin-bottom: 25px;
}

/* Inputs */
input {
    border-radius: 10px !important;
}

/* Botón */
.stButton > button {
    width: 100%;
    border-radius: 12px;
    padding: 12px;
    background: linear-gradient(90deg, #00c896, #00a87d);
    color: white;
    font-weight: bold;
    border: none;
    transition: 0.3s;
}

.stButton > button:hover {
    transform: translateY(-2px);
    background: linear-gradient(90deg, #00a87d, #008f68);
}

/* Checkbox texto blanco */
label {
    color: white !important;
}

/* Links */
a {
    color: #ffffff;
    text-decoration: none;
    font-size: 13px;
    opacity: 0.8;
}

a:hover {
    opacity: 1;
}

</style>
""", unsafe_allow_html=True)

# ── CARD INICIO ─────────────────────────────────────────────
st.markdown('<div class="login-card">', unsafe_allow_html=True)

# Logo / cabecera
st.markdown("""
<div style="text-align:center; margin-bottom:20px;">
    <div style="font-size:20px; font-weight:700;">GOLF ANDES</div>
    <div style="font-size:12px; opacity:0.8;">ADMINISTRACIÓN</div>
</div>
""", unsafe_allow_html=True)

# Título
st.markdown('<div class="title">Iniciar Sesión</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Sistema de Administración<br>Residencial Jolfandes</div>', unsafe_allow_html=True)

# ── LOGIN LOGIC ─────────────────────────────────────────────
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
    usuario  = st.text_input("Usuario", placeholder="Ingrese su usuario")
    password = st.text_input("Contraseña", type="password", placeholder="Ingrese su contraseña")

    col1, col2 = st.columns(2)
    with col1:
        recordar = st.checkbox("Recordar usuario")
    with col2:
        st.markdown('<div style="text-align:right;"><a href="#">Olvidé mi contraseña</a></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    submit = st.form_submit_button("INGRESAR")

    if submit:
        if not usuario or not password:
            st.error("Ingrese usuario y contraseña")
        elif verificar(usuario.strip().lower(), password):
            st.session_state["autenticado"] = True
            st.session_state["usuario"] = usuario.strip().lower()
            st.success("Acceso correcto")
            st.switch_page("pages/1_Buscar.py")
        else:
            st.error("Usuario o contraseña incorrectos")

# Cerrar card
st.markdown("</div>", unsafe_allow_html=True)

# Footer
st.markdown("""
<p style="text-align:center;color:white;font-size:12px;margin-top:20px;opacity:0.7">
    Residencial Golf Los Andes © 2026
</p>
""", unsafe_allow_html=True)
