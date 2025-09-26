# Personal.py
import streamlit as st
import pandas as pd
from supabase import create_client, Client
import os
import io
from datetime import date

# --- CONFIGURACIÓN Y CONEXIÓN A SUPABASE ---
st.set_page_config(page_title="Gestión de Personal", page_icon="👥", layout="wide")
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

try:
    url: str = st.secrets["supabase_url"]
    key: str = st.secrets["supabase_key"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Error al conectar con Supabase. Revisa tus credenciales en .streamlit/secrets.toml")
    st.stop()

# --- SISTEMA DE LOGIN MEJORADO CON ROLES ---
def check_login():
    if "user_info" not in st.session_state:
        st.title("Acceso al Sistema de Gestión")
        email = st.text_input("Email")
        password = st.text_input("Contraseña", type="password")
        if st.button("Acceder"):
            try:
                session = supabase.auth.sign_in_with_password({"email": email, "password": password})
                user_id = session.user.id
                
                # Buscamos el perfil del usuario para obtener su rol y delegación
                response = supabase.table('profiles').select('role, delegacion').eq('user_id', user_id).single().execute()
                
                if response.data:
                    st.session_state.user_info = {
                        "session": session,
                        "role": response.data.get('role', 'Lector'),
                        "delegacion": response.data.get('delegacion')
                    }
                else: # Si no hay perfil, es un Lector sin delegación (no verá nada)
                    st.session_state.user_info = {"session": session, "role": 'Lector', "delegacion": None}
                
                st.rerun()
            except Exception as e:
                st.error(f"Error al iniciar sesión: Email o contraseña incorrectos.")
        return False
    return True

# --- FUNCIONES DE DB ---
def fetch_data(table_name, delegacion):
    response = supabase.table(table_name).select("*").eq('delegacion', delegacion).eq('estado', 'Activo').order('nombre_apellido').execute()
    return pd.DataFrame(response.data)

def fetch_single_record(table_name, record_id):
    response = supabase.table(table_name).select("*").eq('id', int(record_id)).single().execute()
    return response.data if response.data else None

def update_record(table_name, record_id, data):
    supabase.table(table_name).update(data).eq('id', record_id).execute()

def add_record_and_get_id(table_name, data):
    response = supabase.table(table_name).insert(data, returning="representation").execute()
    if response.data:
        return response.data[0]['id']
    return None

def dar_de_baja_personal(personal_id, table_name):
    fecha_de_baja = date.today().strftime("%Y-%m-%d")
    supabase.table(table_name).update({"estado": "Baja", "fecha_baja": fecha_de_baja}).eq('id', personal_id).execute()
    
def update_document_path(table, record_id, filename):
    supabase.table(table).update({'documento_path': filename}).eq('id', record_id).execute()

# --- FUNCIONES DE LA INTERFAZ ---
def start_editing(record_id, table_name): st.session_state.editing_id = record_id; st.session_state.editing_table = table_name
def cancel_editing(): st.session_state.editing_id = None; st.session_state.editing_table = None
def seleccionar_delegacion(nombre_delegacion): st.session_state.delegacion_seleccionada = nombre_delegacion; st.session_state.tipo_personal = None
def seleccionar_tipo_personal(tipo): st.session_state.tipo_personal = tipo
def volver_a_inicio(): st.session_state.delegacion_seleccionada = None; st.session_state.tipo_personal = None; cancel_editing()
def volver_a_delegacion(): st.session_state.tipo_personal = None; cancel_editing()

# --- APP PRINCIPAL ---
if check_login():
    user_info = st.session_state.get("user_info", {})
    user_role = user_info.get('role', 'Lector')
    user_delegacion = user_info.get('delegacion')

    st.sidebar.success(f"Sesión iniciada")
    st.sidebar.info(f"Rol: **{user_role}**")
    if user_delegacion:
        st.sidebar.write(f"Delegación: **{user_delegacion}**")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.clear(); st.rerun()

    # --- LÓGICA DE PERMISOS ---

    # CASO 1: Usuario LECTOR con delegación asignada
    if user_role == 'Lector' and user_delegacion:
        st.title(f"📍 Consulta de Personal: {user_delegacion}")
        tipo_personal_actual = st.selectbox("Selecciona el tipo de personal a consultar:", ["Mensajeros", "Oficina"])
        tabla_db = "mensajeros" if tipo_personal_actual == "Mensajeros" else "oficina"
        st.markdown("---")
        st.subheader(f"Listado de Personal Activo")
        df_activos = fetch_data(tabla_db, user_delegacion)
        st.dataframe(df_activos, use_container_width=True, hide_index=True)

    # CASO 2: Usuario ADMIN o EDITOR (con acceso completo)
    elif user_role in ['Admin', 'Editor']:
        if 'delegacion_seleccionada' not in st.session_state: st.session_state.delegacion_seleccionada = None
        if 'tipo_personal' not in st.session_state: st.session_state.tipo_personal = None
        if 'editing_id' not in st.session_state: st.session_state.editing_id = None
        if 'editing_table' not in st.session_state: st.session_state.editing_table = None

        if st.session_state.delegacion_seleccionada is None:
            st.title("🗺️ Selector de Delegaciones")
            st.markdown("Selecciona una delegación para gestionar su personal.")
            delegaciones = ['Granollers', 'Sabadell', 'Zona FRANCA', 'Manresa', 'Girona', 'Vilafranca']
            col1, col2, col3 = st.columns(3); columnas = [col1, col2, col3, col1, col2, col3]
            for i, d in enumerate(delegaciones):
                with columnas[i]: st.button(d, on_click=seleccionar_delegacion, args=[d], use_container_width=True, key=f"btn_{d}")
        
        elif st.session_state.delegacion_seleccionada and st.session_state.tipo_personal is None:
            delegacion_actual = st.session_state.delegacion_seleccionada
            st.button("⬅️ Volver al selector", on_click=volver_a_inicio)
            st.title(f"📍 Delegación: {delegacion_actual}")
            st.subheader("¿Qué personal deseas gestionar?")
            col1, col2 = st.columns(2)
            with col1: st.button("🚚 Mensajeros", on_click=seleccionar_tipo_personal, args=["Mensajeros"], use_container_width=True)
            with col2: st.button("💼 Oficina", on_click=seleccionar_tipo_personal, args=["Oficina"], use_container_width=True)
        
        else: # VISTA DE GESTIÓN COMPLETA
            delegacion_actual = st.session_state.delegacion_seleccionada
            tipo_personal_actual = st.session_state.tipo_personal
            tabla_db = "mensajeros" if tipo_personal_actual == "Mensajeros" else "oficina"
            st.button("⬅️ Volver a seleccionar tipo", on_click=volver_a_delegacion)
            
            if st.session_state.editing_id:
                st.title(f"✏️ Editando {tipo_personal_actual}")
                record = fetch_single_record(st.session_state.editing_table, st.session_state.editing_id)
                with st.form(key="edit_form"):
                    if tabla_db == "mensajeros":
                        perfil_options = ["Autónomo", "Empleado", "Asegurado Fijo", "Otro"]; perfil_index = perfil_options.index(record.get("perfil_mensajero")) if record.get("perfil_mensajero") in perfil_options else 0
                        vehiculo_options = ["No", "Si"]; vehiculo_index = vehiculo_options.index(record.get("vehiculo_empresa")) if record.get("vehiculo_empresa") in vehiculo_options else 0
                        data = {"nombre_apellido": st.text_input("Nombre y Apellido", value=record.get("nombre_apellido")), "ruta": st.text_input("Ruta", value=record.get("ruta")), "perfil_mensajero": st.selectbox("Perfil mensajero", perfil_options, index=perfil_index), "vehiculo_empresa": st.selectbox("Vehículo empresa", vehiculo_options, index=vehiculo_index), "observaciones": st.text_area("Observaciones", value=record.get("observaciones")), "movil": st.text_input("Móvil", value=record.get("movil"))}
                    else:
                        data = {"nombre_apellido": st.text_input("Nombre y Apellido", value=record.get("nombre_apellido")), "posicion": st.text_input("Posición", value=record.get("posicion")), "telefono_oficina": st.text_input("Teléfono Oficina", value=record.get("telefono_oficina")), "movil": st.text_input("Móvil", value=record.get("movil")), "correo_electronico": st.text_input("Correo Electrónico", value=record.get("correo_electronico")), "telefono_interno": st.text_input("Teléfono Interno", value=record.get("telefono_interno"))}
                    
                    uploaded_file = st.file_uploader("Adjuntar/Reemplazar documento (documento_path)")
                    c1, c2 = st.columns([1, 6])
                    with c1:
                        if st.form_submit_button("Guardar", use_container_width=True):
                            update_record(tabla_db, st.session_state.editing_id, data)
                            if uploaded_file:
                                filename = f"{st.session_state.editing_id}_{uploaded_file.name}"; filepath = os.path.join(UPLOAD_DIR, filename)
                                with open(filepath, "wb") as f: f.write(uploaded_file.getbuffer())
                                update_document_path(tabla_db, st.session_state.editing_id, filename)
                            st.success("¡Registro actualizado!"); cancel_editing(); st.rerun()
                    with c2: st.form_submit_button("Cancelar", on_click=cancel_editing, use_container_width=True)
            else:
                st.title(f"Gestión de {tipo_personal_actual}: {delegacion_actual}")
                if user_role in ['Admin', 'Editor']:
                    with st.expander("➕ Añadir Nuevo Personal"):
                        with st.form(key="add_form", clear_on_submit=True):
                            if tabla_db == "mensajeros":
                                data = {"nombre_apellido": st.text_input("Nombre y Apellido"), "ruta": st.text_input("Ruta"), "perfil_mensajero": st.selectbox("Perfil mensajero", ["Autónomo", "Empleado", "Asegurado Fijo", "Otro"]), "vehiculo_empresa": st.selectbox("Vehículo empresa", ["No", "Si"]), "observaciones": st.text_area("Observaciones"), "movil": st.text_input("Móvil")}
                            else:
                                data = {"nombre_apellido": st.text_input("Nombre y Apellido"), "posicion": st.text_input("Posición"), "telefono_oficina": st.text_input("Teléfono Oficina"), "movil": st.text_input("Móvil"), "correo_electronico": st.text_input("Correo Electrónico"), "telefono_interno": st.text_input("Teléfono Interno")}
                            if st.form_submit_button("Añadir Personal"):
                                if data["nombre_apellido"]:
                                    data["delegacion"] = delegacion_actual; data["estado"] = "Activo"; new_id = add_record_and_get_id(tabla_db, data); st.success("¡Nuevo personal añadido!"); st.rerun()
                                else: st.error("El nombre es un campo obligatorio.")
                
                st.markdown("---")
                st.subheader("Listado de Personal Activo")
                df_activos = fetch_data(tabla_db, delegacion_actual)
                search_query = st.text_input("Buscar por nombre", key=f"search_{tabla_db}")
                if search_query: df_activos = df_activos[df_activos["nombre_apellido"].str.contains(search_query, case=False, na=False)]
                
                if df_activos.empty:
                    st.info("No hay personal que coincida.")
                else:
                    for _, row in df_activos.iterrows():
                        with st.container(border=True):
                            if tabla_db == "mensajeros":
                                cols = st.columns([3, 2, 4, 1, 1]); cols[0].markdown(f"**{row['nombre_apellido']}**"); cols[0].write(f"Ruta: *{row['ruta']}*")
                                if row['documento_path']:
                                    doc_path = os.path.join(UPLOAD_DIR, row['documento_path']);
                                    if os.path.exists(doc_path):
                                        with open(doc_path, "rb") as file: cols[0].download_button(label="📄", data=file, file_name=row['documento_path'], help="Descargar documento")
                                cols[1].write(f"**Móvil:** {row['movil']}"); cols[1].write(f"**Perfil:** {row['perfil_mensajero']}"); cols[2].write(f"**Observaciones:** {row['observaciones']}")
                            else:
                                cols = st.columns([3, 2, 2, 1, 1]); cols[0].markdown(f"**{row['nombre_apellido']}**"); cols[0].write(f"Email: *{row['correo_electronico']}*")
                                if row['documento_path']:
                                    doc_path = os.path.join(UPLOAD_DIR, row['documento_path']);
                                    if os.path.exists(doc_path):
                                        with open(doc_path, "rb") as file: cols[0].download_button(label="📄", data=file, file_name=row['documento_path'], help="Descargar documento")
                                cols[1].write(f"**Móvil:** {row['movil']}"); cols[1].write(f"**Tel. Oficina:** {row['telefono_oficina']}"); cols[2].write(f"**Posición:** {row['posicion']}")
                            
                            if user_role in ['Admin', 'Editor']: cols[-2].button("✏️", key=f"edit_{row['id']}", on_click=start_editing, args=[row['id'], tabla_db])
                            if user_role == 'Admin':
                                if cols[-1].button("Dar de Baja", key=f"baja_{row['id']}", type="primary"):
                                    dar_de_baja_personal(row['id'], tabla_db); st.warning(f"{row['nombre_apellido']} ha sido dado de baja."); st.rerun()

    # CASO 3: El usuario no tiene permisos
    else:
        st.warning("No tienes permisos suficientes o no se te ha asignado una delegación. Contacta con un administrador.")