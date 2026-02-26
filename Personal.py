# Personal.py
import streamlit as st
import pandas as pd
import os
import io
from datetime import date
from utils.db import DELEGACIONES, fetch_data, fetch_single_record, update_record, add_record_and_get_id, dar_de_baja, update_file_path
from utils.auth import check_auth, login, render_sidebar

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Gestión de Personal", page_icon="👥", layout="wide")
UPLOAD_DIR = "uploads"; os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- FUNCIONES DE AUTENTICACIÓN ---
def render_login_form():
    st.title("Acceso al Sistema de Gestión")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Acceder"):
            if login(email, password):
                st.rerun()

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
                if tabla == "mensajeros":
                    cols = st.columns([3, 2, 4, 1])
                    cols[0].markdown(f"**{row['nombre_apellido']}**")
                    cols[0].write(f"Ruta: *{row.get('ruta', 'N/A')}*")
                    cols[1].write(f"**Móvil:** {row.get('movil', 'N/A')}")
                    cols[1].write(f"**Perfil:** {row.get('perfil_mensajero', 'N/A')}")
                    cols[2].write(f"**Observaciones:** {row.get('observaciones', 'N/A')}")
                else:
                    cols = st.columns([3, 2, 2, 1])
                    cols[0].markdown(f"**{row['nombre_apellido']}**")
                    cols[0].write(f"Email: *{row.get('correo_electronico', 'N/A')}*")
                    cols[1].write(f"**Móvil:** {row.get('movil', 'N/A')}")
                    cols[1].write(f"**Tel. Oficina:** {row.get('telefono_oficina', 'N/A')}")
                    cols[2].write(f"**Posición:** {row.get('posicion', 'N/A')}")
                
                if row.get('documento_path'):
                    doc_path = os.path.join(UPLOAD_DIR, row['documento_path'])
                    if os.path.exists(doc_path):
                        with open(doc_path, "rb") as file:
                            cols[-1].download_button(label="📄", data=file, file_name=row['documento_path'], help="Descargar documento")

