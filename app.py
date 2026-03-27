import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import io

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Gestión Negocio Pro", layout="wide")
st.markdown("""<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;} .stDeployButton {display:none;}</style>""", unsafe_allow_html=True)

SHEET_ID = "1UGxbXTQhXKJ-JmKxpzglccDJrZgpCsTDflKO9N8RMTc"
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbyqx3mQopxUsMjokkhejP1newA3Gv-0OySPGFLhgGNlG6wgRPSieC3wlWO8QawQ6DRQXg/exec"

# INICIALIZACIÓN DE SESIÓN SEGURA
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False
if 'usuario' not in st.session_state: st.session_state['usuario'] = ""
if 'rol' not in st.session_state: st.session_state['rol'] = ""

def leer_datos(pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={pestana}"
        res = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(res.text))
        
        # Limpieza de columnas por posición para evitar el KeyError 'nombre'
        if pestana == "usuarios":
            if len(df.columns) >= 3:
                df.columns = ['nombre', 'clave', 'rol'] + list(df.columns[3:])
            else: # Si el Excel está vacío o roto, creamos una tabla base
                return pd.DataFrame(columns=['nombre', 'clave', 'rol'])
        elif pestana == "ventas":
            cols_v = ['fecha', 'n_orden', 'descripcion', 'total', 'abono', 'saldo', 'metodo_pago', 'estado', 'empleado', 'cliente', 'nit', 'celular', 'correo', 'factura']
            df.columns = cols_v + list(df.columns[len(cols_v):])

        # Limpiar datos
        df = df.applymap(lambda x: str(x).strip() if pd.notnull(x) else x)
        # Eliminar filas que repiten el encabezado
        df = df[df.iloc[:,0].astype(str).lower() != df.columns[0].lower()]
        return df
    except: 
        return pd.DataFrame(columns=['nombre', 'clave', 'rol']) if pestana == "usuarios" else pd.DataFrame()

def enviar_google(payload):
    try:
        res = requests.post(URL_SCRIPT, json=payload, timeout=15)
        return res.status_code == 200
    except: return False

# --- LOGIN CON LLAVE MAESTRA ---
df_users_db = leer_datos("usuarios")

# INYECTAR ADMINISTRADOR SI NO APARECE
# Esto asegura que SIEMPRE puedas entrar aunque el Excel falle
admin_existe = not df_users_db[df_users_db['nombre'].str.lower() == 'administrador'].empty if not df_users_db.empty else False

if not admin_existe:
    # Creamos una fila temporal para el administrador
    admin_provisional = pd.DataFrame([{'nombre': 'Administrador', 'clave': 'admin123', 'rol': 'admin'}])
    df_users_db = pd.concat([df_users_db, admin_provisional], ignore_index=True)

