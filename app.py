import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import io

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Gestión Negocio Pro", layout="wide")
st.markdown("""<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;} .stDeployButton {display:none;}</style>""", unsafe_allow_html=True)

SHEET_ID = "1UGxbXTQhXKJ-JmKxpzglccDJrZgpCsTDflKO9N8RMTc"
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbyqx3mQopxUsMjokkhejP1newA3Gv-0OySPGFLhgGNlG6wgRPSieC3wlWO8QawQ6DRQXg/exec"

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

# --- SECCIÓN: GESTIÓN DE EMPLEADOS ---
if opcion == "Gestión de Empleados":
    st.title("👥 Administración de Personal")
    t1, t2 = st.tabs(["➕ Nuevo Empleado", "⚙️ Modificar / Eliminar"])
    with t1:
        n_nom = st.text_input("Nombre Completo")
        n_cla = st.text_input("Contraseña")
        n_rol = st.selectbox("Rol", ["empleado", "admin"])
        if st.button("Registrar Empleado"):
            if n_nom and n_cla:
                payload = {"accion": "insertar", "tipo_registro": "usuarios", "nombre": n_nom, "clave": n_cla, "rol": n_rol}
                if enviar_google(payload): st.success("Registrado"); st.rerun()
    with t2:
        df_u = leer_datos("usuarios")
        if not df_u.empty:
            u_sel = st.selectbox("Usuario a editar", df_u['nombre'].tolist())
            user_edit = df_u[df_u['nombre'] == u_sel].iloc[0]
            e_cla = st.text_input("Nueva Clave", value=str(user_edit['clave']))
            e_rol = st.selectbox("Nuevo Rol", ["empleado", "admin"], index=0 if user_edit['rol'] == "empleado" else 1)
            if st.button("💾 Guardar Cambios"):
                payload = {"accion": "actualizar", "tipo_registro": "usuarios", "id_busqueda": u_sel, "clave": e_cla, "rol": e_rol}
                if enviar_google(payload): st.success("Actualizado"); st.rerun()

