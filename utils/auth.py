import streamlit as st
from utils.db import get_supabase

def check_auth(required_role=None):
    """
    Checks if the user is authenticated and has the required role.
    If not authenticated, it will show the login form (or redirect to the home page if needed).
    """
    if "user_info" not in st.session_state:
        return False

    if required_role:
        if isinstance(required_role, list):
            if st.session_state.user_info.get("role") not in required_role:
                st.error("No tienes permiso para acceder a esta página.")
                st.stop()
        elif st.session_state.user_info.get("role") != required_role:
            st.error("No tienes permiso para acceder a esta página.")
            st.stop()

    return True

def login(email, password):
    supabase = get_supabase()
    try:
        session = supabase.auth.sign_in_with_password({"email": email, "password": password})
        user_id = session.user.id
        # Note: 'profiles' table should exist with user_id, role, delegacion
        response = supabase.table('profiles').select('role, delegacion').eq('user_id', user_id).single().execute()
        profile = response.data or {}
        st.session_state.user_info = {
            "email": email,
            "role": profile.get('role', 'Lector'),
            "delegacion": profile.get('delegacion')
        }
        return True
    except Exception as e:
        st.error(f"Error de autenticación: {e}")
        return False

def logout():
    st.session_state.clear()
    st.rerun()

def render_sidebar():
    if "user_info" in st.session_state:
        user_role = st.session_state.user_info.get("role", "Lector")
        user_delegacion = st.session_state.user_info.get("delegacion")

        st.sidebar.success(f"Sesión iniciada")
        st.sidebar.info(f"Rol: **{user_role}**")
        if user_delegacion:
            st.sidebar.write(f"Delegación: **{user_delegacion}**")

        if st.sidebar.button("Cerrar Sesión", use_container_width=True):
            logout()
    else:
        st.sidebar.warning("No has iniciado sesión.")