# --- VISTA PARA ADMIN/EDITOR (GESTIÓN COMPLETA) ---
def render_admin_view():
    if "delegacion_seleccionada" not in st.session_state: st.session_state.delegacion_seleccionada = None
    if "tipo_personal" not in st.session_state: st.session_state.tipo_personal = None
    if "editing_id" not in st.session_state: st.session_state.editing_id = None

    def start_editing(record_id): st.session_state.editing_id = record_id; st.rerun()
    def cancel_editing(): st.session_state.editing_id = None; st.rerun()
    
    # NAVEGACIÓN: PASO 1 - Elegir delegación
    if st.session_state.delegacion_seleccionada is None:
        st.title("🗺️ Selector de Delegaciones")
        
        col1, col2, col3 = st.columns(3)
        columnas = [col1, col2, col3, col1, col2, col3] # Reutilizamos las columnas para la segunda fila
        for i, delegacion in enumerate(DELEGACIONES):
            with columnas[i]:
                if st.button(delegacion, use_container_width=True, key=f"btn_{delegacion}"):
                    st.session_state.delegacion_seleccionada = delegacion; st.rerun()
        return

    delegacion_actual = st.session_state.delegacion_seleccionada
    if st.button("⬅️ Volver al selector"):
        st.session_state.delegacion_seleccionada = None; st.session_state.tipo_personal = None; st.rerun()

    # NAVEGACIÓN: PASO 2 - Elegir tipo de personal
    if st.session_state.tipo_personal is None:
        st.title(f"📍 Delegación: {delegacion_actual}")
        st.subheader("¿Qué personal deseas gestionar?")
        col1, col2 = st.columns(2)
        if col1.button("🚚 Mensajeros", use_container_width=True): st.session_state.tipo_personal = "Mensajeros"; st.rerun()
        if col2.button("💼 Oficina", use_container_width=True): st.session_state.tipo_personal = "Oficina"; st.rerun()
        return
    
    tipo_personal_actual = st.session_state.tipo_personal
    tabla_db = "mensajeros" if tipo_personal_actual == "Mensajeros" else "oficina"
    if st.button("⬅️ Volver a seleccionar tipo"):
        st.session_state.tipo_personal = None; st.rerun()

    # MODO EDICIÓN
    if st.session_state.editing_id:
        st.title(f"✏️ Editando {tipo_personal_actual}")
        record = fetch_single_record(tabla_db, st.session_state.editing_id)
        with st.form(key="edit_form"):
            if tabla_db == "mensajeros":
                rotulado_options = ["Si", "No", "Pendiente de rotular"]
                current_rotulado = record.get("vehiculo_rotulado")
                # Se establece un valor por defecto si el actual es None (vacío)
                rotulado_index = rotulado_options.index(current_rotulado) if current_rotulado in rotulado_options else 1 

                perfil_options = ["Autónomo", "Empleado", "Asegurado Fijo", "Empleado de un Autónomo externo", "Otro"]; perfil_index = perfil_options.index(record.get("perfil_mensajero", "Autónomo"))
                vehiculo_options = ["No", "Si"]; vehiculo_index = vehiculo_options.index(record.get("vehiculo_empresa", "No"))
                
                data = {
                    "nombre_apellido": st.text_input("Nombre", value=record.get("nombre_apellido")),
                    "ruta": st.text_input("Ruta", value=record.get("ruta")),
                    "perfil_mensajero": st.selectbox("Perfil", perfil_options, index=perfil_index),
                    "vehiculo_empresa": st.selectbox("Vehículo", vehiculo_options, index=vehiculo_index),
                    "observaciones": st.text_area("Observaciones", value=record.get("observaciones")),
                    "movil": st.text_input("Móvil", value=record.get("movil")),
                    "vehiculo_rotulado": st.selectbox("Vehículo Rotulado?", rotulado_options, index=rotulado_index)
                }
                foto_vehiculo = st.file_uploader("Adjuntar/Reemplazar foto del vehículo")
            else:
                data = {"nombre_apellido": st.text_input("Nombre", value=record.get("nombre_apellido")), "posicion": st.text_input("Posición", value=record.get("posicion")), "telefono_oficina": st.text_input("Tel. Oficina", value=record.get("telefono_oficina")), "movil": st.text_input("Móvil", value=record.get("movil")), "correo_electronico": st.text_input("Email", value=record.get("correo_electronico")), "telefono_interno": st.text_input("Tel. Interno", value=record.get("telefono_interno"))}
            uploaded_file = st.file_uploader("Adjuntar/Reemplazar documento (contrato, DNI, etc.)")
            
            c1, c2 = st.columns([1, 6])
            if c1.form_submit_button("Guardar", use_container_width=True):
                if not data.get("nombre_apellido"):
                    st.error("El nombre es obligatorio.")
                else:
                    update_record(tabla_db, st.session_state.editing_id, data)
                    if uploaded_file:
                        filename = f"{st.session_state.editing_id}_{uploaded_file.name}"; filepath = os.path.join(UPLOAD_DIR, filename)
                        with open(filepath, "wb") as f: f.write(uploaded_file.getbuffer())
                        update_file_path(tabla_db, st.session_state.editing_id, "documento_path", filename)
                    if tabla_db == "mensajeros" and foto_vehiculo:
                        filename = f"vehiculo_{st.session_state.editing_id}_{foto_vehiculo.name}"; filepath = os.path.join(UPLOAD_DIR, filename)
                        with open(filepath, "wb") as f: f.write(foto_vehiculo.getbuffer())
                        update_file_path(tabla_db, st.session_state.editing_id, "foto_vehiculo_path", filename)
                    st.toast("✅ ¡Registro actualizado!"); cancel_editing()
            if c2.form_submit_button("Cancelar", use_container_width=True): cancel_editing()
    
    # VISTA PRINCIPAL (Añadir y Listar)
    else:
        st.title(f"Gestión de {tipo_personal_actual}: {delegacion_actual}")
        if st.session_state.user_info.get("role") in ['Admin', 'Editor']:
            with st.expander("➕ Añadir Nuevo Personal"):
                with st.form(key="add_form", clear_on_submit=True):
                    if tabla_db == "mensajeros":
                        nombre_apellido=st.text_input("Nombre y Apellido"); ruta=st.text_input("Ruta"); perfil_mensajero=st.selectbox("Perfil mensajero", ["Autónomo", "Empleado", "Asegurado Fijo", "Otro"]); vehiculo_empresa=st.selectbox("Vehículo empresa", ["No", "Si"]); observaciones=st.text_area("Observaciones"); movil=st.text_input("Móvil"); vehiculo_rotulado=st.selectbox("Vehículo Rotulado?", ["Si", "No", "Pendiente de rotular"]); foto_vehiculo=st.file_uploader("Adjuntar foto del vehículo")
                    else:
                        nombre_apellido=st.text_input("Nombre y Apellido"); posicion=st.text_input("Posición"); telefono_oficina=st.text_input("Teléfono Oficina"); movil=st.text_input("Móvil"); correo_electronico=st.text_input("Correo Electrónico"); telefono_interno=st.text_input("Teléfono Interno")
                    uploaded_file = st.file_uploader("Adjuntar documento (contrato, DNI, etc.)")
                    if st.form_submit_button("Añadir Personal"):
                        if not nombre_apellido:
                            st.error("El nombre es un campo obligatorio.")
                        else:
                            if tabla_db == "mensajeros": data_form = {"nombre_apellido": nombre_apellido, "ruta": ruta, "perfil_mensajero": perfil_mensajero, "vehiculo_empresa": vehiculo_empresa, "observaciones": observaciones, "movil": movil, "vehiculo_rotulado": vehiculo_rotulado}
                            else: data_form = {"nombre_apellido": nombre_apellido, "posicion": posicion, "telefono_oficina": telefono_oficina, "movil": movil, "correo_electronico": correo_electronico, "telefono_interno": telefono_interno}
                            data_form["delegacion"] = delegacion_actual; data_form["estado"] = "Activo"
                            new_id = add_record_and_get_id(tabla_db, data_form)
                            if new_id:
                                if uploaded_file:
                                    filename = f"{new_id}_{uploaded_file.name}"; filepath = os.path.join(UPLOAD_DIR, filename)
                                    with open(filepath, "wb") as f: f.write(uploaded_file.getbuffer())
                                    update_file_path(tabla_db, new_id, "documento_path", filename)
                                if tabla_db == "mensajeros" and foto_vehiculo:
                                    filename = f"vehiculo_{new_id}_{foto_vehiculo.name}"; filepath = os.path.join(UPLOAD_DIR, filename)
                                    with open(filepath, "wb") as f: f.write(foto_vehiculo.getbuffer())
                                    update_file_path(tabla_db, new_id, "foto_vehiculo_path", filename)
                            st.toast("✅ ¡Nuevo personal añadido!"); st.rerun()
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
                        cols = st.columns([3, 2, 4, 1, 1]); cols[0].markdown(f"**{row['nombre_apellido']}**"); cols[0].write(f"Ruta: *{row.get('ruta','')}*")
                        if row.get('documento_path'):
                            doc_path = os.path.join(UPLOAD_DIR, row['documento_path']);
                            if os.path.exists(doc_path):
                                with open(doc_path, "rb") as file: cols[0].download_button(label="📄", data=file, file_name=row['documento_path'], help="Descargar documento")
                        if row.get('foto_vehiculo_path'):
                            doc_path = os.path.join(UPLOAD_DIR, row['foto_vehiculo_path']);
                            if os.path.exists(doc_path):
                                with open(doc_path, "rb") as file: cols[0].download_button(label="📸", data=file, file_name=row['foto_vehiculo_path'], help="Descargar foto vehículo")
                        cols[1].write(f"**Móvil:** {row.get('movil','')}"); cols[1].write(f"**Perfil:** {row.get('perfil_mensajero','')}"); cols[1].write(f"**Rotulado:** {row.get('vehiculo_rotulado','')}")
                        cols[2].write(f"**Observaciones:** {row.get('observaciones','')}")
                    else:
                        cols = st.columns([3, 2, 2, 1, 1]); cols[0].markdown(f"**{row['nombre_apellido']}**"); cols[0].write(f"Email: *{row.get('correo_electronico','')}*")
                        if row.get('documento_path'):
                            doc_path = os.path.join(UPLOAD_DIR, row['documento_path']);
                            if os.path.exists(doc_path):
                                with open(doc_path, "rb") as file: cols[0].download_button(label="📄", data=file, file_name=row['documento_path'], help="Descargar documento")
                        cols[1].write(f"**Móvil:** {row.get('movil','')}"); cols[1].write(f"**Tel. Oficina:** {row.get('telefono_oficina','')}"); cols[2].write(f"**Posición:** {row.get('posicion','')}")
                    if st.session_state.user_info.get("role") in ['Admin', 'Editor']:
                        cols[-2].button("✏️", key=f"edit_{row['id']}", on_click=start_editing, args=[row['id']])
                    if st.session_state.user_info.get("role") == 'Admin':
                        if cols[-1].button("Dar de Baja", key=f"baja_{row['id']}", type="primary"):
                            dar_de_baja(tabla_db, row['id'])
                            st.toast(f"✅ '{row['nombre_apellido']}' ha sido dado de baja.")
                            st.rerun()
            if not df_activos.empty:
                output = io.BytesIO();
                with pd.ExcelWriter(output, engine='openpyxl') as writer: df_activos.to_excel(writer, index=False, sheet_name='Personal')
                st.download_button(label="📥 Exportar a Excel", data=output.getvalue(), file_name=f"personal_{delegacion_actual}.xlsx")

# --- EJECUCIÓN PRINCIPAL ---
if not check_auth():
    render_login_form()
else:
    render_sidebar()
    user_role = st.session_state.user_info.get("role", "Lector")
    user_delegacion = st.session_state.user_info.get("delegacion")

    if user_role == "Lector" and user_delegacion:
        render_lector_view(user_delegacion)
    elif user_role in ["Admin", "Editor"]:
        render_admin_view()
    else:
        st.warning("No tienes permisos suficientes.")