# --- SECCIÓN: VENTAS ---
# --- SECCIÓN: VENTAS (CON PESTAÑA DE REPORTES PRIVADA) ---
elif opcion == "Ventas":
    st.title("🚀 Gestión de Ventas")
    df_v = leer_datos("ventas")
    
    # Definimos qué pestañas mostrar según el ROL
    if st.session_state['rol'] == 'admin':
        tabs = st.tabs(["📝 Registrar", "✏️ Editar", "📊 Reportes"])
        tab_reg, tab_edit, tab_rep = tabs
    else:
        # El empleado NO ve la pestaña de Reportes
        tabs = st.tabs(["📝 Registrar", "✏️ Editar"])
        tab_reg, tab_edit = tabs

    # 1. PESTAÑA REGISTRAR (Todos la ven)
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
            v_abo = st.number_input("Abono ($)", key="a"+vs, step=1.0)
            v_est = st.selectbox("Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], key="e"+vs)
            v_pag = st.selectbox("Pago", ["EFECTIVO", "NEQUI", "DAVIPLATA", "BANCOLOMBIA"], key="p"+vs)

        if st.button("💾 GUARDAR VENTA", use_container_width=True):
            if v_ord and v_cli:
                payload = {"accion": "insertar", "tipo_registro": "ventas", "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "n_orden": v_ord, "descripcion": v_desc, "total": v_tot, "abono": v_abo, "saldo": v_tot-v_abo, "metodo_pago": v_pag, "estado": v_est, "empleado": st.session_state['usuario'], "cliente": v_cli, "nit": v_nit, "celular": v_cel, "correo": "", "factura": v_fac}
                if enviar_google(payload): 
                    st.session_state['limp_v'] += 1
                    st.success("¡Venta guardada!"); st.rerun()

   # 2. PESTAÑA EDITAR (Con filtro de autoría para empleados)
    with tab_edit:
        if not df_v.empty:
            # --- FILTRO DE SEGURIDAD PARA EDICIÓN ---
            if st.session_state['rol'] == 'admin':
                # El admin ve todas las órdenes
                opciones_ordenes = df_v['n_orden'].unique().tolist()
            else:
                # El empleado SOLO ve las órdenes donde su nombre aparece en la columna 'empleado'
                filtro_mis_ordenes = df_v[df_v['empleado'] == st.session_state['usuario']]
                opciones_ordenes = filtro_mis_ordenes['n_orden'].unique().tolist()

            if opciones_ordenes:
                ord_s = st.selectbox("Seleccione N° de Orden para editar:", ["Seleccionar..."] + opciones_ordenes)
                
                if ord_s != "Seleccionar...":
                    # Extraemos los datos de la orden seleccionada
                    d = df_v[df_v['n_orden'] == ord_s].iloc[0]
                    
                    st.info(f"Editando orden de: {d['cliente']} (Registrada por: {d['empleado']})")
                    
                    e_abo = st.number_input("Nuevo Abono ($)", value=float(d['abono']), step=1.0)
                    e_est = st.selectbox("Nuevo Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], 
                                         index=["EN PROCESO", "TERMINADO", "PAGADO"].index(d['estado']))
                    
                    if st.button("Actualizar Registro", use_container_width=True):
                        # Calculamos el nuevo saldo automáticamente
                        nuevo_saldo = float(d['total']) - e_abo
                        
                        payload = {
                            "accion": "actualizar", 
                            "tipo_registro": "ventas", 
                            "id_busqueda": ord_s, 
                            "abono": e_abo, 
                            "saldo": nuevo_saldo, 
                            "estado": e_est
                        }
                        
                        if enviar_google(payload): 
                            st.success(f"✅ Orden {ord_s} actualizada correctamente")
                            st.rerun()
            else:
                st.warning("No tienes órdenes registradas para editar.")
        else:
            st.info("No hay ventas registradas en el sistema.")

  # 3. PESTAÑA REPORTES (SOLO ADMIN - Formato compatible Excel)
    if st.session_state['rol'] == 'admin':
        with tab_rep:
            if not df_v.empty:
                st.subheader("💰 Balance de Caja")
                emp_l = ["Todos"] + df_v['empleado'].unique().tolist()
                sel_e = st.selectbox("Seleccione empleado para el balance:", emp_l)
                
                df_f = df_v.copy()
                if sel_e != "Todos": 
                    df_f = df_f[df_f['empleado'] == sel_e]
                
                # Métricas numéricas
                v_t = pd.to_numeric(df_f['total'], errors='coerce').sum()
                a_t = pd.to_numeric(df_f['abono'], errors='coerce').sum()
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Ventas Totales", f"$ {v_t:,.0f}")
                m2.metric("Abonos Recibidos", f"$ {a_t:,.0f}")
                m3.metric("Saldo por Cobrar", f"$ {v_t - a_t:,.0f}")
                
                # --- GENERACIÓN DE EXCEL SEGURO (Formato HTML-XLS) ---
                # Este formato lo abre Excel directo y no requiere instalar nada nuevo
                html_table = df_f.to_html(index=False)
                # Agregamos una cabecera para que Excel sepa que es una hoja de cálculo
                excel_format = f"""
                <html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40">
                <head><meta charset="utf-8"></head>
                <body>{html_table}</body>
                </html>
                """
                
                st.download_button(
                    label=f"🟢 Descargar Reporte para Excel - {sel_e}",
                    data=excel_format,
                    file_name=f"Reporte_{sel_e}_{datetime.now().strftime('%Y-%m-%d')}.xls",
                    mime="application/vnd.ms-excel",
                    use_container_width=True
                )
            else:
                st.info("No hay datos para generar reportes.")
    # --- TABLA GENERAL (Buscador inferior) ---
    st.divider()
    busq = st.text_input("🔍 Buscador rápido (Orden o Cliente)")
    df_m = df_v.copy().iloc[::-1]
    
    # El empleado SOLO ve sus propias ventas en la tabla inferior
    if st.session_state['rol'] != 'admin': 
        df_m = df_m[df_m['empleado'] == st.session_state['usuario']]
    
    if busq: 
        df_m = df_m[df_m.apply(lambda r: r.astype(str).str.contains(busq, case=False).any(), axis=1)]
    
    st.dataframe(df_m, use_container_width=True, hide_index=True)
