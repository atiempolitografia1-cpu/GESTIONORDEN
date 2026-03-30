import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import io

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(
    page_title="Gestión Negocio Pro", 
    layout="centered", 
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} 
    footer {visibility: hidden;} 
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    section[data-testid="stSidebar"] { top: 0; }
    </style>
    """, unsafe_allow_html=True)

# ⚠️ TUS CREDENCIALES
SHEET_ID = "1UGxbXTQhXKJ-JmKxpzglccDJrZgpCsTDflKO9N8RMTc"
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbwefjYpHKmQNY6BY9-DXWAxk2GNN6VVeiVDxzr0xV-3Z7Ab9QLwkLulFK5d60rqQCVSSA/exec"

# --- 2. FUNCIONES DE DATOS ---
def enviar_google(payload):
    try:
        res = requests.post(URL_SCRIPT, json=payload, timeout=15)
        return res.status_code == 200
    except: return False

def leer_datos(pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={pestana}&t={datetime.now().microsecond}"
        res = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(res.text), dtype=str).fillna('')
        for col in df.columns: df[col] = df[col].astype(str).str.strip()
        if pestana == "usuarios":
            df.columns = ['nombre', 'clave', 'rol'] + list(df.columns[3:])
        elif pestana == "ventas":
            cols_v = ['fecha', 'n_orden', 'descripcion', 'total', 'abono', 'saldo', 'metodo_pago', 'estado', 'empleado', 'cliente', 'nit', 'celular', 'correo', 'factura', 'historial_pagos']
            df = df.iloc[:, :len(cols_v)]
            df.columns = cols_v
        return df
    except: return pd.DataFrame()

# --- 3. LOGIN (CON ENTER) ---
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False
df_users_db = leer_datos("usuarios")

if not st.session_state['autenticado']:
    st.title("🔐 Acceso al Sistema")
    with st.form("login_form"):
        u_input = st.selectbox("Usuario", [u for u in df_users_db['nombre'].unique().tolist() if u != ""])
        p_input = st.text_input("Contraseña", type="password")
        if st.form_submit_button("INGRESAR", use_container_width=True):
            match = df_users_db[df_users_db['nombre'] == u_input]
            if not match.empty and str(match.iloc[0]['clave']).strip() == str(p_input).strip():
                st.session_state.update({"autenticado": True, "usuario": u_input, "rol": str(match.iloc[0]['rol']).lower()})
                st.rerun()
            else: st.error("❌ Datos incorrectos")
    st.stop()

# --- 4. BARRA LATERAL ---
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state['usuario'].upper()}")
    menu = ["Ventas", "Gestión de Empleados"] if st.session_state['rol'] == 'admin' else ["Ventas"]
    opcion = st.radio("Ir a:", menu)
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state['autenticado'] = False
        st.rerun()

# --- 5. SECCIÓN VENTAS ---
if opcion == "Ventas":
    st.title("🚀 Gestión de Ventas")
    df_v = leer_datos("ventas")
    
    tabs = st.tabs(["📝 Registrar", "✏️ Editar / Abonar", "📊 Reportes Avanzados"]) if st.session_state['rol'] == 'admin' else st.tabs(["📝 Registrar", "✏️ Editar / Abonar"])

    with tabs[0]: # REGISTRAR
        if 'limp_v' not in st.session_state: st.session_state['limp_v'] = 0
        vs = str(st.session_state['limp_v'])
        
        c1, c2, c3 = st.columns(3)
        with c1: v_ord = st.text_input("N° Orden", key="o"+vs)
        with c2: v_cli = st.text_input("Cliente", key="cl"+vs)
        with c3: v_nit = st.text_input("NIT / CC", key="ni"+vs)
        
        c4, c5, c6 = st.columns(3)
        with c4: v_cel = st.text_input("Celular", key="ce"+vs)
        with c5: v_cor = st.text_input("Correo", key="co"+vs)
        with c6: v_fac = st.radio("Factura", ["SÍ", "NO"], horizontal=True, key="fa"+vs)
        
        c7, c8 = st.columns(2)
        with c7: v_tot = st.number_input("Total ($)", min_value=0.0, key="t"+vs)
        with c8: v_abo = st.number_input("Abono Inicial ($)", min_value=0.0, key="a"+vs)
        
        v_desc = st.text_area("Descripción Trabajo", key="de"+vs)
        
        c9, c10 = st.columns(2)
        with c9: v_est = st.selectbox("Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], key="es"+vs)
        with c10: v_pag = st.selectbox("Medio Pago Inicial", ["EFECTIVO", "NEQUI", "DAVIPLATA", "BANCOLOMBIA"], key="pa"+vs)
        
        if st.button("💾 GUARDAR VENTA", use_container_width=True):
            if v_ord and v_cli:
                payload = {
                    "accion": "insertar", "tipo_registro": "ventas", 
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "n_orden": v_ord, 
                    "descripcion": v_desc, "total": v_tot, "abono": v_abo, "saldo": v_tot-v_abo, 
                    "metodo_pago": v_pag, "estado": v_est, "empleado": st.session_state['usuario'], 
                    "cliente": v_cli, "nit": v_nit, "celular": v_cel, "correo": v_cor, "factura": v_fac,
                    "historial_pagos": f"${v_abo:,.0f} ({v_pag}) el {datetime.now().date()}"
                }
                if enviar_google(payload): 
                    st.session_state['limp_v'] += 1; st.success("¡Venta guardada!"); st.rerun()

    with tabs[1]: # EDITAR
        if not df_v.empty:
            op_o = df_v['n_orden'].unique().tolist() if st.session_state['rol'] == 'admin' else df_v[df_v['empleado'].str.lower() == st.session_state['usuario'].lower()]['n_orden'].unique().tolist()
            ord_s = st.selectbox("Seleccione Orden para editar:", ["Seleccionar..."] + op_o)
            if ord_s != "Seleccionar...":
                d = df_v[df_v['n_orden'] == str(ord_s)].iloc[0]
                e1, e2, e3 = st.columns(3)
                with e1: e_cli = st.text_input("Cliente", value=d['cliente'])
                with e2: e_nit = st.text_input("NIT / CC", value=d['nit'])
                with e3: e_cel = st.text_input("Celular", value=d['celular'])
                
                e_cor = st.text_input("Correo", value=d['correo'])
                e_des = st.text_area("Descripción", value=d['descripcion'])
                
                e4, e5 = st.columns(2)
                with e4: e_tot = st.number_input("Total ($)", value=float(pd.to_numeric(d['total'], errors='coerce') or 0.0))
                with e5: n_abo = st.number_input("Nuevo abono hoy ($)", min_value=0.0)
                
                if st.button("💾 ACTUALIZAR TODO"):
                    ab_f = float(d['abono']) + n_abo
                    payload = {"accion": "actualizar", "tipo_registro": "ventas", "id_busqueda": ord_s, "cliente": e_cli, "nit": e_nit, "celular": e_cel, "correo": e_cor, "descripcion": e_des, "total": e_tot, "abono": ab_f, "saldo": e_tot-ab_f}
                    if enviar_google(payload): st.success("¡Actualizado!"); st.rerun()

    if st.session_state['rol'] == 'admin':
        with tabs[2]: # REPORTES
            st.subheader("📊 Reportes Avanzados")
            df_v['fecha_dt'] = pd.to_datetime(df_v['fecha'], errors='coerce')
            f1, f2 = st.columns(2)
            with f1: sel_emp = st.selectbox("👤 Empleado:", ["Todos"] + df_v['empleado'].unique().tolist())
            with f2: modo_t = st.radio("📅 Tiempo:", ["Todo", "Día / Semana", "Mes / Año"], horizontal=True)
            
            df_r = df_v.copy()
            if modo_t == "Día / Semana":
                ran = st.date_input("Rango:", value=[datetime.now(), datetime.now()])
                if len(ran) == 2: df_r = df_r[(df_r['fecha_dt'].dt.date >= ran[0]) & (df_r['fecha_dt'].dt.date <= ran[1])]
            elif modo_t == "Mes / Año":
                m = st.selectbox("Mes:", range(1,13), index=datetime.now().month-1)
                df_r = df_r[df_r['fecha_dt'].dt.month == m]
            
            if sel_emp != "Todos": df_r = df_r[df_r['empleado'] == sel_emp]
            st.metric("Total Cobrado", f"$ {pd.to_numeric(df_r['abono'], errors='coerce').sum():,.0f}")
            st.dataframe(df_r.drop(columns=['fecha_dt']), use_container_width=True, hide_index=True)


   # ... (Sección de gestión de empleados igual que antes)
elif opcion == "Gestión de Empleados":
    st.title("👥 Personal")
 
    df_u = leer_datos("usuarios")
    t1, t2 = st.tabs(["➕ Nuevo", "⚙️ Editar"])
    with t1:
        n_nom = st.text_input("Nombre Completo")
        n_cla = st.text_input("Contraseña temporal")
        if st.button("REGISTRAR EMPLEADO", use_container_width=True):
            if enviar_google({"accion": "insertar", "tipo_registro": "usuarios", "nombre": n_nom, "clave": n_cla, "rol": "empleado"}):
                st.success("Empleado creado"); st.rerun()
    with t2:
        if not df_u.empty:
            u_sel = st.selectbox("Seleccione Usuario:", df_u['nombre'].tolist())
            if u_sel != "Administrador" and st.button("ELIMINAR ACCESO", type="primary"):
                if enviar_google({"accion": "eliminar", "tipo_registro": "usuarios", "id_busqueda": u_sel}):
                    st.warning("Usuario eliminado"); st.rerun()
