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

# --- SECCIÓN: VENTAS ---
elif opcion == "Ventas":
    st.title("🚀 Gestión de Ventas")
    df_v = leer_datos("ventas")
    
    tabs = st.tabs(["📝 Registrar", "✏️ Editar / Corregir / Abonar", "📊 Reportes"]) if st.session_state['rol'] == 'admin' else st.tabs(["📝 Registrar", "✏️ Editar / Corregir / Abonar"])

    with tabs[0]: # REGISTRAR
        if 'limp' not in st.session_state: st.session_state['limp'] = 0
        vs = str(st.session_state['limp'])
        c1, c2, c3 = st.columns(3)
        with c1:
            v_ord = st.text_input("N° Orden", key="o"+vs)
            v_desc = st.text_area("Descripción", key="d"+vs)
            v_fac = st.radio("Factura", ["SÍ", "NO"], key="f"+vs, horizontal=True)
        with c2:
            v_cli = st.text_input("Cliente", key="cl"+vs)
            v_nit = st.text_input("NIT/CC", key="n"+vs)
            v_cel = st.text_input("Celular", key="ce"+vs)
        with c3:
            v_tot = st.number_input("Total ($)", key="t"+vs, min_value=0.0)
            v_abo = st.number_input("Abono Inicial ($)", key="a"+vs, min_value=0.0)
            v_est = st.selectbox("Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], key="e"+vs)
            v_pag = st.selectbox("Medio Pago", ["EFECTIVO", "NEQUI", "DAVIPLATA", "BANCOLOMBIA"], key="p"+vs)
        
        if st.button("💾 GUARDAR VENTA", use_container_width=True):
            if v_ord and v_cli:
                h_ini = f"${v_abo:,.0f} ({v_pag}) el {datetime.now().strftime('%Y-%m-%d')}"
                payload = {"accion": "insertar", "tipo_registro": "ventas", "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "n_orden": v_ord, "descripcion": v_desc, "total": v_tot, "abono": v_abo, "saldo": v_tot-v_abo, "metodo_pago": v_pag, "estado": v_est, "empleado": st.session_state['usuario'], "cliente": v_cli, "nit": v_nit, "celular": v_cel, "factura": v_fac, "historial_pagos": h_ini}
                if enviar_google(payload): 
                    st.session_state['limp'] += 1; st.success("¡Venta guardada!"); st.rerun()

    with tabs[1]: # EDITAR TOTAL
        if not df_v.empty:
            f_v = df_v if st.session_state['rol'] == 'admin' else df_v[df_v['empleado'] == st.session_state['usuario']]
            ord_s = st.selectbox("Seleccione Orden para Editar:", ["Seleccionar..."] + f_v['n_orden'].unique().tolist())
            if ord_s != "Seleccionar...":
                d = df_v[df_v['n_orden'] == str(ord_s)].iloc[0]
                
                st.subheader(f"🛠️ Editando Orden N° {ord_s}")
                c1, c2, c3 = st.columns(3)
                with c1:
                    e_cli = st.text_input("Nombre Cliente", value=str(d['cliente']))
                    e_nit = st.text_input("NIT / CC", value=str(d['nit']))
                with c2:
                    e_cel = st.text_input("Celular", value=str(d['celular']))
                    e_fac = st.radio("Factura", ["SÍ", "NO"], index=0 if str(d['factura']) == "SÍ" else 1)
                with c3:
                    e_desc = st.text_area("Descripción", value=str(d['descripcion']))

                st.divider()
                c4, c5, c6 = st.columns(3)
                with c4:
                    e_total = st.number_input("Valor Total ($)", value=float(pd.to_numeric(d['total'], errors='coerce') or 0.0))
                    v_abono_prev = float(pd.to_numeric(d['abono'], errors='coerce') or 0.0)
                    st.info(f"Abonado: ${v_abono_prev:,.0f}")
                with c5:
                    nuevo_pago = st.number_input("Nuevo abono hoy ($)", min_value=0.0)
                    medio_pago = st.selectbox("Medio", ["EFECTIVO", "NEQUI", "DAVIPLATA", "BANCOLOMBIA"])
                with c6:
                    e_est = st.selectbox("Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], index=["EN PROCESO", "TERMINADO", "PAGADO"].index(d['estado']))
                    st.warning(f"Saldo: ${(e_total - (v_abono_prev + nuevo_pago)):,.0f}")

                if st.button("💾 GUARDAR TODOS LOS CAMBIOS", use_container_width=True):
                    abono_f = v_abono_prev + nuevo_pago
                    hist_f = str(d['historial_pagos']) if str(d['historial_pagos']) != "nan" else ""
                    if nuevo_pago > 0:
                        hist_f = (hist_f + " || " if hist_f else "") + f"${nuevo_pago:,.0f} ({medio_pago}) el {datetime.now().strftime('%Y-%m-%d')}"
                    
                    payload = {"accion": "actualizar", "tipo_registro": "ventas", "id_busqueda": ord_s, "cliente": e_cli, "nit": e_nit, "celular": e_cel, "factura": e_fac, "descripcion": e_desc, "total": e_total, "abono": abono_f, "saldo": e_total-abono_f, "estado": e_est, "historial_pagos": hist_f}
                    if enviar_google(payload): 
                        st.success("¡Cambios aplicados!"); st.rerun()
                
                if st.session_state['rol'] == 'admin':
                    st.divider()
                    with st.expander("🗑️ ELIMINAR ESTA ORDEN"):
                        if st.checkbox("Confirmo que deseo borrar la orden permanentemente"):
                            if st.button("ELIMINAR AHORA"):
                                if enviar_google({"accion": "eliminar", "tipo_registro": "ventas", "id_busqueda": str(ord_s)}):
                                    st.warning("Orden eliminada"); st.rerun()

   
       # --- 3. PESTAÑA REPORTES (SOLO ADMIN) ---
    if st.session_state['rol'] == 'admin':
        with tab_rep:
            if not df_v.empty:
                st.subheader("📊 Filtros de Reporte")
                
                # Convertimos la columna fecha a formato datetime para poder filtrar
                df_v['fecha_dt'] = pd.to_datetime(df_v['fecha'], errors='coerce')
                
                col_f1, col_f2, col_f3 = st.columns(3)
                
                with col_f1:
                    # Filtro de Empleado
                    lista_emp = ["Todos"] + df_v['empleado'].unique().tolist()
                    sel_emp = st.selectbox("Seleccionar Empleado:", lista_emp)
                
                with col_f2:
                    # Filtro de Periodo
                    tipo_filtro = st.radio("Filtrar por:", ["Todo", "Día / Rango", "Mes / Año"], horizontal=True)
                
                with col_f3:
                    # Lógica de fechas
                    df_filtrado = df_v.copy()
                    
                    if tipo_filtro == "Día / Rango":
                        rango = st.date_input("Seleccione Día o Rango (Semana):", value=[datetime.now(), datetime.now()])
                        if len(rango) == 2:
                            inicio, fin = rango
                            df_filtrado = df_filtrado[(df_filtrado['fecha_dt'].dt.date >= inicio) & (df_filtrado['fecha_dt'].dt.date <= fin)]
                    
                    elif tipo_filtro == "Mes / Año":
                        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
                        c_m1, c_m2 = st.columns(2)
                        with c_m1:
                            sel_mes = st.selectbox("Mes:", range(1, 13), format_func=lambda x: meses[x-1], index=datetime.now().month - 1)
                        with c_m2:
                            sel_ano = st.selectbox("Año:", sorted(df_v['fecha_dt'].dt.year.unique(), reverse=True))
                        
                        df_filtrado = df_filtrado[(df_filtrado['fecha_dt'].dt.month == sel_mes) & (df_filtrado['fecha_dt'].dt.year == sel_ano)]

                # Aplicar filtro de empleado al final
                if sel_emp != "Todos":
                    df_filtrado = df_filtrado[df_filtrado['empleado'] == sel_emp]

                st.divider()

                # --- MÉTRICAS ---
                v_t = pd.to_numeric(df_filtrado['total'], errors='coerce').sum()
                a_t = pd.to_numeric(df_filtrado['abono'], errors='coerce').sum()
                s_t = v_t - a_t
                
                m1, m2, m3 = st.columns(3)
                m1.metric("💰 Ventas Totales", f"$ {v_t:,.0f}")
                m2.metric("📥 Total Cobrado (Abonos)", f"$ {a_t:,.0f}")
                m3.metric("⏳ Saldo Pendiente", f"$ {s_t:,.0f}")

                # --- TABLA DE RESULTADOS ---
                st.write(f"### Detalle de registros ({len(df_filtrado)})")
                # Quitamos la columna técnica de fecha_dt para mostrar la tabla limpia
                df_mostrar = df_filtrado.drop(columns=['fecha_dt'])
                st.dataframe(df_mostrar, use_container_width=True, hide_index=True)

                # --- BOTÓN DE DESCARGA ---
                html = df_mostrar.to_html(index=False)
                excel_c = f'<html><head><meta charset="utf-8"></head><body>{html}</body></html>'
                st.download_button(
                    label="🟢 Descargar este Reporte (Excel)",
                    data=excel_c,
                    file_name=f"Reporte_{sel_emp}_{datetime.now().strftime('%Y%m%d')}.xls",
                    mime="application/vnd.ms-excel",
                    use_container_width=True
                )
            else:
                st.info("No hay datos de ventas para generar reportes.")

    # --- TABLA ÚNICA ---
    st.divider()
    busq = st.text_input("🔍 Buscar en historial...")
    df_m = df_v.copy().iloc[::-1]
    if st.session_state['rol'] != 'admin': df_m = df_m[df_m['empleado'] == st.session_state['usuario']]
    if busq: df_m = df_m[df_m.apply(lambda r: r.astype(str).str.contains(busq, case=False).any(), axis=1)]
    st.dataframe(df_m, use_container_width=True, hide_index=True)
