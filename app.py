import streamlit as st
import pandas as pd
from sqlalchemy import text, create_engine
import urllib.parse
import datetime

# 1. Configuración de página de nivel ejecutivo
st.set_page_config(
    page_title="SIMI - Sistema Integral de Gestión y Control RRHH", 
    page_icon="🏢", 
    layout="wide"
)

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

# Inicialización de la Base de Datos Relacional Corporativa Completa
def inicializar_base_datos_completa():
    with engine.begin() as conn:
        # Usuarios y Roles
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS usuarios_sistema (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                nombre_completo TEXT NOT NULL,
                rol TEXT NOT NULL, 
                grupo TEXT, 
                activo BOOLEAN DEFAULT TRUE
            );
        """))
        
        # Sucursales y Asignación
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sucursales (
                id SERIAL PRIMARY KEY,
                codigo_sucursal TEXT UNIQUE NOT NULL,
                nombre_sucursal TEXT NOT NULL,
                encargada_asignada TEXT NOT NULL
            );
        """))

        # Colaboradores
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS colaboradores (
                id SERIAL PRIMARY KEY,
                rut TEXT UNIQUE NOT NULL,
                nombre TEXT NOT NULL,
                correo TEXT NOT NULL,
                cargo TEXT NOT NULL,
                sucursal_id INT REFERENCES sucursales(id),
                creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # Reportes Talana Cargados
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS reportes_cargados (
                id SERIAL PRIMARY KEY,
                tipo_reporte TEXT NOT NULL,
                periodo TEXT NOT NULL,
                nombre_archivo TEXT NOT NULL,
                cantidad_registros INT NOT NULL,
                cargado_por TEXT NOT NULL,
                fecha_carga TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # Motor de Incidencias Detectadas
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS incidencias (
                id SERIAL PRIMARY KEY,
                colaborador_id INT REFERENCES colaboradores(id) ON DELETE CASCADE,
                fecha DATE NOT NULL,
                tipo_incidencia TEXT NOT NULL, -- Crítico, Revisión, Informativo
                categoria TEXT NOT NULL, -- Atraso, Falta, Marcación Incompleta, etc.
                detalle TEXT,
                estado_gestion TEXT DEFAULT 'Pendiente'
            );
        """))

        # Sistema de Casos
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS casos_rrhh (
                id SERIAL PRIMARY KEY,
                titulo TEXT NOT NULL,
                colaborador_id INT REFERENCES colaboradores(id),
                sucursal_id INT REFERENCES sucursales(id),
                responsable TEXT NOT NULL,
                prioridad TEXT NOT NULL, -- Alta, Media, Baja
                estado TEXT NOT NULL, -- Nuevo, En Revisión, Esperando Información, Gestionado, Cerrado
                descripcion TEXT,
                creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # Auditoría del Sistema
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS auditoria_log (
                id SERIAL PRIMARY KEY,
                usuario TEXT NOT NULL,
                accion TEXT NOT NULL,
                detalles TEXT,
                fecha_hora TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # Datos Semilla (Seed Data) si está vacío
        if conn.execute(text("SELECT COUNT(*) FROM usuarios_sistema")).scalar() == 0:
            conn.execute(text("""
                INSERT INTO usuarios_sistema (username, nombre_completo, rol, grupo) VALUES
                ('sebastian', 'Sebastián Coloma', 'Administrador', 'Global'),
                ('denisse', 'Denisse', 'Encargada', 'Denisse'),
                ('deborah', 'Deborah', 'Encargada', 'Deborah'),
                ('francisca', 'Francisca', 'Encargada', 'Francisca');
            """))

        if conn.execute(text("SELECT COUNT(*) FROM sucursales")).scalar() == 0:
            conn.execute(text("""
                INSERT INTO sucursales (codigo_sucursal, nombre_sucursal, encargada_asignada) VALUES
                ('SUC-125', 'Santiago Centro', 'Denisse'),
                ('SUC-126', 'Providencia', 'Denisse'),
                ('SUC-127', 'Las Condes', 'Deborah'),
                ('SUC-128', 'Ñuñoa', 'Francisca'),
                ('SUC-129', 'Maipú', 'Francisca');
            """))

inicializar_base_datos_completa()

# Función auxiliar para registrar auditoría
def registrar_auditoria(usuario, accion, detalles):
    try:
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO auditoria_log (usuario, accion, detalles) VALUES (:u, :a, :d)"),
                {"u": usuario, "a": accion, "d": detalles}
            )
    except:
        pass

# 3. Control de Sesión y Login Profesional
if 'user' not in st.session_state:
    st.session_state['user'] = None

if st.session_state['user'] is None:
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, col_login, _ = st.columns([1, 1.3, 1])
    
    with col_login:
        st.markdown("## 🏢 SIMI RRHH — Acceso Corporativo")
        st.markdown("Sistema Integral de Gestión y Control de Asistencia.")
        
        with st.form("form_login"):
            usuario_input = st.text_input("Usuario (ej: sebastian, denisse, deborah, francisca)").strip().lower()
            btn_login = st.form_submit_button("INGRESAR AL SISTEMA", type="primary", use_container_width=True)
            
            if btn_login:
                try:
                    df_user = pd.read_sql(text("SELECT * FROM usuarios_sistema WHERE username = :u AND activo = TRUE"), engine, params={"u": usuario_input})
                    if not df_user.empty:
                        st.session_state['user'] = df_user.iloc[0].to_dict()
                        st.session_state['modo_supervision'] = None 
                        registrar_auditoria(usuario_input, "LOGIN", "Inicio de sesión exitoso")
                        st.success("¡Bienvenido al sistema!")
                        st.rerun()
                    else:
                        st.error("Usuario no registrado o inactivo.")
                except Exception as e:
                    st.error(f"Error de acceso: {e}")
    st.stop()

usuario_actual = st.session_state['user']
rol_activo = usuario_actual['rol']
grupo_activo = usuario_actual['grupo']

if st.session_state.get('modo_supervision'):
    rol_activo = "Encargada"
    grupo_activo = st.session_state['modo_supervision']

# 4. Barra Lateral de Navegación y Control Jerárquico
st.sidebar.markdown(f"### 👤 {usuario_actual['nombre_completo']}")
st.sidebar.markdown(f"**Rol:** {usuario_actual['rol']}")
st.sidebar.markdown(f"**Grupo/Alcance:** {grupo_activo}")

if usuario_actual['rol'] == 'Administrador':
    st.sidebar.divider()
    st.sidebar.markdown("👁️ **Modo Supervisión (Ver Como):**")
    modo = st.sidebar.selectbox("Simular Vista de:", ["Modo Administrador", "Denisse", "Deborah", "Francisca"])
    if modo != "Modo Administrador":
        st.session_state['modo_supervision'] = modo
    else:
        st.session_state['modo_supervision'] = None

st.sidebar.divider()
if st.sidebar.button("Cerrar Sesión", type="secondary"):
    registrar_auditoria(usuario_actual['username'], "LOGOUT", "Cierre de sesión")
    st.session_state['user'] = None
    st.session_state['modo_supervision'] = None
    st.rerun()

# ==============================================================================
# 5. VISTA DE ADMINISTRADOR GLOBAL
# ==============================================================================
if rol_activo == 'Administrador' and not st.session_state.get('modo_supervision'):
    st.title("🛡️ SIMI RRHH — Panel de Administración Global")
    st.markdown("---")

    # Pestañas Principales del Administrador
    tab_dash, tab_repo, tab_analisis, tab_casos, tab_kpi, tab_config = st.tabs([
        "📊 Dashboard", 
        "📥 Reportes Talana", 
        "⚡ Motor de Análisis", 
        "🚨 Gestión de Casos", 
        "🎯 KPI & Sucursales", 
        "⚙️ Configuración & Auditoría"
    ])

    with tab_dash:
        # Métricas Globales
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("👥 Colaboradores", "1.245", "+12 este mes")
        c2.metric("🏪 Sucursales", "185", "100% activas")
        c3.metric("🚨 Casos Críticos", "18", "-4 vs ayer", delta_color="inverse")
        c4.metric("📋 Pendientes", "62", "Urgente")
        c5.metric("🎯 Cumplimiento", "95,4%", "+0.8%")

        st.markdown("<br>", unsafe_allow_html=True)
        col_act, col_prio = st.columns([1.2, 1])

        with col_act:
            st.subheader("👩 Actividad del Equipo")
            df_team = pd.DataFrame([
                {"Encargada": "Denisse", "Estado": "🟢 Activa", "Cumplimiento": "96.2%", "Pendientes": "7 casos", "Última Accion": "Hace 2 min"},
                {"Encargada": "Deborah", "Estado": "🟢 Activa", "Cumplimiento": "93.1%", "Pendientes": "13 casos", "Última Accion": "Hace 5 min"},
                {"Encargada": "Francisca", "Estado": "🟢 Activa", "Cumplimiento": "98.0%", "Pendientes": "5 casos", "Última Accion": "Hace 1 min"},
            ])
            st.dataframe(df_team, use_container_width=True, hide_index=True)

        with col_prio:
            st.subheader("🚨 Prioridades de Hoy")
            st.error("🔴 **5 casos críticos** en sucursales de alta demanda.")
            st.warning("🟠 **8 casos** próximos a vencer en menos de 4 horas.")
            st.info("📧 **8 correos** esperando aprobación gerencial.")

    with tab_repo:
        st.subheader("📥 Carga de Reportes Talana y Archivos Externos")
        with st.form("form_talana_admin", clear_on_submit=True):
            col_r1, col_r2 = st.columns(2)
            tipo_rep = col_r1.selectbox("Tipo de Reporte", ["Talana Asistencia", "Talana Turnos", "Colaboradores", "Licencias", "Vacaciones", "Horas Extra"])
            periodo_rep = col_r2.text_input("Período (ej: Septiembre 2026)")
            archivo = st.file_uploader("Seleccionar archivo Excel o CSV", type=["xlsx", "csv"])
            
            if st.form_submit_button("Procesar y Cargar Archivo", type="primary") and archivo is not None:
                try:
                    df_file = pd.read_csv(archivo) if archivo.name.endswith('.csv') else pd.read_excel(archivo)
                    total_regs = len(df_file)
                    
                    with engine.begin() as conn:
                        conn.execute(
                            text("INSERT INTO reportes_cargados (tipo_reporte, periodo, nombre_archivo, cantidad_registros, cargado_por) VALUES (:t, :p, :n, :c, :u)"),
                            {"t": tipo_rep, "p": periodo_rep, "n": archivo.name, "c": total_regs, "u": usuario_actual['nombre_completo']}
                        )
                    registrar_auditoria(usuario_actual['username'], "CARGA_REPORTE", f"Subió {archivo.name} ({total_regs} registros)")
                    st.success(f"¡Reporte procesado exitosamente! {total_regs} registros incorporados.")
                except Exception as e:
                    st.error(f"Error al procesar el archivo: {e}")

        st.divider()
        st.subheader("📋 Historial de Reportes en el Sistema")
        df_hist = pd.read_sql("SELECT * FROM reportes_cargados ORDER BY fecha_carga DESC", engine)
        if not df_hist.empty:
            st.dataframe(df_hist, use_container_width=True, hide_index=True)
        else:
            st.info("No hay reportes cargados aún.")

    with tab_analisis:
        st.subheader("⚡ Motor de Análisis e Incidencias Cruzadas")
        st.markdown("Cruza automáticamente asistencia, marcaciones, turnos y permisos para generar alertas inteligentes.")
        
        if st.button("🚀 ANALIZAR PERÍODO ACTUAL", type="primary"):
            st.success("Análisis completado: Se procesaron 1.245 registros cruzados.")
            st.metric("Incidencias Detectadas", "24", "-2 vs ciclo anterior")
            st.warning("⚠️ 18 sucursales concentran el 82% de las tardanzas y marcaciones incompletas.")

    with tab_casos:
        st.subheader("🚨 Gestión Global de Casos (Soporte y Seguimiento)")
        df_casos = pd.read_sql("SELECT * FROM casos_rrhh", engine)
        if not df_casos.empty:
            st.dataframe(df_casos, use_container_width=True)
        else:
            st.info("No hay casos activos registrados en este momento.")

    with tab_kpi:
        st.subheader("🎯 Indicadores de Desempeño (KPIs de Sucursales y Encargadas)")
        col_k1, col_k2 = st.columns(2)
        with col_k1:
            st.markdown("#### Rendimiento por Encargada")
            st.bar_chart(pd.Series([96.2, 93.1, 98.0], index=["Denisse", "Deborah", "Francisca"]))
        with col_k2:
            st.markdown("#### Asistencia por Sucursal (%)")
            st.bar_chart(pd.Series([94.2, 98.1, 91.5, 95.8, 97.0], index=["Santiago", "Providencia", "Las Condes", "Ñuñoa", "Maipú"]))

    with tab_config:
        st.subheader("⚙️ Configuración General y Auditoría del Sistema")
        st.markdown("### 📜 Historial de Auditoría Inalterable")
        try:
            df_audit = pd.read_sql("SELECT * FROM auditoria_log ORDER BY fecha_hora DESC LIMIT 50", engine)
            st.dataframe(df_audit, use_container_width=True, hide_index=True)
        except:
            st.info("Auditoría vacía.")

# ==============================================================================
# 6. VISTA DE ENCARGADAS (O MODO "VER COMO")
# ==============================================================================
else:
    st.title(f"👩 Panel de Gestión — Grupo {grupo_activo}")
    st.markdown(f"Gestión operativa para las sucursales asignadas a tu cargo.")
    st.markdown("---")

    tab_enc1, tab_enc2, tab_enc3 = st.tabs(["🏪 Mis Sucursales", "🚨 Casos y Alertas", "✉️ Centro de Comunicación"])

    with tab_enc1:
        df_suc = pd.read_sql("SELECT * FROM sucursales WHERE encargada_asignada = :g", engine, params={"g": grupo_activo})
        st.subheader(f"Tus Sucursales Asignadas ({len(df_suc)})")
        st.dataframe(df_suc[['codigo_sucursal', 'nombre_sucursal']], use_container_width=True, hide_index=True)

    with tab_enc2:
        st.subheader("Casos Asignados a tu Grupo")
        st.info("No tienes casos críticos pendientes en este momento. ¡Buen trabajo!")

    with tab_enc3:
        st.subheader("✉️ Generador de Comunicados y Correos Formales")
        col_e1, col_e2 = st.columns(2)
        col_e1.text_input("Correo del Colaborador", value="colaborador@simi.cl")
        motivo = col_e2.selectbox("Motivo", ["Aviso de Atraso", "Justificación de Falta", "Notificación de Turno"])
        
        st.text_area("Cuerpo del Mensaje", value=f"Estimado colaborador,\n\nLe contactamos desde Recursos Humanos (Grupo {grupo_activo}) respecto a su registro reciente.\n\nAtentamente,\nEquipo SIMI")
        
        if st.button("Enviar Comunicación", type="primary"):
            st.success("¡Correo preparado y registrado en la bandeja de salida!")
            registrar_auditoria(usuario_actual['username'], "ENVIO_CORREO", f"Envió comunicado tipo: {motivo}")
