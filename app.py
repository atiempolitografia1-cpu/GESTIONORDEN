import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import io

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Gestión Negocio Pro", layout="wide")
st.markdown("""<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;} .stDeployButton {display:none;}</style>""", unsafe_allow_html=True)

SHEET_ID = "1UGxbXTQhXKJ-JmKxpzglccDJrZgpCsTDflKO9N8RMTc"
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbwefjYpHKmQNY6BY9-DXWAxk2GNN6VVeiVDxzr0xV-3Z7Ab9QLwkLulFK5d60rqQCVSSA/exec"

# INICIALIZACIÓN DE SESIÓN SEGURA
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False
if 'usuario' not in st.session_state: st.session_state['usuario'] = ""
if 'rol' not in st.session_state: st.session_state['rol'] = ""

# --- FUNCIÓN DE LECTURA SIN CACHÉ ---
def leer_datos(pestana):
    try:
        # Agregamos un timestamp para evitar que el navegador guarde una versión vieja (Caché)
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={pestana}&t={datetime.now().microsecond}"
        res = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(res.text))
        
        # --- EL TRUCO ESTÁ AQUÍ ---
        # Convertimos todo a texto y reemplazamos los 'nan' por texto vacío
        df = df.astype(str).replace('nan', '') 
        
        if df.empty:
            return pd.DataFrame(columns=['nombre', 'clave', 'rol']) if pestana == "usuarios" else pd.DataFrame()
            
        if pestana == "usuarios":
            cols = ['nombre', 'clave', 'rol']
            df.columns = cols + list(df.columns[len(cols):])
        elif pestana == "ventas":
            cols_v = ['fecha', 'n_orden', 'descripcion', 'total', 'abono', 'saldo', 'metodo_pago', 'estado', 'empleado', 'cliente', 'nit', 'celular', 'correo', 'factura', 'historial_pagos']
            df.columns = cols_v + list(df.columns[len(cols_v):])
            
        # Limpiamos espacios en blanco accidentales
        df = df.apply(lambda x: x.str.strip())
        return df
    except Exception as e:
        st.error(f"Error al leer datos: {e}")
        return pd.DataFrame()
        
# --- LOGIN ---
df_real = leer_datos("usuarios")
admin_respaldo = pd.DataFrame([{'nombre': 'Administrador', 'clave': 'admin123', 'rol': 'admin'}])

if not df_real.empty:
    if "administrador" in df_real['nombre'].astype(str).str.lower().values:
        df_users_db = df_real
    else:
        df_users_db = pd.concat([df_real, admin_respaldo], ignore_index=True)
else:
    df_users_db = admin_respaldo

if not st.session_state.get('autenticado', False):
    st.title("🔐 Acceso al Sistema")
    opciones = [u for u in df_users_db['nombre'].unique().tolist() if str(u).lower() != 'nan' and u != ""]
    if opciones:
        u_input = st.selectbox("Seleccione su Usuario", opciones)
        p_input = st.text_input("Contraseña", type="password")
        if st.button("INGRESAR", use_container_width=True):
            user_match = df_users_db[df_users_db['nombre'] == u_input]
            if not user_match.empty:
                user_data = user_match.iloc[0]
                if str(user_data['clave']).strip().lower() == str(p_input).strip().lower():
                    st.session_state.update({"autenticado": True, "usuario": u_input, "rol": str(user_data['rol']).strip().lower()})
                    st.rerun()
                else: st.error("❌ Contraseña incorrecta.")
    st.stop()

# --- MENÚ LATERAL ---
st.sidebar.title(f"👤 {st.session_state['usuario']}")
menu = ["Ventas", "Gestión de Empleados"] if st.session_state['rol'] == 'admin' else ["Ventas"]
opcion = st.sidebar.radio("Ir a:", menu)

if st.sidebar.button("Cerrar Sesión"):
    st.session_state['autenticado'] = False
    st.rerun()

