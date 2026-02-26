# pages/Altas.py
import streamlit as st
import pandas as pd
from utils.db import get_supabase
from utils.auth import check_role

st.set_page_config(page_title="Registro de Altas", page_icon="➕", layout="wide")
st.title("➕ Registro Histórico de Altas")

# --- COMPROBACIÓN DE ROL ---
check_role(["Admin"])

# --- FUNCIÓN PARA OBTENER DATOS ---
@st.cache_data(ttl=60)
def fetch_altas():
    """Obtiene solo los eventos de ALTA de la tabla de registros."""
    supabase = get_supabase()
    response = supabase.table('log_eventos').select("*").eq('accion', 'ALTA').order("timestamp", desc=True).execute()
    return pd.DataFrame(response.data)

if st.button("Refrescar Registros ♻️"):
    st.cache_data.clear()
    st.toast("Registros actualizados.")

with st.spinner("Cargando historial de altas..."):
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
            "timestamp": st.column_config.DatetimeColumn("Fecha y Hora", format="YYYY-MM-DD HH:mm"),
            "usuario_email": "Usuario Responsable",
            "accion": None,
            "delegacion": "Delegación Afectada",
            "descripcion": "Descripción"
        },
        use_container_width=True,
        hide_index=True
    )
