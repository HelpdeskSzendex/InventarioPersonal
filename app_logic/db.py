# app_logic/db.py
import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import date
import os
import re

# UPLOAD_DIR = "uploads"  # Redundante con Supabase Storage

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
    try:
        supabase = get_supabase()
        res = supabase.table(table).select("*").eq('delegacion', delegacion).eq('estado', 'Activo').order('nombre_apellido').execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        st.error(f"Error al cargar datos de {table}: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def fetch_all_messengers():
    try:
        supabase = get_supabase()
        res = supabase.table('mensajeros').select("*, delegacion").eq('estado', 'Activo').order('nombre_apellido').execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        st.error(f"Error al cargar mensajeros: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def fetch_all_office_staff():
    try:
        supabase = get_supabase()
        res = supabase.table('oficina').select("*, delegacion").eq('estado', 'Activo').order('nombre_apellido').execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        st.error(f"Error al cargar personal de oficina: {e}")
        return pd.DataFrame()

def fetch_single_record(table_name, record_id):
    try:
        supabase = get_supabase()
        return supabase.table(table_name).select("*").eq('id', int(record_id)).single().execute().data
    except Exception as e:
        st.error(f"Error al cargar registro {record_id}: {e}")
        return {}

def update_record(table, record_id, data, user_email=None, delegacion=None):
    try:
        supabase = get_supabase()

        # Obtener estado previo para el log
        old_data = {}
        if user_email:
            try:
                old_data = supabase.table(table).select("*").eq('id', record_id).single().execute().data
            except: pass

        res = supabase.table(table).update(data).eq('id', record_id).execute()

        if user_email and old_data:
            diffs = []
            for k, v in data.items():
                old_v = old_data.get(k)
                if str(old_v) != str(v):
                    diffs.append(f"{k}: [{old_v}] -> [{v}]")
            if diffs:
                log_event(user_email, "EDICIÓN", f"Editó a '{old_data.get('nombre_apellido')}'. Cambios: {', '.join(diffs)}", delegacion)

        st.cache_data.clear()
        return res
    except Exception as e:
        st.error(f"Error al actualizar registro: {e}")
        return None

def add_record_and_get_id(table, data, user_email, delegacion_actual):
    try:
        supabase = get_supabase()
        response = supabase.table(table).insert(data, returning="representation").execute()
        if response.data:
            new_id = response.data[0]['id']
            # Log detallado de los campos iniciales
            detalles = ", ".join([f"{k}: {v}" for k, v in data.items() if v])
            log_event(user_email, "ALTA", f"Creó a '{data['nombre_apellido']}' en '{table}'. Datos: {detalles}", delegacion_actual)
            st.cache_data.clear()
            return new_id
        return None
    except Exception as e:
        st.error(f"Error al añadir personal: {e}")
        return None

def dar_de_baja(table, record_id, nombre, user_email, delegacion_actual, motivo):
    try:
        supabase = get_supabase()
        supabase.table(table).update({"estado": "Baja", "fecha_baja": date.today().isoformat()}).eq('id', record_id).execute()
        descripcion_log = f"Dio de baja a '{nombre}' (ID: {record_id}) de la tabla '{table}'."
        log_event(user_email, "BAJA", descripcion_log, delegacion_actual, motivo=motivo)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Error al tramitar baja: {e}")

def update_file_path(table, record_id, column_name, filename):
    try:
        supabase = get_supabase()
        # Si filename es None o lista vacía, guardamos null para limpiar
        val = filename if filename and filename != '[]' else None
        res = supabase.table(table).update({column_name: val}).eq('id', record_id).execute()
        st.cache_data.clear()
        return res
    except Exception as e:
        st.error(f"Error al actualizar ruta de archivo: {e}")
        return None

# --- STORAGE ---

def upload_file_to_storage(file_bytes, filename, bucket="documentos"):
    """Sube un archivo a Supabase Storage."""
    try:
        supabase = get_supabase()
        # Intentar subir el archivo
        supabase.storage.from_(bucket).upload(
            path=filename,
            file=file_bytes,
            file_options={"upsert": "true"}
        )
        return True
    except Exception as e:
        print(f"Error subiendo a Storage: {e}")
        return False

def get_file_download_url(filename, bucket="documentos"):
    """Obtiene la URL de descarga firmada de un archivo."""
    try:
        supabase = get_supabase()
        # create_signed_url en versiones recientes de supabase-py devuelve el string directamente
        res = supabase.storage.from_(bucket).create_signed_url(filename, expires_in=3600)
        if isinstance(res, dict):
            return res.get('signedURL')
        return res # Es el URL directamente
    except Exception as e:
        print(f"Error obteniendo URL: {e}")
        return None

def delete_file_from_storage(filename, bucket="documentos"):
    """Elimina un archivo del storage."""
    try:
        supabase = get_supabase()
        supabase.storage.from_(bucket).remove([filename])
        return True
    except Exception as e:
        print(f"Error eliminando archivo: {e}")
        return False

def log_event(usuario_email, accion, descripcion, delegacion, motivo=None):
    try:
        supabase = get_supabase()
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
    # Regex más estricta para evitar dobles puntos y formatos extraños
    pattern = r'^[a-zA-Z0-9._%+-]+@([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    """Valida el formato de un teléfono español (9 dígitos, opcionalmente con +34)."""
    if not phone:
        return True
    # Eliminar espacios y guiones
    clean_phone = re.sub(r'[\s-]', '', phone)
    pattern = r'^(\+34|34)?[6789]\d{8}$'
    return re.match(pattern, clean_phone) is not None

def get_status_color(expiry_date_str):
    """Calcula el estado de caducidad (Semáforo)."""
    if not expiry_date_str:
        return None
    try:
        expiry_date = date.fromisoformat(expiry_date_str)
        today = date.today()
        days_left = (expiry_date - today).days
        if days_left < 0:
            return "🔴" # Caducado
        elif days_left <= 30:
            return "🟠" # Próximo a caducar
        else:
            return "🟢" # OK
    except:
        return None

@st.cache_data(ttl=300)
def get_estado_licencias_total():
    """Calcula el total de licencias usadas sumando los elementos de las listas."""
    try:
        supabase = get_supabase()
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
