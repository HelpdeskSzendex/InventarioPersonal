# utils/styles.py
import streamlit as st

def apply_custom_styles():
    """
    Inyecta CSS personalizado para mejorar la apariencia de la aplicación.
    """
    st.markdown("""
        <style>
        /* Importar fuente moderna */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

        html, body, [class*="st-"] {
            font-family: 'Inter', sans-serif;
        }

        /* Estilo para las tarjetas de personal */
        .person-card {
            background-color: #ffffff;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 15px;
            border: 1px solid #e5e7eb;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            transition: transform 0.2s ease-in-out;
        }
        .person-card:hover {
            border-color: #3b82f6;
            transform: translateY(-2px);
        }

        /* Encabezados personalizados */
        .main-header {
            color: #1e3a8a;
            font-weight: 700;
            font-size: 2.5rem;
            margin-bottom: 1rem;
        }
        .sub-header {
            color: #1e40af;
            font-weight: 600;
            font-size: 1.5rem;
            margin-top: 1.5rem;
            margin-bottom: 1rem;
            border-bottom: 2px solid #3b82f6;
            padding-bottom: 5px;
        }

        /* Estilo para métricas en Dashboard */
        .metric-card {
            background-color: #f8fafc;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
            border: 1px solid #e2e8f0;
        }

        /* Botones personalizados (Streamlit no permite mucho, pero algo se puede) */
        .stButton>button {
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s;
        }

        /* Ocultar menú de Streamlit y footer para una apariencia más 'app' */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        /* Ajuste de márgenes */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        </style>
    """, unsafe_allow_html=True)

def card_container(title, subtitle=None):
    """
    Helper para crear el inicio de una tarjeta con HTML.
    Streamlit no permite cerrar el div fácilmente si usamos st.write,
    así que se recomienda usar st.container(border=True) y añadir clases vía markdown si es posible,
    o inyectar el HTML completo.
    """
    html = f"""
    <div class="person-card">
        <h3 style="margin-top:0; color:#1e3a8a;">{title}</h3>
        {f'<p style="color:#6b7280; font-weight:600;">{subtitle}</p>' if subtitle else ''}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
