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
    button[kind="headerNoPadding"] { visibility: visible !important; z-index: 9999991; background-color: rgba(255,255,255,0.1); border-radius: 5px; }
    /* Estilo para métricas */
    [data-testid="stMetricValue"] { font-size: 1.8rem; color: #00802b; }
    /* Estilo para el visor de moneda en tiempo real */
    .money-helper {
        font-size: 1.1rem;
        font-weight: bold;
        color: #00802b;
        background-color: #e6f4ea;
        padding: 5px 10px;
        border-radius: 5px;
        margin-top: -15px;
        margin-bottom: 15px;
        display: inline-block;
    }
    </style>
    """, unsafe_allow_html=True)

SHEET_ID = "1UGxbXTQhXKJ-JmKxpzglccDJrZgpCsTDflKO9N8RMTc"
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbwsN0sDjy_uc8NlKe7lYBIeRDWjeD_tIOMi852D8K1RqAz4TYL2QVrMQUalREfegq608w/exec"

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
        # Elimina símbolos de peso, puntos de miles y espacios
        s = re.sub(r'[^\d,]', '', str(valor)).replace(',', '.')
        return float(s) if s else 0.0
    except: return 0.0

def leer_datos(pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={pestana}&t={datetime.now().microsecond}"
        res = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(res.text), dtype=str).fillna('')
        
        if pestana == "ventas":
            cols = ['fecha', 'n_orden', 'descripcion', 'total', 'abono', 'saldo', 'metodo_pago', 'estado', 'empleado', 'cliente', 'nit', 'celular', 'correo', 'factura', 'historial_pagos']
            df = df.iloc[:, :len(cols)]
            df.columns = cols
            df['total_n'] = df['total'].apply(a_numero)
            df['abono_n'] = df['abono'].apply(a_numero)
            df['saldo_n'] = df['total_n'] - df['abono_n']
            df['fecha_dt'] = pd.to_datetime(df['fecha'], errors='coerce')
            df['solo_dia'] = df['fecha_dt'].dt.date
            
        elif pestana == "usuarios":
            df.columns = ['nombre', 'clave', 'rol'] + list(df.columns[3:])
            
        # --- NUEVO BLOQUE PARA LA PESTAÑA CAJA ---
        elif pestana == "caja":
            cols_caja = ['fecha', 'n_orden', 'valor', 'metodo', 'empleado']
            df = df.iloc[:, :len(cols_caja)]
            df.columns = cols_caja
            
            # Limpieza extrema de números
            df['valor_n'] = df['valor'].apply(a_numero)
            
            # Convertir fecha asegurando el formato día/mes/año
            df['fecha_dt'] = pd.to_datetime(df['fecha'], dayfirst=True, errors='coerce')
            df['solo_dia'] = df['fecha_dt'].dt.date
            
        return df
    except: 
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
    df_v_comp = leer_datos("ventas")
    
    # --- FILTRO MAESTRO ---
    if st.session_state['rol'] == 'admin':
        df_v = df_v_comp.copy()
    else:
        df_v = df_v_comp[df_v_comp['empleado'] == st.session_state['usuario']].copy()
    
    t_labels = ["📝 Registrar", "✏️ Editar / Abonar"]
    if st.session_state['rol'] == 'admin': t_labels.append("📊 Reportes Avanzados")
    tabs = st.tabs(t_labels)
    
    # --- PESTAÑA REGISTRAR ---
    with tabs[0]:
        v = str(st.session_state.get('limp', 0)) 
        st.subheader("📝 Registrar Nueva Orden")
        c_f1, c_f2 = st.columns([1, 2])
        fecha_manual = c_f1.date_input("📅 Fecha de la Orden", datetime.now().date())
        c1, c2 = st.columns(2)
        ord = c1.text_input("N° Orden", value=st.session_state.get('n_ord_s', ""), key="or"+v)
        cli = c2.text_input("Cliente", key="cl"+v)
        c3, c4, c5 = st.columns(3)
        nit = c3.text_input("NIT / CC", key="ni"+v)
        cel = c4.text_input("Celular", key="ce"+v)
        cor = c5.text_input("Correo", key="co"+v)
        c6, c7 = st.columns(2)
        tot = a_numero(c6.text_input("Total ($ COP)", value="0", key="t"+v))
        abo = a_numero(c7.text_input("Abono Inicial ($ COP)", value="0", key="a"+v))
        c6.markdown(f'<div class="money-helper">{formato_pesos(tot)}</div>', unsafe_allow_html=True)
        c7.markdown(f'<div class="money-helper">{formato_pesos(abo)}</div>', unsafe_allow_html=True)
        desc = st.text_area("Descripción del Trabajo", key="d"+v)
        c8, c9, c10 = st.columns(3)
        est = c8.selectbox("Estado", ["EN PROCESO", "TERMINADO", "ENTREGADO"], key="e"+v)
        pag = c9.selectbox("Método de Pago", ["SIN ABONO", "EFECTIVO", "NEQUI", "BANCOLOMBIA", "DAVIPLATA"], key="p"+v)
        fac = c10.selectbox("¿Requiere Factura?", ["NO", "SI"], key="f"+v)

        if st.button("💾 GUARDAR VENTA", use_container_width=True):
            if abo > 0 and pag == "SIN ABONO":
                st.error("🚫 ¡Atención! Si hay un abono, debes elegir el medio de pago.")
            elif not ord or not cli:
                st.error("⚠️ El N° de Orden y el Cliente son obligatorios.")
            else:
                fecha_str = fecha_manual.strftime("%d/%m/%Y")
                p_venta = {
                    "accion": "insertar", "tipo_registro": "ventas", "fecha": fecha_str,
                    "n_orden": str(ord), "descripcion": str(desc), "total": float(tot),
                    "abono": float(abo), "saldo": float(tot - abo), "metodo_pago": str(pag),
                    "estado": str(est), "empleado": str(st.session_state['usuario']),
                    "cliente": str(cli), "nit": str(nit), "celular": str(cel),
                    "correo": str(cor), "factura": str(fac), "historial_pagos": f"{formato_pesos(abo)} ({pag}) {fecha_str}"
                }
                p_caja = {
                    "accion": "insertar", "tipo_registro": "caja", "fecha": fecha_str,
                    "n_orden": str(ord), "valor": float(abo), "metodo": str(pag),
                    "empleado": str(st.session_state['usuario'])
                }
                if enviar_google(p_venta):
                    if abo > 0: enviar_google(p_caja)
                    st.success(f"✅ Orden {ord} registrada")
                    st.session_state['limp'] = st.session_state.get('limp', 0) + 1
                    st.rerun()

    # --- PESTAÑA EDITAR / ABONAR ---
    with tabs[1]:
        if not df_v.empty:
            sel = st.selectbox("Seleccione la Orden a editar:", ["Seleccionar..."] + df_v['n_orden'].tolist())
            if sel != "Seleccionar...":
                val = df_v[df_v['n_orden'] == sel].iloc[0]
                st.info(f"Orden: **{sel}** | Registrada por: **{val['empleado']}**")
                
                with st.form("f_edicion_pro"):
                    c1, c2 = st.columns(2)
                    e_cli = c1.text_input("Cliente", value=val['cliente'])
                    e_nit = c2.text_input("NIT / CC", value=val['nit'])
                    c3, c4, c5 = st.columns(3)
                    e_cel = c3.text_input("Celular", value=val['celular'])
                    e_cor = c4.text_input("Correo", value=val['correo'])
                    e_fac = c5.selectbox("Factura", ["NO", "SI"], index=0 if val['factura'] == "NO" else 1)
                    e_desc = st.text_area("Descripción Trabajo", value=val['descripcion'])
                    st.divider()
                    c6, c7 = st.columns(2)
                    es_admin = st.session_state.get('rol') == 'admin'
                    e_tot = a_numero(c6.text_input("Total ($ COP)", value=str(int(val['total_n'])), disabled=not es_admin))
                    e_nab = a_numero(c7.text_input("Añadir nuevo abono ($ COP)", value="0"))
                    c_fecha_edit, c_met_edit = st.columns(2)
                    fecha_abono_manual = c_fecha_edit.date_input("📅 Fecha de este abono", datetime.now().date())
                    e_met = c_met_edit.selectbox("Medio del nuevo abono", ["EFECTIVO", "NEQUI", "BANCOLOMBIA", "DAVIPLATA"])
                    nuevo_abono_total = val['abono_n'] + e_nab
                    nuevo_saldo = e_tot - nuevo_abono_total
                    st.warning(f"Saldo actual: {formato_pesos(val['saldo_n'])} | **Nuevo Saldo: {formato_pesos(nuevo_saldo)}**")
                    e_est = st.selectbox("Estado de la Orden", ["EN PROCESO", "TERMINADO", "ENTREGADO"], 
                                       index=["EN PROCESO", "TERMINADO", "PAGADO"].index(val['estado']) if val['estado'] in ["EN PROCESO", "TERMINADO", "PAGADO"] else 0)
                    
                    if st.form_submit_button("💾 ACTUALIZAR ORDEN", use_container_width=True):
                        h_pago = val['historial_pagos']
                        f_abono_str = fecha_abono_manual.strftime('%d/%m/%Y')
                        if e_nab > 0:
                            h_pago += f" | +{formato_pesos(e_nab)} ({e_met}) {f_abono_str}"
                        payload = {
                            "accion": "actualizar", "tipo_registro": "ventas", "id_busqueda": sel,
                            "cliente": e_cli, "nit": e_nit, "celular": e_cel, "correo": e_cor, "factura": e_fac,
                            "descripcion": e_desc, "total": float(e_tot), "abono": float(nuevo_abono_total),
                            "saldo": float(nuevo_saldo), "estado": e_est, "historial_pagos": h_pago
                        }
                        if enviar_google(payload):
                            if e_nab > 0:
                                p_caja_nuevo = {
                                    "accion": "insertar", "tipo_registro": "caja", "fecha": f_abono_str,
                                    "n_orden": str(sel), "valor": float(e_nab), "metodo": str(e_met),
                                    "empleado": str(st.session_state['usuario'])
                                }
                                enviar_google(p_caja_nuevo)
                            st.success(f"✅ Orden actualizada.")
                            st.rerun()

                if st.session_state['rol'] == 'admin':
                    st.divider()
                    with st.expander("🚨 ZONA DE PELIGRO - ELIMINAR ORDEN"):
                        if st.button(f"🗑️ CONFIRMAR ELIMINAR ORDEN {sel}", use_container_width=True):
                            if enviar_google({"accion": "eliminar", "tipo_registro": "ventas", "id_busqueda": sel}):
                                st.error(f"Orden {sel} eliminada")
                                st.rerun()
        else:
            st.info("No hay órdenes disponibles.")

    # --- PESTAÑA REPORTES (ADMIN) ---
    # --- PESTAÑA REPORTES (ADMIN) ---
    # --- PESTAÑA REPORTES (ADMIN) ---
    if st.session_state['rol'] == 'admin':
        with tabs[2]:
            st.subheader("🧐 Auditoría de Ventas, Caja y Cartera")
            df_caja = leer_datos("caja")
            
            c1, c2, c3 = st.columns(3)
            f_ini = c1.date_input("📅 Desde", datetime.now().date(), key="f_ini_rep")
            f_fin = c2.date_input("📅 Hasta", datetime.now().date(), key="f_fin_rep")
            lista_emp = ["TODOS"] + df_users_db['nombre'].tolist()
            e_sel = c3.selectbox("👤 Empleado", lista_emp)

            # --- NUEVA SECCIÓN: CARTERA DEL DÍA ---
            # Filtramos las ventas generales solo para el rango seleccionado
            df_v_dia = df_v_comp[(df_v_comp['solo_dia'] >= f_ini) & (df_v_comp['solo_dia'] <= f_fin)]
            if e_sel != "TODOS":
                df_v_dia = df_v_dia[df_v_dia['empleado'] == e_sel]
            
            cartera_del_periodo = df_v_dia['saldo_n'].sum()
            
            # Mostramos un banner destacado con la cartera
            st.warning(f"### 🚩 Cartera del Periodo Seleccionado: {formato_pesos(cartera_del_periodo)}")
            st.caption("Este es el valor total que los clientes aún deben de las ventas realizadas en estas fechas.")
            
            st.markdown("---")
            st.markdown("### 💰 Cuadre de Caja (Dinero Ingresado)")
            
            if not df_caja.empty:
                df_c_fil = df_caja[(df_caja['solo_dia'] >= f_ini) & (df_caja['solo_dia'] <= f_fin)]
                if e_sel != "TODOS": 
                    df_c_fil = df_c_fil[df_c_fil['empleado'] == e_sel]
                
                g_efe, g_neq, g_ban, g_dav = 0.0, 0.0, 0.0, 0.0

                for emp in df_c_fil['empleado'].unique():
                    # ... (aquí sigue el resto de tu código de los expanders de empleados que pusimos antes)
                    with st.expander(f"📥 Ver Caja de: {emp.upper()}", expanded=True):
                        df_emp = df_c_fil[df_c_fil['empleado'] == emp]
                        col1, col2, col3, col4 = st.columns(4)
                        
                        # Cálculo individual por empleado
                        s_efe = df_emp[df_emp['metodo'] == "EFECTIVO"]['valor_n'].sum()
                        s_neq = df_emp[df_emp['metodo'] == "NEQUI"]['valor_n'].sum()
                        s_ban = df_emp[df_emp['metodo'] == "BANCOLOMBIA"]['valor_n'].sum()
                        s_dav = df_emp[df_emp['metodo'] == "DAVIPLATA"]['valor_n'].sum()
                        
                        # Mostrar métricas del empleado
                        col1.metric("💵 EFECTIVO", formato_pesos(s_efe))
                        col2.metric("📱 NEQUI", formato_pesos(s_neq))
                        col3.metric("🏦 BANCO", formato_pesos(s_ban))
                        col4.metric("📲 DAVIPLATA", formato_pesos(s_dav))
                        
                        # SUMAR AL TOTAL GLOBAL
                        g_efe += s_efe
                        g_neq += s_neq
                        g_ban += s_ban
                        g_dav += s_dav
                        
                        st.write(f"**Total de {emp}:** {formato_pesos(df_emp['valor_n'].sum())}")

                # --- CUADRO DE GRAN TOTAL (Solo se muestra si seleccionas TODOS) ---
                if e_sel == "TODOS" and not df_c_fil.empty:
                    st.divider()
                    st.markdown("### 🏆 RESUMEN TOTAL DE TODA LA TIENDA")
                    m1, m2, m3, m4 = st.columns(4)
                    m1.info(f"**Total Efectivo**\n\n{formato_pesos(g_efe)}")
                    m2.info(f"**Total Nequi**\n\n{formato_pesos(g_neq)}")
                    m3.info(f"**Total Banco**\n\n{formato_pesos(g_ban)}")
                    m4.info(f"**Total Daviplata**\n\n{formato_pesos(g_dav)}")
                    
                    total_global = g_efe + g_neq + g_ban + g_dav
                    st.success(f"## **RECAUDO TOTAL GLOBAL: {formato_pesos(total_global)}**")

            st.divider()
            st.markdown("### 🔍 Buscador de Órdenes y Cartera")
            filtro_pago = st.radio("Estado de cuenta:", ["📑 Todo", "💸 Solo Pendientes", "✅ Solo Canceladas"], horizontal=True)
            df_r = df_v_comp.copy()
            if not df_r.empty and 'solo_dia' in df_r.columns:
                df_r = df_r[(df_r['solo_dia'] >= f_ini) & (df_r['solo_dia'] <= f_fin)]
                if e_sel != "TODOS": df_r = df_r[df_r['empleado'] == e_sel]
                
                if "Pendientes" in filtro_pago: df_final = df_r[df_r['saldo_n'] > 0]
                elif "Canceladas" in filtro_pago: df_final = df_r[df_r['saldo_n'] <= 0]
                else: df_final = df_r.copy()

                c_m1, c_m2, c_m3 = st.columns(3)
                c_m1.metric("Valor Total Ventas", formato_pesos(df_final['total_n'].sum()))
                c_m2.metric("Abonado (Historico)", formato_pesos(df_final['abono_n'].sum()))
                c_m3.metric("Cartera (Deuda)", formato_pesos(df_final['saldo_n'].sum()), delta_color="inverse")
                st.dataframe(df_final.sort_values('n_orden', ascending=False), use_container_width=True, hide_index=True)

            st.divider()
            with st.expander("🚨 SECCIÓN DE PELIGRO - MANTENIMIENTO"):
                confirmar = st.checkbox("Entiendo que esta acción es irreversible")
                if st.button("🔥 BORRAR TODO EL HISTORIAL", type="primary", disabled=not confirmar):
                    if enviar_google({"accion": "limpiar_todo"}):
                        st.success("✅ Sistema reseteado."); st.rerun()
                        
    # --- HISTORIAL FILTRADO ---
    st.divider()
    st.subheader("📋 Historial de Órdenes")
    busq = st.text_input("🔍 Buscar:")
    df_h = df_v.copy()
    if busq:
        df_h = df_h[df_h['n_orden'].astype(str).str.contains(busq, case=False) | df_h['cliente'].astype(str).str.contains(busq, case=False)]
    cols_h = ['fecha','n_orden','descripcion','cliente','total','abono','saldo','estado']
    if st.session_state['rol'] == 'admin': cols_h.append('empleado')
    st.dataframe(df_h[cols_h].iloc[::-1], use_container_width=True, hide_index=True)

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
