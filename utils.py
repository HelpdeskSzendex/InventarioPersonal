# utils.py
import streamlit as st
from supabase import create_client, Client
import os

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@st.cache_resource
def init_supabase_client():
    """
    Inicializa y devuelve el cliente de Supabase usando las credenciales.
    La función se cachea para no reconectar en cada recarga.
    """

    try:
        url = st.secrets["supabase_url"]
        key = st.secrets["supabase_key"]
        return create_client(url, key)
    except Exception:
        st.error("Error al conectar con Supabase. Revisa tus credenciales en .streamlit/secrets.toml")
        st.stop()

def check_role(roles_permitidos: list):
    """
    Comprueba si el rol del usuario en la sesión actual está en la lista de roles permitidos.
    Si el usuario no ha iniciado sesión o no tiene el rol correcto, muestra un error y detiene la página.
    """
    user_info = st.session_state.get("user_info")
    if not user_info or user_info.get("role") not in roles_permitidos:
        st.error("No tienes permiso para acceder a esta página.")
        st.stop()