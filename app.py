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

# --- FUNCIÓN DE LECTURA SIN CACHÉ ---
def leer_datos(pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={pestana}&t={datetime.now().microsecond}"
        res = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(res.text))
        
        if df.empty:
            return pd.DataFrame(columns=['nombre', 'clave', 'rol']) if pestana == "usuarios" else pd.DataFrame()

        if pestana == "usuarios":
            cols = ['nombre', 'clave', 'rol']
            df.columns = cols + list(df.columns[len(cols):])
        elif pestana == "ventas":
            cols_v = ['fecha', 'n_orden', 'descripcion', 'total', 'abono', 'saldo', 'metodo_pago', 'estado', 'empleado', 'cliente', 'nit', 'celular', 'correo', 'factura']
            df.columns = cols_v + list(df.columns[len(cols_v):])

        df = df.astype(str).apply(lambda x: x.str.strip())
        df = df[df.iloc[:,0].str.lower() != df.columns[0].lower()]
        return df
    except:
        return pd.DataFrame(columns=['nombre', 'clave', 'rol']) if pestana == "usuarios" else pd.DataFrame()

def enviar_google(payload):
    try:
        res = requests.post(URL_SCRIPT, json=payload, timeout=15)
        return res.status_code == 200
    except: return False

# --- LOGIN ---
df_real = leer_datos("usuarios")
admin_respaldo = pd.DataFrame([{'nombre': 'Administrador', 'clave': 'admin123', 'rol': 'admin'}])

if not df_real.empty:
    if "administrador" in df_real['nombre'].astype(str).str.lower().values:
        df_users_db = df_real
    else:
        df_users_db = pd.concat([df_real, admin_respaldo], ignore_index=True)
else:
    df_users_db = admin_respaldo

if not st.session_state.get('autenticado', False):
    st.title("🔐 Acceso al Sistema")
    opciones = [u for u in df_users_db['nombre'].unique().tolist() if str(u).lower() != 'nan' and u != ""]
    if opciones:
        u_input = st.selectbox("Seleccione su Usuario", opciones)
        p_input = st.text_input("Contraseña", type="password")
        if st.button("INGRESAR", use_container_width=True):
            user_match = df_users_db[df_users_db['nombre'] == u_input]
            if not user_match.empty:
                user_data = user_match.iloc[0]
                if str(user_data['clave']).strip().lower() == str(p_input).strip().lower():
                    st.session_state.update({"autenticado": True, "usuario": u_input, "rol": str(user_data['rol']).strip().lower()})
                    st.rerun()
                else: st.error("❌ Contraseña incorrecta.")
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
        n_nom = st.text_input("Nombre Completo")
        n_cla = st.text_input("Contraseña")
        n_rol = st.selectbox("Rol", ["empleado", "admin"])
        if st.button("Registrar Empleado"):
            if n_nom and n_cla:
                payload = {"accion": "insertar", "tipo_registro": "usuarios", "nombre": n_nom, "clave": n_cla, "rol": n_rol}
                if enviar_google(payload): st.success("Registrado"); st.rerun()
    with t2:
        df_u = leer_datos("usuarios")
        if not df_u.empty:
            u_sel = st.selectbox("Usuario a editar", df_u['nombre'].tolist())
            user_edit = df_u[df_u['nombre'] == u_sel].iloc[0]
            e_cla = st.text_input("Nueva Clave", value=str(user_edit['clave']))
            e_rol = st.selectbox("Nuevo Rol", ["empleado", "admin"], index=0 if user_edit['rol'] == "empleado" else 1)
            if st.button("💾 Guardar Cambios"):
                payload = {"accion": "actualizar", "tipo_registro": "usuarios", "id_busqueda": u_sel, "clave": e_cla, "rol": e_rol}
                if enviar_google(payload): st.success("Actualizado"); st.rerun()

