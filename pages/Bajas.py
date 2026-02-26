# pages/Bajas.py
import streamlit as st
import pandas as pd
from supabase import create_client, Client

st.set_page_config(page_title="Registro de Bajas", page_icon="➖", layout="wide")
st.title("➖ Registro Histórico de Bajas")

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
def fetch_bajas():
    """Obtiene solo los eventos de BAJA de la tabla de registros."""
    # select(*) ya incluirá la nueva columna 'motivo'
    response = supabase.table('log_eventos').select("*").eq('accion', 'BAJA').order("timestamp", desc=True).execute()
    return pd.DataFrame(response.data)

if st.button("Refrescar Registros ♻️"):
    st.cache_data.clear()

df_bajas = fetch_bajas()

if df_bajas.empty:
    st.info("Aún no se ha registrado ninguna baja.")
else:
    filtro_usuario = st.text_input("Filtrar por email del usuario que realizó la baja:")
    
    df_filtrado = df_bajas
    if filtro_usuario:
        df_filtrado = df_filtrado[df_filtrado['usuario_email'].str.contains(filtro_usuario, case=False, na=False)]

    st.dataframe(
        df_filtrado,
        column_config={
            "id": None, # Oculta la columna ID
            "timestamp": st.column_config.DatetimeColumn("Fecha y Hora", format="YYYY-MM-DD HH:mm"),
            "usuario_email": "Usuario Responsable",
            "accion": None, # Ocultamos la acción porque ya sabemos que es "BAJA"
            "delegacion": "Delegación",
            "descripcion": "Descripción",
            "motivo": "Motivo de la Baja"  # --- MODIFICADO: Se añade la columna motivo ---
        },
        use_container_width=True,
        hide_index=True
    )