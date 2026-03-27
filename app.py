import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Gestión Litografía Pro", layout="wide")

# Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos(pestana):
    return conn.read(worksheet=pestana, ttl="0s")

# --- LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

df_usuarios = cargar_datos("usuarios")

if not st.session_state['autenticado']:
    st.title("🔐 Acceso al Sistema")
    u_log = st.selectbox("Usuario", df_usuarios['nombre'].tolist())
    p_log = st.text_input("Contraseña", type="password")
    if st.button("INGRESAR", use_container_width=True):
        user_row = df_usuarios[df_usuarios['nombre'] == u_log].iloc[0]
        if str(user_row['clave']) == p_log:
            st.session_state.update({"autenticado": True, "usuario": u_log, "rol": user_row['rol']})
            st.rerun()
        else: st.error("Contraseña incorrecta")
    st.stop()

# --- MENÚ LATERAL ---
st.sidebar.title(f"👤 {st.session_state['usuario']}")
menu = ["Ventas", "Gestión de Empleados"] if st.session_state['rol'] == 'admin' else ["Ventas"]
opcion = st.sidebar.radio("Ir a:", menu)

if st.sidebar.button("Cerrar Sesión"):
    st.session_state['autenticado'] = False
    st.rerun()

# --- SECCIÓN: VENTAS ---
if opcion == "Ventas":
    st.title("🚀 Gestión de Ventas")
    tab_reg, tab_edit = st.tabs(["📝 Registrar Nueva", "✏️ Editar Orden"])

    with tab_reg:
        with st.form("nueva_venta", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                n_ord = st.text_input("N° Orden")
                v_cli = st.text_input("Cliente")
                v_nit = st.text_input("NIT / CC")
            with c2:
                v_cel = st.text_input("Celular")
                v_cor = st.text_input("Correo")
                v_fac = st.radio("Factura", ["SÍ", "NO"], horizontal=True)
            with c3:
                v_tot = st.number_input("Total ($)", min_value=0.0)
                v_abo = st.number_input("Abono ($)", min_value=0.0)
                v_est = st.selectbox("Estado", ["EN PROCESO", "TERMINADO", "PAGADO"])
                v_pag = st.selectbox("Medio de Pago", ["EFECTIVO", "NEQUI", "DAVIPLATA", "BANCOLOMBIA"])
            
            v_desc = st.text_area("Descripción")
            
            if st.form_submit_button("💾 GUARDAR ORDEN", use_container_width=True):
                nueva_fila = pd.DataFrame([{
                    "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "n_orden": str(n_ord), "descripcion": v_desc, "total": v_tot,
                    "abono": v_abo, "saldo": v_tot - v_abo, "metodo_pago": v_pag,
                    "estado": v_est, "empleado": st.session_state['usuario'],
                    "cliente": v_cli, "nit": v_nit, "celular": v_cel,
                    "correo": v_cor, "factura": v_fac
                }])
                df_v = cargar_datos("ventas")
                df_final = pd.concat([df_v, nueva_fila], ignore_index=True)
                conn.update(worksheet="ventas", data=df_final)
                st.success("✅ Guardado en Google Sheets")
                st.rerun()

    with tab_edit:
        st.subheader("Actualizar Orden Existente")
        df_edit = cargar_datos("ventas")
        if not df_edit.empty:
            ord_sel = st.selectbox("Seleccione N° de Orden:", ["Seleccionar..."] + df_edit['n_orden'].unique().tolist())
            if ord_sel != "Seleccionar...":
                idx = df_edit[df_edit['n_orden'] == ord_sel].index[0]
                d = df_edit.loc[idx]
                
                new_abo = st.number_input("Nuevo Abono ($)", value=float(d['abono']))
                new_est = st.selectbox("Nuevo Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], 
                                       index=["EN PROCESO", "TERMINADO", "PAGADO"].index(d['estado']))
                
                if st.button("🔄 Actualizar en Nube"):
                    df_edit.at[idx, 'abono'] = new_abo
                    df_edit.at[idx, 'saldo'] = d['total'] - new_abo
                    df_edit.at[idx, 'estado'] = new_est
                    conn.update(worksheet="ventas", data=df_edit)
                    st.success("Orden actualizada correctamente")
                    st.rerun()

    st.divider()
    search = st.text_input("🔍 Buscar por Orden, Cliente o NIT")
    df_ver = cargar_datos("ventas")
    if not df_ver.empty:
        if st.session_state['rol'] != 'admin':
            df_ver = df_ver[df_ver['empleado'] == st.session_state['usuario']]
        if search:
            df_ver = df_ver[df_ver['n_orden'].astype(str).str.contains(search, case=False) | 
                            df_ver['cliente'].str.contains(search, case=False) | 
                            df_ver['nit'].str.contains(search, case=False)]
        st.dataframe(df_ver, use_container_width=True, hide_index=True)

# --- SECCIÓN: EMPLEADOS ---
elif opcion == "Gestión de Empleados":
    st.title("👥 Administración de Personal")
    t1, t2 = st.tabs(["➕ Nuevo Empleado", "⚙️ Modificar / Eliminar"])
    
    with t1:
        n_nom = st.text_input("Nombre Completo")
        n_cla = st.text_input("Contraseña")
        n_rol = st.selectbox("Rol", ["empleado", "admin"])
        if st.button("Registrar Empleado"):
            df_u = cargar_datos("usuarios")
            if n_nom not in df_u['nombre'].tolist():
                nuevo_u = pd.DataFrame([{"nombre": n_nom, "clave": n_cla, "rol": n_rol}])
                df_u_final = pd.concat([df_u, nuevo_u], ignore_index=True)
                conn.update(worksheet="usuarios", data=df_u_final)
                st.success(f"Usuario {n_nom} creado"); st.rerun()
            else: st.error("El usuario ya existe")

    with t2:
        df_u_edit = cargar_datos("usuarios")
        u_sel = st.selectbox("Usuario a gestionar", df_u_edit['nombre'].tolist())
        u_idx = df_u_edit[df_u_edit['nombre'] == u_sel].index[0]
        u_data = df_u_edit.loc[u_idx]
        
        e_cla = st.text_input("Nueva Contraseña", value=str(u_data['clave']))
        e_rol = st.selectbox("Nuevo Rol", ["empleado", "admin"], index=0 if u_data['rol'] == "empleado" else 1)
        
        c_b1, c_b2 = st.columns(2)
        if c_b1.button("💾 Guardar Cambios"):
            df_u_edit.at[u_idx, 'clave'] = e_cla
            df_u_edit.at[u_idx, 'rol'] = e_rol
            conn.update(worksheet="usuarios", data=df_u_edit)
            st.success("Cambios guardados"); st.rerun()
        if c_b2.button("🗑️ Eliminar"):
            if u_sel != "Administrador":
                df_u_edit = df_u_edit.drop(u_idx)
                conn.update(worksheet="usuarios", data=df_u_edit)
                st.warning("Usuario eliminado"); st.rerun()
            else: st.error("No puedes eliminar al Admin")
