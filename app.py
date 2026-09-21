import streamlit as st
import pandas as pd
from sqlalchemy import text, create_engine
import urllib.parse
import datetime

# 1. Configuración de página
st.set_page_config(page_title="SIMI RRHH - Panel Avanzado", page_icon="📊", layout="wide")

# 2. Conexión a la base de datos Neon
@st.cache_resource
def get_engine():
    db_url = st.secrets["DATABASE_URL"]
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return create_engine(db_url)

engine = get_engine()

# Crear tablas adicionales si no existen (control de incidencias)
with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS incidencias (
            id SERIAL PRIMARY KEY,
            empleado_id INT REFERENCES empleados(id) ON DELETE CASCADE,
            fecha DATE NOT NULL,
            tipo TEXT NOT NULL, -- Atraso, No Marca, Salida Anticipada, Falta, Presente OK
            minutos_atraso INT DEFAULT 0,
            comentario TEXT,
            registrado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """))

st.title("🚀 SIMI - Gestión y Analítica Avanzada de RRHH")

# 3. Pestañas de Navegación
tab_personal, tab_asistencia, tab_reportes, tab_correos = st.tabs([
    "👥 Personal", 
    "⏰ Control de Asistencia e Incidencias", 
    "📈 Reportes y Analíticas", 
    "✉️ Centro de Comunicación"
])

# --- PESTAÑA 1: GESTIÓN DE PERSONAL ---
with tab_personal:
    st.header("Directorio de Colaboradores")
    
    with st.form("form_nuevo_empleado", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        nombre = col1.text_input("Nombre Completo")
        correo = col2.text_input("Correo Electrónico")
        cargo = col3.text_input("Cargo / Área")
        submit = st.form_submit_button("Registrar Colaborador", type="primary")

        if submit and nombre and correo:
            try:
                with engine.begin() as conn:
                    conn.execute(
                        text("INSERT INTO empleados (nombre, correo, cargo) VALUES (:n, :c, :car)"), 
                        {"n": nombre, "c": correo, "car": cargo}
                    )
                st.success(f"¡Colaborador {nombre} registrado exitosamente!")
                st.rerun()
            except Exception as e:
                st.error(f"Error al registrar: {e}")

    st.subheader("Lista Activa de Colaboradores")
    try:
        df_empleados = pd.read_sql("SELECT * FROM empleados ORDER BY creado_en DESC", engine)
        if not df_empleados.empty:
            st.dataframe(df_empleados[['nombre', 'correo', 'cargo']], use_container_width=True)
        else:
            st.info("No hay colaboradores registrados aún.")
    except Exception as e:
        st.info("Agrega tu primer colaborador arriba para comenzar.")

# --- PESTAÑA 2: CONTROL DE ASISTENCIA E INCIDENCIAS ---
with tab_asistencia:
    st.header("Registro Diario de Asistencia e Incidencias")
    st.markdown("Registra el estado de cada colaborador para la fecha de hoy.")
    
    try:
        df_empleados = pd.read_sql("SELECT id, nombre, cargo FROM empleados", engine)
        
        if not df_empleados.empty:
            hoy = datetime.date.today()
            st.info(f"Fecha de registro: **{hoy}**")
            
            for index, emp in df_empleados.iterrows():
                with st.container():
                    col1, col2, col3, col4, col5 = st.columns([2, 1.5, 1.5, 1, 1.5])
                    
                    col1.markdown(f"**{emp['nombre']}**<br><span style='color:gray;font-size:12px;'>{emp['cargo']}</span>", unsafe_allow_html=True)
                    
                    estado = col2.selectbox("Estado", ["Presente OK", "Atraso", "No Marcó", "Salida Anticipada", "Falta Injustificada"], key=f"est_{emp['id']}")
                    
                    minutos = 0
                    if estado == "Atraso":
                        minutos = col3.number_input("Min. Atraso", min_value=1, max_value=300, value=15, key=f"min_{emp['id']}")
                    else:
                        col3.write("") # Espacio vacío

                    comentario = col4.text_input("Nota opcional", key=f"nota_{emp['id']}")
                    
                    if col5.button("Guardar", key=f"btn_inc_{emp['id']}"):
                        with engine.begin() as conn:
                            conn.execute(
                                text("INSERT INTO incidencias (empleado_id, fecha, tipo, minutos_atraso, comentario) VALUES (:e_id, :f, :t, :m, :c)"),
                                {"e_id": int(emp['id']), "f": hoy, "t": estado, "m": minutos, "c": comentario}
                            )
                        st.success(f"Incidencia guardada para {emp['nombre']}")
                    st.divider()
        else:
            st.warning("Primero debes registrar colaboradores en la pestaña 'Personal'.")
    except Exception as e:
        st.info("Configura tu base de colaboradores para habilitar esta sección.")

# --- PESTAÑA 3: REPORTES Y ANALÍTICAS ---
with tab_reportes:
    st.header("📊 Analíticas y Reportes de Asistencia")
    
    try:
        query_incidencias = """
            SELECT i.id, e.nombre, e.cargo, i.fecha, i.tipo, i.minutos_atraso, i.comentario 
            FROM incidencias i 
            JOIN empleados e ON i.empleado_id = e.id 
            ORDER BY i.fecha DESC
        """
        df_incidencias = pd.read_sql(query_incidencias, engine)
        
        if not df_incidencias.empty:
            # Métricas superiores
            total_incidencias = len(df_incidencias)
            atrasos = len(df_incidencias[df_incidencias['tipo'] == 'Atraso'])
            faltas = len(df_incidencias[df_incidencias['tipo'] == 'Falta Injustificada'])
            no_marcas = len(df_incidencias[df_incidencias['tipo'] == 'No Marcó'])
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Registros", total_incidencias)
            m2.metric("Total Atrasos", atrasos, delta_color="inverse")
            m3.metric("Faltas", faltas, delta_color="inverse")
            m4.metric("No Marcaron", no_marcas, delta_color="inverse")
            
            st.divider()
            
            # Gráficos analíticos
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.subheader("Incidencias por Tipo")
                conteo_tipos = df_incidencias['tipo'].value_counts()
                st.bar_chart(conteo_tipos)
                
            with col_g2:
                st.subheader("Colaboradores con Más Atrasos / Faltas")
                conteo_personal = df_incidencias['nombre'].value_counts()
                st.bar_chart(conteo_personal)

            st.subheader("Historial Completo de Incidencias")
            st.dataframe(df_incidencias[['nombre', 'cargo', 'fecha', 'tipo', 'minutos_atraso', 'comentario']], use_container_width=True)
        else:
            st.info("Aún no hay incidencias registradas. Empieza a registrar la asistencia en la pestaña anterior para ver los reportes.")
    except Exception as e:
        st.info("Registra asistencias para generar analíticas.")

# --- PESTAÑA 4: CENTRO DE COMUNICACIÓN (CORREOS) ---
with tab_correos:
    st.header("✉️ Generador Inteligente de Comunicados y Llamados de Atención")
    
    try:
        df_empleados = pd.read_sql("SELECT id, nombre, correo FROM empleados", engine)
        
        if not df_empleados.empty:
            nombres = df_empleados['nombre'].tolist()
            seleccion = st.selectbox("Seleccionar Colaborador", nombres, key="sel_correo")
            
            emp_seleccionado = df_empleados[df_empleados['nombre'] == seleccion].iloc[0]
            
            tipo_correo = st.selectbox("Motivo del Correo", [
                "Llamado de atención por Atraso", 
                "Aviso por Inasistencia / No Marcación", 
                "Notificación por Salida Anticipada", 
                "Felicitación por Excelente Puntualidad"
            ])
            
            # Generador dinámico de contenido según el motivo
            if "Atraso" in tipo_correo:
                asunto = "SIMI RRHH - Notificación de Registro de Atraso"
                mensaje = f"Estimado/a {emp_seleccionado['nombre']},\n\nLe escribimos desde el departamento de Recursos Humanos de SIMI para notificarle que hemos registrado atrasos recientes en su jornada laboral.\n\nLa puntualidad es fundamental para el buen funcionamiento de nuestro equipo. Le pedimos tomar las precauciones necesarias para cumplir con su horario.\n\nSi existe alguna justificación de fuerza mayor, por favor respóndanos este correo.\n\nAtentamente,\nEquipo de RRHH - SIMI."
            elif "Inasistencia" in tipo_correo:
                asunto = "SIMI RRHH - Aviso Importante: Falta de Registro / Inasistencia"
                mensaje = f"Estimado/a {emp_seleccionado['nombre']},\n\nNos ponemos en contacto desde Recursos Humanos ya que registramos una inasistencia o falta de marcación en su turno correspondiente.\n\nPor favor, acérquese a nuestra oficina o responda este correo a la brevedad para justificar la situación.\n\nSaludos cordiales,\nEquipo de RRHH - SIMI."
            elif "Salida Anticipada" in tipo_correo:
                asunto = "SIMI RRHH - Registro de Salida Anticipada"
                mensaje = f"Hola {emp_seleccionado['nombre']},\n\nNotamos un registro de salida anticipada en su turno. Queremos verificar que todo se encuentre en orden y conocer el motivo de su retiro antes de finalizar la jornada.\n\nQuedamos atentos a sus comentarios,\nEquipo de RRHH - SIMI."
            else:
                asunto = "SIMI RRHH - ¡Felicitaciones por tu excelente puntualidad!"
                mensaje = f"Hola {emp_seleccionado/nombre if 'nombre' in locals() else emp_seleccionado['nombre']},\n\nQueremos felicitarle por su impecable registro de asistencia y compromiso constante con sus horarios.\n\n¡Muchas gracias por su dedicación!\n\nSaludos cordiales,\nEquipo de RRHH - SIMI."

            st.text_input("Asunto del Correo", value=asunto)
            cuerpo_final = st.text_area("Cuerpo del Mensaje", value=mensaje, height=180)
            
            mailto_link = f"mailto:{emp_seleccionado['correo']}?subject={urllib.parse.quote(asunto)}&body={urllib.parse.quote(cuerpo_final)}"
            
            st.markdown(f'<a href="{mailto_link}" target="_blank"><button style="background-color:#003366;color:white;padding:14px 28px;border:none;border-radius:8px;cursor:pointer;font-weight:bold;font-size:16px;"><i class="fa-solid fa-paper-plane"></i> Abrir Correo y Enviar</button></a>', unsafe_allow_html=True)
            st.caption("Esto abrirá automáticamente tu programa de correo predeterminado (Outlook, Gmail, etc.) con el mensaje redactado para el colaborador.")
        else:
            st.info("Agrega colaboradores en la pestaña 'Personal' para habilitar el envío de correos.")
    except Exception as e:
        st.info("Configura tu base de datos para habilitar el centro de comunicación.")
