# Personal.py
import streamlit as st
import pandas as pd
from supabase import create_client, Client
import os
import io
from datetime import date
import base64
import json  # Importante para manejar listas de documentos

# --- CONFIGURACIÓN Y CONEXIÓN A SUPABASE ---
st.set_page_config(page_title="Gestión de Personal", page_icon="👥", layout="wide")
UPLOAD_DIR = "uploads"; os.makedirs(UPLOAD_DIR, exist_ok=True)

@st.cache_resource
def init_supabase_client():
    try:
        url, key = st.secrets["supabase_url"], st.secrets["supabase_key"]
        return create_client(url, key)
    except Exception:
        st.error("Error al conectar con Supabase. Revisa tus credenciales."); st.stop()

supabase: Client = init_supabase_client()

# Desactivamos integración externa por ahora
direcline_api = None 

# --- FUNCIÓN PARA REGISTRAR EVENTOS ---
def log_event(usuario_email, accion, descripcion, delegacion, motivo=None):
    try:
        supabase.table('log_eventos').insert({
            "usuario_email": usuario_email,
            "accion": accion,
            "descripcion": descripcion,
            "delegacion": delegacion,
            "motivo": motivo
        }).execute()
    except Exception as e:
        print(f"Error al registrar evento de auditoría: {e}")

# --- FUNCIONES DE AUTENTICACIÓN ---
def render_login_form():
    st.title("Acceso al Sistema de Gestión")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Acceder"):
            try:
                session = supabase.auth.sign_in_with_password({"email": email, "password": password})
                user_id = session.user.id
                response = supabase.table('profiles').select('role, delegacion').eq('user_id', user_id).single().execute()
                profile = response.data or {}
                st.session_state.user_info = {"email": email, "role": profile.get('role', 'Lector'), "delegacion": profile.get('delegacion')}
                st.rerun()
            except Exception:
                st.error("Error: Email o contraseña incorrectos.")

# --- FUNCIONES DE GESTIÓN DE LICENCIAS ---
def get_estado_licencias_total():
    """Calcula el total de licencias usadas sumando los elementos de las listas."""
    TOTAL_LICENCIAS = 250
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
        disponibles = TOTAL_LICENCIAS - usadas
        return TOTAL_LICENCIAS, usadas, disponibles
    except Exception as e:
        return 250, 0, 250

def render_license_manager(current_list, key_prefix="edit"):
    """Renderiza el input interactivo para gestionar la lista de códigos."""
    session_list_key = f"temp_license_list_{key_prefix}"
    session_input_key = f"input_license_{key_prefix}"

    if session_list_key not in st.session_state:
        if isinstance(current_list, list):
            st.session_state[session_list_key] = current_list.copy()
        elif isinstance(current_list, str) and current_list:
            st.session_state[session_list_key] = [current_list]
        else:
            st.session_state[session_list_key] = []

    def add_license():
        code = st.session_state[session_input_key].strip()
        if code:
            if code not in st.session_state[session_list_key]:
                st.session_state[session_list_key].append(code)
            else:
                st.toast("⚠️ Ese código ya está en la lista.", icon="⚠️")
        st.session_state[session_input_key] = ""

    def remove_license(idx):
        st.session_state[session_list_key].pop(idx)

    st.markdown("**Gestión de Licencias DL:**")
    st.text_input("Escribe código DL y pulsa Enter", key=session_input_key, on_change=add_license, placeholder="Ej: DL-5050")

    lista_actual = st.session_state[session_list_key]
    if lista_actual:
        st.caption(f"Licencias asignadas ({len(lista_actual)}):")
        cols = st.columns(4)
        for i, code in enumerate(lista_actual):
            if cols[i % 4].button(f"🗑️ {code}", key=f"del_{key_prefix}_{i}", help="Clic para eliminar", use_container_width=True):
                remove_license(i)
                st.rerun()
    else:
        st.caption("Sin licencias asignadas.")

    return st.session_state[session_list_key]

# --- FUNCIONES DE DB ---
def fetch_data(table, delegacion):
    return pd.DataFrame(supabase.table(table).select("*").eq('delegacion', delegacion).eq('estado', 'Activo').order('nombre_apellido').execute().data)

