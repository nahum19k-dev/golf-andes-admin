import streamlit as st
import streamlit_authenticator as stauth  # si usas autenticación, sino omite
import yaml
from yaml.loader import SafeLoader

st.set_page_config(
    page_title="Jolfandes - Administración",
    page_icon="🏌️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== CARGAR CSS PERSONALIZADO ==========
def load_css():
    css = """
    <style>
        /* Importar fuente */
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap');
        
        /* Estilos generales */
        html, body, .stApp {
            font-family: 'Montserrat', 'Segoe UI', sans-serif;
            background-color: #F8F9FA;
        }
        
        /* Sidebar personalizado */
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

load_css()

# ========== SIDEBAR CON LOGO ==========
with st.sidebar:
    # Logo textual (puedes reemplazar por imagen)
    st.markdown("""
    <div style="text-align: center; padding: 20px 0;">
        <div style="font-size: 2.2rem; font-weight: bold; letter-spacing: 2px; color: #D4AF37;">⛳</div>
        <div style="font-size: 1.2rem; font-weight: 500; margin-top: 5px;">Residencial</div>
        <div style="font-size: 2rem; font-weight: 800; margin-top: -5px; letter-spacing: 1px;">JOLFANDES</div>
        <div style="font-size: 0.9rem; opacity: 0.8;">Administración</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Línea decorativa
    st.markdown("<hr style='margin: 10px 0; border-color: rgba(255,255,255,0.2);'>", unsafe_allow_html=True)
    
    # El resto del menú (páginas) se añade automáticamente por Streamlit
    st.markdown("### Menú")

# ========== CONTENIDO PRINCIPAL ==========
# Aquí se cargarán las páginas automáticamente
# (no necesitas modificar nada más)
