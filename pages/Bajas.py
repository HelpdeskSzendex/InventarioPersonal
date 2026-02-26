# pages/Bajas.py
import streamlit as st
import pandas as pd
from utils.db import get_supabase
from utils.auth import check_role, render_sidebar
from utils.styles import apply_custom_styles

st.set_page_config(page_title="Registro de Bajas", page_icon="➖", layout="wide")
apply_custom_styles()
render_sidebar()

# --- COMPROBACIÓN DE ROL ---
check_role(["Admin"])

st.markdown('<p class="main-header">➖ Registro Histórico de Bajas</p>', unsafe_allow_html=True)

# --- FUNCIÓN PARA OBTENER DATOS ---
@st.cache_data(ttl=60)
def fetch_bajas():
    """Obtiene solo los eventos de BAJA de la tabla de registros."""
    supabase = get_supabase()
    response = supabase.table('log_eventos').select("*").eq('accion', 'BAJA').order("timestamp", desc=True).execute()
    return pd.DataFrame(response.data)

if st.button("Refrescar Registros ♻️"):
    st.cache_data.clear()
    st.toast("Registros actualizados.")

with st.spinner("Cargando historial de bajas..."):
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
            "id": None,
            "timestamp": st.column_config.DatetimeColumn("Fecha y Hora", format="YYYY-MM-DD HH:mm"),
            "usuario_email": "Usuario Responsable",
            "accion": None,
            "delegacion": "Delegación",
            "descripcion": "Descripción",
            "motivo": "Motivo de la Baja"
        },
        use_container_width=True,
        hide_index=True
    )
