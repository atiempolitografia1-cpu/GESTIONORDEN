import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import io

# --- 1. CONFIGURACIÓN VISUAL (CENTRADA Y PROPORCIONAL) ---
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
    
    /* Ajuste de margen superior */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Botón de sidebar visible */
    section[data-testid="stSidebar"] {
        top: 0;
    }
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
    except:
        return False

def leer_datos(pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={pestana}&t={datetime.now().microsecond}"
        res = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(res.text), dtype=str).fillna('')
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
        if pestana == "usuarios":
            df.columns = ['nombre', 'clave', 'rol'] + list(df.columns[3:])
        elif pestana == "ventas":
            cols_v = ['fecha', 'n_orden', 'descripcion', 'total', 'abono', 'saldo', 'metodo_pago', 'estado', 'empleado', 'cliente', 'nit', 'celular', 'correo', 'factura', 'historial_pagos']
            df = df.iloc[:, :len(cols_v)]
            df.columns = cols_v
        return df
    except:
        return pd.DataFrame()

# --- 3. LOGIN Y SESIÓN ---
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False

df_users_db = leer_datos("usuarios")
if df_users_db.empty:
    df_users_db = pd.DataFrame([{'nombre': 'Administrador', 'clave': 'admin123', 'rol': 'admin'}])

if not st.session_state['autenticado']:
    st.title("🔐 Acceso al Sistema")
    u_list = [u for u in df_users_db['nombre'].unique().tolist() if u != ""]
    u_input = st.selectbox("Usuario", u_list)
    p_input = st.text_input("Contraseña", type="password")
    if st.button("INGRESAR", use_container_width=True):
        match = df_users_db[df_users_db['nombre'] == u_input]
        if not match.empty and str(match.iloc[0]['clave']).strip() == str(p_input).strip():
            st.session_state.update({"autenticado": True, "usuario": u_input, "rol": str(match.iloc[0]['rol']).lower()})
            st.rerun()
        else: st.error("❌ Datos incorrectos")
    st.stop()

# --- 4. BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state['usuario'].upper()}")
    st.info(f"Rol: {st.session_state['rol'].capitalize()}")
    st.divider()
    
    menu = ["Ventas", "Gestión de Empleados"] if st.session_state['rol'] == 'admin' else ["Ventas"]
    opcion = st.radio("Menú Principal:", menu)
    
    st.markdown("<br>"*8, unsafe_allow_html=True)
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state['autenticado'] = False
        st.rerun()

