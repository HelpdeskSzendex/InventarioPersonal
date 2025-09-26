# pages/1_Dashboard.py
import streamlit as st
import pandas as pd
from supabase import create_client, Client

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
st.title("📊 Dashboard de Personal")

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

st.markdown("Visión general del personal activo en la empresa.")

@st.cache_data(ttl=600) # Cache por 10 minutos
def fetch_all_data():
    mensajeros_res = supabase.table("mensajeros").select("delegacion, perfil_mensajero").eq("estado", "Activo").execute()
    oficina_res = supabase.table("oficina").select("delegacion").eq("estado", "Activo").execute()
    return pd.DataFrame(mensajeros_res.data), pd.DataFrame(oficina_res.data)

df_mensajeros, df_oficina = fetch_all_data()

# --- MÉTRICAS PRINCIPALES ---
col1, col2, col3 = st.columns(3)
col1.metric("Total Mensajeros Activos", f"{len(df_mensajeros)} 🚚")
col2.metric("Total Personal de Oficina", f"{len(df_oficina)} 💼")
col3.metric("Total Empleados", f"{len(df_mensajeros) + len(df_oficina)} 👥")

st.markdown("---")

# --- GRÁFICOS ---
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Personal por Delegación")
    if not df_mensajeros.empty or not df_oficina.empty:
        personal_total = pd.concat([df_mensajeros[['delegacion']], df_oficina[['delegacion']]])
        conteo_delegacion = personal_total['delegacion'].value_counts()
        st.bar_chart(conteo_delegacion)

with col_b:
    st.subheader("Perfiles de Mensajeros")
    if not df_mensajeros.empty:
        conteo_perfil = df_mensajeros['perfil_mensajero'].value_counts()
        st.bar_chart(conteo_perfil)