if not st.session_state['autenticado']:
    st.title("🔐 Acceso al Sistema")
    
    # Lista de usuarios limpia
    u_list = [u for u in df_users_db['nombre'].unique().tolist() if str(u).lower() != 'nan' and u != '']
    
    if u_list:
        u_input = st.selectbox("Usuario", u_list)
        p_input = st.text_input("Contraseña", type="password")
        
        if st.button("INGRESAR"):
            user_match = df_users_db[df_users_db['nombre'] == u_input]
            if not user_match.empty:
                user_data = user_match.iloc[0]
                # Comparamos contraseña
                if str(user_data['clave']) == str(p_input):
                    st.session_state.update({
                        "autenticado": True, 
                        "usuario": u_input, 
                        "rol": str(user_data['rol']).lower()
                    })
                    st.rerun()
                else:
                    st.error("Contraseña incorrecta")
    else:
        st.error("No se pudo cargar ningún usuario. Revisa el ID de tu Excel.")
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
            if n_nom and n_cla:
                payload = {"accion": "insertar", "tipo_registro": "usuarios", "nombre": n_nom, "clave": n_cla, "rol": n_rol}
                if enviar_google(payload): 
                    st.success("Empleado registrado"); st.rerun()
            else: st.warning("Completa todos los campos")
            
    with t2:
        st.subheader("Editar datos de empleado")
        df_u = leer_datos("usuarios")
        if not df_u.empty:
            u_sel = st.selectbox("Seleccione el usuario para editar", df_u['nombre'].tolist())
            user_to_edit = df_u[df_u['nombre'] == u_sel].iloc[0]
            edit_clave = st.text_input("Nueva Contraseña", value=str(user_to_edit['clave']))
            edit_rol = st.selectbox("Nuevo Rol", ["empleado", "admin"], index=0 if user_to_edit['rol'] == "empleado" else 1)
            
            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                if st.button("💾 Guardar Cambios"):
                    payload = {"accion": "actualizar", "tipo_registro": "usuarios", "id_busqueda": u_sel, "clave": edit_clave, "rol": edit_rol}
                    if enviar_google(payload): st.success("Actualizado"); st.rerun()
            with c_btn2:
                if st.button("🗑️ Eliminar Empleado"):
                    if u_sel != "Administrador":
                        payload = {"accion": "eliminar", "tipo_registro": "usuarios", "id_busqueda": u_sel}
                        if enviar_google(payload): st.warning("Eliminado"); st.rerun()
                    else: st.error("No puedes eliminar al Admin principal")

# --- SECCIÓN: VENTAS ---
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
            v_tot = st.number_input("Total ($)", key="t"+vs, step=100.0)
            v_abo = st.number_input("Abono ($)", key="a"+vs, step=100.0)
            v_est = st.selectbox("Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], key="e"+vs)
            v_pag = st.selectbox("Medio de Pago", ["EFECTIVO", "NEQUI", "DAVIPLATA", "BANCOLOMBIA"], key="p"+vs)

        if st.button("💾 GUARDAR VENTA", use_container_width=True):
            if v_ord and v_cli:
                payload = {
                    "accion": "insertar", "tipo_registro": "ventas",
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "n_orden": v_ord, "descripcion": v_desc,
                    "total": v_tot, "abono": v_abo, "saldo": v_tot-v_abo, "metodo_pago": v_pag,
                    "estado": v_est, "empleado": st.session_state['usuario'], "cliente": v_cli,
                    "nit": v_nit, "celular": v_cel, "correo": v_cor, "factura": v_fac
                }
                if enviar_google(payload): 
                    st.session_state['limp_v'] += 1
                    st.success("¡Venta guardada!")
                    st.rerun()
            else: st.error("Faltan datos críticos (N° Orden o Cliente)")

    with tab_edit:
        st.subheader("Actualizar Orden")
        df_e = leer_datos("ventas")
        if not df_e.empty:
            ord_sel = st.selectbox("Seleccione N° de Orden:", ["Seleccionar..."] + df_e['n_orden'].unique().tolist())
            if ord_sel != "Seleccionar...":
                d = df_e[df_e['n_orden'].astype(str) == str(ord_sel)].iloc[0]
                e_abo = st.number_input("Nuevo Abono ($)", value=float(d['abono']))
                e_est = st.selectbox("Nuevo Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], index=["EN PROCESO", "TERMINADO", "PAGADO"].index(d['estado']))
                if st.button("Actualizar Orden"):
                    payload = {"accion": "actualizar", "tipo_registro": "ventas", "id_busqueda": ord_sel, "abono": e_abo, "saldo": float(d['total'])-e_abo, "estado": e_est}
                    if enviar_google(payload): st.success("Orden actualizada"); st.rerun()

    st.divider()
    search = st.text_input("🔍 Buscar por Orden, Cliente o NIT")
    df_t = leer_datos("ventas")
    if not df_t.empty:
        df_t = df_t.iloc[::-1] 
        if st.session_state['rol'] != 'admin': 
            df_t = df_t[df_t['empleado'] == st.session_state['usuario']]
        if search:
            df_t = df_t[df_t.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]
        st.dataframe(df_t, use_container_width=True, hide_index=True)
