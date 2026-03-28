import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import io

# --- CONFIGURACIÓN VISUAL (CENTRADA Y PROPORCIONAL) ---
st.set_page_config(
    page_title="Gestión Negocio Pro", 
    layout="centered",  # <--- Esto centra el contenido para que no se vea estirado
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} 
    footer {visibility: hidden;} 
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    
    /* Ajuste de margen superior para mejor estética */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Esto permite que el botón del sidebar siga siendo clickable */
    section[data-testid="stSidebar"] {
        top: 0;
    }
    </style>
    """, unsafe_allow_html=True)

# ⚠️ REEMPLAZA CON TU URL SI ES DIFERENTE
SHEET_ID = "1UGxbXTQhXKJ-JmKxpzglccDJrZgpCsTDflKO9N8RMTc"
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbwefjYpHKmQNY6BY9-DXWAxk2GNN6VVeiVDxzr0xV-3Z7Ab9QLwkLulFK5d60rqQCVSSA/exec"

# --- 1. FUNCIÓN DE ENVÍO ---
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

# --- 2. FUNCIÓN DE LECTURA BLINDADA ---
def leer_datos(pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={pestana}&t={datetime.now().microsecond}"
        res = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(res.text), dtype=str)
        df = df.fillna('')
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            
        if df.empty:
            return pd.DataFrame(columns=['nombre', 'clave', 'rol']) if pestana == "usuarios" else pd.DataFrame()
            
        if pestana == "usuarios":
            df.columns = ['nombre', 'clave', 'rol'] + list(df.columns[3:])
        elif pestana == "ventas":
            cols_v = ['fecha', 'n_orden', 'descripcion', 'total', 'abono', 'saldo', 'metodo_pago', 'estado', 'empleado', 'cliente', 'nit', 'celular', 'correo', 'factura', 'historial_pagos']
            df = df.iloc[:, :len(cols_v)]
            df.columns = cols_v
            
        return df
    except Exception as e:
        st.error(f"Error leyendo {pestana}: {e}")
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

# --- MENÚ Y PERFIL EN BARRA LATERAL ---
with st.sidebar:
    # Identificación del usuario actual
    st.markdown(f"### 👤 {st.session_state['usuario'].upper()}")
    st.info(f"Rol: {st.session_state['rol'].capitalize()}")
    st.divider()
    
    menu = ["Ventas", "Gestión de Empleados"] if st.session_state['rol'] == 'admin' else ["Ventas"]
    opcion = st.radio("Menú Principal:", menu)
    
    st.markdown("<br>"*10, unsafe_allow_html=True)
    
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state['autenticado'] = False
        st.rerun()

# --- SECCIÓN: EMPLEADOS ---
if opcion == "Gestión de Empleados":
    st.title("👥 Gestión de Personal")
    t1, t2 = st.tabs(["➕ Nuevo Empleado", "⚙️ Modificar / Eliminar"])
    
    with t1:
        st.subheader("Registrar nuevo acceso")
        n_nom = st.text_input("Nombre Completo", key="n_nombre_reg")
        n_cla = st.text_input("Contraseña", key="n_clave_reg")
        n_rol = st.selectbox("Rol", ["empleado", "admin"], key="n_rol_reg")
        
        if st.button("Registrar en el Sistema", use_container_width=True):
            if n_nom and n_cla:
                payload = {"accion": "insertar", "tipo_registro": "usuarios", "nombre": n_nom, "clave": n_cla, "rol": n_rol}
                if enviar_google(payload): 
                    st.success("Registrado correctamente"); st.rerun()
            else: st.warning("Completa nombre y clave.")
            
    with t2:
        st.subheader("Control de Usuarios Activos")
        df_u = leer_datos("usuarios")
        if not df_u.empty:
            u_sel = st.selectbox("Seleccione Usuario", df_u['nombre'].tolist(), key="u_selector_edit")
            u_data = df_u[df_u['nombre'] == u_sel].iloc[0]
            e_cla = st.text_input("Cambiar Contraseña", value=str(u_data['clave']), key="e_clave_edit")
            e_rol = st.selectbox("Cambiar Rol", ["empleado", "admin"], 
                                 index=0 if str(u_data['rol']).lower() == "empleado" else 1,
                                 key="e_rol_edit")
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("💾 Guardar Cambios", use_container_width=True):
                    if enviar_google({"accion": "actualizar", "tipo_registro": "usuarios", "id_busqueda": u_sel, "clave": e_cla, "rol": e_rol}):
                        st.success("Actualizado"); st.rerun()
            with c2:
                if u_sel != "Administrador":
                    if st.button("🗑️ ELIMINAR ACCESO", use_container_width=True):
                        if enviar_google({"accion": "eliminar", "tipo_registro": "usuarios", "id_busqueda": u_sel}):
                            st.warning("Acceso eliminado"); st.rerun()
                else:
                    st.info("El Administrador principal no se puede eliminar.")

# --- SECCIÓN: VENTAS ---
elif opcion == "Ventas":
    st.title("🚀 Gestión de Ventas")
    df_v = leer_datos("ventas")
    
    if st.session_state['rol'] == 'admin':
        tab_reg, tab_edit, tab_rep = st.tabs(["📝 Registrar", "✏️ Editar / Abonar", "📊 Reportes Avanzados"])
    else:
        tab_reg, tab_edit = st.tabs(["📝 Registrar", "✏️ Editar / Abonar"])

    with tab_reg:
        if 'limp_v' not in st.session_state: st.session_state['limp_v'] = 0
        vs = str(st.session_state['limp_v'])
        c1, c2 = st.columns(2) # Usamos 2 columnas para que sea más proporcional en modo centrado
        with c1:
            v_ord = st.text_input("N° Orden", key="o"+vs)
            v_cli = st.text_input("Cliente", key="cl"+vs)
            v_nit = st.text_input("NIT/CC", key="nit"+vs)
            v_cel = st.text_input("Celular", key="cel"+vs)
        with c2:
            v_tot = st.number_input("Total ($)", key="t"+vs, min_value=0.0, step=1.0)
            v_abo = st.number_input("Abono Inicial ($)", key="a"+vs, min_value=0.0, step=1.0)
            v_est = st.selectbox("Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], key="e"+vs)
            v_pag = st.selectbox("Medio Pago Inicial", ["EFECTIVO", "NEQUI", "DAVIPLATA", "BANCOLOMBIA"], key="p"+vs)
        
        v_desc = st.text_area("Descripción", key="d"+vs)
        v_fac = st.radio("Factura", ["SÍ", "NO"], key="f"+vs, horizontal=True)
        
        if st.button("💾 GUARDAR VENTA", use_container_width=True):
            if v_ord and v_cli:
                h_ini = f"${v_abo:,.0f} ({v_pag}) el {datetime.now().strftime('%Y-%m-%d')}"
                payload = {"accion": "insertar", "tipo_registro": "ventas", "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "n_orden": v_ord, "descripcion": v_desc, "total": v_tot, "abono": v_abo, "saldo": v_tot-v_abo, "metodo_pago": v_pag, "estado": v_est, "empleado": st.session_state['usuario'], "cliente": v_cli, "nit": v_nit, "celular": v_cel, "correo": "", "factura": v_fac, "historial_pagos": h_ini}
                if enviar_google(payload): 
                    st.session_state['limp_v'] += 1; st.success("¡Venta guardada!"); st.rerun()
            else: st.error("Faltan datos (N° Orden o Cliente)")

    with tab_edit:
        if not df_v.empty:
            if st.session_state['rol'] == 'admin':
                opciones_o = df_v['n_orden'].unique().tolist()
            else:
                user_actual = str(st.session_state['usuario']).strip().lower()
                opciones_o = df_v[df_v['empleado'].str.strip().str.lower() == user_actual]['n_orden'].unique().tolist()
            
            ord_s = st.selectbox("Seleccione Orden:", ["Seleccionar..."] + opciones_o, key="sel_edit_v")
            
            if ord_s != "Seleccionar...":
                d = df_v[df_v['n_orden'] == str(ord_s)].iloc[0]
                st.subheader(f"🛠️ Editando Orden N° {ord_s}")
                
                ce1, ce2 = st.columns(2)
                with ce1:
                    e_cli = st.text_input("Nombre Cliente", value=str(d['cliente']), key="ev_cli")
                    e_nit = st.text_input("NIT / CC", value=str(d['nit']), key="ev_nit")
                    e_cel = st.text_input("Celular", value=str(d['celular']), key="ev_cel")
                with ce2:
                    e_total = st.number_input("Valor Total ($)", value=float(pd.to_numeric(d['total'], errors='coerce') or 0.0), key="ev_tot")
                    v_abono_prev = float(pd.to_numeric(d['abono'], errors='coerce') or 0.0)
                    st.info(f"Abonado hasta hoy: ${v_abono_prev:,.0f}")
                    nuevo_pago = st.number_input("Nuevo abono ahora ($)", min_value=0.0, key="ev_nue")
                    medio_pago = st.selectbox("Medio de este abono", ["EFECTIVO", "NEQUI", "DAVIPLATA", "BANCOLOMBIA"], key="ev_med")
                
                e_desc = st.text_area("Descripción Trabajo", value=str(d['descripcion']), key="ev_desc")
                e_est = st.selectbox("Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], index=["EN PROCESO", "TERMINADO", "PAGADO"].index(d['estado']), key="ev_est")
                e_fac = st.radio("Factura", ["SÍ", "NO"], index=0 if str(d['factura']) == "SÍ" else 1, horizontal=True, key="ev_fac")

                if st.button("💾 GUARDAR TODOS LOS CAMBIOS", use_container_width=True, key="btn_save_edit"):
                    abono_f = v_abono_prev + nuevo_pago
                    hist_f = str(d['historial_pagos']) if str(d['historial_pagos']) != "nan" else ""
                    if nuevo_pago > 0:
                        hist_f = (hist_f + " || " if hist_f else "") + f"${nuevo_pago:,.0f} ({medio_pago}) el {datetime.now().strftime('%Y-%m-%d')}"
                    payload = {"accion": "actualizar", "tipo_registro": "ventas", "id_busqueda": ord_s, "cliente": e_cli, "nit": e_nit, "celular": e_cel, "factura": e_fac, "descripcion": e_desc, "total": e_total, "abono": abono_f, "saldo": e_total-abono_f, "estado": e_est, "historial_pagos": hist_f}
                    if enviar_google(payload): st.success("¡Cambios guardados!"); st.rerun()

                if st.session_state['rol'] == 'admin':
                    with st.expander("🚨 ZONA DE PELIGRO"):
                        if st.button("🗑️ ELIMINAR ORDEN DEFINITIVAMENTE", use_container_width=True, type="primary"):
                            if enviar_google({"accion": "eliminar", "tipo_registro": "ventas", "id_busqueda": str(ord_s)}):
                                st.success("Orden eliminada"); st.rerun()

    if st.session_state['rol'] == 'admin' and 'tab_rep' in locals():
        with tab_rep:
            if not df_v.empty:
                st.subheader("📊 Resumen de Ventas")
                df_v['fecha_dt'] = pd.to_datetime(df_v['fecha'], errors='coerce')
                vt = pd.to_numeric(df_v['total'], errors='coerce').sum()
                at = pd.to_numeric(df_v['abono'], errors='coerce').sum()
                c_m1, c_m2 = st.columns(2)
                c_m1.metric("💰 Ventas Totales", f"$ {vt:,.0f}")
                c_m2.metric("📥 Total Cobrado", f"$ {at:,.0f}")
                st.dataframe(df_v.drop(columns=['fecha_dt']), use_container_width=True, hide_index=True)

    # --- HISTORIAL (TABLA) ---
    st.divider()
    st.subheader("📋 Historial de Órdenes")
    df_m = df_v.copy()
    if st.session_state['rol'] != 'admin':
        user_actual = str(st.session_state['usuario']).strip().lower()
        df_m = df_m[df_m['empleado'].str.lower() == user_actual]
    
    st.dataframe(df_m.iloc[::-1], use_container_width=True, hide_index=True)

# --- GESTIÓN EMPLEADOS ---
elif opcion == "Gestión de Empleados":
    # (Ya está manejado arriba en el bloque de 'admin', pero por seguridad lo dejamos)
    pass