# --- SECCIÓN: GESTIÓN DE EMPLEADOS (CORREGIDA) ---
if opcion == "Gestión de Empleados":
    st.title("👥 Administración de Personal")
    t1, t2 = st.tabs(["➕ Nuevo Empleado", "⚙️ Modificar / Eliminar"])
    
    with t1:
        st.subheader("Registrar nuevo acceso")
        n_nom = st.text_input("Nombre Completo (Ej: Juan Perez)")
        n_cla = st.text_input("Contraseña de acceso")
        n_rol = st.selectbox("Rol del usuario", ["empleado", "admin"])
        
        if st.button("Registrar en el Sistema", use_container_width=True):
            if n_nom and n_cla:
                payload = {"accion": "insertar", "tipo_registro": "usuarios", "nombre": n_nom, "clave": n_cla, "rol": n_rol}
                if enviar_google(payload): 
                    st.success(f"✅ {n_nom} ahora tiene acceso al sistema."); st.rerun()
            else: st.warning("Por favor, completa el nombre y la contraseña.")
            
    with t2:
        st.subheader("Control de Usuarios Activos")
        df_u = leer_datos("usuarios")
        if not df_u.empty:
            # Filtramos para no dejar que el admin se borre a sí mismo por error desde aquí
            usuarios_lista = df_u['nombre'].tolist()
            u_sel = st.selectbox("Seleccione el empleado a gestionar:", usuarios_lista)
            
            user_edit = df_u[df_u['nombre'] == u_sel].iloc[0]
            
            st.write(f"**Rol actual:** {user_edit['rol']}")
            e_cla = st.text_input("Cambiar Contraseña", value=str(user_edit['clave']))
            e_rol = st.selectbox("Cambiar Rol", ["empleado", "admin"], index=0 if str(user_edit['rol']).lower() == "empleado" else 1)
            
            c_b1, c_b2 = st.columns(2)
            with c_b1:
                if st.button("💾 Guardar Cambios", use_container_width=True):
                    payload = {"accion": "actualizar", "tipo_registro": "usuarios", "id_busqueda": u_sel, "clave": e_cla, "rol": e_rol}
                    if enviar_google(payload): st.success("Datos actualizados"); st.rerun()
            
            with c_b2:
                # Botón de eliminación definitiva del usuario
                if u_sel != "Administrador": # Seguridad para el admin principal
                    if st.button("🗑️ ELIMINAR ACCESO", use_container_width=True, type="secondary"):
                        # Esta acción SOLO borra la fila en la pestaña 'usuarios'
                        payload = {"accion": "eliminar", "tipo_registro": "usuarios", "id_busqueda": u_sel}
                        if enviar_google(payload):
                            st.warning(f"El acceso de {u_sel} ha sido revocado. Sus ventas registradas permanecerán en el historial.")
                            st.rerun()
                else:
                    st.info("El Administrador principal no puede ser eliminado.")
        else:
            st.info("No hay usuarios registrados además del administrador de respaldo.")

