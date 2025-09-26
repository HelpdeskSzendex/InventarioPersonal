# pages/Admin.py
import streamlit as st
import pandas as pd  # <--- ESTA ES LA LÍNEA QUE FALTABA
from supabase import create_client, Client
from passlib.context import CryptContext

# --- CONFIGURACIÓN Y CONEXIÓN ---
st.set_page_config(page_title="Panel de Administración", page_icon="🔑", layout="centered")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

try:
    url: str = st.secrets["supabase_url"]
    key: str = st.secrets["supabase_key"]
    supabase: Client = create_client(url, key)
except Exception:
    st.error("No se pudo conectar a Supabase. Revisa tus credenciales.")
    st.stop()

# --- SEGURIDAD DE LA PÁGINA ---
st.title("🔑 Panel de Administración de Usuarios")

# Solo los administradores pueden ver esta página
if st.session_state.get("user_info", {}).get("role") != "Admin":
    st.error("No tienes permiso para acceder a esta página.")
    st.stop()

# --- AÑADIR NUEVO USUARIO ---
st.subheader("Añadir Nuevo Usuario")
with st.form("add_user_form", clear_on_submit=True):
    new_username = st.text_input("Nombre de Usuario")
    new_password = st.text_input("Contraseña", type="password")
    new_role = st.selectbox("Rol", ["Editor", "Lector"])
    
    submitted = st.form_submit_button("Crear Usuario")
    if submitted:
        if new_username and new_password:
            # Encriptar la contraseña antes de guardarla
            hashed_password = pwd_context.hash(new_password)
            
            # Insertar en Supabase
            supabase.table('users').insert({
                "username": new_username,
                "hashed_password": hashed_password,
                "role": new_role
            }).execute()
            st.success(f"¡Usuario '{new_username}' creado con éxito!")
        else:
            st.error("Por favor, rellena todos los campos.")

st.markdown("---")

# --- GESTIONAR USUARIOS EXISTENTES ---
st.subheader("Gestionar Usuarios Existentes")

try:
    response = supabase.table('users').select("id, username, role").execute()
    users_df = pd.DataFrame(response.data)

    if users_df.empty:
        st.info("No hay usuarios para mostrar.")
    else:
        # Usamos columnas para alinear el botón de borrado
        for index, row in users_df.iterrows():
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                st.write(f"**Usuario:** {row['username']}")
            with col2:
                st.write(f"**Rol:** {row['role']}")
            with col3:
                # No se puede borrar al usuario 'admin'
                if row['username'] != 'admin':
                    if st.button("Borrar", key=f"del_{row['id']}", type="primary"):
                        supabase.table('users').delete().eq('id', row['id']).execute()
                        st.rerun()

except Exception as e:
    st.error(f"No se pudieron cargar los usuarios: {e}")