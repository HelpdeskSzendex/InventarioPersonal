# pages/1_Dashboard.py
import streamlit as st
import pandas as pd
from utils.db import get_supabase
from utils.auth import check_role, render_sidebar
from utils.styles import apply_custom_styles

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
apply_custom_styles()
render_sidebar()

# --- COMPROBACIÓN DE ROL ---
check_role(["Admin", "Editor", "Lector"])

st.markdown('<p class="main-header">📊 Dashboard de Personal</p>', unsafe_allow_html=True)

if st.button("Refrescar Datos ♻️", use_container_width=True):
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
st.markdown('<p class="sub-header">Métricas Principales</p>', unsafe_allow_html=True)

# Cálculos adicionales
total_mensajeros = len(df_mensajeros)
total_oficina = len(df_oficina)
total_plantilla = total_mensajeros + total_oficina

# Cumplimiento ADR
adr_rate = (total_adr / total_mensajeros * 100) if total_mensajeros > 0 else 0

# Promedio mensajeros por delegación (asumiendo delegaciones activas en los datos)
num_delegaciones = df_mensajeros['delegacion'].nunique() if not df_mensajeros.empty else 1
avg_mensajeros = total_mensajeros / num_delegaciones if num_delegaciones > 0 else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Mensajeros", f"{total_mensajeros} 🚚")
col2.metric("Total Oficina", f"{total_oficina} 💼")
col3.metric("Total Plantilla", f"{total_plantilla} 👥")
col4.metric("Tasa ADR", f"{adr_rate:.1f}% ☢️", help="Porcentaje de mensajeros con ADR")

st.markdown("---")
# Segunda fila de métricas
col5, col6, col7, col8 = st.columns(4)
with col5:
    st.metric("Promedio Mens./Delegación", f"{avg_mensajeros:.1f}")
with col6:
    total_rotulados = df_mensajeros[df_mensajeros['vehiculo_rotulado'] == 'Si'].shape[0] if not df_mensajeros.empty else 0
    st.metric("Total Rotulados", f"{total_rotulados} ✅")
with col7:
    total_sin_rotular = df_mensajeros[df_mensajeros['vehiculo_rotulado'] == 'No'].shape[0] if not df_mensajeros.empty else 0
    st.metric("Total Sin Rotular", f"{total_sin_rotular} ❌")
with col8:
    total_pendientes = df_mensajeros[df_mensajeros['vehiculo_rotulado'] == 'Pendiente de rotular'].shape[0] if not df_mensajeros.empty else 0
    st.metric("Total Pendientes", f"{total_pendientes} ⏳")

st.markdown("---")

# --- 2. GRÁFICOS GENERALES ---
st.markdown('<p class="sub-header">Distribución de Personal</p>', unsafe_allow_html=True)

col_a, col_b = st.columns(2)
with col_a:
    st.markdown("**Personal por Delegación**")
    if not df_mensajeros.empty or not df_oficina.empty:
        personal_total = pd.concat([df_mensajeros[['delegacion']], df_oficina[['delegacion']]])
        conteo_delegacion = personal_total['delegacion'].value_counts()
        st.bar_chart(conteo_delegacion)
with col_b:
    st.markdown("**Perfiles de Mensajeros**")
    if not df_mensajeros.empty:
        conteo_perfil = df_mensajeros['perfil_mensajero'].value_counts()
        st.bar_chart(conteo_perfil)

st.markdown("---") 

# --- 3. SECCIÓN DE ESTADO DE VEHÍCULOS ---
st.markdown('<p class="sub-header">🚚 Estado de Rotulación de Vehículos</p>', unsafe_allow_html=True)

if not df_mensajeros.empty:
    conteo_estados = df_mensajeros['vehiculo_rotulado'].value_counts()
    total_rotulados = conteo_estados.get('Si', 0)
    total_sin_rotular = conteo_estados.get('No', 0)
    total_pendientes = conteo_estados.get('Pendiente de rotular', 0)

    col_r1, col_r2, col_r3 = st.columns(3)
    col_r1.metric("✅ Total Rotulados", total_rotulados)
    col_r2.metric("❌ Total Sin Rotular", total_sin_rotular)
    col_r3.metric("⏳ Total Pendientes", total_pendientes)

    st.markdown("**Estado de Rotulación por Delegación**")
    # Crear un DataFrame para la gráfica agrupada
    df_rot_deleg = df_mensajeros.groupby(['delegacion', 'vehiculo_rotulado']).size().reset_index(name='count')
    st.bar_chart(df_rot_deleg, x='delegacion', y='count', color='vehiculo_rotulado', stack=False)
else:
    st.info("No hay datos de mensajeros.")

st.markdown("---")

# --- 4. LISTADO DE PERSONAS CON ADR ---
if total_adr > 0:
    st.markdown('<p class="sub-header">☢️ Listado de Personal con ADR</p>', unsafe_allow_html=True)
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
