import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gestión Litografía Pro", layout="wide")

# DATOS DE CONEXIÓN
SHEET_ID = "1UGxbXTQhXKJ-JmKxpzglccDJrZgpCsTDflKO9N8RMTc"
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbxOEP-5jAU8RE76-5DsUp2iyn_zXr54kEXY0_H3Dw-BNqPSW5-1W_oGlr48W94o-RqLSA/exec"

def traer_datos(pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={pestana}"
        res = requests.get(url)
        return pd.read_csv(io.StringIO(res.text))
    except:
        st.error(f"Error al conectar con la pestaña {pestana}")
        st.stop()

# --- CARGA INICIAL ---
df_usuarios = traer_datos("usuarios")

if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

# --- PANTALLA DE LOGIN ---
if not st.session_state['autenticado']:
    st.title("🔐 Sistema de Gestión - Litografía")
    u_log = st.selectbox("Seleccione su Usuario", df_usuarios['nombre'].tolist())
    p_log = st.text_input("Contraseña", type="password")
    
    if st.button("INGRESAR", use_container_width=True):
        user_row = df_usuarios[df_usuarios['nombre'] == u_log].iloc[0]
        if str(user_row['clave']) == p_log:
            st.session_state.update({"autenticado": True, "usuario": u_log, "rol": user_row['rol']})
            st.rerun()
        else:
            st.error("Contraseña incorrecta")
    st.stop()

# --- MENÚ PRINCIPAL ---
st.sidebar.title(f"👤 {st.session_state['usuario']}")
opciones = ["Ventas"]
if st.session_state['rol'] == 'admin':
    opciones.append("Gestión de Empleados")

opcion = st.sidebar.radio("Navegación", opciones)

if st.sidebar.button("Cerrar Sesión"):
    st.session_state['autenticado'] = False
    st.rerun()

# --- MÓDULO DE VENTAS ---
if opcion == "Ventas":
    st.title("🚀 Registro de Órdenes")
    tab_reg, tab_hist = st.tabs(["📝 Nueva Orden", "📊 Historial Completo"])

    with tab_reg:
        with st.form("form_venta", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                n_ord = st.text_input("N° Orden / Factura")
                v_cli = st.text_input("Nombre Cliente")
                v_nit = st.text_input("NIT / CC")
            with col2:
                v_cel = st.text_input("Celular")
                v_cor = st.text_input("Correo")
                v_fac = st.radio("¿Requiere Factura?", ["SÍ", "NO"], horizontal=True)
            with col3:
                v_tot = st.number_input("Valor Total ($)", min_value=0.0)
                v_abo = st.number_input("Abono Inicial ($)", min_value=0.0)
                v_est = st.selectbox("Estado", ["EN PROCESO", "TERMINADO", "PAGADO"])
                v_pag = st.selectbox("Método de Pago", ["EFECTIVO", "NEQUI", "DAVIPLATA", "BANCOLOMBIA", "TRANSFERENCIA"])
            
            v_desc = st.text_area("Descripción detallada (Cantidades, medidas, material...)")
            
            if st.form_submit_button("💾 GUARDAR ORDEN EN EXCEL", use_container_width=True):
                # Preparar datos para enviar
                datos_venta = {
                    "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "n_orden": str(n_ord),
                    "descripcion": v_desc,
                    "total": float(v_tot),
                    "abono": float(v_abo),
                    "saldo": float(v_tot - v_abo),
                    "metodo_pago": v_pag,
                    "estado": v_est,
                    "empleado": st.session_state['usuario'],
                    "cliente": v_cli,
                    "nit": v_nit,
                    "celular": v_cel,
                    "correo": v_cor,
                    "factura": v_fac
                }
                
                try:
                    r = requests.post(URL_SCRIPT, json=datos_venta)
                    if r.status_code == 200:
                        st.success(f"✅ ¡Orden {n_ord} guardada exitosamente!")
                        st.balloons()
                    else:
                        st.error("Error al guardar. Revisa la conexión con Google.")
                except Exception as e:
                    st.error(f"Fallo crítico: {e}")

    with tab_hist:
        st.subheader("Buscador de Historial")
        df_hist = traer_datos("ventas")
        if not df_hist.empty:
            busqueda = st.text_input("Buscar por Cliente, NIT o N° Orden")
            if busqueda:
                df_hist = df_hist[df_hist.apply(lambda row: busqueda.lower() in row.astype(str).str.lower().values, axis=1)]
            
            st.dataframe(df_hist, use_container_width=True, hide_index=True)

# --- MÓDULO GESTIÓN (ADMIN) ---
elif opcion == "Gestión de Empleados":
    st.title("👥 Personal de Litografía")
    st.dataframe(traer_datos("usuarios"), use_container_width=True)
    st.info("Para agregar nuevos empleados, edita directamente la pestaña 'usuarios' en tu Google Sheets.")
