# pages/Bajas.py
import streamlit as st
import pandas as pd
import sqlite3

st.set_page_config(page_title="Registro de Bajas", page_icon="📋", layout="wide")
st.title("📋 Registro Histórico de Bajas")

def connect_db():
    return sqlite3.connect('mensajeros.db')

def fetch_all_bajas():
    """Obtiene y une las bajas de ambas tablas."""
    conn = connect_db()
    # Esta consulta une los resultados de ambas tablas en una sola
    query = """
    SELECT delegacion, nombre_apellido, 'Mensajero' as tipo
    FROM mensajeros
    WHERE estado = 'Baja'
    UNION ALL
    SELECT delegacion, nombre_apellido, 'Oficina' as tipo
    FROM oficina
    WHERE estado = 'Baja'
    ORDER BY delegacion, nombre_apellido
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

df_bajas = fetch_all_bajas()

if df_bajas.empty:
    st.info("Aún no se ha registrado ninguna baja.")
else:
    st.dataframe(df_bajas, use_container_width=True, hide_index=True)