import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import io
import re

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
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbw4AawA3h-NJbSU7ZJc2EqpsEJEmfPVT0aOF6V0JMp-V3kiToMtwfmJyXhD79H9uZ7DIQ/exec"

# --- 2. FUNCIONES DE FORMATO Y DATOS ---
def formato_pesos(valor):
    try:
        val = float(valor)
        return f"$ {val:,.0f}".replace(",", ".")
    except:
        return "$ 0"

def a_numero(valor):
    try:
        if not valor: return 0.0
        s = re.sub(r'[^\d,]', '', str(valor)).replace(',', '.')
        return float(s) if s else 0.0
    except: return 0.0

def leer_datos(pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={pestana}&t={datetime.now().microsecond}"
        res = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(res.text), dtype=str).fillna('')
        
        if pestana == "ventas":
            cols = ['fecha', 'n_orden', 'descripcion', 'total', 'abono', 'saldo', 'metodo_pago', 'estado', 'empleado', 'cliente', 'nit', 'celular', 'correo', 'factura', 'historial_pagos']
            df = df.iloc[:, :len(cols)]
            df.columns = cols
            df['total_n'] = df['total'].apply(a_numero)
            df['abono_n'] = df['abono'].apply(a_numero)
            df['saldo_n'] = df['total_n'] - df['abono_n']
            df['fecha_dt'] = pd.to_datetime(df['fecha'], errors='coerce')
            df['solo_dia'] = df['fecha_dt'].dt.date
            
        elif pestana == "usuarios":
            df.columns = ['nombre', 'clave', 'rol'] + list(df.columns[3:])
            
        elif pestana == "caja":
            cols_caja = ['fecha', 'n_orden', 'valor', 'metodo', 'empleado']
            df = df.iloc[:, :len(cols_caja)]
            df.columns = cols_caja
            df['valor_n'] = df['valor'].apply(a_numero)
            df['fecha_dt'] = pd.to_datetime(df['fecha'], dayfirst=True, errors='coerce')
            df['solo_dia'] = df['fecha_dt'].dt.date
            
        return df
    except: 
        return pd.DataFrame()

def enviar_google(payload):
    try:
        res = requests.post(URL_SCRIPT, json=payload, timeout=15)
        return res.status_code == 200
    except: return False

