import streamlit as st
import pandas as pd
from sqlalchemy import text, create_engine
import urllib.parse
import datetime

# 1. Configuración de página de nivel ejecutivo
st.set_page_config(
    page_title="SIMI - Sistema de Gestión y Control RRHH", 
    page_icon="🛡️", 
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

# Inicialización de la estructura relacional corporativa (Fase 1)
def inicializar_base_datos():
    with engine.begin() as conn:
        # Tabla de Usuarios y Roles
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS usuarios_sistema (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                nombre_completo TEXT NOT NULL,
                rol TEXT NOT NULL, -- 'Administrador' o 'Encargada'
                grupo TEXT, -- 'Denisse', 'Deborah', 'Francisca' o 'Global'
                activo BOOLEAN DEFAULT TRUE
            );
        """))
        
        # Tabla de Sucursales
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sucursales (
                id SERIAL PRIMARY KEY,
                codigo_sucursal TEXT UNIQUE NOT NULL,
                nombre_sucursal TEXT NOT NULL,
                encargada_asignada TEXT NOT NULL
            );
        """))

        # Tabla de Colaboradores
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

        # Insertar usuarios por defecto si la tabla está vacía
        resultado = conn.execute(text("SELECT COUNT(*) FROM usuarios_sistema")).scalar()
        if resultado == 0:
            conn.execute(text("""
                INSERT INTO usuarios_sistema (username, nombre_completo, rol, grupo) VALUES
                ('sebastian', 'Sebastián Coloma', 'Administrador', 'Global'),
                ('denisse', 'Denisse', 'Encargada', 'Denisse'),
                ('deborah', 'Deborah', 'Encargada', 'Deborah'),
                ('francisca', 'Francisca', 'Encargada', 'Francisca');
            """))

        # Insertar sucursales de prueba si está vacía
        res_suc = conn.execute(text("SELECT COUNT(*) FROM sucursales")).scalar()
        if res_suc == 0:
            conn.execute(text("""
                INSERT INTO sucursales (codigo_sucursal, nombre_sucursal, encargada_asignada) VALUES
                ('SUC-125', 'Santiago Centro', 'Denisse'),
                ('SUC-126', 'Providencia', 'Denisse'),
                ('SUC-127', 'Las Condes', 'Deborah'),
                ('SUC-128', 'Ñuñoa', 'Francisca');
            """))

inicializar_base_datos()

# 3. Control de Sesión y Login Profesional
if 'user' not in st.session_state:
    st.session_state['user'] = None

if st.session_state['user'] is None:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_l1, col_l2, col_l3 = st.columns([1, 1.2, 1])
    
    with col_l2:
        st.markdown("## 🔐 SIMI RRHH — Acceso al Sistema")
        st.markdown("Ingrese sus credenciales corporativas autorizadas.")
        
        with st.form("form_login"):
            usuario_input = st.text_input("Usuario (ej: sebastian, denisse, deborah, francisca)").strip().lower()
            btn_login = st.form_submit_button("INGRESAR AL SISTEMA", type="primary", use_container_width=True)
            
            if btn_login:
                try:
                    query = text("SELECT * FROM usuarios_sistema WHERE username = :u AND activo = TRUE")
                    df_user = pd.read_sql(query, engine, params={"u": usuario_input})
                    
                    if not df_user.empty:
                        st.session_state['user'] = df_user.iloc[0].to_dict()
                        st.session_state['modo_supervision'] = None # Para la función "Ver como"
                        st.success(f"Bienvenido, {st.session_state['user']['nombre_completo']}")
                        st.rerun()
                    else:
                        st.error("Usuario no encontrado o inactivo.")
                except Exception as e:
                    st.error(f"Error de autenticación: {e}")
    st.stop()

# Usuario autenticado con éxito
usuario_actual = st.session_state['user']
rol_activo = usuario_actual['rol']
grupo_activo = usuario_actual['grupo']

# Si hay modo supervisión activo ("Ver como")
if st.session_state.get('modo_supervision'):
    rol_activo = "Encargada"
    grupo_activo = st.session_state['modo_supervision']

