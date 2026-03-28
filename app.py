import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import io

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Gestión Negocio Pro", layout="wide")
st.markdown("""<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;} .stDeployButton {display:none;}</style>""", unsafe_allow_html=True)

SHEET_ID = "1UGxbXTQhXKJ-JmKxpzglccDJrZgpCsTDflKO9N8RMTc"
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbzF3sYgCJQ8CNZ-flKFetqxJOGCIdel-nasr6X3cmrN7rvuFGaQtS4SFkeqQAny6OhaSA/exec"

# INICIALIZACIÓN DE SESIÓN SEGURA
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False
if 'usuario' not in st.session_state: st.session_state['usuario'] = ""
if 'rol' not in st.session_state: st.session_state['rol'] = ""

# --- FUNCIÓN DE LECTURA SIN CACHÉ ---
def leer_datos(pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={pestana}&t={datetime.now().microsecond}"
        res = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(res.text))
        
        if df.empty:
            return pd.DataFrame(columns=['nombre', 'clave', 'rol']) if pestana == "usuarios" else pd.DataFrame()

        if pestana == "usuarios":
            cols = ['nombre', 'clave', 'rol']
            df.columns = cols + list(df.columns[len(cols):])
        elif pestana == "ventas":
            cols_v = ['fecha', 'n_orden', 'descripcion', 'total', 'abono', 'saldo', 'metodo_pago', 'estado', 'empleado', 'cliente', 'nit', 'celular', 'correo', 'factura']
            df.columns = cols_v + list(df.columns[len(cols_v):])

        df = df.astype(str).apply(lambda x: x.str.strip())
        df = df[df.iloc[:,0].str.lower() != df.columns[0].lower()]
        return df
    except:
        return pd.DataFrame(columns=['nombre', 'clave', 'rol']) if pestana == "usuarios" else pd.DataFrame()

