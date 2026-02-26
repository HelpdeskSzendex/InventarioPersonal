# pages/Bajas.py
import streamlit as st
import pandas as pd
from utils.db import get_supabase
from utils.auth import check_auth, render_sidebar

st.set_page_config(page_title="Registro de Bajas", page_icon="📋", layout="wide")
st.title("📋 Registro Histórico de Bajas")

# --- COMPROBACIÓN DE AUTENTICACIÓN Y ROL ---
if not check_auth(required_role="Admin"):
    st.stop()

render_sidebar()

# --- FUNCIÓN PARA OBTENER DATOS ---
@st.cache_data(ttl=300)
def fetch_all_bajas():
    """Obtiene y une las bajas de ambas tablas desde Supabase."""
    supabase = get_supabase()
    
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
    search_query = st.text_input("Buscar por nombre", key="search_bajas")
    if search_query:
        df_bajas = df_bajas[df_bajas["nombre_apellido"].str.contains(search_query, case=False, na=False)]

    st.dataframe(df_bajas, use_container_width=True, hide_index=True)
