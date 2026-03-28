import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import io

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Gestión Negocio Pro", layout="wide")
st.markdown("""<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;} .stDeployButton {display:none;}</style>""", unsafe_allow_html=True)

# ⚠️ REEMPLAZA CON TU URL SI ES DIFERENTE
SHEET_ID = "1UGxbXTQhXKJ-JmKxpzglccDJrZgpCsTDflKO9N8RMTc"
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbwefjYpHKmQNY6BY9-DXWAxk2GNN6VVeiVDxzr0xV-3Z7Ab9QLwkLulFK5d60rqQCVSSA/exec"

# --- 1. FUNCIÓN DE ENVÍO (LA QUE FALTABA) ---
def enviar_google(payload):
    try:
        res = requests.post(URL_SCRIPT, json=payload, timeout=15)
        if res.status_code == 200:
            return True
        else:
            st.error(f"Error del servidor: {res.status_code}")
            return False
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return False

# --- 2. FUNCIÓN DE LECTURA (CORRIGE EL 'nan') ---
def leer_datos(pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={pestana}&t={datetime.now().microsecond}"
        res = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(res.text))
        
        # EL TRUCO PARA EL CELULAR: Convertir todo a texto y quitar el 'nan'
        df = df.astype(str).replace('nan', '') 
        
        if df.empty:
            return pd.DataFrame(columns=['nombre', 'clave', 'rol']) if pestana == "usuarios" else pd.DataFrame()
            
        if pestana == "usuarios":
            cols = ['nombre', 'clave', 'rol']
            df.columns = cols + list(df.columns[len(cols):])
        elif pestana == "ventas":
            cols_v = ['fecha', 'n_orden', 'descripcion', 'total', 'abono', 'saldo', 'metodo_pago', 'estado', 'empleado', 'cliente', 'nit', 'celular', 'correo', 'factura', 'historial_pagos']
            df.columns = cols_v + list(df.columns[len(cols_v):])
            
        return df.apply(lambda x: x.str.strip())
    except Exception as e:
        return pd.DataFrame()

# --- LOGIN Y SESIÓN ---
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

# --- MENÚ ---
menu = ["Ventas", "Gestión de Empleados"] if st.session_state['rol'] == 'admin' else ["Ventas"]
opcion = st.sidebar.radio("Ir a:", menu)
if st.sidebar.button("Cerrar Sesión"):
    st.session_state['autenticado'] = False
    st.rerun()

# --- SECCIÓN: EMPLEADOS ---
if opcion == "Gestión de Empleados":
    st.title("👥 Gestión de Personal")
    t1, t2 = st.tabs(["➕ Nuevo", "⚙️ Editar/Eliminar"])
    with t1:
        n_nom = st.text_input("Nombre")
        n_cla = st.text_input("Clave")
        n_rol = st.selectbox("Rol", ["empleado", "admin"])
        if st.button("Registrar"):
            if enviar_google({"accion": "insertar", "tipo_registro": "usuarios", "nombre": n_nom, "clave": n_cla, "rol": n_rol}):
                st.success("Registrado"); st.rerun()
    with t2:
        df_u = leer_datos("usuarios")
        if not df_u.empty:
            u_sel = st.selectbox("Seleccione Usuario", df_u['nombre'].tolist())
            u_data = df_u[df_u['nombre'] == u_sel].iloc[0]
            e_cla = st.text_input("Clave", value=u_data['clave'])
            e_rol = st.selectbox("Rol", ["empleado", "admin"], index=0 if u_data['rol'] == "empleado" else 1)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("💾 Guardar"):
                    if enviar_google({"accion": "actualizar", "tipo_registro": "usuarios", "id_busqueda": u_sel, "clave": e_cla, "rol": e_rol}):
                        st.success("Actualizado"); st.rerun()
            with c2:
                if u_sel != "Administrador" and st.button("🗑️ Eliminar"):
                    if enviar_google({"accion": "eliminar", "tipo_registro": "usuarios", "id_busqueda": u_sel}):
                        st.warning("Eliminado"); st.rerun()

