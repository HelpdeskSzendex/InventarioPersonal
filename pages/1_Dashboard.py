# pages/1_Dashboard.py
import streamlit as st
import pandas as pd
import sqlite3

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
st.title("📊 Dashboard de Personal")
st.markdown("Visión general del personal activo en la empresa.")

@st.cache_data
def fetch_all_data():
    conn = sqlite3.connect('mensajeros.db')
    df_mensajeros = pd.read_sql_query("SELECT * FROM mensajeros WHERE estado = 'Activo'", conn)
    df_oficina = pd.read_sql_query("SELECT * FROM oficina WHERE estado = 'Activo'", conn)
    conn.close()
    return df_mensajeros, df_oficina

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
    # Unir ambos dataframes para un conteo total
    personal_total = pd.concat([df_mensajeros[['delegacion']], df_oficina[['delegacion']]])
    conteo_delegacion = personal_total['delegacion'].value_counts()
    st.bar_chart(conteo_delegacion)

with col_b:
    st.subheader("Perfiles de Mensajeros")
    if not df_mensajeros.empty:
        conteo_perfil = df_mensajeros['perfil_mensajero'].value_counts()
        st.bar_chart(conteo_perfil)
    else:
        st.info("No hay datos de mensajeros para mostrar.")