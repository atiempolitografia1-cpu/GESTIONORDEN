import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import io

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Gestión Negocio Pro", layout="wide")

# Ocultar menús de Streamlit (Tu estilo original)
st.markdown("""<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;} .stDeployButton {display:none;}</style>""", unsafe_allow_html=True)

# --- CONEXIÓN GOOGLE SHEETS ---
SHEET_ID = "1UGxbXTQhXKJ-JmKxpzglccDJrZgpCsTDflKO9N8RMTc"
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbxOEP-5jAU8RE76-5DsUp2iyn_zXr54kEXY0_H3Dw-BNqPSW5-1W_oGlr48W94o-RqLSA/exec"

def traer_datos(pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={pestana}"
        res = requests.get(url)
        return pd.read_csv(io.StringIO(res.text))
    except:
        return pd.DataFrame()

# --- LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

df_users_db = traer_datos("usuarios")

if not st.session_state['autenticado']:
    st.title("🔐 Acceso al Sistema")
    if not df_users_db.empty:
        u_input = st.selectbox("Usuario", df_users_db['nombre'].tolist())
        p_input = st.text_input("Contraseña", type="password")
        if st.button("INGRESAR"):
            user_data = df_users_db[df_users_db['nombre'] == u_input].iloc[0]
            if str(user_data['clave']) == p_input:
                st.session_state.update({"autenticado": True, "usuario": u_input, "rol": user_data['rol']})
                st.rerun()
            else: st.error("Contraseña incorrecta")
    else:
        st.error("No se pudo cargar la base de datos de usuarios.")
    st.stop()

# --- MENÚ LATERAL ---
st.sidebar.title(f"👤 {st.session_state['usuario']}")
menu = ["Ventas", "Gestión de Empleados"] if st.session_state['rol'] == 'admin' else ["Ventas"]
opcion = st.sidebar.radio("Ir a:", menu)

if st.sidebar.button("Cerrar Sesión"):
    st.session_state['autenticado'] = False
    st.rerun()

# --- SECCIÓN: GESTIÓN DE EMPLEADOS (Tu lógica original) ---
if opcion == "Gestión de Empleados":
    st.title("👥 Administración de Personal")
    t1, t2 = st.tabs(["➕ Nuevo Empleado", "⚙️ Modificar / Eliminar"])
    
    with t1:
        st.subheader("Registrar nuevo usuario")
        n_nom = st.text_input("Nombre Completo")
        n_cla = st.text_input("Contraseña")
        n_rol = st.selectbox("Rol", ["empleado", "admin"])
        if st.button("Registrar Empleado"):
            # Aquí enviarías al script con una lógica similar al de ventas
            st.info("Funcionalidad de escritura para empleados en desarrollo.")
            
    with t2:
        st.subheader("Editar datos de empleado")
        df_u = traer_datos("usuarios")
        if not df_u.empty:
            u_sel = st.selectbox("Seleccione el usuario a gestionar", df_u['nombre'].tolist())
            user_to_edit = df_u[df_u['nombre'] == u_sel].iloc[0]
            edit_clave = st.text_input("Nueva Contraseña", value=str(user_to_edit['clave']))
            edit_rol = st.selectbox("Nuevo Rol", ["empleado", "admin"], index=0 if user_to_edit['rol'] == "empleado" else 1)
            st.button("💾 Guardar Cambios (Próximamente)")

# --- SECCIÓN: VENTAS (TU CÓDIGO ORIGINAL COMPLETO) ---
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

        if st.button("💾 GUARDAR EN NUBE", use_container_width=True):
            datos_venta = {
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "n_orden": str(v_ord),
                "descripcion": v_desc,
                "total": float(v_tot),
                "abono": float(v_abo),
                "saldo": float(v_tot - v_abo),
                "metodo_pago": v_pag,
                "estado": v_est,
                "empleado": st.session_state['usuario'],
                "cliente": v_cli,
                "nit": v_nit,
                "celular": v_cel,
                "correo": v_cor,
                "factura": v_fac
            }
            try:
                r = requests.post(URL_SCRIPT, json=datos_venta)
                if r.status_code == 200:
                    st.success("✅ ¡Venta guardada en Google Sheets!"); st.balloons()
                    st.session_state['limp_v'] += 1
                    st.rerun()
                else: st.error("Error al guardar.")
            except: st.error("Fallo de conexión.")

    with tab_edit:
        st.subheader("Actualizar Orden")
        df_e = traer_datos("ventas")
        if not df_e.empty:
            ord_sel = st.selectbox("Seleccione N° de Orden:", ["Seleccionar..."] + df_e['n_orden'].astype(str).unique().tolist())
            if ord_sel != "Seleccionar...":
                d = df_e[df_e['n_orden'].astype(str) == ord_sel].iloc[0]
                st.write(f"Cliente: {d['cliente']}")
                st.info("Módulo de edición vía Google Sheets en camino.")

    st.divider()
    search = st.text_input("🔍 Buscar por Orden, Cliente o NIT")
    df_t = traer_datos("ventas")
    if not df_t.empty:
        if st.session_state['rol'] != 'admin': df_t = df_t[df_t['empleado'] == st.session_state['usuario']]
        if search:
            df_t = df_t[df_t['n_orden'].astype(str).str.contains(search, case=False) | df_t['cliente'].str.contains(search, case=False) | df_t['nit'].astype(str).str.contains(search, case=False)]
        st.dataframe(df_t, use_container_width=True, hide_index=True)
