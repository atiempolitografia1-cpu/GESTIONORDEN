import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Gestión Negocio Pro", layout="wide")

st.markdown("""<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;} .stDeployButton {display:none;}</style>""", unsafe_allow_html=True)

# --- BASE DE DATOS ---
def conectar():
    return sqlite3.connect('gestion_negocio.db')

def inicializar_db():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS ventas 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, n_orden TEXT, descripcion TEXT, 
         total REAL, abono REAL, saldo REAL, metodo_pago TEXT, estado TEXT, 
         empleado TEXT, cliente TEXT, nit TEXT, celular TEXT, correo TEXT, factura TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE, clave TEXT, rol TEXT)''')
    
    cursor.execute("SELECT * FROM usuarios WHERE nombre='Administrador'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO usuarios (nombre, clave, rol) VALUES (?,?,?)", ("Administrador", "admin123", "admin"))
    conn.commit()
    conn.close()

inicializar_db()

def obtener_usuarios():
    conn = conectar()
    df = pd.read_sql_query("SELECT * FROM usuarios", conn)
    conn.close()
    return df

# --- LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

df_users_db = obtener_usuarios()
if not st.session_state['autenticado']:
    st.title("🔐 Acceso al Sistema")
    u_input = st.selectbox("Usuario", df_users_db['nombre'].tolist())
    p_input = st.text_input("Contraseña", type="password")
    if st.button("INGRESAR"):
        user_data = df_users_db[df_users_db['nombre'] == u_input].iloc[0]
        if str(user_data['clave']) == p_input:
            st.session_state.update({"autenticado": True, "usuario": u_input, "rol": user_data['rol']})
            st.rerun()
        else: st.error("Contraseña incorrecta")
    st.stop()

# --- MENÚ LATERAL ---
st.sidebar.title(f"👤 {st.session_state['usuario']}")
menu = ["Ventas", "Gestión de Empleados"] if st.session_state['rol'] == 'admin' else ["Ventas"]
opcion = st.sidebar.radio("Ir a:", menu)

if st.sidebar.button("Cerrar Sesión"):
    st.session_state['autenticado'] = False
    st.rerun()

# --- SECCIÓN: GESTIÓN DE EMPLEADOS ---
if opcion == "Gestión de Empleados":
    st.title("👥 Administración de Personal")
    t1, t2 = st.tabs(["➕ Nuevo Empleado", "⚙️ Modificar / Eliminar"])
    
    with t1:
        st.subheader("Registrar nuevo usuario")
        n_nom = st.text_input("Nombre Completo")
        n_cla = st.text_input("Contraseña")
        n_rol = st.selectbox("Rol", ["empleado", "admin"])
        if st.button("Registrar Empleado"):
            try:
                conn = conectar()
                conn.execute("INSERT INTO usuarios (nombre, clave, rol) VALUES (?,?,?)", (n_nom, n_cla, n_rol))
                conn.commit(); conn.close()
                st.success("Empleado registrado"); st.rerun()
            except: st.error("El nombre ya existe")
            
    with t2:
        st.subheader("Editar datos de empleado")
        df_u = obtener_usuarios()
        u_sel = st.selectbox("Seleccione el usuario a gestionar", df_u['nombre'].tolist())
        
        # Aquí recuperamos los datos del usuario seleccionado para que puedas cambiarlos
        user_to_edit = df_u[df_u['nombre'] == u_sel].iloc[0]
        
        edit_clave = st.text_input("Nueva Contraseña", value=str(user_to_edit['clave']))
        edit_rol = st.selectbox("Nuevo Rol", ["empleado", "admin"], index=0 if user_to_edit['rol'] == "empleado" else 1)
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("💾 Guardar Cambios"):
                conn = conectar()
                conn.execute("UPDATE usuarios SET clave=?, rol=? WHERE nombre=?", (edit_clave, edit_rol, u_sel))
                conn.commit(); conn.close()
                st.success(f"Datos de {u_sel} actualizados"); st.rerun()
        
        with col_btn2:
            if st.button("🗑️ Eliminar Empleado"):
                if u_sel != "Administrador":
                    conn = conectar(); conn.execute("DELETE FROM usuarios WHERE nombre=?", (u_sel,)); conn.commit(); conn.close()
                    st.warning(f"Usuario {u_sel} eliminado"); st.rerun()
                else: st.error("No puedes eliminar al Administrador principal")

# --- SECCIÓN: VENTAS (CON TODAS TUS CASILLAS) ---
elif opcion == "Ventas":
    st.title("🚀 Gestión de Ventas")
    tab_reg, tab_edit = st.tabs(["📝 Registrar Nueva", "✏️ Editar Orden"])

    with tab_reg:
        if 'limp_v' not in st.session_state: st.session_state['limp_v'] = 0
        vs = str(st.session_state['limp_v'])
        c1, c2, c3 = st.columns(3)
        with c1:
            v_ord = st.text_input("N° Orden", key="o"+vs)
            v_desc = st.text_area("Descripción", key="d"+vs)
            v_fac = st.radio("Factura", ["SÍ", "NO"], key="f"+vs, horizontal=True)
        with c2:
            v_cli = st.text_input("Nombre Cliente", key="cl"+vs)
            v_nit = st.text_input("NIT / CC", key="nit"+vs)
            v_cel = st.text_input("Celular", key="cel"+vs)
            v_cor = st.text_input("Correo", key="cor"+vs)
        with c3:
            v_tot = st.number_input("Total ($)", key="t"+vs)
            v_abo = st.number_input("Abono ($)", key="a"+vs)
            v_est = st.selectbox("Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], key="e"+vs)
            v_pag = st.selectbox("Medio de Pago", ["EFECTIVO", "NEQUI", "DAVIPLATA", "BANCOLOMBIA"], key="p"+vs)

        if st.button("💾 GUARDAR", use_container_width=True):
            conn = conectar()
            conn.execute('''INSERT INTO ventas (fecha, n_orden, descripcion, total, abono, saldo, metodo_pago, estado, empleado, cliente, nit, celular, correo, factura) 
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', 
                           (datetime.now().strftime("%Y-%m-%d %H:%M"), v_ord, v_desc, v_tot, v_abo, v_tot-v_abo, v_pag, v_est, st.session_state['usuario'], v_cli, v_nit, v_cel, v_cor, v_fac))
            conn.commit(); conn.close(); st.session_state['limp_v'] += 1; st.rerun()

    with tab_edit:
        st.subheader("Actualizar Orden")
        conn = conectar(); df_e = pd.read_sql_query("SELECT * FROM ventas", conn); conn.close()
        if not df_e.empty:
            ord_sel = st.selectbox("Seleccione N° de Orden:", ["Seleccionar..."] + df_e['n_orden'].unique().tolist())
            if ord_sel != "Seleccionar...":
                d = df_e[df_e['n_orden'] == ord_sel].iloc[0]
                e_abo = st.number_input("Nuevo Abono ($)", value=float(d['abono']))
                e_est = st.selectbox("Nuevo Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], index=["EN PROCESO", "TERMINADO", "PAGADO"].index(d['estado']))
                if st.button("Actualizar"):
                    conn = conectar(); conn.execute("UPDATE ventas SET abono=?, saldo=?, estado=? WHERE n_orden=?", (e_abo, d['total']-e_abo, e_est, ord_sel)); conn.commit(); conn.close(); st.rerun()

    st.divider()
    search = st.text_input("🔍 Buscar por Orden, Cliente o NIT")
    conn = conectar(); df_t = pd.read_sql_query("SELECT * FROM ventas ORDER BY id DESC", conn); conn.close()
    if not df_t.empty:
        if st.session_state['rol'] != 'admin': df_t = df_t[df_t['empleado'] == st.session_state['usuario']]
        if search:
            df_t = df_t[df_t['n_orden'].astype(str).str.contains(search, case=False) | df_t['cliente'].str.contains(search, case=False) | df_t['nit'].str.contains(search, case=False)]
        st.dataframe(df_t, use_container_width=True, hide_index=True)
