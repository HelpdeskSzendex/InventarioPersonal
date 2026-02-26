# utils/styles.py
import streamlit as st

def apply_custom_styles(show_sidebar=True):
    """
    Inyecta CSS personalizado para profesionalizar la apariencia de la aplicación.
    """
    sidebar_style = "" if show_sidebar else """
        [data-testid="stSidebar"] {display: none;}
        [data-testid="stSidebarNav"] {display: none;}
    """

    css_template = """
        <style>
        /* Importar fuente moderna y profesional */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        html, body, [class*="st-"] {
            font-family: 'Inter', sans-serif;
            color: #1f2937;
        }

        /* Fondo de página con degradado sutil */
        .stApp {
            background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
        }

        /* --- SIDEBAR --- */
        [data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #e5e7eb;
        }

        /* SIDEBAR_STYLE_PLACEHOLDER */

        .sidebar-user-box {
            background-color: #f9fafb;
            padding: 16px;
            border-radius: 12px;
            border: 1px solid #f3f4f6;
            margin-bottom: 20px;
        }

        /* --- CARDS & CONTAINERS --- */
        .person-card {
            background-color: #ffffff;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            border: 1px solid #e5e7eb;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            transition: all 0.3s ease;
        }
        .person-card:hover {
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
            border-color: #3b82f6;
        }

        /* --- TYPOGRAPHY --- */
        .main-header {
            color: #111827;
            font-weight: 800;
            font-size: 2.25rem;
            margin-bottom: 1.5rem;
            letter-spacing: -0.025em;
        }
        .sub-header {
            color: #1e40af;
            font-weight: 600;
            font-size: 1.25rem;
            margin-top: 2rem;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
        }
        .sub-header::after {
            content: "";
            flex: 1;
            height: 1px;
            background: #e5e7eb;
            margin-left: 15px;
        }

        /* --- METRIC CARDS --- */
        .metric-container {
            background: white;
            padding: 20px;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }

        /* --- BUTTONS --- */
        .stButton>button {
            border-radius: 10px;
            font-weight: 500;
            padding: 0.5rem 1rem;
            border: 1px solid #d1d5db;
            transition: all 0.2s;
        }
        .stButton>button:hover {
            border-color: #3b82f6;
            color: #3b82f6;
            background-color: #eff6ff;
        }

        /* Primary Button Style */
        .stButton>button[kind="primary"] {
            background-color: #2563eb;
            border-color: #2563eb;
            color: white;
        }
        .stButton>button[kind="primary"]:hover {
            background-color: #1d4ed8;
            border-color: #1d4ed8;
        }

        /* Ocultar elementos innecesarios */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        .block-container {
            padding-top: 3rem;
            max-width: 1200px;
        }
        </style>
    """
    st.markdown(css_template.replace("/* SIDEBAR_STYLE_PLACEHOLDER */", sidebar_style), unsafe_allow_html=True)
