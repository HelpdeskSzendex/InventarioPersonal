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

if st.button("Refrescar Datos ♻️"):
    st.cache_data.clear()
    st.success("Datos actualizados.")

st.markdown("Visión general del personal activo en la empresa.")

@st.cache_data(ttl=600)
def fetch_all_data():
    mensajeros_res = supabase.table("mensajeros").select("delegacion, perfil_mensajero, vehiculo_rotulado, ADR, nombre_apellido").eq("estado", "Activo").execute()
    oficina_res = supabase.table("oficina").select("delegacion").eq("estado", "Activo").execute()
    return pd.DataFrame(mensajeros_res.data), pd.DataFrame(oficina_res.data)

df_mensajeros, df_oficina = fetch_all_data()

# Calcular Total ADR
total_adr = 0
if not df_mensajeros.empty and 'ADR' in df_mensajeros.columns:
    # Asegurar tipo booleano
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
    # Contadores totales
    conteo_estados = df_mensajeros['vehiculo_rotulado'].value_counts()
    total_rotulados = conteo_estados.get('Si', 0)
    total_sin_rotular = conteo_estados.get('No', 0)
    total_pendientes = conteo_estados.get('Pendiente de rotular', 0)

    col_r1, col_r2, col_r3 = st.columns(3)
    col_r1.metric("✅ Total Rotulados", total_rotulados)
    col_r2.metric("❌ Total Sin Rotular", total_sin_rotular)
    col_r3.metric("⏳ Total Pendientes", total_pendientes, help="Vehículos cuya rotulación ha sido aceptada pero aún no se ha completado.")

    # Gráfica detallada por delegación
    st.markdown("#### Detalle de Rotulados por Delegación")
    df_rotulados = df_mensajeros[df_mensajeros['vehiculo_rotulado'] == 'Si']
    if not df_rotulados.empty:
        conteo_rotulados_delegacion = df_rotulados['delegacion'].value_counts()
        st.bar_chart(conteo_rotulados_delegacion)
    else:
        st.info("No hay vehículos registrados como 'Si' rotulados para mostrar en la gráfica.")
else:
    st.info("No hay datos de mensajeros para mostrar el estado de los vehículos.")

st.markdown("---")

# --- 4. NUEVA SECCIÓN: LISTADO DE PERSONAS CON ADR (MOVIDO AQUÍ ABAJO) ---
if total_adr > 0:
    st.subheader("☢️ Listado de Personal con ADR")
    
    # Filtramos solo los que tienen ADR
    df_adr_list = df_mensajeros[df_mensajeros['ADR'] == True][['nombre_apellido', 'delegacion', 'perfil_mensajero']]
    
    # Mostramos la tabla limpia
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