elif opcion == "Ventas":
    st.title("🚀 Gestión de Ventas")
    df_v = leer_datos("ventas")
    
    # Definición de pestañas según el rol para evitar el NameError
    if st.session_state['rol'] == 'admin':
        tab_reg, tab_edit, tab_rep = st.tabs(["📝 Registrar", "✏️ Editar / Abonar", "📊 Reportes Avanzados"])
    else:
        tab_reg, tab_edit = st.tabs(["📝 Registrar", "✏️ Editar / Abonar"])

    # --- 1. PESTAÑA REGISTRAR ---
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
            v_tot = st.number_input("Total ($)", key="t"+vs, min_value=0.0, step=1.0)
            v_abo = st.number_input("Abono Inicial ($)", key="a"+vs, min_value=0.0, step=1.0)
            v_est = st.selectbox("Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], key="e"+vs)
            v_pag = st.selectbox("Medio Pago Inicial", ["EFECTIVO", "NEQUI", "DAVIPLATA", "BANCOLOMBIA"], key="p"+vs)
        
        if st.button("💾 GUARDAR VENTA", use_container_width=True):
            if v_ord and v_cli:
                h_ini = f"${v_abo:,.0f} ({v_pag}) el {datetime.now().strftime('%Y-%m-%d')}"
                payload = {"accion": "insertar", "tipo_registro": "ventas", "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "n_orden": v_ord, "descripcion": v_desc, "total": v_tot, "abono": v_abo, "saldo": v_tot-v_abo, "metodo_pago": v_pag, "estado": v_est, "empleado": st.session_state['usuario'], "cliente": v_cli, "nit": v_nit, "celular": v_cel, "correo": "", "factura": v_fac, "historial_pagos": h_ini}
                if enviar_google(payload): 
                    st.session_state['limp_v'] += 1; st.success("¡Venta guardada!"); st.rerun()
            else: st.error("Faltan datos (N° Orden o Cliente)")

    # --- 2. PESTAÑA EDITAR ---
    with tab_edit:
        if not df_v.empty:
            opciones_o = df_v['n_orden'].unique().tolist() if st.session_state['rol'] == 'admin' else df_v[df_v['empleado'] == st.session_state['usuario']]['n_orden'].unique().tolist()
            ord_s = st.selectbox("Seleccione Orden:", ["Seleccionar..."] + opciones_o)
            
            if ord_s != "Seleccionar...":
                d = df_v[df_v['n_orden'] == str(ord_s)].iloc[0]
                st.subheader(f"🛠️ Editando Orden N° {ord_s}")
                ce1, ce2, ce3 = st.columns(3)
                with ce1:
                    e_cli = st.text_input("Nombre Cliente", value=str(d['cliente']))
                    e_nit = st.text_input("NIT / CC", value=str(d['nit']))
                with ce2:
                    e_cel = st.text_input("Celular", value=str(d['celular']))
                    e_fac = st.radio("Factura", ["SÍ", "NO"], index=0 if str(d['factura']) == "SÍ" else 1, horizontal=True)
                with ce3:
                    e_desc = st.text_area("Descripción Trabajo", value=str(d['descripcion']))

                st.divider()
                ce4, ce5, ce6 = st.columns(3)
                with ce4:
                    e_total = st.number_input("Valor Total ($)", value=float(pd.to_numeric(d['total'], errors='coerce') or 0.0))
                    v_abono_prev = float(pd.to_numeric(d['abono'], errors='coerce') or 0.0)
                    st.info(f"Abonado: ${v_abono_prev:,.0f}")
                with ce5:
                    nuevo_pago = st.number_input("Nuevo abono ($)", min_value=0.0)
                    medio_pago = st.selectbox("Medio de pago", ["EFECTIVO", "NEQUI", "DAVIPLATA", "BANCOLOMBIA"])
                with ce6:
                    e_est = st.selectbox("Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], index=["EN PROCESO", "TERMINADO", "PAGADO"].index(d['estado']))
                    st.warning(f"Saldo: ${(e_total - (v_abono_prev + nuevo_pago)):,.0f}")

                if st.button("💾 GUARDAR CAMBIOS", use_container_width=True):
                    abono_f = v_abono_prev + nuevo_pago
                    hist_f = str(d['historial_pagos']) if str(d['historial_pagos']) != "nan" else ""
                    if nuevo_pago > 0:
                        hist_f = (hist_f + " || " if hist_f else "") + f"${nuevo_pago:,.0f} ({medio_pago}) el {datetime.now().strftime('%Y-%m-%d')}"
                    payload = {"accion": "actualizar", "tipo_registro": "ventas", "id_busqueda": ord_s, "cliente": e_cli, "nit": e_nit, "celular": e_cel, "factura": e_fac, "descripcion": e_desc, "total": e_total, "abono": abono_f, "saldo": e_total-abono_f, "estado": e_est, "historial_pagos": hist_f}
                    if enviar_google(payload): st.success("¡Listo!"); st.rerun()

                if st.session_state['rol'] == 'admin':
                    with st.expander("🗑️ ELIMINAR ORDEN"):
                        if st.checkbox("Confirmar eliminación definitiva"):
                            if st.button("ELIMINAR AHORA"):
                                if enviar_google({"accion": "eliminar", "tipo_registro": "ventas", "id_busqueda": str(ord_s)}):
                                    st.warning("Borrado"); st.rerun()

    # --- 3. PESTAÑA REPORTES (SOLO ADMIN) ---
    if st.session_state['rol'] == 'admin':
        with tab_rep:
            if not df_v.empty:
                st.subheader("🔍 Filtros de Inteligencia de Negocio")
                df_v['fecha_dt'] = pd.to_datetime(df_v['fecha'], errors='coerce')
                
                f1, f2, f3 = st.columns(3)
                with f1:
                    sel_emp = st.selectbox("Empleado:", ["Todos"] + df_v['empleado'].unique().tolist())
                with f2:
                    modo_t = st.radio("Temporalidad:", ["Todo", "Día / Semana", "Mes / Año"], horizontal=True)
                with f3:
                    df_rep = df_v.copy()
                    if modo_t == "Día / Semana":
                        rango = st.date_input("Rango:", value=[datetime.now(), datetime.now()])
                        if len(rango) == 2:
                            df_rep = df_rep[(df_rep['fecha_dt'].dt.date >= rango[0]) & (df_rep['fecha_dt'].dt.date <= rango[1])]
                    elif modo_t == "Mes / Año":
                        m_sel = st.selectbox("Mes:", range(1, 13), index=datetime.now().month-1, format_func=lambda x: ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"][x-1])
                        a_sel = st.selectbox("Año:", sorted(df_v['fecha_dt'].dt.year.unique(), reverse=True))
                        df_rep = df_rep[(df_rep['fecha_dt'].dt.month == m_sel) & (df_rep['fecha_dt'].dt.year == a_sel)]

                if sel_emp != "Todos": df_rep = df_rep[df_rep['empleado'] == sel_emp]

                st.divider()
                vt = pd.to_numeric(df_rep['total'], errors='coerce').sum()
                at = pd.to_numeric(df_rep['abono'], errors='coerce').sum()
                c_m1, c_m2, c_m3 = st.columns(3)
                c_m1.metric("💰 Ventas", f"$ {vt:,.0f}")
                c_m2.metric("📥 Cobrado", f"$ {at:,.0f}")
                c_m3.metric("⏳ Pendiente", f"$ {vt-at:,.0f}")

                st.dataframe(df_rep.drop(columns=['fecha_dt']), use_container_width=True, hide_index=True)
                html = df_rep.drop(columns=['fecha_dt']).to_html(index=False)
                st.download_button("🟢 Descargar Excel Filtrado", f'<html><meta charset="utf-8"><body>{html}</body></html>', f"Reporte_{sel_emp}.xls", "application/vnd.ms-excel")
            else: st.info("Sin datos.")

    # --- TABLA ÚNICA INFERIOR ---
    st.divider()
    busq = st.text_input("🔍 Buscar en historial general...")
    df_m = df_v.copy().iloc[::-1]
    if st.session_state['rol'] != 'admin': df_m = df_m[df_m['empleado'] == st.session_state['usuario']]
    if busq: df_m = df_m[df_m.apply(lambda r: r.astype(str).str.contains(busq, case=False).any(), axis=1)]
    st.dataframe(df_m, use_container_width=True, hide_index=True)
