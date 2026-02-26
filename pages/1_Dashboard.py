# pages/1_Dashboard.py
import streamlit as st
import pandas as pd
from utils.db import get_supabase
from utils.auth import check_role

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
st.title("📊 Dashboard de Personal")

# --- COMPROBACIÓN DE ROL ---
check_role(["Admin"])

if st.button("Refrescar Datos ♻️"):
    st.cache_data.clear()
    st.toast("Datos actualizados.", icon="✅")

st.markdown("Visión general del personal activo en la empresa.")

@st.cache_data(ttl=600)
def fetch_dashboard_data():
    supabase = get_supabase()
    mensajeros_res = supabase.table("mensajeros").select("delegacion, perfil_mensajero, vehiculo_rotulado, ADR, nombre_apellido").eq("estado", "Activo").execute()
    oficina_res = supabase.table("oficina").select("delegacion").eq("estado", "Activo").execute()
    return pd.DataFrame(mensajeros_res.data), pd.DataFrame(oficina_res.data)

with st.spinner("Cargando métricas..."):
    df_mensajeros, df_oficina = fetch_dashboard_data()

# Calcular Total ADR
total_adr = 0
if not df_mensajeros.empty and 'ADR' in df_mensajeros.columns:
    df_mensajeros['ADR'] = df_mensajeros['ADR'].fillna(False).astype(bool)
    total_adr = df_mensajeros[df_mensajeros['ADR'] == True].shape[0]

# --- 1. MÉTRICAS PRINCIPALES ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Mensajeros", f"{len(df_mensajeros)} 🚚")
col2.metric("Total Oficina", f"{len(df_oficina)} 💼")
col3.metric("Total Plantilla", f"{len(df_mensajeros) + len(df_oficina)} 👥")
col4.metric("Con Certificado ADR", f"{total_adr} ☢️", help="Mensajeros activos con casilla ADR marcada")

st.markdown("---")

# --- 2. GRÁFICOS GENERALES ---
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

# --- 3. SECCIÓN DE ESTADO DE VEHÍCULOS ---
st.subheader("🚚 Estado de Rotulación de Vehículos")

if not df_mensajeros.empty:
    conteo_estados = df_mensajeros['vehiculo_rotulado'].value_counts()
    total_rotulados = conteo_estados.get('Si', 0)
    total_sin_rotular = conteo_estados.get('No', 0)
    total_pendientes = conteo_estados.get('Pendiente de rotular', 0)

    col_r1, col_r2, col_r3 = st.columns(3)
    col_r1.metric("✅ Total Rotulados", total_rotulados)
    col_r2.metric("❌ Total Sin Rotular", total_sin_rotular)
    col_r3.metric("⏳ Total Pendientes", total_pendientes)

    st.markdown("#### Detalle de Rotulados por Delegación")
    df_rotulados = df_mensajeros[df_mensajeros['vehiculo_rotulado'] == 'Si']
    if not df_rotulados.empty:
        st.bar_chart(df_rotulados['delegacion'].value_counts())
    else:
        st.info("No hay vehículos rotulados para mostrar.")
else:
    st.info("No hay datos de mensajeros.")

st.markdown("---")

# --- 4. LISTADO DE PERSONAS CON ADR ---
if total_adr > 0:
    st.subheader("☢️ Listado de Personal con ADR")
    df_adr_list = df_mensajeros[df_mensajeros['ADR'] == True][['nombre_apellido', 'delegacion', 'perfil_mensajero']]
    st.dataframe(
        df_adr_list,
        use_container_width=True,
        hide_index=True,
        column_config={
            "nombre_apellido": "Nombre del Mensajero",
            "delegacion": "Delegación",
            "perfil_mensajero": "Perfil"
        }
    )
