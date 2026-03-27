import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import io

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Gestión Negocio Pro", layout="wide")
st.markdown("""<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;} .stDeployButton {display:none;}</style>""", unsafe_allow_html=True)

SHEET_ID = "1UGxbXTQhXKJ-JmKxpzglccDJrZgpCsTDflKO9N8RMTc"
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbz61gcjsNtVT5L2utA6XbRUVdLxjw_WTPDzC5lIuSDq7vzKeoyOuvng5Xb9MPgTOgAwEQ/exec"

def leer_datos(pestana):
    try:
        # Forzamos la lectura sin saltar filas y limpiando nombres
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={pestana}"
        res = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(res.text))
        
        # Limpieza extrema: nombres de columnas a minúsculas y sin espacios
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        # Si por error los datos están en el nombre de la columna (como vimos antes)
        # los bajamos a la tabla
        if "administrador" in df.columns.tolist():
             # Reiniciamos el DataFrame si detectamos datos en los headers
             df = pd.read_csv(io.StringIO(res.text), header=None)
             df.columns = ["nombre", "clave", "rol"]
             # Quitamos la primera fila si se repite el encabezado
             if df.iloc[0,0] == "nombre": df = df.drop(0)
             
        return df
    except: 
        return pd.DataFrame()
def enviar_google(payload):
    try:
        # Añadimos un timeout para que no se quede colgado
        res = requests.post(URL_SCRIPT, json=payload, timeout=15)
        if res.status_code == 200:
            return True
        else:
            st.error(f"Error al guardar: {res.status_code}")
            return False
    except Exception as e:
        st.error(f"Error de red: {e}")
        return False

# --- LOGIN ---
df_users_db = leer_datos("usuarios")

if not st.session_state['autenticado']:
    st.title("🔐 Acceso al Sistema")
    if not df_users_db.empty:
        # Convertimos todo a texto y quitamos nulos para que no falle el selectbox
        df_users_db['nombre'] = df_users_db['nombre'].astype(str).str.strip()
        u_list = df_users_db['nombre'].unique().tolist()
        
        # ELIMINAMOS NOMBRES VACÍOS O "NAN"
        u_list = [u for u in u_list if u.lower() != 'nan' and u != '']
        
        if u_list:
            u_input = st.selectbox("Seleccione su Usuario", u_list)
            p_input = st.text_input("Contraseña", type="password")
            
            if st.button("INGRESAR"):
                # Buscamos al usuario ignorando mayúsculas/minúsculas
                user_match = df_users_db[df_users_db['nombre'].astype(str) == u_input]
                
                if not user_match.empty:
                    user_data = user_match.iloc[0]
                    # Convertimos ambos a string para comparar sin errores
                    if str(user_data['clave']).strip() == str(p_input).strip():
                        st.session_state.update({
                            "autenticado": True, 
                            "usuario": u_input, 
                            "rol": str(user_data['rol']).lower().strip()
                        })
                        st.rerun()
                    else: 
                        st.error("Contraseña incorrecta")
        else:
            st.error("No hay usuarios registrados en el Excel.")
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
            payload = {"accion": "insertar", "tipo_registro": "usuarios", "nombre": n_nom, "clave": n_cla, "rol": n_rol}
            if enviar_google(payload): 
                st.success("Empleado registrado"); st.rerun()
            
    with t2:
        st.subheader("Editar datos de empleado")
        df_u = leer_datos("usuarios")
        if not df_u.empty and 'nombre' in df_u.columns:
            u_sel = st.selectbox("Seleccione el usuario", df_u['nombre'].tolist())
            user_to_edit = df_u[df_u['nombre'] == u_sel].iloc[0]
            edit_clave = st.text_input("Nueva Contraseña", value=str(user_to_edit['clave']))
            edit_rol = st.selectbox("Nuevo Rol", ["empleado", "admin"], index=0 if user_to_edit['rol'] == "empleado" else 1)
            
            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                if st.button("💾 Guardar Cambios"):
                    payload = {"accion": "actualizar", "tipo_registro": "usuarios", "id_busqueda": u_sel, "clave": edit_clave, "rol": edit_rol}
                    enviar_google(payload); st.success("Actualizado"); st.rerun()
            with c_btn2:
                if st.button("🗑️ Eliminar Empleado"):
                    if u_sel != "Administrador":
                        payload = {"accion": "eliminar", "tipo_registro": "usuarios", "id_busqueda": u_sel}
                        enviar_google(payload); st.warning("Eliminado"); st.rerun()
                    else: 
                        st.error("No puedes eliminar al Admin principal")

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
            v_tot = st.number_input("Total ($)", key="t"+vs)
            v_abo = st.number_input("Abono ($)", key="a"+vs)
            v_est = st.selectbox("Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], key="e"+vs)
            v_pag = st.selectbox("Medio de Pago", ["EFECTIVO", "NEQUI", "DAVIPLATA", "BANCOLOMBIA"], key="p"+vs)

        if st.button("💾 GUARDAR", use_container_width=True):
            payload = {
                "accion": "insertar", "tipo_registro": "ventas",
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "n_orden": v_ord, "descripcion": v_desc,
                "total": v_tot, "abono": v_abo, "saldo": v_tot-v_abo, "metodo_pago": v_pag,
                "estado": v_est, "empleado": st.session_state['usuario'], "cliente": v_cli,
                "nit": v_nit, "celular": v_cel, "correo": v_cor, "factura": v_fac
            }
            if enviar_google(payload): 
                st.session_state['limp_v'] += 1; st.rerun()

    with tab_edit:
        st.subheader("Actualizar Orden")
        df_e = leer_datos("ventas")
        if not df_e.empty and 'n_orden' in df_e.columns:
            ord_sel = st.selectbox("Seleccione N° de Orden:", ["Seleccionar..."] + df_e['n_orden'].unique().tolist())
            if ord_sel != "Seleccionar...":
                d = df_e[df_e['n_orden'].astype(str) == str(ord_sel)].iloc[0]
                e_abo = st.number_input("Nuevo Abono ($)", value=float(d['abono']))
                e_est = st.selectbox("Nuevo Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], index=["EN PROCESO", "TERMINADO", "PAGADO"].index(d['estado']))
                if st.button("Actualizar"):
                    payload = {"accion": "actualizar", "tipo_registro": "ventas", "id_busqueda": ord_sel, "abono": e_abo, "saldo": d['total']-e_abo, "estado": e_est}
                    enviar_google(payload); st.rerun()

    st.divider()
    search = st.text_input("🔍 Buscar por Orden, Cliente o NIT")
    df_t = leer_datos("ventas")
    if not df_t.empty:
        df_t = df_t.iloc[::-1] 
        if st.session_state['rol'] != 'admin' and 'empleado' in df_t.columns: 
            df_t = df_t[df_t['empleado'] == st.session_state['usuario']]
        
        if search:
            # Filtro robusto
            mask = df_t.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)
            df_t = df_t[mask]
            
        st.dataframe(df_t, use_container_width=True, hide_index=True)