# --- 5. SECCIÓN VENTAS ---
if opcion == "Ventas":
    st.title("🚀 Gestión de Ventas")
    df_v = leer_datos("ventas")
    
    # Pestañas según rol
    if st.session_state['rol'] == 'admin':
        tab_reg, tab_edit, tab_rep = st.tabs(["📝 Registrar", "✏️ Editar / Abonar", "📊 Reportes Avanzados"])
    else:
        tab_reg, tab_edit = st.tabs(["📝 Registrar", "✏️ Editar / Abonar"])

    with tab_reg:
        if 'limp_v' not in st.session_state: st.session_state['limp_v'] = 0
        vs = str(st.session_state['limp_v'])
        c1, c2 = st.columns(2)
        with c1:
            v_ord = st.text_input("N° Orden", key="o"+vs)
            v_cli = st.text_input("Cliente", key="cl"+vs)
        with c2:
            v_tot = st.number_input("Total ($)", key="t"+vs, min_value=0.0)
            v_abo = st.number_input("Abono Inicial ($)", key="a"+vs, min_value=0.0)
        
        v_desc = st.text_area("Descripción", key="d"+vs)
        v_est = st.selectbox("Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], key="e"+vs)
        v_pag = st.selectbox("Medio Pago", ["EFECTIVO", "NEQUI", "DAVIPLATA", "BANCOLOMBIA"], key="p"+vs)
        
        if st.button("💾 GUARDAR VENTA", use_container_width=True):
            if v_ord and v_cli:
                h_ini = f"${v_abo:,.0f} ({v_pag}) el {datetime.now().strftime('%Y-%m-%d')}"
                payload = {"accion": "insertar", "tipo_registro": "ventas", "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "n_orden": v_ord, "descripcion": v_desc, "total": v_tot, "abono": v_abo, "saldo": v_tot-v_abo, "metodo_pago": v_pag, "estado": v_est, "empleado": st.session_state['usuario'], "cliente": v_cli, "factura": "NO", "historial_pagos": h_ini}
                if enviar_google(payload): 
                    st.session_state['limp_v'] += 1; st.success("¡Venta guardada!"); st.rerun()
            else: st.error("Faltan datos obligatorios")

    with tab_edit:
        if not df_v.empty:
            opciones_o = df_v['n_orden'].unique().tolist() if st.session_state['rol'] == 'admin' else df_v[df_v['empleado'].str.lower() == st.session_state['usuario'].lower()]['n_orden'].unique().tolist()
            ord_s = st.selectbox("Seleccione Orden:", ["Seleccionar..."] + opciones_o)
            if ord_s != "Seleccionar...":
                d = df_v[df_v['n_orden'] == str(ord_s)].iloc[0]
                e_cli = st.text_input("Cliente", value=str(d['cliente']))
                c3, c4 = st.columns(2)
                with c3:
                    e_total = st.number_input("Total ($)", value=float(pd.to_numeric(d['total'], errors='coerce') or 0.0))
                    v_ab_prev = float(pd.to_numeric(d['abono'], errors='coerce') or 0.0)
                    st.info(f"Abonado: ${v_ab_prev:,.0f}")
                with c4:
                    nuevo_p = st.number_input("Abono hoy ($)", min_value=0.0)
                    e_est = st.selectbox("Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], index=["EN PROCESO", "TERMINADO", "PAGADO"].index(d['estado']))
                
                if st.button("💾 ACTUALIZAR", use_container_width=True):
                    ab_f = v_ab_prev + nuevo_p
                    h_f = (str(d['historial_pagos']) if str(d['historial_pagos']) != "nan" else "") + (f" || ${nuevo_p:,.0f} el {datetime.now().date()}" if nuevo_p > 0 else "")
                    payload = {"accion": "actualizar", "tipo_registro": "ventas", "id_busqueda": ord_s, "cliente": e_cli, "total": e_total, "abono": ab_f, "saldo": e_total-ab_f, "estado": e_est, "historial_pagos": h_f}
                    if enviar_google(payload): st.success("¡Actualizado!"); st.rerun()

    # --- REPORTES AVANZADOS (SOLO ADMIN) ---
    if st.session_state['rol'] == 'admin':
        with tab_rep:
            st.subheader("📊 Filtros de Reporte")
            df_v['fecha_dt'] = pd.to_datetime(df_v['fecha'], errors='coerce')
            
            f1, f2 = st.columns(2)
            with f1:
                sel_emp = st.selectbox("👤 Por Empleado:", ["Todos"] + df_v['empleado'].unique().tolist())
            with f2:
                modo_t = st.radio("📅 Temporalidad:", ["Todo", "Día / Semana", "Mes / Año"], horizontal=True)

            df_res = df_v.copy()
            if modo_t == "Día / Semana":
                rango = st.date_input("Rango de fechas:", value=[datetime.now(), datetime.now()])
                if len(rango) == 2:
                    df_res = df_res[(df_res['fecha_dt'].dt.date >= rango[0]) & (df_res['fecha_dt'].dt.date <= rango[1])]
            elif modo_t == "Mes / Año":
                c_m1, c_m2 = st.columns(2)
                with c_m1:
                    m_sel = st.selectbox("Mes:", range(1, 13), index=datetime.now().month-1, format_func=lambda x: ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"][x-1])
                with c_m2:
                    a_sel = st.selectbox("Año:", sorted(df_v['fecha_dt'].dt.year.unique() if not df_v.empty else [datetime.now().year], reverse=True))
                df_res = df_res[(df_res['fecha_dt'].dt.month == m_sel) & (df_res['fecha_dt'].dt.year == a_sel)]

            if sel_emp != "Todos":
                df_res = df_res[df_res['empleado'] == sel_emp]

            st.divider()
            vt = pd.to_numeric(df_res['total'], errors='coerce').sum()
            at = pd.to_numeric(df_res['abono'], errors='coerce').sum()
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Ventas", f"$ {vt:,.0f}")
            m2.metric("Cobrado", f"$ {at:,.0f}")
            m3.metric("Pendiente", f"$ {vt-at:,.0f}")
            
            st.dataframe(df_res.drop(columns=['fecha_dt']), use_container_width=True, hide_index=True)

    # --- HISTORIAL GENERAL ---
    st.divider()
    st.subheader("📋 Historial Reciente")
    df_h = df_v.copy()
    if st.session_state['rol'] != 'admin':
        df_h = df_h[df_h['empleado'].str.lower() == st.session_state['usuario'].lower()]
    st.dataframe(df_h.iloc[::-1], use_container_width=True, hide_index=True)

# --- 6. GESTIÓN EMPLEADOS ---
elif opcion == "Gestión de Empleados":
    st.title("👥 Gestión de Personal")
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
