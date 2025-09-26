# pages/Admin.py
import streamlit as st
import pandas as pd
from supabase import create_client, Client

st.set_page_config(page_title="Panel de Administración", page_icon="🔑", layout="wide")
st.title("🔑 Panel de Administración de Usuarios")

# --- CONEXIÓN A SUPABASE CON PERMISOS DE ADMIN ---
@st.cache_resource
def init_supabase_admin_client():
    try:
        url = st.secrets["supabase_url"]
        service_key = st.secrets["supabase_service_key"]
        return create_client(url, service_key)
    except Exception:
        st.error("No se pudo conectar a Supabase. Revisa tus credenciales.")
        st.stop()

supabase_admin: Client = init_supabase_admin_client()

# --- COMPROBACIÓN DE ROL ---
user_role = st.session_state.get("user_info", {}).get("role")
if user_role != "Admin":
    st.error("No tienes permiso para acceder a esta página.")
    st.stop()

# --- AÑADIR NUEVO USUARIO ---
st.subheader("Añadir Nuevo Usuario")
with st.form("add_user_form", clear_on_submit=True):
    email = st.text_input("Email del Nuevo Usuario")
    password = st.text_input("Contraseña", type="password")
    col1, col2 = st.columns(2)
    role = col1.selectbox("Rol", ["Admin", "Editor", "Lector"])
    delegacion = col2.text_input("Delegación (solo para rol 'Lector')")
    
    submitted = st.form_submit_button("Crear Usuario")
    if submitted:
        if email and password:
            try:
                user_response = supabase_admin.auth.admin.create_user({
                    "email": email,
                    "password": password,
                    "email_confirm": True
                })
                new_user_id = user_response.user.id
                
                supabase_admin.table('profiles').insert({
                    "user_id": new_user_id,
                    "role": role,
                    "delegacion": delegacion if role == 'Lector' else None
                }).execute()
                
                st.success(f"¡Usuario '{email}' creado con éxito!")
            except Exception as e:
                st.error(f"Error al crear usuario: {e}")
        else:
            st.error("Email y Contraseña son obligatorios.")

st.markdown("---")

# --- GESTIONAR USUARIOS EXISTENTES ---
st.subheader("Gestionar Usuarios Existentes")
try:
    auth_users_response = supabase_admin.auth.admin.list_users()
    
    # --- LÍNEA CORREGIDA ---
    # La respuesta ya es la lista de usuarios, no un objeto que la contiene.
    auth_users = auth_users_response
    
    profiles_response = supabase_admin.table('profiles').select("user_id, role, delegacion").execute()
    profiles_map = {p['user_id']: p for p in profiles_response.data}

    # El resto del código funciona igual
    for user in auth_users:
        profile = profiles_map.get(user.id, {})
        role = profile.get('role', 'No asignado')
        delegacion = profile.get('delegacion', 'N/A')
        
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            col1.write(f"**Email:** {user.email}")
            col2.write(f"**Rol:** {role}")
            col3.write(f"**Delegación:** {delegacion}")
            
            if user.email != st.session_state.get("user_info", {}).get("email"):
                if col4.button("Borrar", key=f"del_{user.id}", type="primary"):
                    supabase_admin.auth.admin.delete_user(user.id)
                    st.rerun()

except Exception as e:
    st.error(f"No se pudieron cargar los usuarios: {e}")