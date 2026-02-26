# pages/1_Dashboard.py
import streamlit as st
import pandas as pd
from utils.db import get_supabase, DELEGACIONES
from utils.auth import check_auth, render_sidebar

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
st.title("📊 Dashboard de Personal")

# --- COMPROBACIÓN DE AUTENTICACIÓN Y ROL ---
if not check_auth(required_role="Admin"):
    st.stop()

render_sidebar()

if st.button("Refrescar Datos ♻️"):
    st.cache_data.clear()
    st.success("Datos actualizados.")

st.markdown("Visión general del personal activo en la empresa.")

# --- FILTROS ---
delegaciones_seleccionadas = st.multiselect("Filtrar por Delegación", DELEGACIONES, default=DELEGACIONES)

@st.cache_data(ttl=600)
def fetch_all_data():
    supabase = get_supabase()
    mensajeros_res = supabase.table("mensajeros").select("delegacion, perfil_mensajero, vehiculo_rotulado").eq("estado", "Activo").execute()
    oficina_res = supabase.table("oficina").select("delegacion").eq("estado", "Activo").execute()
    return pd.DataFrame(mensajeros_res.data), pd.DataFrame(oficina_res.data)

df_mensajeros, df_oficina = fetch_all_data()

# Filtrar por delegación
if delegaciones_seleccionadas:
    df_mensajeros = df_mensajeros[df_mensajeros['delegacion'].isin(delegaciones_seleccionadas)]
    df_oficina = df_oficina[df_oficina['delegacion'].isin(delegaciones_seleccionadas)]

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

st.markdown("---") 

# --- SECCIÓN DE ESTADO DE VEHÍCULOS ---
st.subheader("🚚 Estado de Rotulación de Vehículos")

if not df_mensajeros.empty:
    # 1. Contadores totales
    conteo_estados = df_mensajeros['vehiculo_rotulado'].value_counts()
    total_rotulados = conteo_estados.get('Si', 0)
    total_sin_rotular = conteo_estados.get('No', 0)
    total_pendientes = conteo_estados.get('Pendiente de rotular', 0)

    col_r1, col_r2, col_r3 = st.columns(3)
    col_r1.metric("✅ Total Rotulados", total_rotulados)
    col_r2.metric("❌ Total Sin Rotular", total_sin_rotular)
    col_r3.metric("⏳ Total Pendientes", total_pendientes, help="Vehículos cuya rotulación ha sido aceptada pero aún no se ha completado.")

    # 2. Gráfica detallada por delegación
    st.markdown("#### Detalle de Rotulados por Delegación")
    df_rotulados = df_mensajeros[df_mensajeros['vehiculo_rotulado'] == 'Si']
    if not df_rotulados.empty:
        conteo_rotulados_delegacion = df_rotulados['delegacion'].value_counts()
        st.bar_chart(conteo_rotulados_delegacion)
    else:
        st.info("No hay vehículos registrados como 'Si' rotulados para mostrar en la gráfica.")
else:
    st.info("No hay datos de mensajeros para mostrar el estado de los vehículos.")
