import streamlit as st
import hashlib

st.set_page_config(
    page_title="Golf Los Andes - Login",
    page_icon="🏌️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ========== CSS GLOBAL (se aplicará a toda la aplicación después del login) ==========
def load_global_css():
    css = """
    <style>
        /* Importar fuente */
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap');
        
        /* Estilos generales */
        html, body, .stApp {
            font-family: 'Montserrat', 'Segoe UI', sans-serif;
            background-color: #F8F9FA;
        }
        
        /* Sidebar personalizado (se aplicará cuando el sidebar esté visible) */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1B4D1C 0%, #2C5F2D 100%);
            border-right: 1px solid rgba(255,255,255,0.1);
        }
        [data-testid="stSidebar"] * {
            color: white !important;
        }
        [data-testid="stSidebar"] .stSelectbox, 
        [data-testid="stSidebar"] .stNumberInput,
        [data-testid="stSidebar"] .stTextInput {
            background-color: rgba(255,255,255,0.1);
            border-radius: 8px;
            padding: 4px 8px;
        }
        [data-testid="stSidebar"] .stSelectbox > div > div {
            background-color: rgba(255,255,255,0.1) !important;
        }
        [data-testid="stSidebar"] .stSelectbox label, 
        [data-testid="stSidebar"] .stNumberInput label,
        [data-testid="stSidebar"] .stTextInput label {
            color: white !important;
            font-weight: 500;
        }
        
        /* Títulos principales */
        h1, h2, h3 {
            color: #2C5F2D;
            font-weight: 600;
        }
        
        /* Botones */
        .stButton > button {
            background-color: #2C5F2D;
            color: white;
            border-radius: 8px;
            border: none;
            padding: 0.5rem 1rem;
            font-weight: 500;
            transition: all 0.2s;
        }
        .stButton > button:hover {
            background-color: #1B4D1C;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transform: translateY(-1px);
        }
        
        /* Tarjetas (métricas) */
        [data-testid="stMetricValue"] {
            font-size: 2rem;
            font-weight: bold;
            color: #2C5F2D;
        }
        [data-testid="stMetricDelta"] {
            font-size: 0.9rem;
        }
        
        /* Tablas */
        .dataframe {
            border-collapse: collapse;
            width: 100%;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        .dataframe th {
            background-color: #2C5F2D;
            color: white;
            padding: 10px;
            font-weight: 500;
        }
        .dataframe td {
            padding: 8px;
            border-bottom: 1px solid #E9ECEF;
        }
        .dataframe tr:hover {
            background-color: #F5F5DC;
        }
        
        /* Inputs */
        .stTextInput > div > div > input, 
        .stNumberInput > div > div > input {
            border-radius: 8px;
            border: 1px solid #CED4DA;
        }
        .stTextInput > div > div > input:focus,
        .stNumberInput > div > div > input:focus {
            border-color: #D4AF37;
            box-shadow: 0 0 0 2px rgba(212,175,55,0.2);
        }
        
        /* Mensajes de éxito/error */
        .stAlert {
            border-radius: 10px;
            border-left: 5px solid #D4AF37;
        }
        
        /* Footer */
        .footer {
            text-align: center;
            margin-top: 3rem;
            padding: 1rem;
            font-size: 0.8rem;
            color: #6c757d;
            border-top: 1px solid #E9ECEF;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# ========== OCULTAR SIDEBAR EN LOGIN ==========
st.markdown("""
<style>
[data-testid="stSidebar"] { display: none; }
[data-testid="collapsedControl"] { display: none; }
.block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)

# Cargar CSS global (se aplicará después del login)
load_global_css()

