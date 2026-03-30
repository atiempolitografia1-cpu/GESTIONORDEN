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
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbwefjYpHKmQNY6BY9-DXWAxk2GNN6VVeiVDxzr0xV-3Z7Ab9QLwkLulFK5d60rqQCVSSA/exec"

# --- 2. FUNCIONES DE FORMATO Y DATOS ---
def formato_pesos(valor):
    try:
        val = float(valor)
        return f"$ {val:,.0f}".replace(",", ".")
    except:
        return "$ 0"

def a_numero(valor):
    """Limpia el texto para convertirlo en número real funcional"""
    try:
        if valor is None or str(valor).strip() == "": return 0.0
        # Eliminamos símbolos y corregimos puntuación para que Python entienda el número
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
        if res.status_code == 200:
            return True
        else:
            st.error(f"Error de conexión con Excel (Código: {res.status_code})")
            return False
    except Exception as e:
        st.error(f"Error crítico: {e}")
        return False

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
    
    if st.session_state['rol'] == 'admin':
        df_v = df_v_completo.copy()
    else:
        df_v = df_v_completo[df_v_completo['empleado'] == st.session_state['usuario']].copy()
    
    tabs = st.tabs(["📝 Registrar", "✏️ Editar / Abonar", "📊 Reportes Avanzados"]) if st.session_state['rol'] == 'admin' else st.tabs(["📝 Registrar", "✏️ Editar / Abonar"])

    with tabs[0]: # REGISTRAR
        if 'limp_v' not in st.session_state: st.session_state['limp_v'] = 0
        vs = str(st.session_state['limp_v'])
        c1, c2, c3 = st.columns(3)
        v_ord = c1.text_input("N° Orden", key="o"+vs)
        v_cli = c2.text_input("Cliente", key="cl"+vs)
        v_nit = c3.text_input("NIT / CC", key="ni"+vs)
        
        c4, c5, c6 = st.columns(3)
        v_cel = c4.text_input("Celular", key="ce"+vs)
        v_cor = c5.text_input("Correo", key="co"+vs)
        v_fac = c6.radio("Factura", ["SÍ", "NO"], horizontal=True, key="fa"+vs)
        
        c7, c8 = st.columns(2)
        v_tot_raw = c7.text_input("Total ($ COP)", value="0", key="tr"+vs)
        v_tot = a_numero(v_tot_raw)
        c7.markdown(f'<div class="money-helper">{formato_pesos(v_tot)}</div>', unsafe_allow_html=True)
        
        v_abo_raw = c8.text_input("Abono Inicial ($ COP)", value="0", key="ar"+vs)
        v_abo = a_numero(v_abo_raw)
        c8.markdown(f'<div class="money-helper">{formato_pesos(v_abo)}</div>', unsafe_allow_html=True)
        
        v_desc = st.text_area("Descripción Trabajo", key="de"+vs)
        c9, c10 = st.columns(2)
        v_est = c9.selectbox("Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], key="es"+vs)
        v_pag = c10.selectbox("Medio Pago", ["EFECTIVO", "NEQUI", "DAVIPLATA", "BANCOLOMBIA"], key="pa"+vs)
        
        if st.button("💾 GUARDAR VENTA", use_container_width=True):
            if v_ord and v_cli:
                payload = {
                    "accion": "insertar", "tipo_registro": "ventas", 
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), 
                    "n_orden": str(v_ord), "descripcion": str(v_desc), 
                    "total": float(v_tot), "abono": float(v_abo), 
                    "saldo": float(v_tot-v_abo), "metodo_pago": str(v_pag), 
                    "estado": str(v_est), "empleado": st.session_state['usuario'], 
                    "cliente": str(v_cli), "nit": str(v_nit), "celular": str(v_cel), 
                    "correo": str(v_cor), "factura": str(v_fac), 
                    "historial_pagos": f"${v_abo:,.0f} ({v_pag}) {datetime.now().date()}"
                }
                if enviar_google(payload): 
                    st.session_state['limp_v'] += 1
                    st.success("✅ Venta registrada")
                    st.rerun()

    with tabs[1]: # EDITAR / ABONAR (COMPLETO)
        st.subheader("Modificar Orden Existente")
        if not df_v.empty:
            orden_buscada = st.selectbox("Seleccione la Orden a editar:", ["Seleccionar..."] + df_v['n_orden'].tolist())
            
            if orden_buscada != "Seleccionar...":
                idx = df_v[df_v['n_orden'] == orden_buscada].index[0]
                val = df_v.loc[idx]
                
                with st.form("form_edit"):
                    st.info(f"Editando Orden: {orden_buscada} | Registrada por: {val['empleado']}")
                    col1, col2 = st.columns(2)
                    e_cli = col1.text_input("Cliente", value=val['cliente'])
                    e_nit = col2.text_input("NIT / CC", value=val['nit'])
                    
                    col3, col4, col5 = st.columns(3)
                    e_cel = col3.text_input("Celular", value=val['celular'])
                    e_cor = col4.text_input("Correo", value=val['correo'])
                    e_fac = col5.selectbox("Factura", ["SÍ", "NO"], index=0 if val['factura'] == "SÍ" else 1)
                    
                    e_desc = st.text_area("Descripción Trabajo", value=val['descripcion'])
                    
                    col6, col7 = st.columns(2)
                    e_tot = a_numero(col6.text_input("Total ($ COP)", value=str(int(val['total_n']))))
                    col6.markdown(f'<div class="money-helper">{formato_pesos(e_tot)}</div>', unsafe_allow_html=True)
                    
                    e_nuevo_abo = a_numero(col7.text_input("Añadir nuevo abono ($ COP)", value="0"))
                    col7.markdown(f'<div class="money-helper">Abonar ahora: {formato_pesos(e_nuevo_abo)}</div>', unsafe_allow_html=True)
                    
                    abono_acumulado = val['abono_n'] + e_nuevo_abo
                    saldo_final = e_tot - abono_acumulado
                    st.warning(f"Saldo Previo: {formato_pesos(val['saldo_n'])} | **Nuevo Saldo: {formato_pesos(saldo_final)}**")
                    
                    col8, col9 = st.columns(2)
                    e_est = col8.selectbox("Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], index=["EN PROCESO", "TERMINADO", "PAGADO"].index(val['estado']) if val['estado'] in ["EN PROCESO", "TERMINADO", "PAGADO"] else 0)
                    e_pag = col9.selectbox("Medio del nuevo abono", ["EFECTIVO", "NEQUI", "DAVIPLATA", "BANCOLOMBIA"])

                    if st.form_submit_button("💾 ACTUALIZAR EN EXCEL"):
                        hist_act = val['historial_pagos']
                        if e_nuevo_abo > 0:
                            hist_act += f" | +${e_nuevo_abo:,.0f} ({e_pag}) {datetime.now().date()}"
                        
                        payload = {
                            "accion": "actualizar", "tipo_registro": "ventas", "id_busqueda": orden_buscada,
                            "cliente": e_cli, "nit": e_nit, "celular": e_cel, "correo": e_cor, "factura": e_fac,
                            "descripcion": e_desc, "total": float(e_tot), "abono": float(abono_acumulado),
                            "saldo": float(saldo_final), "estado": e_est, "historial_pagos": hist_act
                        }
                        if enviar_google(payload): 
                            st.success("✅ Orden actualizada en Excel")
                            st.rerun()


        with tabs[2]: # REPORTES AVANZADOS (RESTAURADO)
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

    
    # --- HISTORIAL ---
    st.divider()
    st.subheader("📋 Historial")
    busqueda = st.text_input("🔍 Buscar orden, cliente o descripción:")
    df_h = df_v.copy()
    if busqueda:
        mask = (df_h['n_orden'].astype(str).str.contains(busqueda, case=False) |
                df_h['cliente'].astype(str).str.contains(busqueda, case=False) |
                df_h['descripcion'].astype(str).str.contains(busqueda, case=False))
        df_h = df_h[mask]
    
    df_h['total'] = df_h['total_n'].apply(formato_pesos)
    df_h['abono'] = df_h['abono_n'].apply(formato_pesos)
    df_h['saldo'] = df_h['saldo_n'].apply(formato_pesos)
    st.dataframe(df_h.drop(columns=['total_n','abono_n','saldo_n','fecha_dt'], errors='ignore').iloc[::-1], use_container_width=True, hide_index=True)

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