def fetch_all_messengers():
    return pd.DataFrame(supabase.table('mensajeros').select("*, delegacion").eq('estado', 'Activo').order('nombre_apellido').execute().data)

def fetch_all_office_staff():
    return pd.DataFrame(supabase.table('oficina').select("*, delegacion").eq('estado', 'Activo').order('nombre_apellido').execute().data)

def fetch_single_record(table_name, record_id):
    return supabase.table(table_name).select("*").eq('id', int(record_id)).single().execute().data

def update_record(table, record_id, data):
    supabase.table(table).update(data).eq('id', record_id).execute()

def add_record_and_get_id(table, data, delegacion_actual):
    response = supabase.table(table).insert(data, returning="representation").execute()
    if response.data:
        new_id = response.data[0]['id']
        log_event(st.session_state.user_info['email'], "ALTA", f"Creó a '{data['nombre_apellido']}' en '{table}'.", delegacion_actual)
        return new_id
    return None

def dar_de_baja(table, record_id, nombre, delegacion_actual, motivo):
    supabase.table(table).update({"estado": "Baja", "fecha_baja": date.today().isoformat()}).eq('id', record_id).execute()
    descripcion_log = f"Dio de baja a '{nombre}' (ID: {record_id}) de la tabla '{table}'."
    log_event(st.session_state.user_info['email'], "BAJA", descripcion_log, delegacion_actual, motivo=motivo)
    st.warning(f"'{nombre}' ha sido dado de baja.");
    st.session_state.baja_in_progress = None
    st.rerun()

def update_file_path(table, record_id, column_name, filename):
    # Si filename es None o lista vacía, guardamos null para limpiar
    val = filename if filename and filename != '[]' else None
    supabase.table(table).update({column_name: val}).eq('id', record_id).execute()

# --- HELPER: MOSTRAR DOCUMENTOS (LECTURA) ---
def display_documents_buttons(row_docs, record_id):
    if not row_docs: return
    file_list = []
    try:
        parsed = json.loads(row_docs)
        file_list = parsed if isinstance(parsed, list) else [str(row_docs)]
    except:
        file_list = [str(row_docs)]

    for i, file_name in enumerate(file_list):
        doc_path = os.path.join(UPLOAD_DIR, file_name)
        if os.path.exists(doc_path):
            with open(doc_path, "rb") as f:
                btn_label = "📄 Doc" if len(file_list) == 1 else f"📄 Doc {i+1}"
                st.download_button(label=btn_label, data=f, file_name=file_name, key=f"dl_{record_id}_{i}", use_container_width=True)

# --- VISTA PARA LECTORES (SOLO LECTURA) ---
def render_lector_view(user_delegacion):
    st.title(f"📍 Consulta de Personal: {user_delegacion}")
    tipo = st.selectbox("Selecciona el tipo de personal:", ["Mensajeros", "Oficina"])
    
    tabla = "mensajeros" if tipo == "Mensajeros" else "oficina"
        
    st.markdown("---")
    st.subheader("Listado de Personal Activo")
    df = fetch_data(tabla, user_delegacion)
    
    if df.empty:
        st.info("No hay personal para mostrar en esta categoría.")
    else:
        for _, row in df.iterrows():
            with st.container(border=True):
                st.markdown(f"**{row['nombre_apellido']}**")
                
                if tabla == "mensajeros":
                    col1, col2, col3 = st.columns(3)
                    codigos_raw = row.get('codigo_dl')
                    if isinstance(codigos_raw, list):
                        codigos_str = ", ".join(codigos_raw)
                    else:
                        codigos_str = str(codigos_raw) if codigos_raw else "N/A"

                    col1.markdown(f"""
                        **Ruta:** {row.get('ruta', 'N/A')} <br>
                        **Móvil:** {row.get('movil', 'N/A')} <br>
                        **Email:** {row.get('email_personal', 'N/A')}
                    """, unsafe_allow_html=True)
                    
                    # --- MOSTRAR PAQ | DHL | ADR EN UNA LÍNEA ---
                    paq = '✅ Sí' if row.get('hace_paqueteria') else '❌ No'
                    dhl = '✅ Sí' if row.get('DHL') else '❌ No'
                    adr = '✅ Sí' if row.get('ADR') else '❌ No'
                    
                    col2.markdown(f"""
                        **Perfil:** {row.get('perfil_mensajero', 'N/A')} <br>
                        **Licencias DL:** {codigos_str} <br>
                        **Paq:** {paq} | **DHL:** {dhl} | **ADR:** {adr}
                    """, unsafe_allow_html=True)
                    # --------------------------------------------
                    
                    with col3:
                        display_documents_buttons(row.get('documento_path'), row['id'])
                        
                        foto_path = row.get('foto_vehiculo_path')
                        if foto_path and os.path.exists(os.path.join(UPLOAD_DIR, foto_path)):
                            with open(os.path.join(UPLOAD_DIR, foto_path), "rb") as file:
                                st.download_button(label="📸 Foto", data=file, file_name=foto_path, use_container_width=True)
                        observaciones = row.get('observaciones')
                        if observaciones and observaciones != 'None':
                            with st.expander("Obs."):
                                st.write(observaciones)
                else: # Oficina
                    col1, col2 = st.columns(2)
                    col1.markdown(f"**Posición:** {row.get('posicion', 'N/A')} <br> **Email:** {row.get('correo_electronico', 'N/A')}", unsafe_allow_html=True)
                    col2.markdown(f"**Móvil:** {row.get('movil', 'N/A')} <br> **Tel. Oficina:** {row.get('telefono_oficina', 'N/A')}", unsafe_allow_html=True)