# --- 3. LOGIN ---
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False
if 'limp' not in st.session_state: st.session_state['limp'] = 0

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
    df_v_comp = leer_datos("ventas")
    
    if st.session_state['rol'] == 'admin':
        df_v = df_v_comp.copy()
    else:
        df_v = df_v_comp[df_v_comp['empleado'] == st.session_state['usuario']].copy()
    
    t_labels = ["📝 Registrar", "✏️ Editar / Abonar"]
    if st.session_state['rol'] == 'admin': t_labels.append("📊 Reportes Avanzados")
    tabs = st.tabs(t_labels)

    # --- PESTAÑA REGISTRAR ---
    with tabs[0]:
        v = str(st.session_state.get('limp', 0)) 
        st.subheader("📝 Registrar Nueva Orden")
        fecha_manual = st.date_input("📅 Fecha de la Orden", datetime.now().date())
        c1, c2 = st.columns(2)
        ord = c1.text_input("N° Orden", key="or"+v)
        cli = c2.text_input("Cliente", key="cl"+v)
        c3, c4, c5 = st.columns(3)
        nit = c3.text_input("NIT / CC", key="ni"+v)
        cel = c4.text_input("Celular", key="ce"+v)
        cor = c5.text_input("Correo", key="co"+v)
        c6, c7 = st.columns(2)
        tot = a_numero(c6.text_input("Total ($ COP)", value="0", key="t"+v))
        abo = a_numero(c7.text_input("Abono Inicial ($ COP)", value="0", key="a"+v))
        c6.markdown(f'<div class="money-helper">{formato_pesos(tot)}</div>', unsafe_allow_html=True)
        c7.markdown(f'<div class="money-helper">{formato_pesos(abo)}</div>', unsafe_allow_html=True)
        desc = st.text_area("Descripción del Trabajo", key="d"+v)
        c8, c9, c10 = st.columns(3)
        est = c8.selectbox("Estado", ["EN PROCESO", "TERMINADO", "ENTREGADO"], key="e"+v)
        pag = c9.selectbox("Método de Pago", ["SIN ABONO", "EFECTIVO", "NEQUI", "BANCOLOMBIA", "DAVIPLATA"], key="p"+v)
        fac = c10.selectbox("¿Requiere Factura?", ["NO", "SI"], key="f"+v)

        if st.button("💾 GUARDAR VENTA", use_container_width=True):
            if abo > 0 and pag == "SIN ABONO":
                st.error("🚫 Elija medio de pago para el abono.")
            elif not ord or not cli:
                st.error("⚠️ N° Orden y Cliente obligatorios.")
            else:
                fecha_str = fecha_manual.strftime("%d/%m/%Y")
                p_venta = {"accion": "insertar", "tipo_registro": "ventas", "fecha": fecha_str, "n_orden": str(ord), "descripcion": str(desc), "total": float(tot), "abono": float(abo), "saldo": float(tot - abo), "metodo_pago": str(pag), "estado": str(est), "empleado": str(st.session_state['usuario']), "cliente": str(cli), "nit": str(nit), "celular": str(cel), "correo": str(cor), "factura": str(fac), "historial_pagos": f"{formato_pesos(abo)} ({pag}) {fecha_str}"}
                p_caja = {"accion": "insertar", "tipo_registro": "caja", "fecha": fecha_str, "n_orden": str(ord), "valor": float(abo), "metodo": str(pag), "empleado": str(st.session_state['usuario'])}
                if enviar_google(p_venta):
                    enviar_google(p_caja)
                    st.success(f"✅ Orden {ord} guardada")
                    st.session_state['limp'] += 1
                    st.rerun()

    # --- PESTAÑA EDITAR / ABONAR ---
    with tabs[1]:
        if not df_v.empty:
            sel = st.selectbox("Seleccione la Orden a editar:", ["Seleccionar..."] + df_v['n_orden'].tolist())
            if sel != "Seleccionar...":
                val = df_v[df_v['n_orden'] == sel].iloc[0]
                st.info(f"Orden: **{sel}** | Registrada por: **{val['empleado']}**")
                with st.form("f_edicion_pro"):
                    c1, c2 = st.columns(2)
                    e_cli = c1.text_input("Cliente", value=val['cliente'])
                    e_nit = c2.text_input("NIT / CC", value=val['nit'])
                    c3, c4, c5 = st.columns(3)
                    e_cel = c3.text_input("Celular", value=val['celular'])
                    e_cor = c4.text_input("Correo", value=val['correo'])
                    e_fac = c5.selectbox("Factura", ["NO", "SI"], index=0 if val['factura'] == "NO" else 1)
                    e_desc = st.text_area("Descripción Trabajo", value=val['descripcion'])
                    st.divider()
                    c6, c7 = st.columns(2)
                    es_admin = st.session_state.get('rol') == 'admin'
                    e_tot = a_numero(c6.text_input("Total ($ COP)", value=str(int(val['total_n'])), disabled=not es_admin))
                    e_nab = a_numero(c7.text_input("Añadir nuevo abono ($ COP)", value="0"))
                    c_fecha_edit, c_met_edit = st.columns(2)
                    fecha_abono_manual = c_fecha_edit.date_input("📅 Fecha de este abono", datetime.now().date())
                    e_met = c_met_edit.selectbox("Medio del nuevo abono", ["EFECTIVO", "NEQUI", "BANCOLOMBIA", "DAVIPLATA"])
                    
                    nuevo_abono_total = val['abono_n'] + e_nab
                    nuevo_saldo = e_tot - nuevo_abono_total
                    st.warning(f"Saldo actual: {formato_pesos(val['saldo_n'])} | **Nuevo Saldo: {formato_pesos(nuevo_saldo)}**")
                    
                    e_est = st.selectbox("Estado de la Orden", ["EN PROCESO", "TERMINADO", "PAGADO"], 
                                         index=["EN PROCESO", "TERMINADO", "PAGADO"].index(val['estado']) if val['estado'] in ["EN PROCESO", "TERMINADO", "PAGADO"] else 0)
                    
                    if st.form_submit_button("💾 ACTUALIZAR ORDEN", use_container_width=True):
                        f_abono_str = fecha_abono_manual.strftime('%d/%m/%Y')
                        h_pago = val['historial_pagos']
                        if e_nab > 0:
                            h_pago += f" | +{formato_pesos(e_nab)} ({e_met}) {f_abono_str}"
                        
                        payload = {"accion": "actualizar", "tipo_registro": "ventas", "id_busqueda": sel, "cliente": e_cli, "nit": e_nit, "celular": e_cel, "correo": e_cor, "factura": e_fac, "descripcion": e_desc, "total": float(e_tot), "abono": float(nuevo_abono_total), "saldo": float(nuevo_saldo), "estado": e_est, "historial_pagos": h_pago}
                        
                        if enviar_google(payload):
                            if e_nab > 0:
                                enviar_google({"accion": "insertar", "tipo_registro": "caja", "fecha": f_abono_str, "n_orden": str(sel), "valor": float(e_nab), "metodo": str(e_met), "empleado": str(st.session_state['usuario'])})
                            st.success("✅ Actualizado"); st.rerun()

                if st.session_state['rol'] == 'admin':
                    st.divider()
                    with st.expander("🚨 ZONA DE PELIGRO - ELIMINAR ORDEN"):
                        if st.button(f"🗑️ CONFIRMAR ELIMINAR ORDEN {sel}", use_container_width=True):
                            if enviar_google({"accion": "eliminar", "tipo_registro": "ventas", "id_busqueda": sel}):
                                st.error("Orden eliminada"); st.rerun()
        else:
            st.info("No hay órdenes.")

    # --- PESTAÑA REPORTES (ADMIN) ---
    import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import io
