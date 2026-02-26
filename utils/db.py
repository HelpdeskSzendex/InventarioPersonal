# utils/db.py
import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import date
import os
import re

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- CONSTANTES ---
DELEGACIONES = ['Granollers', 'Sabadell', 'Zona Franca', 'Manresa', 'Girona', 'Vilafranca', 'Sanitario']
PERFIL_OPTS = ["Autónomo", "Empleado", "Asegurado Fijo", "Asegurado a Producción", "Empleado de un Autónomo externo", "Jefe de Autónomos"]
ROTULADO_OPTS = ["Si", "No", "Pendiente de rotular"]
TOTAL_LICENCIAS_DL = 250

@st.cache_resource
def init_supabase_client():
    try:
        url = st.secrets["supabase_url"]
        key = st.secrets["supabase_key"]
        return create_client(url, key)
    except Exception:
        st.error("Error al conectar con Supabase. Revisa tus credenciales en .streamlit/secrets.toml")
        st.stop()

@st.cache_resource
def init_supabase_admin_client():
    try:
        url = st.secrets["supabase_url"]
        service_key = st.secrets["supabase_service_key"]
        return create_client(url, service_key)
    except Exception:
        st.error("Error al conectar con Supabase (Admin). Revisa tus credenciales.")
        st.stop()

def get_supabase():
    return init_supabase_client()

def get_supabase_admin():
    return init_supabase_admin_client()

# --- FUNCIONES CRUD ---

@st.cache_data(ttl=300)
def fetch_data(table, delegacion):
    supabase = get_supabase()
    return pd.DataFrame(supabase.table(table).select("*").eq('delegacion', delegacion).eq('estado', 'Activo').order('nombre_apellido').execute().data)

@st.cache_data(ttl=300)
def fetch_all_messengers():
    supabase = get_supabase()
    return pd.DataFrame(supabase.table('mensajeros').select("*, delegacion").eq('estado', 'Activo').order('nombre_apellido').execute().data)

@st.cache_data(ttl=300)
def fetch_all_office_staff():
    supabase = get_supabase()
    return pd.DataFrame(supabase.table('oficina').select("*, delegacion").eq('estado', 'Activo').order('nombre_apellido').execute().data)

def fetch_single_record(table_name, record_id):
    supabase = get_supabase()
    return supabase.table(table_name).select("*").eq('id', int(record_id)).single().execute().data

def update_record(table, record_id, data):
    supabase = get_supabase()
    res = supabase.table(table).update(data).eq('id', record_id).execute()
    st.cache_data.clear()
    return res

def add_record_and_get_id(table, data, user_email, delegacion_actual):
    supabase = get_supabase()
    response = supabase.table(table).insert(data, returning="representation").execute()
    if response.data:
        new_id = response.data[0]['id']
        log_event(user_email, "ALTA", f"Creó a '{data['nombre_apellido']}' en '{table}'.", delegacion_actual)
        st.cache_data.clear()
        return new_id
    return None

def dar_de_baja(table, record_id, nombre, user_email, delegacion_actual, motivo):
    supabase = get_supabase()
    supabase.table(table).update({"estado": "Baja", "fecha_baja": date.today().isoformat()}).eq('id', record_id).execute()
    descripcion_log = f"Dio de baja a '{nombre}' (ID: {record_id}) de la tabla '{table}'."
    log_event(user_email, "BAJA", descripcion_log, delegacion_actual, motivo=motivo)
    st.cache_data.clear()

def update_file_path(table, record_id, column_name, filename):
    supabase = get_supabase()
    # Si filename es None o lista vacía, guardamos null para limpiar
    val = filename if filename and filename != '[]' else None
    res = supabase.table(table).update({column_name: val}).eq('id', record_id).execute()
    st.cache_data.clear()
    return res

def log_event(usuario_email, accion, descripcion, delegacion, motivo=None):
    supabase = get_supabase()
    try:
        supabase.table('log_eventos').insert({
            "usuario_email": usuario_email,
            "accion": accion,
            "descripcion": descripcion,
            "delegacion": delegacion,
            "motivo": motivo
        }).execute()
        st.cache_data.clear()
    except Exception as e:
        print(f"Error al registrar evento de auditoría: {e}")

# --- VALIDACIONES ---

def validate_email(email):
    """Valida el formato de un email."""
    if not email:
        return True  # Opcional en algunos casos, se valida si existe
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    """Valida el formato de un teléfono español (9 dígitos, opcionalmente con +34)."""
    if not phone:
        return True
    # Eliminar espacios y guiones
    clean_phone = re.sub(r'[\s-]', '', phone)
    pattern = r'^(\+34|34)?[6789]\d{8}$'
    return re.match(pattern, clean_phone) is not None

@st.cache_data(ttl=300)
def get_estado_licencias_total():
    """Calcula el total de licencias usadas sumando los elementos de las listas."""
    supabase = get_supabase()
    try:
        response = supabase.table('mensajeros').select('codigo_dl').eq('estado', 'Activo').execute()
        data = response.data
        usadas = 0
        for row in data:
            codigos = row.get('codigo_dl')
            if isinstance(codigos, list):
                usadas += len(codigos)
            elif isinstance(codigos, str) and len(codigos) > 1:
                usadas += 1
        disponibles = TOTAL_LICENCIAS_DL - usadas
        return TOTAL_LICENCIAS_DL, usadas, disponibles
    except Exception:
        return TOTAL_LICENCIAS_DL, 0, TOTAL_LICENCIAS_DL