# --- VISTA PARA ADMIN/EDITOR (GESTIÓN COMPLETA) ---
def render_admin_view():
    if "baja_in_progress" not in st.session_state: st.session_state.baja_in_progress = None
    if "delegacion_seleccionada" not in st.session_state: st.session_state.delegacion_seleccionada = None
    if "tipo_personal" not in st.session_state: st.session_state.tipo_personal = None
    if "editing_id" not in st.session_state: st.session_state.editing_id = None
    if "show_add_form" not in st.session_state: st.session_state.show_add_form = False

    if st.session_state.baja_in_progress:
        st.components.v1.html("<script>window.scrollTo(0, 0);</script>", height=0)
        record_id, record_name, tabla, delegacion = st.session_state.baja_in_progress
        st.error("⚠️ Confirmación de Baja Requerida")
        with st.container(border=True):
            st.warning(f"Estás a punto de dar de baja a **{record_name}**.")
            motivo = st.text_area("Por favor, introduce el motivo de la baja:", key=f"motivo_{record_id}")
            col1, col2 = st.columns(2)
            if col1.button("✅ Confirmar Baja", type="primary", use_container_width=True):
                if motivo: dar_de_baja(tabla, record_id, record_name, delegacion, motivo)
                else: st.error("El motivo es obligatorio para dar de baja.")
            if col2.button("❌ Cancelar", use_container_width=True):
                st.session_state.baja_in_progress = None
                st.rerun()

    def start_editing(record_id): st.session_state.editing_id = record_id
    def cancel_editing(): 
        st.session_state.editing_id = None
        if "temp_license_list_edit" in st.session_state: del st.session_state["temp_license_list_edit"]

    def set_delegacion(delegacion): st.session_state.delegacion_seleccionada = delegacion; st.session_state.tipo_personal = None
    def set_tipo_personal(tipo): st.session_state.tipo_personal = tipo
    def reset_delegacion(): st.session_state.delegacion_seleccionada = None; st.session_state.tipo_personal = None; st.session_state.editing_id = None
    def reset_tipo_personal(): st.session_state.tipo_personal = None; st.session_state.editing_id = None
    def start_baja_process(record_id, record_name, table, delegacion):
        st.session_state.baja_in_progress = (record_id, record_name, table, delegacion)
    
    if st.session_state.delegacion_seleccionada is None:
        st.title("🗺️ Selector de Delegaciones")
        delegaciones = ['Granollers', 'Sabadell', 'Zona Franca', 'Manresa', 'Girona', 'Vilafranca', 'Sanitario']
        col1, col2, col3 = st.columns(3); columnas = [col1, col2, col3] * 3
        for i, delegacion in enumerate(delegaciones):
            if i < len(columnas):
                with columnas[i]: st.button(delegacion, on_click=set_delegacion, args=[delegacion], use_container_width=True, key=f"btn_{delegacion}")
        return

    delegacion_actual = st.session_state.delegacion_seleccionada
    st.button("⬅️ Volver al selector", on_click=reset_delegacion)

    if delegacion_actual == "Sanitario":
        st.title(f"⚕️ Vista Global de Personal (Solo Lectura)")
        tab_mensajeros, tab_oficina = st.tabs(["Todos los Mensajeros", "Todo el Personal de Oficina"])
        with tab_mensajeros:
            st.subheader("Listado de todos los Mensajeros Activos")
            df_mensajeros = fetch_all_messengers()
            search_query_mens = st.text_input("Buscar por nombre de mensajero", key="search_global_mens")
            if search_query_mens: df_mensajeros = df_mensajeros[df_mensajeros["nombre_apellido"].str.contains(search_query_mens, case=False, na=False)]
            if df_mensajeros.empty: st.info("No hay mensajeros activos para mostrar.")
            else:
                for _, row in df_mensajeros.iterrows():
                    with st.container(border=True):
                        st.markdown(f"**{row['nombre_apellido']}** (`{row.get('delegacion', 'N/A')}`)")
                        col1, col2, col3 = st.columns(3)
                        col1.write(f"**Ruta:** *{row.get('ruta','')}*")
                        col1.write(f"**Móvil:** {row.get('movil','')}")
                        col2.write(f"**Perfil:** {row.get('perfil_mensajero','')}")
                        col3.write(f"**Observaciones:** {row.get('observaciones','')}")
        with tab_oficina:
            st.subheader("Listado de todo el Personal de Oficina Activo")
            df_oficina = fetch_all_office_staff()
            search_query_ofi = st.text_input("Buscar por nombre de personal de oficina", key="search_global_ofi")
            if search_query_ofi: df_oficina = df_oficina[df_oficina["nombre_apellido"].str.contains(search_query_ofi, case=False, na=False)]
            if df_oficina.empty: st.info("No hay personal de oficina activo para mostrar.")
            else:
                for _, row in df_oficina.iterrows():
                    with st.container(border=True):
                        st.markdown(f"**{row['nombre_apellido']}** (`{row.get('delegacion', 'N/A')}`)")
                        col1, col2 = st.columns(2)
                        col1.write(f"**Posición:** {row.get('posicion','')}")
                        col1.write(f"**Email:** *{row.get('correo_electronico','')}*")
                        col2.write(f"**Móvil:** {row.get('movil','')}")
                        col2.write(f"**Tel. Oficina:** {row.get('telefono_oficina','')}")
    else:
        # --- PANEL DE CONTROL DE LICENCIAS ---
        if st.session_state.tipo_personal is None:
            st.title(f"📍 Delegación: {delegacion_actual}")
            
            with st.container(border=True):
                st.markdown("### 📱 Estado de Inventario: Licencias DLS-PhoneVWE")
                total_lic, usadas_lic, disponibles_lic = get_estado_licencias_total()
                
                metric_col1, metric_col2, metric_col3 = st.columns(3)
                metric_col1.metric("Total Contratadas", total_lic)
                metric_col2.metric("En uso (Asignadas)", usadas_lic)
                delta_color = "normal" if disponibles_lic > 10 else "inverse"
                metric_col3.metric("Disponibles", disponibles_lic, delta_color=delta_color)
                
                progreso = min(usadas_lic / total_lic, 1.0)
                st.progress(progreso, text=f"Ocupación: {int(progreso*100)}%")
                if disponibles_lic <= 0:
                    st.error("⚠️ **Inventario agotado.** No se pueden asignar nuevas licencias sin liberar otras.")
            
            st.markdown("---")
            st.subheader("¿Qué personal deseas gestionar?")
            col1, col2 = st.columns(2)
            col1.button("🚚 Mensajeros", on_click=set_tipo_personal, args=["Mensajeros"], use_container_width=True)
            col2.button("💼 Oficina", on_click=set_tipo_personal, args=["Oficina"], use_container_width=True)
            return
        
        tipo_personal_actual = st.session_state.tipo_personal
        tabla_db = "mensajeros" if tipo_personal_actual == "Mensajeros" else "oficina"
        st.button("⬅️ Volver a seleccionar tipo", on_click=reset_tipo_personal)

        if st.session_state.editing_id:
            st.title(f"✏️ Editando {tipo_personal_actual}")
            record = fetch_single_record(tabla_db, st.session_state.editing_id)
            
            with st.container(border=True):
                if tabla_db == "mensajeros":
                    nombre_apellido = st.text_input("Nombre", value=record.get("nombre_apellido"))
                    ruta = st.text_input("Ruta", value=record.get("ruta"))
                    perfil_opts = ["Autónomo", "Empleado", "Asegurado Fijo", "Empleado de un Autónomo externo", "Jefe de Autónomos"]
                    curr_perfil = record.get("perfil_mensajero")
                    perfil_index = perfil_opts.index(curr_perfil) if curr_perfil in perfil_opts else 0
                    perfil_mensajero = st.selectbox("Perfil", perfil_opts, index=perfil_index)
                    observaciones = st.text_area("Observaciones", value=record.get("observaciones"))
                    movil = st.text_input("Móvil", value=record.get("movil"))
                    
                    rotulado_opts = ["Si", "No", "Pendiente de rotular"]
                    curr_rotulado = record.get("vehiculo_rotulado")
                    rotulado_index = rotulado_opts.index(curr_rotulado) if curr_rotulado in rotulado_opts else 1
                    vehiculo_rotulado = st.selectbox("Vehículo Rotulado?", rotulado_opts, index=rotulado_index)
                    
                    email_personal = st.text_input("Email Personal", value=record.get("email_personal", ""))
                    
                    # --- GESTOR DE LICENCIAS (LISTA DINÁMICA) ---
                    codigos_dl_final = render_license_manager(record.get("codigo_dl"), key_prefix="edit")
                    # ---------------------------------------------

                    hace_paqueteria = st.checkbox("¿Hace paquetería?", value=record.get("hace_paqueteria", False))
                    dhl = st.checkbox("DHL", value=record.get("DHL", False))
                    # --- CASILLA ADR ---
                    adr = st.checkbox("ADR", value=record.get("ADR", False))
                    
                    st.markdown("---")
                    if record.get("foto_vehiculo_path"):
                        c1, c2 = st.columns([3, 1]); c1.write(f"Foto actual: `{record['foto_vehiculo_path']}`"); c2.button("Quitar Foto", on_click=update_file_path, args=(tabla_db, st.session_state.editing_id, "foto_vehiculo_path", None), key="rm_photo_btn")
                    foto_vehiculo = st.file_uploader("Adjuntar/Reemplazar foto del vehículo", key="foto_vehiculo_edit")

                    data = {
                        "nombre_apellido": nombre_apellido, "ruta": ruta, "perfil_mensajero": perfil_mensajero,
                        "observaciones": observaciones, "movil": movil, "vehiculo_rotulado": vehiculo_rotulado,
                        "email_personal": email_personal, "codigo_dl": codigos_dl_final, 
                        "hace_paqueteria": hace_paqueteria, "DHL": dhl, "ADR": adr
                    }

                else:
                    nombre_apellido = st.text_input("Nombre", value=record.get("nombre_apellido"))
                    posicion = st.text_input("Posición", value=record.get("posicion"))
                    telefono_oficina = st.text_input("Tel. Oficina", value=record.get("telefono_oficina"))
                    movil = st.text_input("Móvil", value=record.get("movil"))
                    correo_electronico = st.text_input("Email", value=record.get("correo_electronico"))
                    telefono_interno = st.text_input("Tel. Interno", value=record.get("telefono_interno"))
                    
                    data = {"nombre_apellido": nombre_apellido, "posicion": posicion, "telefono_oficina": telefono_oficina, "movil": movil, "correo_electronico": correo_electronico, "telefono_interno": telefono_interno}
                
                st.markdown("---")
                
                # --- LOGICA VISUALIZACIÓN Y BORRADO DE DOCUMENTOS INDIVIDUAL ---
                current_docs = record.get("documento_path")
                doc_list = []
                if current_docs:
                    try:
                        parsed = json.loads(current_docs)
                        doc_list = parsed if isinstance(parsed, list) else [str(current_docs)]
                    except:
                        doc_list = [str(current_docs)]

                if doc_list:
                    st.caption("Gestión de Documentos:")
                    for i, doc_name in enumerate(doc_list):
                        # Layout: Nombre | Descarga | Borrar
                        c1, c2, c3 = st.columns([6, 1, 1])
                        c1.text(f"📄 {doc_name}")
                        
                        # Botón Descarga
                        doc_path = os.path.join(UPLOAD_DIR, doc_name)
                        if os.path.exists(doc_path):
                            with open(doc_path, "rb") as f:
                                c2.download_button("📥", f, file_name=doc_name, key=f"dledit_{i}")
                        
                        # Botón Borrar Individual
                        if c3.button("🗑️", key=f"rm_doc_{i}", help="Eliminar este archivo"):
                            doc_list.pop(i) # Quitamos de la lista
                            # Si queda vacía, guardamos None o lista vacía
                            new_val = json.dumps(doc_list) if doc_list else None
                            update_file_path(tabla_db, st.session_state.editing_id, "documento_path", new_val)
                            st.rerun()

                # --- MULTI ARCHIVO: ADJUNTAR NUEVOS ---
                uploaded_files = st.file_uploader("Adjuntar nuevos documentos", key="uploaded_file_edit", accept_multiple_files=True)
                
                st.markdown("---")
                c1, c2 = st.columns([1, 6])
                if c1.button("💾 Guardar Cambios", type="primary", use_container_width=True):
                    update_record(tabla_db, st.session_state.editing_id, data)
                    
                    # LOGICA GUARDADO: Añadir a los existentes
                    if uploaded_files:
                        # 1. Recuperar lista actual
                        current_list = []
                        if record.get("documento_path"):
                            try:
                                current_list = json.loads(record.get("documento_path"))
                                if not isinstance(current_list, list): current_list = [str(record.get("documento_path"))]
                            except:
                                current_list = [str(record.get("documento_path"))]
                        
                        # 2. Guardar nuevos y añadir a lista
                        for up_file in uploaded_files:
                            filename = f"{st.session_state.editing_id}_{up_file.name}"
                            filepath = os.path.join(UPLOAD_DIR, filename)
                            with open(filepath, "wb") as f: f.write(up_file.getbuffer())
                            current_list.append(filename)
                        
                        # 3. Actualizar DB
                        update_file_path(tabla_db, st.session_state.editing_id, "documento_path", json.dumps(current_list))
                    
                    if tabla_db == "mensajeros" and foto_vehiculo:
                        filename = f"vehiculo_{st.session_state.editing_id}_{foto_vehiculo.name}"; filepath = os.path.join(UPLOAD_DIR, filename)
                        with open(filepath, "wb") as f: f.write(foto_vehiculo.getbuffer())
                        update_file_path(tabla_db, st.session_state.editing_id, "foto_vehiculo_path", filename)
                    
                    st.success("¡Registro actualizado!"); 
                    if "temp_license_list_edit" in st.session_state: del st.session_state["temp_license_list_edit"]
                    st.session_state.editing_id = None
                    st.rerun()
                
                if c2.button("Cancelar", use_container_width=True): cancel_editing(); st.rerun()
        
        else:
            st.title(f"Gestión de {tipo_personal_actual}: {delegacion_actual}")
            if st.session_state.user_info.get("role") in ['Admin', 'Editor']:
                if st.session_state.show_add_form:
                    with st.container(border=True):
                        st.subheader("📝 Rellena los datos del nuevo personal")
                        
                        if tabla_db == "mensajeros":
                            nombre_apellido=st.text_input("Nombre y Apellido", key="add_nombre")
                            ruta=st.text_input("Ruta", key="add_ruta")
                            perfil_mensajero=st.selectbox("Perfil mensajero", ["Autónomo", "Asegurado Fijo", "Asegurado a Producción", "Empleado de un Autónomo externo", "Jefe de Autónomos"], key="add_perfil")
                            observaciones=st.text_area("Observaciones", key="add_obs")
                            movil=st.text_input("Móvil", key="add_movil")
                            vehiculo_rotulado=st.selectbox("Vehículo Rotulado?", ["Si", "No", "Pendiente de rotular"], key="add_rotulado")
                            email_personal = st.text_input("Email Personal", key="add_email")
                            codigos_dl_final = render_license_manager([], key_prefix="add")
                            hace_paqueteria = st.checkbox("¿Hace paquetería?", key="add_paq")
                            dhl = st.checkbox("DHL", key="add_dhl")
                            adr = st.checkbox("ADR", key="add_adr")
                            foto_vehiculo=st.file_uploader("Adjuntar foto del vehículo", key="add_foto")
                        else:
                            nombre_apellido=st.text_input("Nombre y Apellido", key="add_nombre")
                            posicion=st.text_input("Posición", key="add_pos")
                            telefono_oficina=st.text_input("Teléfono Oficina", key="add_tel_ofi")
                            movil=st.text_input("Móvil", key="add_movil")
                            correo_electronico=st.text_input("Correo Electrónico", key="add_email")
                            telefono_interno=st.text_input("Teléfono Interno", key="add_tel_int")
                        
                        # --- MULTI ARCHIVO EN ALTA ---
                        uploaded_files = st.file_uploader("Adjuntar documentos", key="add_doc", accept_multiple_files=True)
                        
                        s_col1, s_col2 = st.columns([1,5])
                        
                        if s_col1.button("✅ Añadir Personal", type="primary", use_container_width=True):
                            if nombre_apellido:
                                if tabla_db == "mensajeros": 
                                    data_form = {
                                        "nombre_apellido": nombre_apellido, "ruta": ruta, "perfil_mensajero": perfil_mensajero, 
                                        "observaciones": observaciones, "movil": movil, "vehiculo_rotulado": vehiculo_rotulado, 
                                        "email_personal": email_personal, "codigo_dl": codigos_dl_final, 
                                        "hace_paqueteria": hace_paqueteria, "DHL": dhl, "ADR": adr
                                    }
                                else: 
                                    data_form = {"nombre_apellido": nombre_apellido, "posicion": posicion, "telefono_oficina": telefono_oficina, "movil": movil, "correo_electronico": correo_electronico, "telefono_interno": telefono_interno}
                                
                                data_form["delegacion"] = delegacion_actual; data_form["estado"] = "Activo"
                                new_id = add_record_and_get_id(tabla_db, data_form, delegacion_actual)
                                
                                if new_id:
                                    # GUARDAR LISTA DE ARCHIVOS
                                    if uploaded_files:
                                        saved_names = []
                                        for up_file in uploaded_files:
                                            filename = f"{new_id}_{up_file.name}"
                                            filepath = os.path.join(UPLOAD_DIR, filename)
                                            with open(filepath, "wb") as f: f.write(up_file.getbuffer())
                                            saved_names.append(filename)
                                        
                                        update_file_path(tabla_db, new_id, "documento_path", json.dumps(saved_names))

                                    if tabla_db == "mensajeros" and foto_vehiculo:
                                        filename = f"vehiculo_{new_id}_{foto_vehiculo.name}"; filepath = os.path.join(UPLOAD_DIR, filename)
                                        with open(filepath, "wb") as f: f.write(foto_vehiculo.getbuffer())
                                        update_file_path(tabla_db, new_id, "foto_vehiculo_path", filename)
                                    st.success("¡Nuevo personal añadido!");
                                    st.session_state.show_add_form = False
                                    if "temp_license_list_add" in st.session_state: del st.session_state["temp_license_list_add"]
                                    st.rerun()
                            else: st.error("El nombre es un campo obligatorio.")
                        
                        if s_col2.button("❌ Cancelar", use_container_width=True):
                            st.session_state.show_add_form = False
                            if "temp_license_list_add" in st.session_state: del st.session_state["temp_license_list_add"]
                            st.rerun()
                else:
                    if st.button("➕ Añadir Nuevo Personal"):
                        st.session_state.show_add_form = True
                        st.rerun()
            st.markdown("---")
            st.subheader("Listado de Personal Activo")
            df_activos = fetch_data(tabla_db, delegacion_actual)
            search_query = st.text_input("Buscar por nombre", key=f"search_{tabla_db}")
            if search_query: df_activos = df_activos[df_activos["nombre_apellido"].str.contains(search_query, case=False, na=False)]
            if df_activos.empty: st.info("No hay personal que coincida.")
            else:
                for _, row in df_activos.iterrows():
                    with st.container(border=True):
                        user_role = st.session_state.user_info.get("role")
                        header_cols = st.columns([5, 2])
                        header_cols[0].markdown(f"**{row['nombre_apellido']}**")
                        with header_cols[1]:
                            action_cols = st.columns(2)
                            if user_role in ['Admin', 'Editor']:
                                action_cols[0].button("✏️", key=f"edit_{row['id']}", on_click=start_editing, args=[row['id']], use_container_width=True, help="Editar")
                            if user_role == 'Admin':
                                action_cols[1].button("🚫", key=f"baja_{row['id']}", type="primary", on_click=start_baja_process, args=(row['id'], row['nombre_apellido'], tabla_db, delegacion_actual), use_container_width=True, help="Dar de Baja")
                        
                        if tabla_db == "mensajeros":
                            col1, col2, col3 = st.columns(3)
                            codigos_raw = row.get('codigo_dl')
                            if isinstance(codigos_raw, list):
                                codigos_display = f"📚 {len(codigos_raw)} Licencias: " + ", ".join(codigos_raw)
                            elif codigos_raw:
                                codigos_display = f"Licencia: {codigos_raw}"
                            else:
                                codigos_display = "Sin licencias"

                            col1.markdown(f"""
                                <small><b>Ruta:</b> {row.get('ruta', 'N/A')}</small><br>
                                <small><b>Móvil:</b> {row.get('movil', 'N/A')}</small><br>
                                <small><b>Email:</b> {row.get('email_personal', 'N/A')}</small>
                            """, unsafe_allow_html=True)
                            
                            # --- MODIFICADO: PAQ | DHL | ADR EN UNA LÍNEA ---
                            paq = '✅ Sí' if row.get('hace_paqueteria') else '❌ No'
                            dhl = '✅ Sí' if row.get('DHL') else '❌ No'
                            adr = '✅ Sí' if row.get('ADR') else '❌ No'
                            
                            col2.markdown(f"""
                                <small><b>Perfil:</b> {row.get('perfil_mensajero', 'N/A')}</small><br>
                                <small><b>{codigos_display}</b></small><br>
                                <small><b>Paq:</b> {paq} | <b>DHL:</b> {dhl} | <b>ADR:</b> {adr}</small>
                            """, unsafe_allow_html=True)
                            
                            with col3:
                                display_documents_buttons(row.get('documento_path'), row['id'])
                                
                                foto_path = row.get('foto_vehiculo_path')
                                if foto_path and os.path.exists(os.path.join(UPLOAD_DIR, foto_path)):
                                    with open(os.path.join(UPLOAD_DIR, foto_path), "rb") as file:
                                        st.download_button(label="📸 Foto", data=file, file_name=foto_path, use_container_width=True, help="Descargar Foto")
                                observaciones = row.get('observaciones')
                                if observaciones and observaciones != 'None':
                                    with st.expander("Obs."):
                                        st.write(observaciones)
                        else: # Oficina
                            col1, col2 = st.columns(2)
                            col1.markdown(f"""
                                <small><b>Posición:</b> {row.get('posicion', 'N/A')}</small><br>
                                <small><b>Email:</b> {row.get('correo_electronico', 'N/A')}</small>
                            """, unsafe_allow_html=True)
                            col2.markdown(f"""
                                <small><b>Móvil:</b> {row.get('movil', 'N/A')}</small><br>
                                <small><b>Tel. Oficina:</b> {row.get('telefono_oficina', 'N/A')}</small>
                            """, unsafe_allow_html=True)
                
                if not df_activos.empty:
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer: df_activos.to_excel(writer, index=False, sheet_name='Personal')
                    st.download_button(label="📥 Exportar a Excel", data=output.getvalue(), file_name=f"personal_{delegacion_actual}.xlsx")

# --- EJECUCIÓN PRINCIPAL ---
if "user_info" not in st.session_state:
    render_login_form()
else:
    user_role = st.session_state.user_info.get("role", "Lector")
    user_delegacion = st.session_state.user_info.get("delegacion")
    st.sidebar.success(f"Sesión iniciada: {st.session_state.user_info.get('email', '')}")
    st.sidebar.info(f"Rol: **{user_role}**")
    if user_delegacion: st.sidebar.write(f"Delegación: **{user_delegacion}**")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.clear(); st.rerun()

    if user_role == "Lector" and user_delegacion:
        render_lector_view(user_delegacion)
    elif user_role in ["Admin", "Editor"]:
        render_admin_view()
    else:
        st.warning("No tienes permisos suficientes.")