import re

# --- 1. CONFIGURACIÓN Y ESTILOS ---
st.set_page_config(page_title="Gestión Negocio Pro", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stDeployButton {display:none;}
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
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbw4AawA3h-NJbSU7ZJc2EqpsEJEmfPVT0aOF6V0JMp-V3kiToMtwfmJyXhD79H9uZ7DIQ/exec"

# --- 2. FUNCIONES ---
def formato_pesos(valor):
    try:
        val = float(valor)
        return f"$ {val:,.0f}".replace(",", ".")
    except: return "$ 0"

def a_numero(valor):
    try:
        if not valor: return 0.0
        s = re.sub(r'[^\d,]', '', str(valor)).replace(',', '.')
        return float(s) if s else 0.0
    except: return 0.0

def leer_datos(pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={pestana}&t={datetime.now().microsecond}"
        res = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(res.text), dtype=str).fillna('')
        if pestana == "ventas":
            cols = ['fecha', 'n_orden', 'descripcion', 'total', 'abono', 'saldo', 'metodo_pago', 'estado', 'empleado', 'cliente', 'nit', 'celular', 'correo', 'factura', 'historial_pagos']
            df = df.iloc[:, :len(cols)]
            df.columns = cols
            df['total_n'] = df['total'].apply(a_numero)
            df['abono_n'] = df['abono'].apply(a_numero)
            df['saldo_n'] = df['total_n'] - df['abono_n']
            df['fecha_dt'] = pd.to_datetime(df['fecha'], errors='coerce')
            df['solo_dia'] = df['fecha_dt'].dt.date
        elif pestana == "caja":
            df.columns = ['fecha', 'n_orden', 'valor', 'metodo', 'empleado']
            df['valor_n'] = df['valor'].apply(a_numero)
            df['fecha_dt'] = pd.to_datetime(df['fecha'], dayfirst=True, errors='coerce')
            df['solo_dia'] = df['fecha_dt'].dt.date
        return df
    except: return pd.DataFrame()

def enviar_google(payload):
    try:
        res = requests.post(URL_SCRIPT, json=payload, timeout=15)
        return res.status_code == 200
    except: return False

# --- 3. LOGIN ---
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False
if 'limp' not in st.session_state: st.session_state['limp'] = 0

df_u_db = leer_datos("usuarios")
if not st.session_state['autenticado']:
    st.title("🔐 Acceso")
    with st.form("login"):
        u_list = df_u_db['nombre'].tolist() if not df_u_db.empty else ["admin"]
        u_in = st.selectbox("Usuario", u_list)
        p_in = st.text_input("Clave", type="password")
        if st.form_submit_button("INGRESAR"):
            u_dat = df_u_db[df_u_db['nombre'] == u_in]
            if not u_dat.empty and str(u_dat.iloc[0]['clave']).strip() == str(p_in).strip():
                st.session_state.update({"autenticado": True, "usuario": u_in, "rol": str(u_dat.iloc[0]['rol']).lower()})
                st.rerun()
    st.stop()

# --- 4. INTERFAZ ---
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state['usuario'].upper()}")
    menu = ["Ventas", "Gestión de Empleados"] if st.session_state['rol'] == 'admin' else ["Ventas"]
    opcion = st.radio("Menú:", menu)
    if st.button("🚪 Cerrar Sesión"):
        st.session_state['autenticado'] = False
        st.rerun()

