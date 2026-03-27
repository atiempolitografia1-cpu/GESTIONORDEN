import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Gestión Litografía Pro", layout="wide")

# Conexión a Google Sheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Error al inicializar la conexión. Revisa los Secrets.")
    st.stop()

def traer_datos(pestana):
    try:
        # Intentamos leer la pestaña con un tiempo de espera
        return conn.read(worksheet=pestana, ttl=0)
    except Exception as e:
        st.error(f"⚠️ Error al leer la pestaña '{pestana}'.")
        st.info("Esto sucede si el nombre de la pestaña en Excel no es EXACTAMENTE igual o si falta el permiso de Editor.")
        st.write(f"Detalle técnico: {e}") # Esto nos dirá el error real
        st.stop()

# --- CARGA INICIAL ---
df_usuarios = traer_datos("usuarios")

# --- LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.title("🔐 Acceso al Sistema")
    if df_usuarios.empty:
        st.warning("No hay usuarios en el Excel. Agrega uno en la pestaña 'usuarios'.")
    else:
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
menu_opciones = ["Ventas"]
if st.session_state['rol'] == 'admin':
    menu_opciones.append("Gestión de Empleados")

opcion = st.sidebar.radio("Ir a:", menu_opciones)

if st.sidebar.button("Cerrar Sesión"):
    st.session_state['autenticado'] = False
    st.rerun()

