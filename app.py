import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import io

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(page_title="Gestión Negocio Pro", layout="centered", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stDeployButton {display:none;}
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    button[kind="headerNoPadding"] { visibility: visible !important; z-index: 9999991; background-color: rgba(255,255,255,0.1); border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

SHEET_ID = "1UGxbXTQhXKJ-JmKxpzglccDJrZgpCsTDflKO9N8RMTc"
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbwefjYpHKmQNY6BY9-DXWAxk2GNN6VVeiVDxzr0xV-3Z7Ab9QLwkLulFK5d60rqQCVSSA/exec"

# --- 2. FUNCIONES DE LIMPIEZA ---
def a_numero(valor):
    """Convierte texto sucio del Excel a número limpio."""
    try:
        if not valor or str(valor).strip() == "": return 0.0
        # Quita puntos de miles y cambia coma por punto decimal si existe
        s = str(valor).replace('$', '').replace(' ', '').replace('.', '')
        s = s.replace(',', '.')
        return float(s)
    except: return 0.0

def leer_datos(pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={pestana}&t={datetime.now().microsecond}"
        res = requests.get(url, timeout=10)
        if res.status_code != 200: return pd.DataFrame()
        
        df = pd.read_csv(io.StringIO(res.text), dtype=str).fillna('')
        
        if pestana == "usuarios":
            df.columns = ['nombre', 'clave', 'rol'] + list(df.columns[3:])
        elif pestana == "ventas":
            columnas_esperadas = ['fecha', 'n_orden', 'descripcion', 'total', 'abono', 'saldo', 'metodo_pago', 'estado', 'empleado', 'cliente', 'nit', 'celular', 'correo', 'factura', 'historial_pagos']
            df = df.iloc[:, :len(columnas_esperadas)]
            df.columns = columnas_esperadas
            # Crear columnas numéricas seguras
            df['total_n'] = df['total'].apply(a_numero)
            df['abono_n'] = df['abono'].apply(a_numero)
            df['saldo_n'] = df['total_n'] - df['abono_n']
        return df
    except Exception as e:
        st.error(f"Error cargando {pestana}: {e}")
        return pd.DataFrame()

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
    with st.form("login_form"):
        u_list = df_users_db['nombre'].unique().tolist() if not df_users_db.empty else ["Administrador"]
        u_input = st.selectbox("Usuario", [u for u in u_list if u != ""])
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
        with st.form("form_registro"):
            c1, c2, c3 = st.columns(3)
            v_ord = c1.text_input("N° Orden", key="o"+vs)
            v_cli = c2.text_input("Cliente", key="cl"+vs)
            v_nit = c3.text_input("NIT / CC", key="ni"+vs)
            v_tot = st.number_input("Total ($)", min_value=0.0, step=100.0)
            v_abo = st.number_input("Abono Inicial ($)", min_value=0.0, step=100.0)
            v_desc = st.text_area("Descripción")
            if st.form_submit_button("💾 GUARDAR VENTA", use_container_width=True):
                if v_ord and v_cli:
                    payload = {"accion": "insertar", "tipo_registro": "ventas", "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "n_orden": v_ord, "descripcion": v_desc, "total": v_tot, "abono": v_abo, "saldo": v_tot-v_abo, "empleado": st.session_state['usuario'], "cliente": v_cli, "estado": "EN PROCESO"}
                    if enviar_google(payload): 
                        st.session_state['limp_v'] += 1
                        st.success("¡Venta guardada!"); st.rerun()

    with tabs[1]: # EDITAR
        if not df_v.empty:
            ord_s = st.selectbox("Seleccione Orden:", ["Seleccionar..."] + df_v['n_orden'].tolist())
            if ord_s != "Seleccionar...":
                d = df_v[df_v['n_orden'] == ord_s].iloc[0]
                n_abo = st.number_input(f"Nuevo abono (Ya tiene ${d.get('abono_n', 0):,.0f})", min_value=0.0)
                e_est = st.selectbox("Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], index=0)
                if st.button("💾 ACTUALIZAR"):
                    total_actual = d.get('total_n', 0)
                    abono_nuevo = d.get('abono_n', 0) + n_abo
                    payload = {"accion": "actualizar", "tipo_registro": "ventas", "id_busqueda": ord_s, "abono": abono_nuevo, "saldo": total_actual - abono_nuevo, "estado": e_est}
                    if enviar_google(payload): st.success("¡Listo!"); st.rerun()

    if st.session_state['rol'] == 'admin' and not df_v.empty:
        with tabs[2]: # REPORTES
            st.subheader("📊 Análisis de Cartera")
            col_e, col_p = st.columns(2)
            sel_emp = col_e.selectbox("👤 Empleado:", ["Todos"] + df_v['empleado'].unique().tolist())
            tipo_pago = col_p.radio("💰 Filtro:", ["Todas", "Solo Pendientes", "Solo Pagadas"], horizontal=True)
            
            df_r = df_v.copy()
            if 'saldo_n' in df_r.columns:
                if tipo_pago == "Solo Pendientes": df_r = df_r[df_r['saldo_n'] > 10]
                elif tipo_pago == "Solo Pagadas": df_r = df_r[df_r['saldo_n'] <= 10]
            
            if sel_emp != "Todos": df_r = df_r[df_r['empleado'] == sel_emp]
            
            if not df_r.empty and 'total_n' in df_r.columns:
                m1, m2, m3 = st.columns(3)
                m1.metric("Ventas Totales", f"$ {df_r['total_n'].sum():,.0f}")
                m2.metric("Total Cobrado", f"$ {df_r['abono_n'].sum():,.0f}")
                m3.metric("Por Cobrar", f"$ {df_r['saldo_n'].sum():,.0f}")
                st.dataframe(df_r.drop(columns=['total_n', 'abono_n', 'saldo_n'], errors='ignore'), use_container_width=True, hide_index=True)
            else:
                st.warning("No hay datos para mostrar con estos filtros.")

    # --- HISTORIAL ---
    st.divider()
    st.subheader("📋 Historial")
    busqueda = st.text_input("🔍 Buscar:")
    df_h = df_v.copy()
    if busqueda and not df_h.empty:
        df_h = df_h[df_h.apply(lambda row: busqueda.lower() in row.astype(str).str.lower().values, axis=1)]
    if not df_h.empty:
        st.dataframe(df_h.drop(columns=['total_n', 'abono_n', 'saldo_n'], errors='ignore').iloc[::-1], use_container_width=True, hide_index=True)



# ... (Mismo código de gestión de empleados)
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
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("ACTUALIZAR DATOS"):
                        if enviar_google({"accion": "actualizar", "tipo_registro": "usuarios", "id_busqueda": u_sel, "clave": e_cla, "rol": e_rol}):
                            st.success("Datos actualizados"); st.rerun()
                with col2:
                    if u_sel != st.session_state['usuario'] and st.form_submit_button("⚠️ ELIMINAR ACCESO"):
                        if enviar_google({"accion": "eliminar", "tipo_registro": "usuarios", "id_busqueda": u_sel}):
                            st.warning("Usuario eliminado"); st.rerun()
