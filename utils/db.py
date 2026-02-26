import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import date

def init_supabase_client() -> Client:
    try:
        url = st.secrets["supabase_url"]
        key = st.secrets["supabase_key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Error al conectar con Supabase: {e}")
        st.stop()

def init_supabase_admin_client() -> Client:
    try:
        url = st.secrets["supabase_url"]
        service_key = st.secrets["supabase_service_key"]
        return create_client(url, service_key)
    except Exception as e:
        st.error(f"Error al conectar con Supabase (Admin): {e}")
        st.stop()

# Get clients (cached)
@st.cache_resource
def get_supabase():
    return init_supabase_client()

@st.cache_resource
def get_supabase_admin():
    return init_supabase_admin_client()

DELEGACIONES = ['Granollers', 'Sabadell', 'Zona Franca', 'Manresa', 'Girona', 'Vilafranca']

def fetch_data(table, delegacion):
    supabase = get_supabase()
    try:
        response = supabase.table(table).select("*").eq('delegacion', delegacion).eq('estado', 'Activo').order('nombre_apellido').execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Error al obtener datos: {e}")
        return pd.DataFrame()

def fetch_single_record(table_name, record_id):
    supabase = get_supabase()
    try:
        response = supabase.table(table_name).select("*").eq('id', int(record_id)).single().execute()
        return response.data if response.data else None
    except Exception as e:
        st.error(f"Error al obtener registro: {e}")
        return None

def update_record(table, record_id, data):
    supabase = get_supabase()
    try:
        supabase.table(table).update(data).eq('id', record_id).execute()
    except Exception as e:
        st.error(f"Error al actualizar registro: {e}")

def add_record_and_get_id(table, data):
    supabase = get_supabase()
    try:
        response = supabase.table(table).insert(data, returning="representation").execute()
        return response.data[0]['id'] if response.data else None
    except Exception as e:
        st.error(f"Error al añadir registro: {e}")
        return None

def dar_de_baja(table, record_id):
    supabase = get_supabase()
    try:
        supabase.table(table).update({"estado": "Baja", "fecha_baja": date.today().isoformat()}).eq('id', record_id).execute()
    except Exception as e:
        st.error(f"Error al dar de baja: {e}")

def update_file_path(table, record_id, column_name, filename):
    supabase = get_supabase()
    try:
        supabase.table(table).update({column_name: filename}).eq('id', record_id).execute()
    except Exception as e:
        st.error(f"Error al actualizar ruta de archivo: {e}")
