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
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbwefjYpHKmQNY6BY9-DXWAxk2GNN6VVeiVDxzr0xV-3Z7Ab9QLwkLulFK5d60rqQCVSSA/exec"

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
        if pestana == "usuarios":
            df.columns = ['nombre', 'clave', 'rol'] + list(df.columns[3:])
        elif pestana == "ventas":
            cols = ['fecha', 'n_orden', 'descripcion', 'total', 'abono', 'saldo', 'metodo_pago', 'estado', 'empleado', 'cliente', 'nit', 'celular', 'correo', 'factura', 'historial_pagos']
            df = df.iloc[:, :len(cols)]
            df.columns = cols
            df['total_n'] = df['total'].apply(a_numero)
            df['abono_n'] = df['abono'].apply(a_numero)
            df['saldo_n'] = df['total_n'] - df['abono_n']
            df['fecha_dt'] = pd.to_datetime(df['fecha'], errors='coerce')
        return df
    except: return pd.DataFrame()

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
    
    # --- FILTRO MAESTRO: ESTA ES LA CLAVE ---
    # Si es admin ve todo, si es empleado solo ve sus propias filas
    if st.session_state['rol'] == 'admin':
        df_v = df_v_comp.copy()
    else:
        # Filtramos el DataFrame para que solo contenga lo que el usuario logueado registró
        df_v = df_v_comp[df_v_comp['empleado'] == st.session_state['usuario']].copy()
    
    t_labels = ["📝 Registrar", "✏️ Editar / Abonar"]
    if st.session_state['rol'] == 'admin': t_labels.append("📊 Reportes Avanzados")
    tabs = st.tabs(t_labels)

    with tabs[0]: # 📝 REGISTRAR (BLOQUE COMPLETO)
        if 'limp' not in st.session_state: st.session_state['limp'] = 0
        v = str(st.session_state['limp'])
        
        c1, c2 = st.columns(2)
        ord = c1.text_input("N° Orden", key="o"+v)
        cli = c2.text_input("Cliente", key="cl"+v)
        
        c3, c4, c5 = st.columns(3)
        nit = c3.text_input("NIT / CC", key="ni"+v)
        cel = c4.text_input("Celular", key="ce"+v)
        cor = c5.text_input("Correo", key="co"+v)
        
        c6, c7 = st.columns(2)
        tot = a_numero(c6.text_input("Total ($ COP)", value="0", key="t"+v))
        abo = a_numero(c7.text_input("Abono Inicial ($ COP)", value="0", key="a"+v))
        
        # Ayudas visuales de moneda
        c6.markdown(f'<div class="money-helper">{formato_pesos(tot)}</div>', unsafe_allow_html=True)
        c7.markdown(f'<div class="money-helper">{formato_pesos(abo)}</div>', unsafe_allow_html=True)
        
        desc = st.text_area("Descripción del Trabajo", key="d"+v)
        
        c8, c9, c10 = st.columns(3)
        est = c8.selectbox("Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], key="e"+v)
        pag = c9.selectbox("Método de Pago", ["EFECTIVO", "NEQUI", "BANCOLOMBIA"], key="p"+v)
        fac = c10.selectbox("¿Requiere Factura?", ["NO", "SI"], key="f"+v)

        if st.button("💾 GUARDAR VENTA", use_container_width=True):
            if not ord or not cli:
                st.error("⚠️ El N° de Orden y el Cliente son obligatorios.")
            else:
                # Armamos el paquete de datos para Google Sheets
                p = {
                    "accion": "insertar",
                    "tipo_registro": "ventas",
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "n_orden": ord,
                    "descripcion": desc,
                    "total": float(tot),
                    "abono": float(abo),
                    "saldo": float(tot - abo),
                    "metodo_pago": pag,
                    "estado": est,
                    "empleado": st.session_state['usuario'], # Se guarda quién lo registró
                    "cliente": cli,
                    "nit": nit,
                    "celular": cel,
                    "correo": cor,
                    "factura": fac,
                    "historial_pagos": f"{formato_pesos(abo)} ({pag}) {datetime.now().strftime('%d/%m/%Y')}"
                }
                
                if enviar_google(p):
                    st.success(f"✅ Orden {ord} guardada con éxito")
                    st.session_state['limp'] += 1 # Limpia el formulario
                    st.rerun()
                    
    with tabs[1]: # ✏️ EDITAR / ABONAR / ELIMINAR
        if not df_v.empty:
            sel = st.selectbox("Seleccione la Orden a editar:", ["Seleccionar..."] + df_v['n_orden'].tolist())
            if sel != "Seleccionar...":
                val = df_v[df_v['n_orden'] == sel].iloc[0]
                
                st.info(f"Orden: **{sel}** | Registrada por: **{val['empleado']}**")
                
                # --- FORMULARIO DE EDICIÓN ---
                with st.form("f_edicion_pro"):
                    c1, c2 = st.columns(2)
                    e_cli = c1.text_input("Cliente", value=val['cliente'])
                    e_nit = c2.text_input("NIT / CC", value=val['nit'])
                    
                    c3, c4, c5 = st.columns(3)
                    e_cel = c3.text_input("Celular", value=val['celular'])
                    e_cor = c4.text_input("Correo", value=val['correo'])
                    e_fac = c5.selectbox("Factura", ["NO", "SI"], index=0 if val['factura'] == "NO" else 1)
                    
                    e_desc = st.text_area("Descripción Trabajo", value=val['descripcion'])
                    
                    c6, c7 = st.columns(2)
                    e_tot = a_numero(c6.text_input("Total ($ COP)", value=str(int(val['total_n']))))
                    e_nab = a_numero(c7.text_input("Añadir nuevo abono ($ COP)", value="0"))
                    
                    nuevo_abono_total = val['abono_n'] + e_nab
                    nuevo_saldo = e_tot - nuevo_abono_total
                    st.warning(f"Saldo actual: {formato_pesos(val['saldo_n'])} | **Nuevo Saldo: {formato_pesos(nuevo_saldo)}**")
                    
                    c8, c9 = st.columns(2)
                    e_est = c8.selectbox("Estado", ["EN PROCESO", "TERMINADO", "PAGADO"], 
                                         index=["EN PROCESO", "TERMINADO", "PAGADO"].index(val['estado']) if val['estado'] in ["EN PROCESO", "TERMINADO", "PAGADO"] else 0)
                    e_met = c9.selectbox("Medio del nuevo abono", ["EFECTIVO", "NEQUI", "BANCOLOMBIA"])
                    
                    if st.form_submit_button("💾 ACTUALIZAR ORDEN", use_container_width=True):
                        h_pago = val['historial_pagos']
                        if e_nab > 0:
                            h_pago += f" | +{formato_pesos(e_nab)} ({e_met}) {datetime.now().strftime('%d/%m/%Y')}"
                        
                        payload = {
                            "accion": "actualizar",
                            "tipo_registro": "ventas",
                            "id_busqueda": sel,
                            "cliente": e_cli, "nit": e_nit, "celular": e_cel, "correo": e_cor, "factura": e_fac,
                            "descripcion": e_desc, "total": float(e_tot), "abono": float(nuevo_abono_total),
                            "saldo": float(nuevo_saldo), "estado": e_est, "historial_pagos": h_pago
                        }
                        if enviar_google(payload):
                            st.success("✅ Cambios guardados")
                            st.rerun()

                # --- SECCIÓN EXCLUSIVA PARA EL ADMIN (ELIMINAR) ---
                if st.session_state['rol'] == 'admin':
                    st.divider()
                    with st.expander("🚨 ZONA DE PELIGRO - ELIMINAR ORDEN"):
                        st.write("Esta acción borrará permanentemente la orden del sistema.")
                        if st.button(f"🗑️ CONFIRMAR ELIMINAR ORDEN {sel}", use_container_width=True):
                            # Enviar al Apps Script la instrucción de borrar
                            # Nota: Asegúrate de que tu Apps Script maneje la acción 'eliminar'
                            p_del = {
                                "accion": "eliminar", 
                                "tipo_registro": "ventas", 
                                "id_busqueda": sel
                            }
                            if enviar_google(p_del):
                                st.error(f"Orden {sel} eliminada")
                                st.rerun()
        else:
            st.info("No hay órdenes disponibles.")

    if st.session_state['rol'] == 'admin':
        with tabs[2]: # 📊 REPORTES DE AUDITORÍA Y CONTROL (ADMIN)
            st.subheader("🧐 Auditoría de Ventas y Cartera")
            
            # --- FILTROS SUPERIORES ---
            c_f1, c_f2, c_f3 = st.columns(3)
            f_ini = c_f1.date_input("📅 Desde", datetime.now().replace(day=1), key="rep_f_ini")
            f_fin = c_f2.date_input("📅 Hasta", datetime.now(), key="rep_f_fin")
            
            lista_emp = ["TODOS"] + df_users_db['nombre'].tolist()
            e_sel = c_f3.selectbox("👤 Empleado", lista_emp, key="rep_emp")
            
            # --- FILTRO DE ESTADO DE CUENTA (LO QUE PEDISTE) ---
            c_f4, c_f5 = st.columns([2, 1])
            filtro_pago = c_f4.tabs(["📑 Todo", "💸 Solo Pendientes (Deben)", "✅ Solo Canceladas"])
            
            # --- LÓGICA DE FILTRADO MAESTRA ---
            df_r = df_v_comp.copy()
            df_r = df_r[df_r['fecha_dt'].notna()]
            df_r = df_r[(df_r['fecha_dt'].dt.date >= f_ini) & (df_r['fecha_dt'].dt.date <= f_fin)]
            
            if e_sel != "TODOS":
                df_r = df_r[df_r['empleado'] == e_sel]

            # --- SUB-FILTROS POR PESTAÑA ---
            with filtro_pago[0]: # TODO
                df_final = df_r.copy()
                st.caption("Mostrando todos los registros en este rango.")
            
            with filtro_pago[1]: # 💸 SOLO PENDIENTES (CARTERA)
                # CORRECCIÓN: Filtramos por saldo mayor a 0 
                # y nos aseguramos de que el estado no sea 'PAGADO'
                df_final = df_r[(df_r['saldo_n'] > 0) & (df_r['estado'] != "PAGADO")]
                st.caption(f"🔍 Órdenes con dinero pendiente de {e_sel}")
                
                if df_final.empty:
                    st.success(f"✨ ¡Felicidades! {e_sel} no tiene cuentas pendientes en este rango.")
                
            with filtro_pago[2]: # SOLO CANCELADAS
                # Filtra donde el saldo sea 0 o el estado sea PAGADO
                df_final = df_r[(df_r['estado'] == "PAGADO") | (df_r['saldo_n'] <= 0)]
                st.caption("Mostrando órdenes que ya fueron liquidadas al 100%.")

            # --- MÉTRICAS DINÁMICAS ---
            st.divider()
            v_total = df_final['total_n'].sum()
            a_total = df_final['abono_n'].sum()
            s_total = df_final['saldo_n'].sum()
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Valor Total Órdenes", formato_pesos(v_total))
            m2.metric("Total Recaudado", formato_pesos(a_total), delta=f"+ {formato_pesos(a_total)}", delta_color="normal")
            m3.metric("Cartera (Por Cobrar)", formato_pesos(s_total), delta=f"- {formato_pesos(s_total)}", delta_color="inverse")
            
            # --- TABLA FINAL ---
            if not df_final.empty:
                # Color de las filas según el saldo para que sea visual
                st.dataframe(
                    df_final[['fecha', 'n_orden', 'cliente', 'total', 'abono', 'saldo', 'estado', 'empleado']].sort_values('fecha', ascending=False),
                    use_container_width=True,
                    hide_index=True
                )
                
                # Resumen rápido por empleado en este filtro
                if e_sel == "TODOS":
                    st.write("---")
                    st.write("📊 **Dinero por Empleado (en esta selección):**")
                    resumen = df_final.groupby('empleado')[['total_n', 'abono_n', 'saldo_n']].sum()
                    st.table(resumen.style.format(formato_pesos))
            else:
                st.info("No hay datos que coincidan con estos filtros.")

    
    # --- HISTORIAL FILTRADO ---
    st.divider()
    st.subheader("📋 Historial de Órdenes")
    busq = st.text_input("🔍 Buscar:")
    df_h = df_v.copy() # Aquí df_h ya viene filtrado por el Filtro Maestro
    if busq:
        df_h = df_h[df_h['n_orden'].str.contains(busq, case=False) | df_h['cliente'].str.contains(busq, case=False)]
    
    # Definimos qué columnas ver (admin ve el nombre del empleado, el empleado no necesita verse a sí mismo)
    cols = ['fecha','n_orden','cliente','total','abono','saldo','estado']
    if st.session_state['rol'] == 'admin': cols.append('empleado')
    
    st.dataframe(df_h[cols].iloc[::-1], use_container_width=True, hide_index=True)


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