# --- SECCIÓN: VENTAS ---
elif opcion == "Ventas":
    st.title("🚀 Gestión de Ventas")
    df_v = leer_datos("ventas")
    
    tab_reg, tab_edit, tab_rep = st.tabs(["📝 Registrar", "✏️ Editar", "📊 Reportes"])

    with tab_reg:
        if 'limp_v' not in st.session_state: st.session_state['limp_v'] = 0
        vs = str(st.session_state['limp_v'])
        c1, c2, c3 = st.columns(3)
        with c1:
            v_ord = st.text_input("N° Orden", key="o"+vs)
            v_desc = st.text_area("Descripción", key="d"+vs)
            v_fac = st.radio("Factura", ["SÍ", "NO"], key="f"+vs, horizontal=True)
        with c2:
            v_cli = st.text_input("Cliente", key="cl"+vs)
            v_nit = st.text_input("NIT/CC", key="nit"+vs)
            v_cel = st.text_input("Celular", key="cel"+vs)
        with c3:
            v_tot = st.number_input("Total ($)", key="t"+vs, step=1.0)
            v_abo = st.number_input("Abono ($)", key="a"+vs, step=1.0)
            v_est = st.selectbox("Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], key="e"+vs)
            v_pag = st.selectbox("Pago", ["EFECTIVO", "NEQUI", "DAVIPLATA", "BANCOLOMBIA"], key="p"+vs)

        if st.button("💾 GUARDAR VENTA"):
            if v_ord and v_cli:
                payload = {"accion": "insertar", "tipo_registro": "ventas", "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "n_orden": v_ord, "descripcion": v_desc, "total": v_tot, "abono": v_abo, "saldo": v_tot-v_abo, "metodo_pago": v_pag, "estado": v_est, "empleado": st.session_state['usuario'], "cliente": v_cli, "nit": v_nit, "celular": v_cel, "correo": "", "factura": v_fac}
                if enviar_google(payload): st.session_state['limp_v'] += 1; st.success("Guardado"); st.rerun()

    with tab_edit:
        if not df_v.empty:
            ord_s = st.selectbox("N° Orden a editar:", ["..."] + df_v['n_orden'].unique().tolist())
            if ord_s != "...":
                d = df_v[df_v['n_orden'] == ord_s].iloc[0]
                e_abo = st.number_input("Nuevo Abono", value=float(d['abono']))
                e_est = st.selectbox("Nuevo Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], index=["EN PROCESO", "TERMINADO", "PAGADO"].index(d['estado']))
                if st.button("Actualizar"):
                    payload = {"accion": "actualizar", "tipo_registro": "ventas", "id_busqueda": ord_s, "abono": e_abo, "saldo": float(d['total'])-e_abo, "estado": e_est}
                    if enviar_google(payload): st.success("Actualizado"); st.rerun()

    with tab_rep:
        if not df_v.empty:
            emp_l = ["Todos"] + df_v['empleado'].unique().tolist()
            sel_e = st.selectbox("Filtrar por empleado:", emp_l)
            df_f = df_v.copy()
            if sel_e != "Todos": df_f = df_f[df_f['empleado'] == sel_e]
            
            # Métricas numéricas
            v_t = pd.to_numeric(df_f['total']).sum()
            a_t = pd.to_numeric(df_f['abono']).sum()
            m1, m2, m3 = st.columns(3)
            m1.metric("Ventas", f"$ {v_t:,.0f}")
            m2.metric("Abonos", f"$ {a_t:,.0f}")
            m3.metric("Saldo", f"$ {v_t - a_t:,.0f}")
            
            csv = df_f.to_csv(index=False).encode('utf-8-sig')
            st.download_button(f"📥 Descargar reporte {sel_e}", csv, f"Ventas_{sel_e}.csv", "text/csv", use_container_width=True)

    st.divider()
    busq = st.text_input("🔍 Buscar orden o cliente")
    df_m = df_v.copy().iloc[::-1]
    if st.session_state['rol'] != 'admin': df_m = df_m[df_m['empleado'] == st.session_state['usuario']]
    if busq: df_m = df_m[df_m.apply(lambda r: r.astype(str).str.contains(busq, case=False).any(), axis=1)]
    st.dataframe(df_m, use_container_width=True, hide_index=True)
