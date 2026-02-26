# pages/Altas.py
import streamlit as st
import pandas as pd
from supabase import create_client, Client

st.set_page_config(page_title="Registro de Altas", page_icon="➕", layout="wide")
st.title("➕ Registro Histórico de Altas")

# --- CONEXIÓN A SUPABASE ---
@st.cache_resource
def init_supabase_client():
    try:
        url, key = st.secrets["supabase_url"], st.secrets["supabase_key"]
        return create_client(url, key)
    except Exception:
        st.error("No se pudo conectar a Supabase. Revisa tus credenciales.")
        st.stop()

supabase: Client = init_supabase_client()

# --- COMPROBACIÓN DE ROL ---
user_role = st.session_state.get("user_info", {}).get("role")
if user_role != "Admin":
    st.error("No tienes permiso para acceder a esta página.")
    st.stop()

# --- FUNCIÓN PARA OBTENER DATOS ---
@st.cache_data(ttl=60)
def fetch_altas():
    """Obtiene solo los eventos de ALTA de la tabla de registros."""
    response = supabase.table('log_eventos').select("*").eq('accion', 'ALTA').order("timestamp", desc=True).execute()
    return pd.DataFrame(response.data)

if st.button("Refrescar Registros ♻️"):
    st.cache_data.clear()

df_altas = fetch_altas()

if df_altas.empty:
    st.info("Aún no se ha registrado ninguna alta.")
else:
    filtro_usuario = st.text_input("Filtrar por email del usuario que realizó el alta:")
    
    df_filtrado = df_altas
    if filtro_usuario:
        df_filtrado = df_filtrado[df_filtrado['usuario_email'].str.contains(filtro_usuario, case=False)]
    
    st.dataframe(
        df_filtrado,
        column_config={
            "id": None,
            "timestamp": "Fecha y Hora",
            "usuario_email": "Usuario Responsable",
            "accion": "Acción",
            "delegacion": "Delegación Afectada", # <-- Columna añadida
            "descripcion": "Descripción"
        },
        use_container_width=True,
        hide_index=True
    )