def enviar_google(payload):
    try:
        res = requests.post(URL_SCRIPT, json=payload, timeout=15)
        return res.status_code == 200
    except: return False

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
    
    # Definimos las pestañas según el ROL
    if st.session_state['rol'] == 'admin':
        tab_reg, tab_edit, tab_rep = st.tabs(["📝 Registrar", "✏️ Abonos / Estados / Eliminar", "📊 Reportes"])
    else:
        # El empleado NO ve la pestaña de Reportes
        tab_reg, tab_edit = st.tabs(["📝 Registrar", "✏️ Abonos / Estados"])

    # --- 1. PESTAÑA REGISTRAR (Todos la ven) ---
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
            v_tot = st.number_input("Total ($)", key="t"+vs, step=1.0)
            v_abo = st.number_input("Abono Inicial ($)", key="a"+vs, step=1.0)
            v_est = st.selectbox("Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], key="e"+vs)
            v_pag = st.selectbox("Medio Pago Inicial", ["EFECTIVO", "NEQUI", "DAVIPLATA", "BANCOLOMBIA"], key="p"+vs)
        
        if st.button("💾 GUARDAR VENTA", use_container_width=True):
            if v_ord and v_cli:
                # Historial de pagos inicial con formato numérico limpio
                historial_ini = f"${v_abo:,.0f} ({v_pag}) en {datetime.now().strftime('%Y-%m-%d')}"
                payload = {"accion": "insertar", "tipo_registro": "ventas", "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "n_orden": v_ord, "descripcion": v_desc, "total": v_tot, "abono": v_abo, "saldo": v_tot-v_abo, "metodo_pago": v_pag, "estado": v_est, "empleado": st.session_state['usuario'], "cliente": v_cli, "nit": v_nit, "celular": v_cel, "correo": "", "factura": v_fac, "historial_pagos": historial_ini}
                if enviar_google(payload): 
                    st.session_state['limp_v'] += 1
                    st.success("¡Venta guardada!"); st.rerun()
            else: st.error("Faltan datos críticos (N° Orden o Cliente)")

    # --- 2. PESTAÑA EDITAR / ELIMINAR (Con filtro de seguridad) ---
    with tab_edit:
        if not df_v.empty:
            # Filtro: Admin ve todo, Empleado solo sus órdenes
            if st.session_state['rol'] == 'admin':
                opciones_ordenes = df_v['n_orden'].unique().tolist()
            else:
                filtro_mis_v = df_v[df_v['empleado'] == st.session_state['usuario']]
                opciones_ordenes = filtro_mis_v['n_orden'].unique().tolist()

            if opciones_ordenes:
                ord_s = st.selectbox("Seleccione N° de Orden para Abonar:", ["Seleccionar..."] + opciones_ordenes)
                
                if ord_s != "Seleccionar...":
                    # Extraemos los datos numéricos de forma segura
                    d = df_v[df_v['n_orden'] == str(ord_s)].iloc[0]
                    v_total = pd.to_numeric(d['total'], errors='coerce') or 0.0
                    v_abono_previo = pd.to_numeric(d['abono'], errors='coerce') or 0.0
                    v_saldo_previo = pd.to_numeric(d['saldo'], errors='coerce') or 0.0

                    st.info(f"Gestión de Orden: {ord_s} | Cliente: {d['cliente']}")
                    st.warning(f"Total: ${v_total:,.0f} | Abonado Previos: ${v_abono_previo:,.0f} | **Saldo Pendiente: ${v_saldo_previo:,.0f}**")
                    
                    # Mostrar historial de pagos si existe
                    if 'historial_pagos' in d and str(d['historial_pagos']) != "nan":
                        st.markdown(f"**📜 Detalles de abonos:** {d['historial_pagos']}")

                    st.divider()
                    col_a1, col_a2 = st.columns(2)
                    with col_a1:
                        nuevo_monto_abono = st.number_input("¿Cuánto va a abonar AHORA? ($)", min_value=0.0, step=100.0)
                    with col_a2:
                        medio_nuevo = st.selectbox("¿Medio de pago de este abono?", ["EFECTIVO", "NEQUI", "DAVIPLATA", "BANCOLOMBIA"])
                    
                    e_est = st.selectbox("Actualizar Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], index=["EN PROCESO", "TERMINADO", "PAGADO"].index(d['estado']))
                    
                    if st.button("💾 REGISTRAR NUEVO ABONO", use_container_width=True):
                        # Calculamos los nuevos acumulados
                        total_abonado_final = v_abono_previo + nuevo_monto_abono
                        nuevo_saldo_final = v_total - total_abonado_final
                        
                        # Crear la nueva entrada de historial
                        nota_actual = f"${nuevo_monto_abono:,.0f} ({medio_nuevo}) en {datetime.now().strftime('%Y-%m-%d')}"
                        # Unimos el historial previo con el nuevo
                        historial_previo = str(d['historial_pagos']) if str(d['historial_pagos']) != "nan" else ""
                        historial_completo = historial_previo + " || " + nota_actual if historial_previo else nota_actual
                        
                        payload = {
                            "accion": "actualizar", 
                            "tipo_registro": "ventas", 
                            "id_busqueda": ord_s, 
                            "abono": total_abonado_final, 
                            "saldo": nuevo_saldo_final, 
                            "estado": e_est,
                            "historial_pagos": historial_completo # Columna O en Excel
                        }
                        
                        if enviar_google(payload): 
                            st.success(f"✅ Abono de ${nuevo_monto_abono:,.0f} registrado en la orden {ord_s}. Nuevo saldo: ${nuevo_saldo_final:,.0f}"); st.rerun()

                    # --- ZONA DE ELIMINAR (SOLO ADMIN) ---
                    if st.session_state['rol'] == 'admin':
                        st.divider()
                        with st.expander("🗑️ ZONA DE PELIGRO: Eliminar Orden"):
                            st.warning(f"¿Seguro que desea borrar la orden {ord_s}? Esta acción no se puede deshacer.")
                            confirmar_borrado = st.checkbox("Confirmo que quiero eliminar esta orden permanentemente")
                            if st.button("ELIMINAR AHORA", disabled=not confirmar_borrado, use_container_width=True, type="secondary"):
                                payload = {"accion": "eliminar", "tipo_registro": "ventas", "id_busqueda": str(ord_s)}
                                if enviar_google(payload):
                                    st.warning(f"La orden {ord_s} ha sido eliminada."); st.rerun()
            else:
                st.warning("No tienes órdenes registradas para gestionar.")
        else:
            st.info("No hay ventas registradas.")

    # --- 3. PESTAÑA REPORTES (SOLO ADMIN - Versión Excel Real) ---
    if st.session_state['rol'] == 'admin':
        with tab_rep:
            if not df_v.empty:
                st.subheader("💰 Balance de Caja y Descarga de Excel")
                emp_l = ["Todos"] + df_v['empleado'].unique().tolist()
                sel_e = st.selectbox("Seleccione empleado para el balance:", emp_l)
                
                df_f = df_v.copy()
                if sel_e != "Todos": 
                    df_f = df_f[df_f['empleado'] == sel_e]
                
                # Métricas numéricas seguras
                v_t = pd.to_numeric(df_f['total'], errors='coerce').sum() or 0.0
                a_t = pd.to_numeric(df_f['abono'], errors='coerce').sum() or 0.0
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Ventas Totales", f"$ {v_t:,.0f}")
                m2.metric("Abonos Recibidos", f"$ {a_t:,.0f}")
                m3.metric("Saldo por Cobrar", f"$ {v_t - a_t:,.0f}")
                
                # Generar Excel (Formato compatible con Excel directo)
                html_table = df_f.to_html(index=False)
                excel_c = f'<html><head><meta charset="utf-8"></head><body>{html_table}</body></html>'
                st.download_button(f"🟢 Descargar Excel de {sel_e}", excel_c, f"Reporte_{sel_e}.xls", "application/vnd.ms-excel", use_container_width=True)
            else:
                st.info("No hay datos para generar reportes.")

    # =========================================================
    # --- VISUALIZACIÓN DE TABLA GENERAL (UNA SOLA VEZ AL FINAL) ---
    # =========================================================
    st.divider()
    busq = st.text_input("🔍 Buscador rápido (Orden, Cliente, Empleado, Detalles...)")
    
    # Preparamos los datos: Invertimos para ver lo nuevo primero
    df_m = df_v.copy().iloc[::-1]
    
    # 🔒 FILTRO DE SEGURIDAD PARA EMPLEADOS 🔒
    # Si NO eres admin, solo ves tus ventas
    if st.session_state['rol'] != 'admin':
        df_m = df_m[df_m['empleado'] == st.session_state['usuario']]
    
    # Aplicamos el buscador si hay texto
    if busq:
        df_m = df_m[df_m.apply(lambda r: r.astype(str).str.contains(busq, case=False).any(), axis=1)]
    
    # Mostramos la tabla UNA SOLA VEZ
    st.dataframe(df_m, use_container_width=True, hide_index=True)
