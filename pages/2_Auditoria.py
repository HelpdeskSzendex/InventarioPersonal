# pages/2_Auditoria.py
import streamlit as st
import pandas as pd
from app_logic.db import get_supabase
from app_logic.auth import check_role, render_sidebar
from app_logic.styles import apply_custom_styles

st.set_page_config(page_title="Auditoría de Cambios", page_icon="🔍", layout="wide")
apply_custom_styles()
render_sidebar()

# --- COMPROBACIÓN DE ROL ---
check_role(["Admin"])

st.markdown('<p class="main-header">🔍 Auditoría Detallada de Cambios</p>', unsafe_allow_html=True)

@st.cache_data(ttl=60)
def fetch_logs():
    supabase = get_supabase()
    response = supabase.table('log_eventos').select("*").order("timestamp", desc=True).execute()
    return pd.DataFrame(response.data)

if st.button("Refrescar Logs ♻️"):
    st.cache_data.clear()
    st.rerun()

with st.spinner("Cargando historial..."):
    df_logs = fetch_logs()

if df_logs.empty:
    st.info("No hay registros de actividad.")
else:
    # Filtros
    col1, col2 = st.columns(2)
    acc_filter = col1.multiselect("Filtrar por Acción", options=df_logs['accion'].unique(), default=df_logs['accion'].unique())
    user_filter = col2.text_input("Filtrar por Usuario (email)")

    df_f = df_logs[df_logs['accion'].isin(acc_filter)]
    if user_filter:
        df_f = df_f[df_f['usuario_email'].str.contains(user_filter, case=False, na=False)]

    st.dataframe(
        df_f,
        column_config={
            "id": None,
            "timestamp": st.column_config.DatetimeColumn("Fecha/Hora", format="YYYY-MM-DD HH:mm"),
            "usuario_email": "Usuario",
            "accion": "Acción",
            "delegacion": "Deleg.",
            "descripcion": st.column_config.TextColumn("Descripción/Cambios", width="large"),
            "motivo": "Motivo (Bajas)"
        },
        use_container_width=True,
        hide_index=True
    )