# --- SECCIÓN: VENTAS ---
elif opcion == "Ventas":
    st.title("🚀 Gestión de Ventas")
    df_v = leer_datos("ventas")
    
    if st.session_state['rol'] == 'admin':
        tab_reg, tab_edit, tab_rep = st.tabs(["📝 Registrar", "✏️ Editar / Corregir / Eliminar", "📊 Reportes"])
    else:
        tab_reg, tab_edit = st.tabs(["📝 Registrar", "✏️ Editar / Corregir"])

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
                hist_ini = f"${v_abo:,.0f} ({v_pag}) en {datetime.now().strftime('%Y-%m-%d')}"
                payload = {"accion": "insertar", "tipo_registro": "ventas", "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "n_orden": v_ord, "descripcion": v_desc, "total": v_tot, "abono": v_abo, "saldo": v_tot-v_abo, "metodo_pago": v_pag, "estado": v_est, "empleado": st.session_state['usuario'], "cliente": v_cli, "nit": v_nit, "celular": v_cel, "correo": "", "factura": v_fac, "historial_pagos": hist_ini}
                if enviar_google(payload): 
                    st.session_state['limp_v'] += 1; st.success("¡Venta guardada!"); st.rerun()
            else: st.error("Faltan datos (N° Orden o Cliente)")

    # --- 2. PESTAÑA EDITAR (EDICIÓN TOTAL) ---
    with tab_edit:
        if not df_v.empty:
            if st.session_state['rol'] == 'admin':
                opciones_o = df_v['n_orden'].unique().tolist()
            else:
                opciones_o = df_v[df_v['empleado'] == st.session_state['usuario']]['n_orden'].unique().tolist()

            ord_s = st.selectbox("Seleccione Orden para Editar:", ["Seleccionar..."] + opciones_o)
            
            if ord_s != "Seleccionar...":
                d = df_v[df_v['n_orden'] == str(ord_s)].iloc[0]
                
                st.subheader(f"🛠️ Editando Orden N° {ord_s}")
                
                # Campos de texto y contacto
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
                
                # Campos de Dinero y Estado
                ce4, ce5, ce6 = st.columns(3)
                with ce4:
                    e_total = st.number_input("Valor Total ($)", value=float(pd.to_numeric(d['total'], errors='coerce') or 0.0))
                    e_abono_prev = float(pd.to_numeric(d['abono'], errors='coerce') or 0.0)
                    st.write(f"Abonado hasta hoy: **${e_abono_prev:,.0f}**")
                with ce5:
                    nuevo_pago = st.number_input("Sumar nuevo abono ($)", min_value=0.0, step=100.0)
                    medio_nuevo = st.selectbox("Medio de este pago", ["EFECTIVO", "NEQUI", "DAVIPLATA", "BANCOLOMBIA"])
                with ce6:
                    e_est = st.selectbox("Estado Actual", ["EN PROCESO", "TERMINADO", "PAGADO"], index=["EN PROCESO", "TERMINADO", "PAGADO"].index(d['estado']))
                    st.write(f"Saldo restante: **${(e_total - (e_abono_prev + nuevo_pago)):,.0f}**")

                if st.button("💾 GUARDAR TODOS LOS CAMBIOS", use_container_width=True):
                    abono_final = e_abono_prev + nuevo_pago
                    saldo_final = e_total - abono_final
                    
                    # Manejo del historial
                    hist_ant = str(d['historial_pagos']) if str(d['historial_pagos']) != "nan" else ""
                    if nuevo_pago > 0:
                        nueva_nota = f"${nuevo_pago:,.0f} ({medio_nuevo}) el {datetime.now().strftime('%Y-%m-%d')}"
                        hist_ant = hist_ant + " || " + nueva_nota if hist_ant else nueva_nota

                    payload = {
                        "accion": "actualizar", "tipo_registro": "ventas", "id_busqueda": ord_s,
                        "cliente": e_cli, "nit": e_nit, "celular": e_cel, "factura": e_fac,
                        "descripcion": e_desc, "total": e_total, "abono": abono_final,
                        "saldo": saldo_final, "estado": e_est, "historial_pagos": hist_ant
                    }
                    if enviar_google(payload): 
                        st.success("¡Cambios guardados con éxito!"); st.rerun()

                # --- ELIMINAR (SOLO ADMIN) ---
                if st.session_state['rol'] == 'admin':
                    st.divider()
                    with st.expander("🗑️ ZONA DE PELIGRO"):
                        conf = st.checkbox("Confirmar eliminación")
                        if st.button("ELIMINAR ORDEN", disabled=not conf, use_container_width=True):
                            if enviar_google({"accion": "eliminar", "tipo_registro": "ventas", "id_busqueda": str(ord_s)}):
                                st.warning("Orden eliminada"); st.rerun()
        else: st.info("No hay ventas.")

    # --- 3. PESTAÑA REPORTES (SOLO ADMIN) ---
    if st.session_state['rol'] == 'admin':
        with tab_rep:
            if not df_v.empty:
                emp_l = ["Todos"] + df_v['empleado'].unique().tolist()
                sel_e = st.selectbox("Balance de:", emp_l)
                df_f = df_v.copy()
                if sel_e != "Todos": df_f = df_f[df_f['empleado'] == sel_e]
                vt = pd.to_numeric(df_f['total'], errors='coerce').sum() or 0.0
                at = pd.to_numeric(df_f['abono'], errors='coerce').sum() or 0.0
                c1, c2, c3 = st.columns(3); c1.metric("Ventas", f"$ {vt:,.0f}"); c2.metric("Abonos", f"$ {at:,.0f}"); c3.metric("Saldo", f"$ {vt-at:,.0f}")
                html = df_f.to_html(index=False)
                excel_c = f'<html><head><meta charset="utf-8"></head><body>{html}</body></html>'
                st.download_button(f"🟢 Descargar Excel", excel_c, f"Reporte.xls", "application/vnd.ms-excel", use_container_width=True)

    # --- TABLA ÚNICA AL FINAL ---
    st.divider()
    busq = st.text_input("🔍 Buscar...")
    df_m = df_v.copy().iloc[::-1]
    if st.session_state['rol'] != 'admin': df_m = df_m[df_m['empleado'] == st.session_state['usuario']]
    if busq: df_m = df_m[df_m.apply(lambda r: r.astype(str).str.contains(busq, case=False).any(), axis=1)]
    st.dataframe(df_m, use_container_width=True, hide_index=True)
