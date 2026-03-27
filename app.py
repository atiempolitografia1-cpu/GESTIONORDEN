import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import io

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Sistema de Gestión", layout="wide")

# Estilo para ocultar cosas innecesarias de Streamlit
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- DATOS DE CONEXIÓN ---
# 1. Tu ID de Google Sheet (Ya lo tienes)
SHEET_ID = "1UGxbXTQhXKJ-JmKxpzglccDJrZgpCsTDflKO9N8RMTc"
# 2. PEGA AQUÍ LA URL QUE COPIASTE EN EL PASO ANTERIOR
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbyDy11desfhOJhagy2EbvxdJZaEO9-6iGn1ZN1WA8GR8Oo1SKv1wFLPa17ptIgg6Vl08A/exec"

# Función para leer datos de Google Sheets
def leer_datos(nombre_pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
        res = requests.get(url)
        return pd.read_csv(io.StringIO(res.text))
    except:
        return pd.DataFrame()

# --- LÓGICA DE LOGIN ---
if 'logueado' not in st.session_state:
    st.session_state['logueado'] = False

usuarios_df = leer_datos("usuarios")

if not st.session_state['logueado']:
    st.title("🔐 Acceso al Sistema")
    if not usuarios_df.empty:
        user_list = usuarios_df['nombre'].tolist()
        user_input = st.selectbox("Usuario", user_list)
        pass_input = st.text_input("Contraseña", type="password")
        
        if st.button("ENTRAR"):
            user_row = usuarios_df[usuarios_df['nombre'] == user_input].iloc[0]
            if str(user_row['clave']) == pass_input:
                st.session_state.update({
                    'logueado': True,
                    'user': user_input,
                    'rol': user_row['rol']
                })
                st.rerun()
            else:
                st.error("❌ Contraseña incorrecta")
    else:
        st.error("No se pudo conectar con la base de datos de usuarios.")
    st.stop()

# --- INTERFAZ PRINCIPAL ---
st.sidebar.title(f"Bienvenido, {st.session_state['user']}")
st.sidebar.write(f"Rol: {st.session_state['rol']}")

# Menu dinámico
menu = ["Nueva Venta", "Ver Ventas"]
if st.session_state['rol'] == 'admin':
    menu.append("Gestión de Empleados")

choice = st.sidebar.radio("Menú", menu)

if st.sidebar.button("Cerrar Sesión"):
    st.session_state['logueado'] = False
    st.rerun()

# --- SECCIÓN: NUEVA VENTA ---
if choice == "Nueva Venta":
    st.header("📝 Registrar Orden de Servicio")
    
    # Usamos un contador para limpiar el formulario después de guardar
    if 'form_id' not in st.session_state: st.session_state['form_id'] = 0
    fid = str(st.session_state['form_id'])

    with st.form("venta_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            n_orden = st.text_input("N° de Orden", key="ord"+fid)
            cliente = st.text_input("Nombre del Cliente", key="cli"+fid)
            nit = st.text_input("NIT / CC", key="nit"+fid)
            celular = st.text_input("Celular", key="cel"+fid)
            correo = st.text_input("Correo Electrónico", key="cor"+fid)
        
        with col2:
            descripcion = st.text_area("Descripción del Trabajo", key="des"+fid)
            total = st.number_input("Valor Total ($)", min_value=0, key="tot"+fid)
            abono = st.number_input("Abono Inicial ($)", min_value=0, key="abo"+fid)
            metodo = st.selectbox("Método de Pago", ["EFECTIVO", "NEQUI", "DAVIPLATA", "TRANSFERENCIA"], key="met"+fid)
            factura = st.radio("¿Requiere Factura?", ["SÍ", "NO"], horizontal=True, key="fac"+fid)
            estado = st.selectbox("Estado Inicial", ["EN PROCESO", "TERMINADO", "PAGADO"], key="est"+fid)

        submit = st.form_submit_button("💾 GUARDAR ORDEN")

        if submit:
            if not n_orden or not cliente:
                st.warning("⚠️ El N° de Orden y el Cliente son obligatorios.")
            else:
                payload = {
                    "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "n_orden": n_orden,
                    "descripcion": descripcion,
                    "total": total,
                    "abono": abono,
                    "saldo": total - abono,
                    "metodo_pago": metodo,
                    "estado": estado,
                    "empleado": st.session_state['user'],
                    "cliente": cliente,
                    "nit": nit,
                    "celular": celular,
                    "correo": correo,
                    "factura": factura
                }
                
                try:
                    response = requests.post(URL_SCRIPT, json=payload)
                    if response.status_code == 200:
                        st.success(f"✅ Orden {n_orden} guardada en Google Sheets")
                        st.balloons()
                        st.session_state['form_id'] += 1 # Esto limpia el form
                    else:
                        st.error("Error al conectar con Google. Revisa la URL del Script.")
                except Exception as e:
                    st.error(f"Error: {e}")

# --- SECCIÓN: VER VENTAS ---
elif choice == "Ver Ventas":
    st.header("📋 Historial de Ventas")
    df_ventas = leer_datos("ventas")
    
    if not df_ventas.empty:
        # Filtro: si no es admin, solo ve sus ventas
        if st.session_state['rol'] != 'admin':
            df_ventas = df_ventas[df_ventas['empleado'] == st.session_state['user']]
            
        search = st.text_input("🔍 Buscar por Cliente, NIT o N° Orden")
        if search:
            df_ventas = df_ventas[
                df_ventas['cliente'].str.contains(search, case=False, na=False) |
                df_ventas['n_orden'].astype(str).str.contains(search, na=False) |
                df_ventas['nit'].astype(str).str.contains(search, na=False)
            ]
        
        st.dataframe(df_ventas, use_container_width=True, hide_index=True)
    else:
        st.info("No hay ventas registradas aún.")

# --- SECCIÓN: EMPLEADOS ---
elif choice == "Gestión de Empleados":
    st.header("👥 Gestión de Usuarios")
    st.write("Datos actuales en la nube:")
    st.dataframe(usuarios_df, use_container_width=True, hide_index=True)
    st.info("Para agregar o quitar empleados, edita la pestaña 'usuarios' en tu Google Sheets.")
