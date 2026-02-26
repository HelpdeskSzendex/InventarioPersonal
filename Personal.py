# Personal.py
import streamlit as st
import pandas as pd
import os
import io
import json
from datetime import date
from utils.db import (
    DELEGACIONES, PERFIL_OPTS, ROTULADO_OPTS, UPLOAD_DIR,
    fetch_data, fetch_all_messengers, fetch_all_office_staff,
    fetch_single_record, update_record, add_record_and_get_id,
    dar_de_baja, update_file_path, get_estado_licencias_total
)
from utils.auth import render_login_form, logout

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Gestión de Personal", page_icon="👥", layout="wide")

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

# --- FUNCIÓN DE GESTIÓN DE LICENCIAS ---
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

# --- VISTA PARA LECTORES (SOLO LECTURA) ---
def render_lector_view(user_delegacion):
    st.title(f"📍 Consulta de Personal: {user_delegacion}")
    tipo = st.selectbox("Selecciona el tipo de personal:", ["Mensajeros", "Oficina"])
    
    tabla = "mensajeros" if tipo == "Mensajeros" else "oficina"
        
    st.markdown("---")
    st.subheader("Listado de Personal Activo")

    with st.spinner("Cargando personal..."):
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
                    codigos_str = ", ".join(codigos_raw) if isinstance(codigos_raw, list) else (str(codigos_raw) if codigos_raw else "N/A")

                    col1.markdown(f"""
                        **Ruta:** {row.get('ruta', 'N/A')} <br>
                        **Móvil:** {row.get('movil', 'N/A')} <br>
                        **Email:** {row.get('email_personal', 'N/A')}
                    """, unsafe_allow_html=True)
                    
                    paq = '✅ Sí' if row.get('hace_paqueteria') else '❌ No'
                    dhl = '✅ Sí' if row.get('DHL') else '❌ No'
                    adr = '✅ Sí' if row.get('ADR') else '❌ No'
                    
                    col2.markdown(f"""
                        **Perfil:** {row.get('perfil_mensajero', 'N/A')} <br>
                        **Licencias DL:** {codigos_str} <br>
                        **Paq:** {paq} | **DHL:** {dhl} | **ADR:** {adr}
                    """, unsafe_allow_html=True)
                    
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

    # Confirmación de Baja
    if st.session_state.baja_in_progress:
        st.components.v1.html("<script>window.scrollTo(0, 0);</script>", height=0)
        record_id, record_name, tabla, delegacion = st.session_state.baja_in_progress
        st.error("⚠️ Confirmación de Baja Requerida")
        with st.container(border=True):
            st.warning(f"Estás a punto de dar de baja a **{record_name}**.")
            motivo = st.text_area("Por favor, introduce el motivo de la baja:", key=f"motivo_{record_id}")
            col1, col2 = st.columns(2)
            if col1.button("✅ Confirmar Baja", type="primary", use_container_width=True):
                if motivo:
                    dar_de_baja(tabla, record_id, record_name, st.session_state.user_info['email'], delegacion, motivo)
                    st.session_state.baja_in_progress = None
                    st.toast(f"'{record_name}' ha sido dado de baja correctamente.", icon="✅")
                    st.rerun()
                else:
                    st.error("El motivo es obligatorio para dar de baja.")
            if col2.button("❌ Cancelar", use_container_width=True):
                st.session_state.baja_in_progress = None
                st.rerun()

    # Helpers de Navegación
    def set_delegacion(delegacion):
        st.session_state.delegacion_seleccionada = delegacion
        st.session_state.tipo_personal = None
        st.session_state.editing_id = None

    def reset_delegacion():
        st.session_state.delegacion_seleccionada = None
        st.session_state.tipo_personal = None
        st.session_state.editing_id = None

    if st.session_state.delegacion_seleccionada is None:
        st.title("🗺️ Selector de Delegaciones")
        col1, col2, col3 = st.columns(3); columnas = [col1, col2, col3] * 3
        for i, delegacion in enumerate(DELEGACIONES):
            if i < len(columnas):
                with columnas[i]: st.button(delegacion, on_click=set_delegacion, args=[delegacion], use_container_width=True, key=f"btn_{delegacion}")
        return

    delegacion_actual = st.session_state.delegacion_seleccionada
    st.button("⬅️ Volver al selector", on_click=reset_delegacion)

    # Vista Sanitario (Global)
    if delegacion_actual == "Sanitario":
        st.title(f"⚕️ Vista Global de Personal (Solo Lectura)")
        tab_mensajeros, tab_oficina = st.tabs(["Todos los Mensajeros", "Todo el Personal de Oficina"])
        with tab_mensajeros:
            df_mensajeros = fetch_all_messengers()
            search_query_mens = st.text_input("Buscar por nombre de mensajero", key="search_global_mens")
            if search_query_mens: df_mensajeros = df_mensajeros[df_mensajeros["nombre_apellido"].str.contains(search_query_mens, case=False, na=False)]
            if df_mensajeros.empty: st.info("No hay mensajeros activos.")
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
            df_oficina = fetch_all_office_staff()
            search_query_ofi = st.text_input("Buscar por nombre de personal de oficina", key="search_global_ofi")
            if search_query_ofi: df_oficina = df_oficina[df_oficina["nombre_apellido"].str.contains(search_query_ofi, case=False, na=False)]
            if df_oficina.empty: st.info("No hay personal de oficina activo.")
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
        # Panel de Control Delegación
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
                st.progress(min(usadas_lic / total_lic, 1.0), text=f"Ocupación: {int((usadas_lic/total_lic)*100)}%")
                if disponibles_lic <= 0: st.error("⚠️ **Inventario agotado.**")
            
            st.markdown("---")
            st.subheader("¿Qué personal deseas gestionar?")
            col1, col2 = st.columns(2)
            if col1.button("🚚 Mensajeros", use_container_width=True): st.session_state.tipo_personal = "Mensajeros"; st.rerun()
            if col2.button("💼 Oficina", use_container_width=True): st.session_state.tipo_personal = "Oficina"; st.rerun()
            return
        
        tipo_personal_actual = st.session_state.tipo_personal
        tabla_db = "mensajeros" if tipo_personal_actual == "Mensajeros" else "oficina"
        if st.button("⬅️ Volver a seleccionar tipo"): st.session_state.tipo_personal = None; st.session_state.editing_id = None; st.rerun()

        # FORMULARIO EDICIÓN
        if st.session_state.editing_id:
            st.title(f"✏️ Editando {tipo_personal_actual}")
            record = fetch_single_record(tabla_db, st.session_state.editing_id)
            
            with st.container(border=True):
                if tabla_db == "mensajeros":
                    nombre_apellido = st.text_input("Nombre", value=record.get("nombre_apellido"))
                    ruta = st.text_input("Ruta", value=record.get("ruta"))
                    perfil_index = PERFIL_OPTS.index(record.get("perfil_mensajero")) if record.get("perfil_mensajero") in PERFIL_OPTS else 0
                    perfil_mensajero = st.selectbox("Perfil", PERFIL_OPTS, index=perfil_index)
                    observaciones = st.text_area("Observaciones", value=record.get("observaciones"))
                    movil = st.text_input("Móvil", value=record.get("movil"))
                    rotulado_index = ROTULADO_OPTS.index(record.get("vehiculo_rotulado")) if record.get("vehiculo_rotulado") in ROTULADO_OPTS else 1
                    vehiculo_rotulado = st.selectbox("Vehículo Rotulado?", ROTULADO_OPTS, index=rotulado_index)
                    email_personal = st.text_input("Email Personal", value=record.get("email_personal", ""))
                    codigos_dl_final = render_license_manager(record.get("codigo_dl"), key_prefix="edit")
                    hace_paqueteria = st.checkbox("¿Hace paquetería?", value=record.get("hace_paqueteria", False))
                    dhl = st.checkbox("DHL", value=record.get("DHL", False))
                    adr = st.checkbox("ADR", value=record.get("ADR", False))
                    st.markdown("---")
                    if record.get("foto_vehiculo_path"):
                        c1, c2 = st.columns([3, 1]); c1.write(f"Foto actual: `{record['foto_vehiculo_path']}`")
                        if c2.button("Quitar Foto", key="rm_photo_btn"): update_file_path(tabla_db, st.session_state.editing_id, "foto_vehiculo_path", None); st.rerun()
                    foto_vehiculo = st.file_uploader("Adjuntar/Reemplazar foto del vehículo", key="foto_vehiculo_edit")
                    data = {"nombre_apellido": nombre_apellido, "ruta": ruta, "perfil_mensajero": perfil_mensajero, "observaciones": observaciones, "movil": movil, "vehiculo_rotulado": vehiculo_rotulado, "email_personal": email_personal, "codigo_dl": codigos_dl_final, "hace_paqueteria": hace_paqueteria, "DHL": dhl, "ADR": adr}
                else:
                    nombre_apellido = st.text_input("Nombre", value=record.get("nombre_apellido"))
                    posicion = st.text_input("Posición", value=record.get("posicion"))
                    telefono_oficina = st.text_input("Tel. Oficina", value=record.get("telefono_oficina"))
                    movil = st.text_input("Móvil", value=record.get("movil"))
                    correo_electronico = st.text_input("Email", value=record.get("correo_electronico"))
                    telefono_interno = st.text_input("Tel. Interno", value=record.get("telefono_interno"))
                    data = {"nombre_apellido": nombre_apellido, "posicion": posicion, "telefono_oficina": telefono_oficina, "movil": movil, "correo_electronico": correo_electronico, "telefono_interno": telefono_interno}
                
                st.markdown("---")
                # Gestión Documentos
                current_docs = record.get("documento_path")
                doc_list = []
                if current_docs:
                    try:
                        parsed = json.loads(current_docs); doc_list = parsed if isinstance(parsed, list) else [str(current_docs)]
                    except: doc_list = [str(current_docs)]
                if doc_list:
                    st.caption("Gestión de Documentos:")
                    for i, doc_name in enumerate(doc_list):
                        c1, c2, c3 = st.columns([6, 1, 1]); c1.text(f"📄 {doc_name}")
                        doc_path = os.path.join(UPLOAD_DIR, doc_name)
                        if os.path.exists(doc_path):
                            with open(doc_path, "rb") as f: c2.download_button("📥", f, file_name=doc_name, key=f"dledit_{i}")
                        if c3.button("🗑️", key=f"rm_doc_{i}"):
                            doc_list.pop(i); new_val = json.dumps(doc_list) if doc_list else None
                            update_file_path(tabla_db, st.session_state.editing_id, "documento_path", new_val); st.rerun()

                uploaded_files = st.file_uploader("Adjuntar nuevos documentos", key="uploaded_file_edit", accept_multiple_files=True)
                
                st.markdown("---")
                c1, c2 = st.columns([1, 6])
                if c1.button("💾 Guardar", type="primary", use_container_width=True):
                    update_record(tabla_db, st.session_state.editing_id, data)
                    if uploaded_files:
                        current_list = doc_list.copy()
                        for up_file in uploaded_files:
                            filename = f"{st.session_state.editing_id}_{up_file.name}"
                            with open(os.path.join(UPLOAD_DIR, filename), "wb") as f: f.write(up_file.getbuffer())
                            current_list.append(filename)
                        update_file_path(tabla_db, st.session_state.editing_id, "documento_path", json.dumps(current_list))
                    if tabla_db == "mensajeros" and foto_vehiculo:
                        filename = f"vehiculo_{st.session_state.editing_id}_{foto_vehiculo.name}"
                        with open(os.path.join(UPLOAD_DIR, filename), "wb") as f: f.write(foto_vehiculo.getbuffer())
                        update_file_path(tabla_db, st.session_state.editing_id, "foto_vehiculo_path", filename)
                    st.toast("¡Registro actualizado correctamente!", icon="✅")
                    if f"temp_license_list_edit" in st.session_state: del st.session_state[f"temp_license_list_edit"]
                    st.session_state.editing_id = None; st.rerun()
                if c2.button("Cancelar", use_container_width=True):
                    if f"temp_license_list_edit" in st.session_state: del st.session_state[f"temp_license_list_edit"]
                    st.session_state.editing_id = None; st.rerun()
        
        # LISTADO Y ALTA
        else:
            st.title(f"Gestión de {tipo_personal_actual}: {delegacion_actual}")
            if st.session_state.show_add_form:
                with st.container(border=True):
                    st.subheader("📝 Nuevo Personal")
                    if tabla_db == "mensajeros":
                        nombre_apellido=st.text_input("Nombre y Apellido", key="add_nombre")
                        ruta=st.text_input("Ruta", key="add_ruta")
                        perfil_mensajero=st.selectbox("Perfil", PERFIL_OPTS, key="add_perfil")
                        observaciones=st.text_area("Observaciones", key="add_obs")
                        movil=st.text_input("Móvil", key="add_movil")
                        vehiculo_rotulado=st.selectbox("Vehículo Rotulado?", ROTULADO_OPTS, key="add_rotulado")
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

                    uploaded_files = st.file_uploader("Adjuntar documentos", key="add_doc", accept_multiple_files=True)
                    s_col1, s_col2 = st.columns([1,5])

                    if s_col1.button("✅ Añadir", type="primary", use_container_width=True):
                        if nombre_apellido:
                            data_form = {"nombre_apellido": nombre_apellido, "delegacion": delegacion_actual, "estado": "Activo"}
                            if tabla_db == "mensajeros":
                                data_form.update({"ruta": ruta, "perfil_mensajero": perfil_mensajero, "observaciones": observaciones, "movil": movil, "vehiculo_rotulado": vehiculo_rotulado, "email_personal": email_personal, "codigo_dl": codigos_dl_final, "hace_paqueteria": hace_paqueteria, "DHL": dhl, "ADR": adr})
                            else:
                                data_form.update({"posicion": posicion, "telefono_oficina": telefono_oficina, "movil": movil, "correo_electronico": correo_electronico, "telefono_interno": telefono_interno})

                            new_id = add_record_and_get_id(tabla_db, data_form, st.session_state.user_info['email'], delegacion_actual)
                            if new_id:
                                if uploaded_files:
                                    saved_names = []
                                    for up_file in uploaded_files:
                                        filename = f"{new_id}_{up_file.name}"
                                        with open(os.path.join(UPLOAD_DIR, filename), "wb") as f: f.write(up_file.getbuffer())
                                        saved_names.append(filename)
                                    update_file_path(tabla_db, new_id, "documento_path", json.dumps(saved_names))
                                if tabla_db == "mensajeros" and foto_vehiculo:
                                    filename = f"vehiculo_{new_id}_{foto_vehiculo.name}"
                                    with open(os.path.join(UPLOAD_DIR, filename), "wb") as f: f.write(foto_vehiculo.getbuffer())
                                    update_file_path(tabla_db, new_id, "foto_vehiculo_path", filename)
                                st.toast("¡Nuevo personal añadido!", icon="✅")
                                st.session_state.show_add_form = False
                                if "temp_license_list_add" in st.session_state: del st.session_state["temp_license_list_add"]
                                st.rerun()
                        else: st.error("El nombre es obligatorio.")

                    if s_col2.button("❌ Cancelar", use_container_width=True):
                        st.session_state.show_add_form = False
                        if "temp_license_list_add" in st.session_state: del st.session_state["temp_license_list_add"]
                        st.rerun()
            else:
                if st.button("➕ Añadir Nuevo Personal"): st.session_state.show_add_form = True; st.rerun()

            st.markdown("---")
            df_activos = fetch_data(tabla_db, delegacion_actual)
            search_query = st.text_input("Buscar por nombre", key=f"search_{tabla_db}")
            if search_query: df_activos = df_activos[df_activos["nombre_apellido"].str.contains(search_query, case=False, na=False)]

            if df_activos.empty: st.info("No hay personal que coincida.")
            else:
                for _, row in df_activos.iterrows():
                    with st.container(border=True):
                        header_cols = st.columns([5, 2])
                        header_cols[0].markdown(f"**{row['nombre_apellido']}**")
                        with header_cols[1]:
                            action_cols = st.columns(2)
                            if st.session_state.user_info.get("role") in ['Admin', 'Editor']:
                                if action_cols[0].button("✏️", key=f"edit_{row['id']}", use_container_width=True, help="Editar"):
                                    st.session_state.editing_id = row['id']; st.rerun()
                            if st.session_state.user_info.get("role") == 'Admin':
                                if action_cols[1].button("🚫", key=f"baja_{row['id']}", type="primary", use_container_width=True, help="Dar de Baja"):
                                    st.session_state.baja_in_progress = (row['id'], row['nombre_apellido'], tabla_db, delegacion_actual); st.rerun()
                        
                        if tabla_db == "mensajeros":
                            col1, col2, col3 = st.columns(3)
                            codigos_raw = row.get('codigo_dl')
                            codigos_display = (f"📚 {len(codigos_raw)} Licencias: " + ", ".join(codigos_raw)) if isinstance(codigos_raw, list) else (f"Licencia: {codigos_raw}" if codigos_raw else "Sin licencias")
                            col1.markdown(f"<small><b>Ruta:</b> {row.get('ruta', 'N/A')}</small><br><small><b>Móvil:</b> {row.get('movil', 'N/A')}</small><br><small><b>Email:</b> {row.get('email_personal', 'N/A')}</small>", unsafe_allow_html=True)
                            col2.markdown(f"<small><b>Perfil:</b> {row.get('perfil_mensajero', 'N/A')}</small><br><small><b>{codigos_display}</b></small><br><small><b>Paq:</b> {'✅ Sí' if row.get('hace_paqueteria') else '❌ No'} | <b>DHL:</b> {'✅ Sí' if row.get('DHL') else '❌ No'} | <b>ADR:</b> {'✅ Sí' if row.get('ADR') else '❌ No'}</small>", unsafe_allow_html=True)
                            with col3:
                                display_documents_buttons(row.get('documento_path'), row['id'])
                                foto_path = row.get('foto_vehiculo_path')
                                if foto_path and os.path.exists(os.path.join(UPLOAD_DIR, foto_path)):
                                    with open(os.path.join(UPLOAD_DIR, foto_path), "rb") as file: st.download_button(label="📸 Foto", data=file, file_name=foto_path, use_container_width=True)
                                if row.get('observaciones') and row.get('observaciones') != 'None':
                                    with st.expander("Obs."): st.write(row.get('observaciones'))
                        else: # Oficina
                            col1, col2 = st.columns(2)
                            col1.markdown(f"<small><b>Posición:</b> {row.get('posicion', 'N/A')}</small><br><small><b>Email:</b> {row.get('correo_electronico', 'N/A')}</small>", unsafe_allow_html=True)
                            col2.markdown(f"<small><b>Móvil:</b> {row.get('movil', 'N/A')}</small><br><small><b>Tel. Oficina:</b> {row.get('telefono_oficina', 'N/A')}</small>", unsafe_allow_html=True)
                
                if not df_activos.empty:
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer: df_activos.to_excel(writer, index=False, sheet_name='Personal')
                    st.download_button(label="📥 Exportar a Excel", data=output.getvalue(), file_name=f"personal_{delegacion_actual}.xlsx")

# --- EJECUCIÓN ---
if "user_info" not in st.session_state:
    render_login_form()
else:
    role = st.session_state.user_info.get("role", "Lector")
    deleg = st.session_state.user_info.get("delegacion")
    st.sidebar.success(f"Sesión: {st.session_state.user_info.get('email')}")
    st.sidebar.info(f"Rol: **{role}**")
    if deleg: st.sidebar.write(f"Delegación: **{deleg}**")
    if st.sidebar.button("Cerrar Sesión"): logout()

    if role == "Lector" and deleg: render_lector_view(deleg)
    elif role in ["Admin", "Editor"]: render_admin_view()
    else: st.warning("No tienes permisos suficientes.")
