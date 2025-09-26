# pages/Bajas.py
import streamlit as st
import pandas as pd
from supabase import create_client, Client

st.set_page_config(page_title="Registro de Bajas", page_icon="📋", layout="wide")
st.title("📋 Registro Histórico de Bajas")

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
# Asegurarse de que el usuario ha iniciado sesión y tiene el rol correcto
user_role = st.session_state.get("user_info", {}).get("role")
if user_role != "Admin":
    st.error("No tienes permiso para acceder a esta página.")
    st.stop() # Detiene la ejecución si no es Admin

# --- FUNCIÓN PARA OBTENER DATOS ---
@st.cache_data(ttl=300) # La caché se refresca cada 5 minutos
def fetch_all_bajas():
    """Obtiene y une las bajas de ambas tablas desde Supabase."""
    
    # 1. Obtener bajas de mensajeros
    res_mensajeros = supabase.table("mensajeros").select("delegacion, nombre_apellido, fecha_baja").eq("estado", "Baja").execute()
    df_mensajeros = pd.DataFrame(res_mensajeros.data).assign(tipo="Mensajero")

    # 2. Obtener bajas de oficina
    res_oficina = supabase.table("oficina").select("delegacion, nombre_apellido, fecha_baja").eq("estado", "Baja").execute()
    df_oficina = pd.DataFrame(res_oficina.data).assign(tipo="Oficina")

    # 3. Unir ambos resultados y ordenar
    df_bajas_total = pd.concat([df_mensajeros, df_oficina]).sort_values("fecha_baja", ascending=False)
    
    return df_bajas_total

# --- MOSTRAR LA TABLA ---
df_bajas = fetch_all_bajas()

if df_bajas.empty:
    st.info("Aún no se ha registrado ninguna baja.")
else:
    st.dataframe(df_bajas, use_container_width=True, hide_index=True)