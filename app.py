import streamlit as st
import pandas as pd
from datetime import datetime
import io
import requests

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Gestión Litografía Pro", layout="wide")

# ID DE TU HOJA (Ya configurado)
SHEET_ID = "1UGxbXTQhXKJ-JmKxpzglccDJrZgpCsTDflKO9N8RMTc"

# Función para leer datos de Google Sheets sin errores 400
def traer_datos(pestana):
    try:
        # Forzamos la descarga como CSV de la pestaña específica
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={pestana}"
        response = requests.get(url)
        if response.status_code == 200:
            return pd.read_csv(io.StringIO(response.text))
        else:
            st.error(f"Error de Google: {response.status_code}")
            st.stop()
    except Exception as e:
        st.error(f"⚠️ Error al conectar con la pestaña '{pestana}'")
        st.info("Asegúrate de haber ido a: Archivo > Compartir > Publicar en la Web > Publicar")
        st.stop()

# --- INICIO: CARGA DE USUARIOS ---
df_usuarios = traer_datos("usuarios")

if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

# --- PANTALLA DE LOGIN ---
if not st.session_state['autenticado']:
    st.title("🔐 Acceso Litografía")
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

# --- SECCIÓN: VENTAS (TU ESTRUCTURA ORIGINAL) ---
if opcion == "Ventas":
    st.title("🚀 Gestión de Ventas e Inventario")
    tab_reg, tab_edit = st.tabs(["📝 Registrar Nueva Orden", "✏️ Actualizar Orden"])

    with tab_reg:
        with st.form("nueva_venta", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                n_ord = st.text_input("N° Orden / Factura")
                v_cli = st.text_input("Nombre del Cliente")
                v_nit = st.text_input("NIT o Cédula")
            with c2:
                v_cel = st.text_input("Celular")
                v_cor = st.text_input("Correo")
                v_fac = st.radio("¿Factura?", ["SÍ", "NO"], horizontal=True)
            with c3:
                v_tot = st.number_input("Valor Total ($)", min_value=0.0)
                v_abo = st.number_input("Abono Inicial ($)", min_value=0.0)
                v_est = st.selectbox("Estado", ["EN PROCESO", "TERMINADO", "PAGADO"])
                v_pag = st.selectbox("Método de Pago", ["EFECTIVO", "NEQUI", "DAVIPLATA", "BANCOLOMBIA"])
            
            v_desc = st.text_area("Descripción del trabajo")
            
            if st.form_submit_button("💾 GUARDAR ORDEN", use_container_width=True):
                # NOTA: Para guardar usaremos un sistema de Google Apps Script 
                # (Te lo explicaré apenas logremos que entres a la app)
                st.success("¡Datos capturados correctamente! (Conexión de escritura pendiente)")

    with tab_edit:
        st.subheader("Modificar Orden Existente")
        df_edit = traer_datos("ventas")
        if not df_edit.empty:
            search_edit = st.text_input("Buscar por Orden o Cliente")
            if search_edit:
                df_edit = df_edit[df_edit['n_orden'].astype(str).str.contains(search_edit, case=False)]
            
            if not df_edit.empty:
                ord_sel = st.selectbox("Seleccione Orden:", df_edit['n_orden'].tolist())
                # Lógica de edición aquí...
                st.info("Módulo de edición cargado.")

    st.divider()
    st.subheader("🔍 Historial y Buscador")
    df_ver = traer_datos("ventas")
    if not df_ver.empty:
        if st.session_state['rol'] != 'admin':
            df_ver = df_ver[df_ver['empleado'] == st.session_state['usuario']]
        st.dataframe(df_ver, use_container_width=True, hide_index=True)

# --- SECCIÓN: EMPLEADOS ---
elif opcion == "Gestión de Empleados":
    st.title("👥 Gestión de Personal")
    df_u = traer_datos("usuarios")
    st.table(df_u[['nombre', 'rol']])
    # Formulario para nuevos empleados aquí...
