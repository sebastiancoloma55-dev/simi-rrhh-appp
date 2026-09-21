import streamlit as st
import pandas as pd
from sqlalchemy import text
import urllib.parse

# 1. Configuración de página
st.set_page_config(page_title="SIMI RRHH", page_icon="👥", layout="wide")

# 2. Conexión a la base de datos Neon (Postgres)
conn = st.connection("postgresql", type="sql", url=st.secrets["DATABASE_URL"])

st.title("👥 SIMI - Gestión de Asistencia y Turnos")

# 3. Pestañas de navegación
tab_personal, tab_turnos, tab_correos = st.tabs(["Personal", "Turnos y Asistencia", "Comunicación"])

# --- PESTAÑA 1: PERSONAL ---
with tab_personal:
    st.header("Registrar Nuevo Empleado")
    with st.form("form_nuevo_empleado", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        nombre = col1.text_input("Nombre Completo")
        correo = col2.text_input("Correo Electrónico")
        cargo = col3.text_input("Cargo")
        submit = st.form_submit_button("Agregar Empleado", type="primary")

        if submit and nombre and correo:
            with conn.session as s:
                s.execute(text("INSERT INTO empleados (nombre, correo, cargo) VALUES (:n, :c, :car)"), 
                          {"n": nombre, "c": correo, "car": cargo})
                s.commit()
            st.success("¡Empleado agregado correctamente!")
            st.rerun()

    st.subheader("Lista de Empleados")
    df_empleados = conn.query("SELECT * FROM empleados ORDER BY creado_en DESC")
    if not df_empleados.empty:
        st.dataframe(df_empleados[['nombre', 'correo', 'cargo']], use_container_width=True)
    else:
        st.info("No hay empleados registrados aún.")

# --- PESTAÑA 2: TURNOS Y ASISTENCIA ---
with tab_turnos:
    st.header("Asignación de Turnos (Hoy)")
    df_empleados = conn.query("SELECT id, nombre, cargo FROM empleados")
    
    if not df_empleados.empty:
        for index, emp in df_empleados.iterrows():
            col1, col2, col3, col4 = st.columns(4)
            col1.write(f"**{emp['nombre']}**\n{emp['cargo']}")
            
            turno = col2.selectbox("Turno", ["Sin asignar", "Mañana", "Tarde", "Noche"], key=f"turno_{emp['id']}")
            estado = col3.selectbox("Estado", ["Pendiente", "Presente", "Ausente", "Día Libre"], key=f"est_{emp['id']}")
            
            if col4.button("Guardar Asistencia", key=f"btn_{emp['id']}"):
                import datetime
                hoy = datetime.date.today().isoformat()
                with conn.session as s:
                    s.execute(text("INSERT INTO turnos (empleado_id, fecha, turno, estado) VALUES (:e_id, :f, :t, :est)"), 
                              {"e_id": emp['id'], "f": hoy, "t": turno, "est": estado})
                    s.commit()
                st.success(f"Turno y asistencia guardados para {emp['nombre']}")
            st.divider()
    else:
        st.warning("Agrega empleados en la pestaña 'Personal' primero.")

# --- PESTAÑA 3: CORREOS ---
with tab_correos:
    st.header("Preparar Correo para Personal")
    df_empleados = conn.query("SELECT nombre, correo FROM empleados")
    
    if not df_empleados.empty:
        nombres = df_empleados['nombre'].tolist()
        seleccion = st.selectbox("Seleccionar Empleado", nombres)
        
        emp_seleccionado = df_empleados[df_empleados['nombre'] == seleccion].iloc[0]
        
        motivo = st.selectbox("Motivo", ["Recordatorio de Turno", "Aviso de Inasistencia", "Día Libre", "Felicitaciones por Desempeño"])
        
        asunto = f"SIMI RRHH - {motivo}"
        mensaje = f"Hola {emp_seleccionado['nombre']},\n\nTe escribimos desde el área de Recursos Humanos para informarte sobre: {motivo}.\n\nPor favor, responde este correo si tienes alguna duda.\n\nSaludos cordiales,\nEquipo SIMI"
        
        st.text_input("Asunto", value=asunto)
        cuerpo_final = st.text_area("Mensaje", value=mensaje, height=150)
        
        mailto_link = f"mailto:{emp_seleccionado['correo']}?subject={urllib.parse.quote(asunto)}&body={urllib.parse.quote(cuerpo_final)}"
        st.markdown(f'<a href="{mailto_link}" target="_blank"><button style="background-color:#003366;color:white;padding:12px 24px;border:none;border-radius:6px;cursor:pointer;font-weight:bold;">Abrir Correo y Enviar</button></a>', unsafe_allow_html=True)
    else:
        st.info("Agrega empleados para poder enviar correos.")