if opcion == "Ventas":
    st.title("🚀 Gestión de Ventas")
    df_v_comp = leer_datos("ventas")
    df_v = df_v_comp if st.session_state['rol'] == 'admin' else df_v_comp[df_v_comp['empleado'] == st.session_state['usuario']]
    
    tabs = st.tabs(["📝 Registrar", "✏️ Editar / Abonar", "📊 Reportes Avanzados"] if st.session_state['rol'] == 'admin' else ["📝 Registrar", "✏️ Editar / Abonar"])

    with tabs[0]:
        v = str(st.session_state['limp'])
        st.subheader("Nueva Orden")
        f_reg = st.date_input("Fecha", datetime.now().date(), key="f"+v)
        c1, c2 = st.columns(2)
        ord_n = c1.text_input("Orden", key="o"+v)
        cli_n = c2.text_input("Cliente", key="cl"+v)
        c3, c4 = st.columns(2)
        tot_n = a_numero(c3.text_input("Total", value="0", key="t"+v))
        abo_n = a_numero(c4.text_input("Abono", value="0", key="a"+v))
        c3.markdown(f'<div class="money-helper">{formato_pesos(tot_n)}</div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="money-helper">{formato_pesos(abo_n)}</div>', unsafe_allow_html=True)
        met_n = st.selectbox("Pago", ["EFECTIVO", "NEQUI", "BANCOLOMBIA", "DAVIPLATA", "SIN ABONO"], key="m"+v)
        if st.button("💾 GUARDAR"):
            f_s = f_reg.strftime("%d/%m/%Y")
            if enviar_google({"accion":"insertar","tipo_registro":"ventas","fecha":f_s,"n_orden":ord_n,"cliente":cli_n,"total":tot_n,"abono":abo_n,"saldo":tot_n-abo_n,"metodo_pago":met_n,"empleado":st.session_state['usuario'],"historial_pagos":f"{formato_pesos(abo_n)} ({met_n}) {f_s}"}):
                if abo_n > 0: enviar_google({"accion":"insertar","tipo_registro":"caja","fecha":f_s,"n_orden":ord_n,"valor":abo_n,"metodo":met_n,"empleado":st.session_state['usuario']})
                st.success("Guardado"); st.session_state['limp']+=1; st.rerun()

    with tabs[1]:
        if not df_v.empty:
            sel = st.selectbox("Orden:", ["Seleccionar..."] + df_v['n_orden'].tolist())
            if sel != "Seleccionar...":
                val = df_v[df_v['n_orden'] == sel].iloc[0]
                with st.form("edit"):
                    e_nab = a_numero(st.text_input("Nuevo Abono", value="0"))
                    e_fec = st.date_input("Fecha Abono", datetime.now().date())
                    e_met = st.selectbox("Medio", ["EFECTIVO", "NEQUI", "BANCOLOMBIA", "DAVIPLATA"])
                    e_est = st.selectbox("Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], index=0)
                    if st.form_submit_button("ACTUALIZAR"):
                        f_s = e_fec.strftime("%d/%m/%Y")
                        n_abo = val['abono_n'] + e_nab
                        h_p = val['historial_pagos'] + (f" | +{formato_pesos(e_nab)} ({e_met}) {f_s}" if e_nab > 0 else "")
                        if enviar_google({"accion":"actualizar","tipo_registro":"ventas","id_busqueda":sel,"abono":n_abo,"saldo":val['total_n']-n_abo,"estado":e_est,"historial_pagos":h_p}):
                            if e_nab > 0: enviar_google({"accion":"insertar","tipo_registro":"caja","fecha":f_s,"n_orden":sel,"valor":e_nab,"metodo":e_met,"empleado":st.session_state['usuario']})
                            st.rerun()

    if st.session_state['rol'] == 'admin':
        with tabs[2]:
            st.subheader("🧐 Reportes de Ventas, Caja y Cartera")
            df_caja = leer_datos("caja")
            c1, c2, c3 = st.columns(3)
            f_i = c1.date_input("Desde", datetime.now().date())
            f_f = c2.date_input("Hasta", datetime.now().date())
            e_s = c3.selectbox("Empleado", ["TODOS"] + df_u_db['nombre'].tolist())

            # --- SECCION CAJA REAL ---
            st.markdown("### 💰 Cuadre de Caja")
            if not df_caja.empty:
                df_c_f = df_caja[(df_caja['solo_dia'] >= f_i) & (df_caja['solo_dia'] <= f_f)]
                if e_s != "TODOS": df_c_f = df_c_f[df_c_f['empleado'] == e_s]
                for emp in df_c_f['empleado'].unique():
                    with st.expander(f"Caja de: {emp.upper()}", expanded=True):
                        df_e = df_c_f[df_c_f['empleado'] == emp]
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("Efectivo", formato_pesos(df_e[df_e['metodo']=="EFECTIVO"]['valor_n'].sum()))
                        col2.metric("Nequi", formato_pesos(df_e[df_e['metodo']=="NEQUI"]['valor_n'].sum()))
                        col3.metric("Bancolombia", formato_pesos(df_e[df_e['metodo']=="BANCOLOMBIA"]['valor_n'].sum()))
                        col4.metric("Daviplata", formato_pesos(df_e[df_e['metodo']=="DAVIPLATA"]['valor_n'].sum()))
                        st.write(f"**Total {emp}:** {formato_pesos(df_e['valor_n'].sum())}")

            # --- SECCION CARTERA ---
            st.divider()
            st.markdown("### 🔍 Cartera y Saldos Pendientes")
            df_r = df_v_comp.copy()
            if not df_r.empty:
                df_r = df_r[(df_r['solo_dia'] >= f_i) & (df_r['solo_dia'] <= f_f)]
                if e_s != "TODOS": df_r = df_r[df_r['empleado'] == e_s]
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Ventas", formato_pesos(df_r['total_n'].sum()))
                m2.metric("Abonado", formato_pesos(df_r['abono_n'].sum()))
                m3.metric("Cartera (Deuda)", formato_pesos(df_r['saldo_n'].sum()), delta_color="inverse")
                st.dataframe(df_r[['fecha','n_orden','cliente','total','abono','saldo','estado','empleado']], use_container_width=True, hide_index=True)

    # --- HISTORIAL ABAJO ---
    st.divider()
    st.subheader("📋 Historial Rápido")
    bus = st.text_input("Buscar por Orden o Cliente:")
    df_h = df_v.copy()
    if bus: df_h = df_h[df_h['n_orden'].str.contains(bus, case=False) | df_h['cliente'].str.contains(bus, case=False)]
    st.dataframe(df_h[['fecha','n_orden','cliente','total','saldo','estado']].iloc[::-1], use_container_width=True, hide_index=True)

elif opcion == "Gestión de Empleados":
    st.title("👥 Empleados")
    # ... Lógica de empleados simplificada ...
    df_emp = leer_datos("usuarios")
    st.dataframe(df_emp)
