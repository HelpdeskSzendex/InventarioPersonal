# utils/auth.py
import streamlit as st
from utils.db import get_supabase

def check_role(roles_permitidos: list):
    """
    Comprueba si el rol del usuario en la sesión actual está en la lista de roles permitidos.
    Si el usuario no ha iniciado sesión o no tiene el rol correcto, muestra un error y detiene la página.
    """
    user_info = st.session_state.get("user_info")
    if not user_info:
        st.error("Por favor, inicia sesión para acceder a esta página.")
        st.stop()

    if user_info.get("role") not in roles_permitidos:
        st.error("No tienes permiso para acceder a esta página.")
        st.stop()

def render_login_form():
    """
    Muestra el formulario de login y maneja la autenticación con Supabase.
    """
    st.title("Acceso al Sistema de Gestión")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Acceder"):
            if not email or not password:
                st.error("Por favor, rellena todos los campos.")
                return

            try:
                supabase = get_supabase()
                session = supabase.auth.sign_in_with_password({"email": email, "password": password})

                if session.user:
                    user_id = session.user.id
                    # Obtener perfil del usuario
                    response = supabase.table('profiles').select('role, delegacion').eq('user_id', user_id).single().execute()
                    profile = response.data or {}

                    st.session_state.user_info = {
                        "email": email,
                        "role": profile.get('role', 'Lector'),
                        "delegacion": profile.get('delegacion')
                    }
                    st.toast(f"¡Bienvenido de nuevo, {email}!")
                    st.rerun()
                else:
                    st.error("Error en la autenticación.")
            except Exception as e:
                # El error de Supabase suele ser descriptivo, pero mostramos uno genérico por seguridad
                st.error("Error: Email o contraseña incorrectos.")
                print(f"Error login: {e}")

def logout():
    """
    Cierra la sesión del usuario.
    """
    st.session_state.clear()
    st.rerun()
