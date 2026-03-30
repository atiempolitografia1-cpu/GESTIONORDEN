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
    /* Estilo para métricas */
    [data-testid="stMetricValue"] { font-size: 1.8rem; color: #00802b; }
    /* Estilo para el visor de moneda en tiempo real */
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
    """Convierte un número a formato $ 1.234.567"""
    try:
        val = float(valor)
        return f"$ {val:,.0f}".replace(",", ".")
    except:
        return "$ 0"

def a_numero(valor):
    """Limpia el texto para convertirlo en número funcional"""
    try:
        if not valor: return 0.0
        # Elimina símbolos de peso, puntos de miles y espacios
        s = re.sub(r'[^\d,]', '', str(valor)).replace(',', '.')
        return float(s) if s else 0.0
    except: return 0.0

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
    df_v_comp = leer_datos("ventas")
    
    # --- FILTRO MAESTRO: ESTA ES LA CLAVE ---
    # Si es admin ve todo, si es empleado solo ve sus propias filas
    if st.session_state['rol'] == 'admin':
        df_v = df_v_comp.copy()
    else:
        # Filtramos el DataFrame para que solo contenga lo que el usuario logueado registró
        df_v = df_v_comp[df_v_comp['empleado'] == st.session_state['usuario']].copy()
    
    t_labels = ["📝 Registrar", "✏️ Editar / Abonar"]
    if st.session_state['rol'] == 'admin': t_labels.append("📊 Reportes Avanzados")
    tabs = st.tabs(t_labels)

    with tabs[0]: # REGISTRAR (Sin cambios, usa st.session_state['usuario'])
        if 'limp' not in st.session_state: st.session_state['limp'] = 0
        v = str(st.session_state['limp'])
        c1, c2, c3 = st.columns(3)
        ord, cli, nit = c1.text_input("N° Orden", key="o"+v), c2.text_input("Cliente", key="cl"+v), c3.text_input("NIT", key="ni"+v)
        c4, c5 = st.columns(2)
        tot = a_numero(c4.text_input("Total ($ COP)", value="0", key="t"+v))
        abo = a_numero(c5.text_input("Abono Inicial ($ COP)", value="0", key="a"+v))
        c4.markdown(f'<div class="money-helper">{formato_pesos(tot)}</div>', unsafe_allow_html=True)
        c5.markdown(f'<div class="money-helper">{formato_pesos(abo)}</div>', unsafe_allow_html=True)
        desc = st.text_area("Descripción", key="d"+v)
        c6, c7 = st.columns(2)
        est, pag = c6.selectbox("Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], key="e"+v), c7.selectbox("Pago", ["EFECTIVO", "NEQUI", "BANCOLOMBIA"], key="p"+v)
        if st.button("💾 GUARDAR VENTA", use_container_width=True):
            if ord and cli:
                p = {"accion": "insertar", "tipo_registro": "ventas", "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "n_orden": ord, "descripcion": desc, "total": float(tot), "abono": float(abo), "saldo": float(tot-abo), "metodo_pago": pag, "estado": est, "empleado": st.session_state['usuario'], "cliente": cli, "nit": nit, "celular": "", "correo": "", "factura": "NO", "historial_pagos": f"${abo:,.0f} ({pag}) {datetime.now().date()}"}
                if enviar_google(p): st.session_state['limp'] += 1; st.rerun()

    with tabs[1]: # EDITAR (USANDO EL FILTRO MAESTRO)
        if not df_v.empty:
            # El selectbox ahora solo mostrará las órdenes permitidas en df_v
            sel = st.selectbox("Orden a editar:", ["Seleccionar..."] + df_v['n_orden'].tolist())
            if sel != "Seleccionar...":
                val = df_v[df_v['n_orden'] == sel].iloc[0]
                with st.form("f_ed"):
                    e_cli = st.text_input("Cliente", value=val['cliente'])
                    e_desc = st.text_area("Descripción", value=val['descripcion'])
                    c1, c2 = st.columns(2)
                    e_tot = a_numero(c1.text_input("Total", value=str(int(val['total_n']))))
                    e_nab = a_numero(c2.text_input("Nuevo Abono", value="0"))
                    e_est = st.selectbox("Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], index=["EN PROCESO", "TERMINADO", "PAGADO"].index(val['estado']) if val['estado'] in ["EN PROCESO", "TERMINADO", "PAGADO"] else 0)
                    if st.form_submit_button("💾 ACTUALIZAR"):
                        h = val['historial_pagos'] + (f" | +${e_nab:,.0f} {datetime.now().date()}" if e_nab > 0 else "")
                        p = {"accion": "actualizar", "tipo_registro": "ventas", "id_busqueda": sel, "cliente": e_cli, "descripcion": e_desc, "total": float(e_tot), "abono": float(val['abono_n']+e_nab), "saldo": float(e_tot-(val['abono_n']+e_nab)), "estado": e_est, "historial_pagos": h}
                        if enviar_google(p): st.success("Ok"); st.rerun()
        else:
            st.info("No hay órdenes disponibles para editar.")

    if st.session_state['rol'] == 'admin':
        with tabs[2]: # REPORTES (PARA ADMIN)
            st.subheader("📊 Reporte Mensual")
            c1, c2 = st.columns(2)
            f_i, f_f = c1.date_input("Desde", datetime.now().replace(day=1)), c2.date_input("Hasta", datetime.now())
            df_r = df_v_comp.copy()
            df_r = df_r[df_r['fecha_dt'].notna()]
            df_r = df_r[(df_r['fecha_dt'].dt.date >= f_i) & (df_r['fecha_dt'].dt.date <= f_f)]
            m1, m2, m3 = st.columns(3)
            m1.metric("Ventas", formato_pesos(df_r['total_n'].sum()))
            m2.metric("Recaudado", formato_pesos(df_r['abono_n'].sum()))
            m3.metric("Saldos", formato_pesos(df_r['saldo_n'].sum()))
            st.dataframe(df_r[['fecha','n_orden','cliente','total','abono','saldo','estado','empleado']], use_container_width=True, hide_index=True)

    # --- HISTORIAL FILTRADO ---
    st.divider()
    st.subheader("📋 Historial de Órdenes")
    busq = st.text_input("🔍 Buscar:")
    df_h = df_v.copy() # Aquí df_h ya viene filtrado por el Filtro Maestro
    if busq:
        df_h = df_h[df_h['n_orden'].str.contains(busq, case=False) | df_h['cliente'].str.contains(busq, case=False)]
    
    # Definimos qué columnas ver (admin ve el nombre del empleado, el empleado no necesita verse a sí mismo)
    cols = ['fecha','n_orden','cliente','total','abono','saldo','estado']
    if st.session_state['rol'] == 'admin': cols.append('empleado')
    
    st.dataframe(df_h[cols].iloc[::-1], use_container_width=True, hide_index=True)


elif opcion == "Gestión de Empleados":
    st.title("👥 Personal")
    df_u = leer_datos("usuarios")
    t1, t2 = st.tabs(["➕ Nuevo Empleado", "✏️ Modificar / Eliminar"])
    
    with t1:
        with st.form("nuevo_emp"):
            n_nom = st.text_input("Nombre Completo")
            n_cla = st.text_input("Contraseña")
            n_rol = st.selectbox("Rol", ["empleado", "admin"])
            if st.form_submit_button("Registrar en el Sistema"):
                if n_nom and n_cla:
                    if enviar_google({"accion": "insertar", "tipo_registro": "usuarios", "nombre": n_nom, "clave": n_cla, "rol": n_rol}):
                        st.success(f"¡{n_nom} registrado!"); st.rerun()
    
    with t2:
        if not df_u.empty:
            u_sel = st.selectbox("Seleccione Usuario:", df_u['nombre'].tolist())
            datos_u = df_u[df_u['nombre'] == u_sel].iloc[0]
            with st.form("edit_emp"):
                e_cla = st.text_input("Nueva Contraseña", value=datos_u['clave'])
                e_rol = st.selectbox("Rol", ["empleado", "admin"], index=0 if datos_u['rol'] == 'empleado' else 1)
                c1, c2 = st.columns(2)
                if c1.form_submit_button("ACTUALIZAR DATOS"):
                    if enviar_google({"accion": "actualizar", "tipo_registro": "usuarios", "id_busqueda": u_sel, "clave": e_cla, "rol": e_rol}):
                        st.success("Datos actualizados"); st.rerun()
                if u_sel != st.session_state['usuario'] and c2.form_submit_button("⚠️ ELIMINAR ACCESO"):
                    if enviar_google({"accion": "eliminar", "tipo_registro": "usuarios", "id_busqueda": u_sel}):
                        st.warning("Usuario eliminado"); st.rerun()