# Logo original (copiado de tu código)
LOGO_B64 = "/9j/4AAQSkZJRgABAQAAAQABAAD/4gHYSUNDX1BST0ZJTEUAAQEAAAHIAAAAAAQwAABtbnRyUkdCIFhZWiAH4AABAAEAAAAAAABhY3NwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQAA9tYAAQAAAADTLQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAlkZXNjAAAA8AAAACRyWFlaAAABFAAAABRnWFlaAAABKAAAABRiWFlaAAABPAAAABR3dHB0AAABUAAAABRyVFJDAAABZAAAAChnVFJDAAABZAAAAChiVFJDAAABZAAAAChjcHJ0AAABjAAAADxtbHVjAAAAAAAAAAEAAAAMZW5VUwAAAAgAAAAcAHMAUgBHAEJYWVogAAAAAAAAb6IAADj1AAADkFhZWiAAAAAAAABimQAAt4UAABjaWFlaIAAAAAAAACSgAAAPhAAAts9YWVogAAAAAAAA9tYAAQAAAADTLXBhcmEAAAAAAAQAAAACZmYAAPKnAAANWQAAE9AAAApbAAAAAAAAAABtbHVjAAAAAAAAAAEAAAAMZW5VUwAAACAAAAAcAEcAbwBvAGcAbABlACAASQBuAGMALgAgADIAMAAxADb/2wBDAAUDBAQEAwUEBAQFBQUGBwwIBwcHBw8LCwkMEQ8SEhEPERETFhwXExQaFRERGCEYGh0dHx8fExciJCIeJBweHx7/2wBDAQUFBQcGBw4ICA4eFBEUHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh7/wAARCAE4B84DASIAAhEBAxEB/8QAHQAAAQQDAQEAAAAAAAAAAAAAAAECAwQFBgcICf/EAF4QAAEDAwMCAwYCBgcDCAYBFQECAwQABREGEiEHMRNBUQgUImFxgTKRFSNCUqGxFjNCYnLB0SSCkhclNFNjorLhCRchJjVEc4KSs8LxJ1R0hZSVw9Pj/8QAGwEBAAIDAQEBAAAAAAAAAAAAAAABAgMEBQYH/8QALREBAAICAgICAQQCAgEFAAAAAAECAxESIQQxE0FRImFxBRQygZGhFSOxweH/2gAMAwEAAhEDEQA/AO9UmeaBnNJtOaEw/9k="

# ── Usuarios y contraseñas ────────────────────────────────────────────────────
USUARIOS = {
    "admin":     hashlib.sha256("golf2026".encode()).hexdigest(),
    "nahum":     hashlib.sha256("andes2026".encode()).hexdigest(),
    "operador":  hashlib.sha256("operador123".encode()).hexdigest(),
}

def verificar(usuario, password):
    if usuario in USUARIOS:
        return USUARIOS[usuario] == hashlib.sha256(password.encode()).hexdigest()
    return False

# ── Logo centrado (versión mejorada) ──────────────────────────────────────────
st.markdown(
    f"""
    <div style="display: flex; justify-content: center; margin-bottom: 0.5rem;">
        <div style="background: white; border-radius: 20px; padding: 0.75rem 1.5rem; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
            <img src="data:image/png;base64,{LOGO_B64}" style="max-width: 240px; height: auto; display: block;"/>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Card de login
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

# Formulario
with st.form("login_form"):
    st.markdown("<br>", unsafe_allow_html=True)
    usuario  = st.text_input("👤  Usuario:", placeholder="Ingrese su usuario")
    password = st.text_input("🔒  Contraseña:", type="password", placeholder="Ingrese su contraseña")
    st.markdown("<br>", unsafe_allow_html=True)
    submit = st.form_submit_button("🔐  INGRESAR", use_container_width=True)

    if submit:
        if not usuario or not password:
            st.error("⚠️ Ingrese usuario y contraseña")
        elif verificar(usuario.strip().lower(), password):
            st.session_state["autenticado"] = True
            st.session_state["usuario"]     = usuario.strip().lower()
            st.success("✅ Acceso correcto!")
            st.switch_page("pages/1_Buscar.py")
        else:
            st.error("❌ Usuario o contraseña incorrectos")

st.markdown("""
<p style="text-align:center;color:#aaa;font-size:12px;margin-top:20px">
    Residencial Golf Los Andes © 2026
</p>
""", unsafe_allow_html=True)
