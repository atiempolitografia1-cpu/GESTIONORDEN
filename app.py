import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import io

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Atiempo Litografía", layout="wide")

SHEET_ID = "1UGxbXTQhXKJ-JmKxpzglccDJrZgpCsTDflKO9N8RMTc"
URL_SCRIPT = "https://script.google.com/macros/s/AKfycby1nYVVa-gvt1GumMceDK-IVXqYtcvkyI0Cnr4lCAx_0gBGeU8Vctp96Rh2aOz47uSnFQ/exec"

def leer_datos(nombre_pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
        res = requests.get(url)
        return pd.read_csv(io.StringIO(res.text))
    except:
        return pd.DataFrame()

# --- LOGIN ---
if 'logueado' not in st.session_state:
    st.session_state['logueado'] = False

df_usuarios = leer_datos("usuarios")

if not st.session_state['logueado']:
    st.title("🔐 Acceso Atiempo")
    if not df_usuarios.empty:
        u_input = st.selectbox("Usuario", df_usuarios['nombre'].tolist())
        p_input = st.text_input("Contraseña", type="password")
        if st.button("ENTRAR"):
            user_row = df_usuarios[df_usuarios['nombre'] == u_input].iloc[0]
            if str(user_row['clave']) == p_input:
                st.session_state.update({'logueado': True, 'user': u_input, 'rol': user_row['rol']})
                st.rerun()
            else: st.error("Clave incorrecta")
    st.stop()

# --- NAVEGACIÓN ---
menu = ["Nueva Venta", "Ver Ventas"]
if st.session_state['rol'] == 'admin':
    menu.extend(["Gestión de Empleados", "➕ Registrar Empleado"])

choice = st.sidebar.radio("Menú Principal", menu)

# --- SECCIÓN: NUEVA VENTA ---
if choice == "Nueva Venta":
    st.header("📝 Registrar Orden de Servicio")
    with st.form("venta_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            n_orden = st.text_input("N° de Orden")
            cliente = st.text_input("Nombre del Cliente")
            nit = st.text_input("NIT / CC")
            celular = st.text_input("Celular")
            correo = st.text_input("Correo Electrónico")
        
        with col2:
            descripcion = st.text_area("Descripción del Trabajo")
            total = st.number_input("Valor Total ($)", min_value=0)
            abono = st.number_input("Abono Inicial ($)", min_value=0)
            metodo = st.selectbox("Método de Pago", ["EFECTIVO", "NEQUI", "DAVIPLATA", "TRANSFERENCIA"])
            factura = st.radio("¿Requiere Factura?", ["SÍ", "NO"], horizontal=True)
            estado = st.selectbox("Estado Inicial", ["EN PROCESO", "TERMINADO", "PAGADO"])

        if st.form_submit_button("💾 GUARDAR ORDEN"):
            if n_orden and cliente:
                payload = {
                    "tipo_registro": "ventas",
                    "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "n_orden": n_orden, "descripcion": descripcion,
                    "total": total, "abono": abono, "saldo": total - abono,
                    "metodo_pago": metodo, "estado": estado, "empleado": st.session_state['user'],
                    "cliente": cliente, "nit": nit, "celular": celular, "correo": correo, "factura": factura
                }
                res = requests.post(URL_SCRIPT, json=payload)
                if res.status_code == 200:
                    st.success(f"✅ Venta {n_orden} guardada")
                else: st.error("Error al guardar")
            else: st.warning("Faltan campos obligatorios")

# --- SECCIÓN: VER VENTAS ---
elif choice == "Ver Ventas":
    st.header("📋 Historial de Ventas")
    df_v = leer_datos("ventas")
    if not df_v.empty:
        if st.session_state['rol'] != 'admin':
            df_v = df_v[df_v['empleado'] == st.session_state['user']]
        st.dataframe(df_v, use_container_width=True, hide_index=True)

# --- SECCIÓN: GESTIÓN DE EMPLEADOS ---
elif choice == "Gestión de Empleados":
    st.header("👥 Lista de Usuarios")
    st.dataframe(df_usuarios, use_container_width=True)

# --- SECCIÓN: NUEVO EMPLEADO ---
elif choice == "➕ Registrar Empleado":
    st.header("👤 Crear Nuevo Usuario")
    with st.form("form_nuevo_usuario"):
        nuevo_nom = st.text_input("Nombre Completo")
        nueva_clave = st.text_input("Contraseña de Acceso", type="password")
        nuevo_rol = st.selectbox("Rol del Usuario", ["admin", "vendedor"])
        
        if st.form_submit_button("✅ CREAR USUARIO"):
            if nuevo_nom and nueva_clave:
                payload_u = {
                    "tipo_registro": "usuarios",
                    "nombre": nuevo_nom,
                    "clave": nueva_clave,
                    "rol": nuevo_rol
                }
                r = requests.post(URL_SCRIPT, json=payload_u)
                if r.status_code == 200:
                    st.success(f"Usuario {nuevo_nom} registrado exitosamente.")
                else: st.error("No se pudo registrar el usuario.")
