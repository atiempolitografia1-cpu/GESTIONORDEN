import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import io

# --- 1. CONFIGURACIÓN Y ESTILOS ---
st.set_page_config(page_title="Gestión Negocio Pro", layout="centered", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stDeployButton {display:none;}
    button[kind="headerNoPadding"] { visibility: visible !important; z-index: 9999991; background-color: rgba(255,255,255,0.1); border-radius: 5px; }
    [data-testid="stMetricValue"] { font-size: 1.8rem; color: #00802b; }
    .money-helper {
        font-size: 1.1rem;
        font-weight: bold;
        color: #00802b;
        background-color: #e6f4ea;
        padding: 5px 10px;
        border-radius: 5px;
        margin-top: -15px;
        margin-bottom: 15px;
        display: inline-block;
    }
    </style>
    """, unsafe_allow_html=True)

SHEET_ID = "1UGxbXTQhXKJ-JmKxpzglccDJrZgpCsTDflKO9N8RMTc"
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbwefjYpHKmQNY6BY9-DXWAxk2GNN6VVeiVDxzr0xV-3Z7Ab9QLwkLulFK5d60rqQCVSSA/exec"

# --- 2. FUNCIONES DE FORMATO Y DATOS ---
def formato_pesos(valor):
    try:
        val = float(valor)
        return f"$ {val:,.0f}".replace(",", ".")
    except:
        return "$ 0"

def a_numero(valor):
    try:
        if valor is None or str(valor).strip() == "": return 0.0
        s = str(valor).replace("$", "").replace(".", "").replace(" ", "").replace(",", ".")
        return float(s) if s else 0.0
    except:
        return 0.0

def leer_datos(pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={pestana}&t={datetime.now().microsecond}"
        res = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(res.text), dtype=str).fillna('')
        if pestana == "usuarios":
            df.columns = ['nombre', 'clave', 'rol'] + list(df.columns[3:])
        elif pestana == "ventas":
            cols = ['fecha', 'n_orden', 'descripcion', 'total', 'abono', 'saldo', 'metodo_pago', 'estado', 'empleado', 'cliente', 'nit', 'celular', 'correo', 'factura', 'historial_pagos']
            df = df.iloc[:, :len(cols)]
            df.columns = cols
            df['total_n'] = df['total'].apply(a_numero)
            df['abono_n'] = df['abono'].apply(a_numero)
            df['saldo_n'] = df['total_n'] - df['abono_n']
            df['fecha_dt'] = pd.to_datetime(df['fecha'], errors='coerce')
        return df
    except: return pd.DataFrame()

def enviar_google(payload):
    try:
        res = requests.post(URL_SCRIPT, json=payload, timeout=15)
        return res.status_code == 200
    except: return False

# --- 3. LOGIN ---
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False
df_users_db = leer_datos("usuarios")

if not st.session_state['autenticado']:
    st.title("🔐 Acceso al Sistema")
    with st.form("login"):
        u_list = df_users_db['nombre'].unique().tolist() if not df_users_db.empty else ["Administrador"]
        u_input = st.selectbox("Usuario", u_list)
        p_input = st.text_input("Contraseña", type="password")
        if st.form_submit_button("INGRESAR", use_container_width=True):
            user_data = df_users_db[df_users_db['nombre'] == u_input]
            if not user_data.empty and str(user_data.iloc[0]['clave']).strip() == str(p_input).strip():
                st.session_state.update({"autenticado": True, "usuario": u_input, "rol": str(user_data.iloc[0]['rol']).lower()})
                st.rerun()
            else: st.error("❌ Datos incorrectos")
    st.stop()

# --- 4. INTERFAZ ---
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state['usuario'].upper()}")
    menu = ["Ventas", "Gestión de Empleados"] if st.session_state['rol'] == 'admin' else ["Ventas"]
    opcion = st.radio("Menú:", menu)
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state['autenticado'] = False
        st.rerun()

if opcion == "Ventas":
    st.title("🚀 Gestión de Ventas")
    df_v_completo = leer_datos("ventas")
    df_v = df_v_completo.copy() if st.session_state['rol'] == 'admin' else df_v_completo[df_v_completo['empleado'] == st.session_state['usuario']].copy()
    
    # Manejo dinámico de pestañas según el ROL
    if st.session_state['rol'] == 'admin':
        tabs = st.tabs(["📝 Registrar", "✏️ Editar / Abonar", "📊 Reportes Avanzados"])
    else:
        tabs = st.tabs(["📝 Registrar", "✏️ Editar / Abonar"])

    with tabs[0]: # REGISTRAR
        if 'limp_v' not in st.session_state: st.session_state['limp_v'] = 0
        vs = str(st.session_state['limp_v'])
        c1, c2, c3 = st.columns(3)
        v_ord, v_cli, v_nit = c1.text_input("N° Orden", key="o"+vs), c2.text_input("Cliente", key="cl"+vs), c3.text_input("NIT / CC", key="ni"+vs)
        c4, c5, c6 = st.columns(3)
        v_cel, v_cor, v_fac = c4.text_input("Celular", key="ce"+vs), c5.text_input("Correo", key="co"+vs), c6.radio("Factura", ["SÍ", "NO"], horizontal=True, key="fa"+vs)
        c7, c8 = st.columns(2)
        v_tot = a_numero(c7.text_input("Total ($ COP)", value="0", key="tr"+vs))
        c7.markdown(f'<div class="money-helper">{formato_pesos(v_tot)}</div>', unsafe_allow_html=True)
        v_abo = a_numero(c8.text_input("Abono Inicial ($ COP)", value="0", key="ar"+vs))
        c8.markdown(f'<div class="money-helper">{formato_pesos(v_abo)}</div>', unsafe_allow_html=True)
        v_desc = st.text_area("Descripción Trabajo", key="de"+vs)
        c9, c10 = st.columns(2)
        v_est, v_pag = c9.selectbox("Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], key="es"+vs), c10.selectbox("Medio Pago", ["EFECTIVO", "NEQUI", "DAVIPLATA", "BANCOLOMBIA"], key="pa"+vs)
        if st.button("💾 GUARDAR VENTA", use_container_width=True):
            if v_ord and v_cli:
                p = {"accion": "insertar", "tipo_registro": "ventas", "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "n_orden": str(v_ord), "descripcion": str(v_desc), "total": float(v_tot), "abono": float(v_abo), "saldo": float(v_tot-v_abo), "metodo_pago": str(v_pag), "estado": str(v_est), "empleado": st.session_state['usuario'], "cliente": str(v_cli), "nit": str(v_nit), "celular": str(v_cel), "correo": str(v_cor), "factura": str(v_fac), "historial_pagos": f"${v_abo:,.0f} ({v_pag}) {datetime.now().date()}"}
                if enviar_google(p): 
                    st.session_state['limp_v'] += 1
                    st.success("✅ Registrado"); st.rerun()

    with tabs[1]: # EDITAR / ABONAR
        if not df_v.empty:
            ord_ed = st.selectbox("Seleccione Orden:", ["Seleccionar..."] + df_v['n_orden'].tolist())
            if ord_ed != "Seleccionar...":
                val = df_v[df_v['n_orden'] == ord_ed].iloc[0]
                with st.form("form_edit"):
                    c1, c2 = st.columns(2)
                    e_cli, e_nit = c1.text_input("Cliente", value=val['cliente']), c2.text_input("NIT / CC", value=val['nit'])
                    c3, c4, c5 = st.columns(3)
                    e_cel, e_cor, e_fac = c3.text_input("Celular", value=val['celular']), c4.text_input("Correo", value=val['correo']), c5.selectbox("Factura", ["SÍ", "NO"], index=0 if val['factura']=="SÍ" else 1)
                    e_desc = st.text_area("Descripción", value=val['descripcion'])
                    c6, c7 = st.columns(2)
                    e_tot = a_numero(c6.text_input("Total", value=str(int(val['total_n']))))
                    e_n_abo = a_numero(c7.text_input("Nuevo Abono", value="0"))
                    c8, c9 = st.columns(2)
                    e_est = c8.selectbox("Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], index=["EN PROCESO", "TERMINADO", "PAGADO"].index(val['estado']) if val['estado'] in ["EN PROCESO", "TERMINADO", "PAGADO"] else 0)
                    e_pag = c9.selectbox("Medio Abono", ["EFECTIVO", "NEQUI", "DAVIPLATA", "BANCOLOMBIA"])
                    if st.form_submit_button("💾 ACTUALIZAR EXCEL"):
                        ab_ac = val['abono_n'] + e_n_abo
                        h = val['historial_pagos'] + (f" | +${e_n_abo:,.0f} ({e_pag}) {datetime.now().date()}" if e_n_abo > 0 else "")
                        p = {"accion": "actualizar", "tipo_registro": "ventas", "id_busqueda": ord_ed, "cliente": e_cli, "nit": e_nit, "celular": e_cel, "correo": e_cor, "factura": e_fac, "descripcion": e_desc, "total": float(e_tot), "abono": float(ab_ac), "saldo": float(e_tot-ab_ac), "estado": e_est, "historial_pagos": h}
                        if enviar_google(p): st.success("✅ Actualizado"); st.rerun()

    # SOLO PARA ADMINS: REPORTE AVANZADO
    if st.session_state['rol'] == 'admin':
        with tabs[2]:
            st.subheader("📊 Filtros de Reporte")
            c1, c2, c3 = st.columns(3)
            f_ini = c1.date_input("Desde", datetime.now().replace(day=1))
            f_fin = c2.date_input("Hasta", datetime.now())
            f_emp = c3.selectbox("Empleado", ["TODOS"] + df_v_completo['empleado'].unique().tolist())
            
            df_r = df_v_completo.copy()
            df_r['fecha_dt'] = pd.to_datetime(df_r['fecha']).dt.date
            df_r = df_r[(df_r['fecha_dt'] >= f_ini) & (df_r['fecha_dt'] <= f_fin)]
            if f_emp != "TODOS": df_r = df_r[df_r['empleado'] == f_emp]
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Ventas Totales", formato_pesos(df_r['total_n'].sum()))
            m2.metric("Recaudado (Abonos)", formato_pesos(df_r['abono_n'].sum()))
            m3.metric("Por Cobrar (Saldos)", formato_pesos(df_r['saldo_n'].sum()))
            st.dataframe(df_r.drop(columns=['total_n','abono_n','saldo_n','fecha_dt'], errors='ignore'), use_container_width=True, hide_index=True)

    # --- HISTORIAL RÁPIDO ---
    st.divider()
    st.subheader("📋 Historial Reciente")
    busq = st.text_input("🔍 Buscar orden o cliente:")
    df_h = df_v.copy()
    if busq: df_h = df_h[df_h['n_orden'].str.contains(busq, case=False) | df_h['cliente'].str.contains(busq, case=False)]
    df_h['total'], df_h['abono'], df_h['saldo'] = df_h['total_n'].apply(formato_pesos), df_h['abono_n'].apply(formato_pesos), df_h['saldo_n'].apply(formato_pesos)
    st.dataframe(df_h.drop(columns=['total_n','abono_n','saldo_n','fecha_dt'], errors='ignore').iloc[::-1], use_container_width=True, hide_index=True)

elif opcion == "Gestión de Empleados":
    st.title("👥 Personal")
    df_u = leer_datos("usuarios")
    t1, t2 = st.tabs(["➕ Nuevo", "✏️ Editar"])
    with t1:
        with st.form("n_u"):
            n, c, r = st.text_input("Nombre"), st.text_input("Clave"), st.selectbox("Rol", ["empleado", "admin"])
            if st.form_submit_button("Registrar"):
                if enviar_google({"accion": "insertar", "tipo_registro": "usuarios", "nombre": n, "clave": c, "rol": r}): st.success("Ok"); st.rerun()
    with t2:
        if not df_u.empty:
            u_s = st.selectbox("Usuario:", df_u['nombre'].tolist())
            dat = df_u[df_u['nombre'] == u_s].iloc[0]
            with st.form("e_u"):
                ec, er = st.text_input("Clave", value=dat['clave']), st.selectbox("Rol", ["empleado", "admin"], index=0 if dat['rol']=='empleado' else 1)
                if st.form_submit_button("Actualizar"):
                    if enviar_google({"accion": "actualizar", "tipo_registro": "usuarios", "id_busqueda": u_s, "clave": ec, "rol": er}): st.success("Ok"); st.rerun()