# 4. Barra Superior de Navegación y Control de Sesión
st.sidebar.markdown(f"### 👤 {usuario_actual['nombre_completo']}")
st.sidebar.markdown(f"**Rol:** {usuario_actual['rol']}")
st.sidebar.markdown(f"**Grupo/Alcance:** {grupo_activo}")

if usuario_actual['rol'] == 'Administrador':
    st.sidebar.divider()
    st.sidebar.markdown("👁️ **Supervisión Global (Ver Como):**")
    modo = st.sidebar.selectbox("Simular Vista de:", ["Modo Administrador", "Denisse", "Deborah", "Francisca"])
    if modo != "Modo Administrador":
        st.session_state['modo_supervision'] = modo
    else:
        st.session_state['modo_supervision'] = None

st.sidebar.divider()
if st.sidebar.button("Cerrar Sesión", type="secondary"):
    st.session_state['user'] = None
    st.session_state['modo_supervision'] = None
    st.rerun()

# 5. Panel Principal de Administrador (Global) vs Panel de Encargadas
if rol_activo == 'Administrador' and not st.session_state.get('modo_supervision'):
    # --- PANEL DEL ADMINISTRADOR (SEBASTIÁN) ---
    st.title("🛡️ CONTROL RRHH — Panel de Administración Global")
    st.markdown("---")

    # Métricas Principales (Diseño ejecutivo)
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("👥 Colaboradores", "1.245", "+12 este mes")
    col2.metric("🏪 Sucursales", "185", "100% activas")
    col3.metric("🚨 Casos Críticos", "18", "-4 vs ayer", delta_color="inverse")
    col4.metric("📋 Pendientes", "62", "Urgente")
    col5.metric("🎯 Cumplimiento", "95,4%", "+0.8%")

    st.markdown("<br>", unsafe_allow_html=True)

    # Sección de Actividad del Equipo y Prioridades
    c_act, c_prio = st.columns([1.2, 1])

    with c_act:
        st.subheader("👩 Actividad del Equipo de Encargadas")
        df_equipo = pd.DataFrame([
            {"Encargada": "Denisse", "Estado": "🟢 Activa", "Cumplimiento": "96.2%", "Pendientes": "7 casos", "Última Accion": "Hace 2 min"},
            {"Encargada": "Deborah", "Estado": "🟢 Activa", "Cumplimiento": "93.1%", "Pendientes": "13 casos", "Última Accion": "Hace 5 min"},
            {"Encargada": "Francisca", "Estado": "🟢 Activa", "Cumplimiento": "98.0%", "Pendientes": "5 casos", "Última Accion": "Hace 1 min"},
        ])
        st.dataframe(df_equipo, use_container_width=True, hide_index=True)

    with c_prio:
        st.subheader("🚨 Prioridades de Hoy")
        st.error("🔴 **5 casos críticos** sin resolver en sucursales críticas.")
        st.warning("🟠 **8 casos** próximos a vencer en menos de 4 horas.")
        st.info("📧 **8 correos** esperando aprobación de gerencia.")

    st.markdown("---")
    st.info("💡 **Fase 1 completada con éxito:** El motor de autenticación multiusuario, roles dinámicos y la estructura jerárquica ya están operativos. En la siguiente fase conectaremos la ingesta masiva de reportes (Talana).")

else:
    # --- PANEL DE LAS ENCARGADAS (DENISSE, DEBORAH, FRANCISCA) ---
    st.title(f"👩 Panel de Gestión — Grupo {grupo_activo}")
    st.markdown(f"Gestión exclusiva para las sucursales asignadas a tu cargo.")
    st.markdown("---")

    # Mostrar sucursales asignadas a este grupo
    try:
        df_sucursales = pd.read_sql("SELECT * FROM sucursales WHERE encargada_asignada = :g", engine, params={"g": grupo_activo})
        st.subheader(f"🏪 Tus Sucursales Asignadas ({len(df_sucursales)})")
        st.dataframe(df_sucursales[['codigo_sucursal', 'nombre_sucursal']], use_container_width=True, hide_index=True)
    except Exception as e:
        st.info("Configurando sucursales para este grupo...")

    st.divider()
    st.markdown("### 📋 Casos Pendientes de tu Grupo")
    st.info("Los módulos de carga de Talana, incidencias y generación de casos automáticos se activarán en las siguientes fases del sistema.")
