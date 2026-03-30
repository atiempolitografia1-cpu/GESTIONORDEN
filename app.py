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
    /* Estilo para la confirmación de dinero en verde */
    .money-preview {
        color: #00802b;
        font-weight: bold;
        background-color: #e6ffed;
        padding: 2px 10px;
        border-radius: 5px;
        border: 1px solid #b7eb8f;
        display: inline-block;
        margin-top: -15px;
        margin-bottom: 10px;
    }
    [data-testid="stMetricValue"] { font-size: 1.8rem; color: #00802b; }
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
        # Elimina cualquier cosa que no sea número o punto decimal
        s = re.sub(r'[^\d.]', '', str(valor))
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
    df_v = leer_datos("ventas")
    tabs = st.tabs(["📝 Registrar", "✏️ Editar / Abonar", "📊 Reportes Avanzados"]) if st.session_state['rol'] == 'admin' else st.tabs(["📝 Registrar", "✏️ Editar / Abonar"])

    with tabs[0]: # REGISTRAR
        if 'limp_v' not in st.session_state: st.session_state['limp_v'] = 0
        vs = str(st.session_state['limp_v'])
        c1, c2, c3 = st.columns(3)
        v_ord = c1.text_input("N° Orden", key="o"+vs)
        v_cli = c2.text_input("Cliente", key="cl"+vs)
        v_nit = c3.text_input("NIT / CC", key="ni"+vs)
        
        c7, c8 = st.columns(2)
        # Cambiado a number_input para evitar errores de librerías
        v_tot = c7.number_input("Total Venta ($)", min_value=0, step=1000, key="tr"+vs)
        c7.markdown(f'<div class="money-preview">Confirmado: {formato_pesos(v_tot)}</div>', unsafe_allow_html=True)
        
        v_abo = c8.number_input("Abono Inicial ($)", min_value=0, step=1000, key="ar"+vs)
        c8.markdown(f'<div class="money-preview">Confirmado: {formato_pesos(v_abo)}</div>', unsafe_allow_html=True)
        
        v_desc = st.text_area("Descripción Trabajo", key="de"+vs)
        c9, c10 = st.columns(2)
        v_est = c9.selectbox("Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], key="es"+vs)
        v_pag = c10.selectbox("Medio Pago", ["EFECTIVO", "NEQUI", "DAVIPLATA", "BANCOLOMBIA"], key="pa"+vs)
        
        if st.button("💾 GUARDAR VENTA", use_container_width=True):
            if v_ord and v_cli:
                payload = {"accion": "insertar", "tipo_registro": "ventas", "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "n_orden": v_ord, "descripcion": v_desc, "total": v_tot, "abono": v_abo, "saldo": v_tot-v_abo, "metodo_pago": v_pag, "estado": v_est, "empleado": st.session_state['usuario'], "cliente": v_cli, "nit": v_nit, "historial_pagos": f"${v_abo:,.0f} ({v_pag}) {datetime.now().date()}"}
                if enviar_google(payload): st.session_state['limp_v'] += 1; st.success("¡Guardado!"); st.rerun()

    with tabs[1]: # EDITAR ORDEN
        st.subheader("Modificar Orden Existente")
        if not df_v.empty:
            orden_buscada = st.selectbox("Seleccione la Orden a editar:", ["Seleccionar..."] + df_v['n_orden'].tolist())
            if orden_buscada != "Seleccionar...":
                idx = df_v[df_v['n_orden'] == orden_buscada].index[0]
                val = df_v.loc[idx]
                
                with st.form("form_edit"):
                    st.info(f"Editando Orden: {orden_buscada}")
                    e_cli = st.text_input("Cliente", value=val['cliente'])
                    e_desc = st.text_area("Descripción Trabajo", value=val['descripcion'])
                    
                    col6, col7 = st.columns(2)
                    e_tot = col6.number_input("Total de la Venta ($)", value=int(val['total_n']), step=1000)
                    col6.markdown(f'<div class="money-preview">{formato_pesos(e_tot)}</div>', unsafe_allow_html=True)
                    
                    e_nuevo_abo = col7.number_input("¿Cuánto abona HOY? ($)", value=0, step=1000)
                    col7.markdown(f'<div class="money-preview">Abono hoy: {formato_pesos(e_nuevo_abo)}</div>', unsafe_allow_html=True)
                    
                    abono_total_acumulado = val['abono_n'] + e_nuevo_abo
                    nuevo_saldo = e_tot - abono_total_acumulado
                    
                    st.warning(f"Saldo previo: {formato_pesos(val['saldo_n'])} | **Nuevo Saldo Final: {formato_pesos(nuevo_saldo)}**")
                    
                    col8, col9 = st.columns(2)
                    e_est = col8.selectbox("Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], index=["EN PROCESO", "TERMINADO", "PAGADO"].index(val['estado']) if val['estado'] in ["EN PROCESO", "TERMINADO", "PAGADO"] else 0)
                    e_pag = col9.selectbox("Medio del nuevo abono", ["EFECTIVO", "NEQUI", "DAVIPLATA", "BANCOLOMBIA"])

                    if st.form_submit_button("💾 ACTUALIZAR TODA LA ORDEN"):
                        hist_act = val['historial_pagos']
                        if e_nuevo_abo > 0:
                            hist_act += f" | +${e_nuevo_abo:,.0f} ({e_pag}) {datetime.now().date()}"
                        
                        payload = {
                            "accion": "actualizar", "tipo_registro": "ventas", "id_busqueda": orden_buscada,
                            "cliente": e_cli, "descripcion": e_desc, "total": e_tot, 
                            "abono": abono_total_acumulado, "saldo": nuevo_saldo, "estado": e_est, "historial_pagos": hist_act
                        }
                        if enviar_google(payload): st.success("✅ Orden actualizada"); st.rerun()
        else:
            st.warning("No hay órdenes.")
            

    if st.session_state['rol'] == 'admin':
        with tabs[2]: # REPORTES
            st.subheader("📊 Auditoría de Caja")
            f1, f2 = st.columns(2)
            sel_emp = f1.selectbox("👤 Empleado:", ["Todos"] + df_v['empleado'].unique().tolist())
            tipo_pago = f2.radio("💰 Filtro:", ["Todas", "Solo Pendientes", "Solo Pagadas"], horizontal=True)
            
            modo_t = st.radio("📅 Rango:", ["Todo", "Día / Semana", "Mes / Año"], horizontal=True)
            df_r = df_v.copy()
            
            if modo_t == "Día / Semana":
                rango = st.date_input("Rango:", value=[datetime.now(), datetime.now()])
                if len(rango) == 2:
                    df_r = df_r[(df_r['fecha_dt'].dt.date >= rango[0]) & (df_r['fecha_dt'].dt.date <= rango[1])]
            elif modo_t == "Mes / Año":
                m = st.selectbox("Mes:", range(1,13), index=datetime.now().month-1, format_func=lambda x: ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"][x-1])
                a = st.selectbox("Año:", sorted(df_v['fecha_dt'].dt.year.dropna().unique().astype(int), reverse=True) if not df_v.empty else [2026])
                df_r = df_r[(df_r['fecha_dt'].dt.month == m) & (df_r['fecha_dt'].dt.year == a)]
            
            if sel_emp != "Todos": df_r = df_r[df_r['empleado'] == sel_emp]
            if tipo_pago == "Solo Pendientes": df_r = df_r[df_r['saldo_n'] > 100]
            elif tipo_pago == "Solo Pagadas": df_r = df_r[df_r['saldo_n'] <= 100]

            m1, m2, m3 = st.columns(3)
            m1.metric("Ventas", formato_pesos(df_r['total_n'].sum()))
            m2.metric("Cobrado", formato_pesos(df_r['abono_n'].sum()))
            m3.metric("Por Cobrar", formato_pesos(df_r['saldo_n'].sum()))
            
            df_m = df_r.copy()
            df_m['total'] = df_m['total_n'].apply(formato_pesos)
            df_m['abono'] = df_m['abono_n'].apply(formato_pesos)
            df_m['saldo'] = df_m['saldo_n'].apply(formato_pesos)
            st.dataframe(df_m.drop(columns=['total_n','abono_n','saldo_n','fecha_dt'], errors='ignore'), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("📋 Historial")
    df_h = df_v.copy()
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