# --- SECCIÓN: VENTAS (ESTRUCTURA COMPLETA) ---
if opcion == "Ventas":
    st.title("🚀 Gestión de Ventas e Inventario")
    tab_reg, tab_edit = st.tabs(["📝 Registrar Nueva Orden", "✏️ Actualizar Estado/Abono"])

    with tab_reg:
        with st.form("nueva_venta", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                n_ord = st.text_input("N° Orden / Factura")
                v_cli = st.text_input("Nombre del Cliente")
                v_nit = st.text_input("NIT o Cédula")
            with c2:
                v_cel = st.text_input("Celular de Contacto")
                v_cor = st.text_input("Correo Electrónico")
                v_fac = st.radio("¿Requiere Factura?", ["SÍ", "NO"], horizontal=True)
            with c3:
                v_tot = st.number_input("Valor Total ($)", min_value=0.0)
                v_abo = st.number_input("Abono Inicial ($)", min_value=0.0)
                v_est = st.selectbox("Estado Inicial", ["EN PROCESO", "TERMINADO", "PAGADO"])
                v_pag = st.selectbox("Método de Pago", ["EFECTIVO", "NEQUI", "DAVIPLATA", "BANCOLOMBIA", "TRANSFERENCIA"])
            
            v_desc = st.text_area("Descripción detallada del trabajo (Cantidades, material, tamaño...)")
            
            if st.form_submit_button("💾 GUARDAR EN LA NUBE", use_container_width=True):
                nueva_fila = pd.DataFrame([{
                    "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "n_orden": str(n_ord), "descripcion": v_desc, "total": v_tot,
                    "abono": v_abo, "saldo": v_tot - v_abo, "metodo_pago": v_pag,
                    "estado": v_est, "empleado": st.session_state['usuario'],
                    "cliente": v_cli, "nit": v_nit, "celular": v_cel,
                    "correo": v_cor, "factura": v_fac
                }])
                df_v = traer_datos("ventas")
                df_final = pd.concat([df_v, nueva_fila], ignore_index=True)
                conn.update(worksheet="ventas", data=df_final)
                st.success("✅ Orden guardada exitosamente en Google Sheets")
                st.rerun()

    with tab_edit:
        st.subheader("Modificar Orden Existente")
        df_edit = traer_datos("ventas")
        if not df_edit.empty:
            # Buscador para no perderse entre tantas órdenes
            search_edit = st.text_input("Filtrar por N° Orden o Cliente")
            if search_edit:
                df_edit = df_edit[df_edit['n_orden'].str.contains(search_edit, case=False) | df_edit['cliente'].str.contains(search_edit, case=False)]
            
            lista_ordenes = df_edit['n_orden'].tolist()
            if lista_ordenes:
                ord_sel = st.selectbox("Seleccione la Orden a actualizar:", lista_ordenes)
                idx = df_edit[df_edit['n_orden'] == ord_sel].index[0]
                d = df_edit.loc[idx]
                
                c_e1, c_e2 = st.columns(2)
                new_abo = c_e1.number_input("Actualizar Abono ($)", value=float(d['abono']))
                new_est = c_e2.selectbox("Cambiar Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], 
                                       index=["EN PROCESO", "TERMINADO", "PAGADO"].index(d['estado']))
                
                if st.button("🔄 ACTUALIZAR CAMBIOS", use_container_width=True):
                    # Actualizamos la tabla completa y la volvemos a subir
                    df_full = traer_datos("ventas")
                    df_full.at[idx, 'abono'] = new_abo
                    df_full.at[idx, 'saldo'] = d['total'] - new_abo
                    df_full.at[idx, 'estado'] = new_est
                    conn.update(worksheet="ventas", data=df_full)
                    st.success("Orden actualizada correctamente"); st.rerun()
            else: st.warning("No se encontraron órdenes con ese nombre.")

    st.divider()
    st.subheader("🔍 Historial y Buscador")
    df_ver = traer_datos("ventas")
    if not df_ver.empty:
        # Filtro de búsqueda general
        search = st.text_input("Buscador rápido (Cliente, NIT o N° Orden)")
        if st.session_state['rol'] != 'admin':
            df_ver = df_ver[df_ver['empleado'] == st.session_state['usuario']]
        if search:
            df_ver = df_ver[df_ver['n_orden'].astype(str).str.contains(search, case=False) | 
                            df_ver['cliente'].str.contains(search, case=False) | 
                            df_ver['nit'].str.contains(search, case=False)]
        st.dataframe(df_ver, use_container_width=True, hide_index=True)

# --- SECCIÓN: EMPLEADOS (Solo Admin) ---
elif opcion == "Gestión de Empleados":
    st.title("👥 Panel de Administración de Personal")
    t1, t2 = st.tabs(["➕ Nuevo Empleado", "⚙️ Modificar / Eliminar"])
    
    with t1:
        with st.form("nuevo_u"):
            n_nom = st.text_input("Nombre Completo")
            n_cla = st.text_input("Contraseña para el empleado")
            n_rol = st.selectbox("Rol del usuario", ["empleado", "admin"])
            if st.form_submit_button("REGISTRAR"):
                df_u = traer_datos("usuarios")
                nuevo_u = pd.DataFrame([{"nombre": n_nom, "clave": n_cla, "rol": n_rol}])
                df_u_final = pd.concat([df_u, nuevo_u], ignore_index=True)
                conn.update(worksheet="usuarios", data=df_u_final)
                st.success(f"Empleado {n_nom} registrado."); st.rerun()

    with t2:
        df_u_edit = traer_datos("usuarios")
        u_sel = st.selectbox("Seleccione empleado a gestionar", df_u_edit['nombre'].tolist())
        u_idx = df_u_edit[df_u_edit['nombre'] == u_sel].index[0]
        u_data = df_u_edit.loc[u_idx]
        
        e_cla = st.text_input("Nueva Contraseña", value=str(u_data['clave']))
        e_rol = st.selectbox("Nuevo Rol", ["empleado", "admin"], index=0 if u_data['rol'] == "empleado" else 1)
        
        c_b1, c_b2 = st.columns(2)
        if c_b1.button("💾 GUARDAR CAMBIOS"):
            df_u_edit.at[u_idx, 'clave'] = e_cla
            df_u_edit.at[u_idx, 'rol'] = e_rol
            conn.update(worksheet="usuarios", data=df_u_edit)
            st.success("Datos actualizados"); st.rerun()
        if c_b2.button("🗑️ ELIMINAR USUARIO"):
            if u_sel != "Administrador":
                df_u_edit = df_u_edit.drop(u_idx)
                conn.update(worksheet="usuarios", data=df_u_edit)
                st.warning("Usuario eliminado"); st.rerun()
            else: st.error("No puedes eliminar la cuenta principal.")
