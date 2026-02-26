# utils/auth.py
import streamlit as st
import os
from utils.db import get_supabase
from utils.styles import apply_custom_styles

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
    Muestra el formulario de login profesional y maneja la autenticación con Supabase.
    """
    # Ocultar sidebar en el login
    apply_custom_styles(show_sidebar=False)

    # Centrado usando columnas
    _, col, _ = st.columns([1, 2, 1])

    with col:
        st.markdown("<br><br>", unsafe_allow_html=True) # Espacio arriba

        # Simulamos una card usando un contenedor con borde (Streamlit 1.30+)
        with st.container(border=True):
            if os.path.exists("assets/banner.png"):
                st.image("assets/banner.png", use_container_width=True)
            else:
                st.markdown("<h2 style='color:#1e3a8a; text-align:center;'>SZENDEX</h2>", unsafe_allow_html=True)

            st.markdown("<p style='color:#6b7280; text-align:center; margin-bottom:24px;'>Gestión de Personal - Iniciar Sesión</p>", unsafe_allow_html=True)

            with st.form("login_form", border=False):
                email = st.text_input("Correo electrónico", placeholder="usuario@ejemplo.com")
                password = st.text_input("Contraseña", type="password", placeholder="••••••••")
                submit = st.form_submit_button("Entrar", type="primary", use_container_width=True)

                if submit:
                    if not email or not password:
                        st.error("Rellena todos los campos")
                    else:
                        try:
                            supabase = get_supabase()
                            session = supabase.auth.sign_in_with_password({"email": email, "password": password})

                            if session.user:
                                user_id = session.user.id
                                response = supabase.table('profiles').select('role, delegacion').eq('user_id', user_id).single().execute()
                                profile = response.data or {}

                                st.session_state.user_info = {
                                    "email": email,
                                    "role": profile.get('role', 'Lector'),
                                    "delegacion": profile.get('delegacion')
                                }
                                st.success("Acceso concedido")
                                st.rerun()
                            else:
                                st.error("Acceso denegado")
                        except Exception:
                            st.error("Credenciales inválidas")

def logout():
    """
    Cierra la sesión del usuario.
    """
    st.session_state.clear()
    st.rerun()

def render_sidebar():
    """
    Renderiza la barra lateral con información del usuario y botón de cerrar sesión.
    """
    user_info = st.session_state.get("user_info")
    if not user_info:
        return

    role = user_info.get("role", "Lector")
    deleg = user_info.get("delegacion")

    with st.sidebar:
        if os.path.exists("assets/banner.png"):
            st.image("assets/banner.png", use_container_width=True)
            st.markdown("---")

        st.markdown(f"""
            <div class="sidebar-user-box">
                <p style="margin:0; font-size:0.8rem; color:#6b7280;">Sesión activa</p>
                <p style="margin:0; font-weight:600; color:#1e3a8a; word-break: break-all;">{user_info.get('email')}</p>
                <p style="margin:8px 0 0 0; font-size:0.8rem; color:#6b7280;">Rol</p>
                <p style="margin:0; font-weight:500;">{role}</p>
                {f'<p style="margin:8px 0 0 0; font-size:0.8rem; color:#6b7280;">Delegación</p><p style="margin:0; font-weight:500;">{deleg}</p>' if deleg else ''}
            </div>
        """, unsafe_allow_html=True)

        if st.button("Cerrar Sesión", use_container_width=True, key="logout_btn"):
            logout()
