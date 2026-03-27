import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import io

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Gestión Negocio Pro", layout="wide")
st.markdown("""<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;} .stDeployButton {display:none;}</style>""", unsafe_allow_html=True)

# ASEGÚRATE DE QUE ESTOS DATOS SEAN CORRECTOS
SHEET_ID = "1UGxbXTQhXKJ-JmKxpzglccDJrZgpCsTDflKO9N8RMTc"
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbyqx3mQopxUsMjokkhejP1newA3Gv-0OySPGFLhgGNlG6wgRPSieC3wlWO8QawQ6DRQXg/exec"

# 1. EVITA EL KEYERROR DE LA ÚLTIMA IMAGEN
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False
if 'usuario' not in st.session_state:
    st.session_state['usuario'] = ""
if 'rol' not in st.session_state:
    st.session_state['rol'] = ""

def leer_datos(pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={pestana}"
        res = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(res.text))
        
        # 2. SOLUCIÓN A COLUMNAS PEGADAS: Renombrar por posición
        if pestana == "usuarios":
            # Forzamos que las primeras 3 columnas sean nombre, clave, rol
            nuevas_cols = ['nombre', 'clave', 'rol']
            df.columns = nuevas_cols + list(df.columns[len(nuevas_cols):])
        elif pestana == "ventas":
            nuevas_cols = ['fecha', 'n_orden', 'descripcion', 'total', 'abono', 'saldo', 'metodo_pago', 'estado', 'empleado', 'cliente', 'nit', 'celular', 'correo', 'factura']
            df.columns = nuevas_cols + list(df.columns[len(nuevas_cols):])

        # Limpiamos todos los datos de espacios y basura
        df = df.applymap(lambda x: str(x).strip() if pd.notnull(x) else x)
        
        # Filtramos si la primera fila es igual al encabezado
        df = df[df['nombre'].str.lower() != 'nombre']
        return df
    except:
        return pd.DataFrame()

def enviar_google(payload):
    try:
        res = requests.post(URL_SCRIPT, json=payload, timeout=15)
        return res.status_code == 200
    except:
        return False

# --- LOGIN ---
df_users_db = leer_datos("usuarios")

if not st.session_state['autenticado']:
    st.title("🔐 Acceso al Sistema")
    if not df_users_db.empty:
        # Filtramos nombres válidos para el selector
        u_list = [u for u in df_users_db['nombre'].unique().tolist() if str(u).lower() != 'nan' and u != '']
        
        if u_list:
            u_input = st.selectbox("Usuario", u_list)
            p_input = st.text_input("Contraseña", type="password")
            
            if st.button("INGRESAR"):
                # Buscamos al usuario en la tabla
                user_match = df_users_db[df_users_db['nombre'] == u_input]
                if not user_match.empty:
                    user_data = user_match.iloc[0]
                    if str(user_data['clave']) == str(p_input):
                        st.session_state['autenticado'] = True
                        st.session_state['usuario'] = u_input
                        st.session_state['rol'] = str(user_data['rol']).lower()
                        st.rerun()
                    else:
                        st.error("Contraseña incorrecta")
        else:
            st.warning("No se encontraron usuarios. Revisa el Excel.")
    else:
        st.error("Error al conectar con la base de datos.")
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
        st.subheader("Registrar nuevo usuario")
        n_nom = st.text_input("Nombre Completo")
        n_cla = st.text_input("Contraseña")
        n_rol = st.selectbox("Rol", ["empleado", "admin"])
        if st.button("Registrar Empleado"):
            payload = {"accion": "insertar", "tipo_registro": "usuarios", "nombre": n_nom, "clave": n_cla, "rol": n_rol}
            if enviar_google(payload): 
                st.success("Empleado registrado")
                st.rerun()
            
    with t2:
        st.subheader("Editar datos de empleado")
        df_u = leer_datos("usuarios")
        if not df_u.empty:
            u_sel = st.selectbox("Seleccione el usuario", df_u['nombre'].tolist())
            user_to_edit = df_u[df_u['nombre'] == u_sel].iloc[0]
            edit_clave = st.text_input("Nueva Contraseña", value=str(user_to_edit['clave']))
            edit_rol = st.selectbox("Nuevo Rol", ["empleado", "admin"], index=0 if user_to_edit['rol'] == "empleado" else 1)
            
            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                if st.button("💾 Guardar Cambios"):
                    payload = {"accion": "actualizar", "tipo_registro": "usuarios", "id_busqueda": u_sel, "clave": edit_clave, "rol": edit_rol}
                    if enviar_google(payload):
                        st.success("Actualizado")
                        st.rerun()
            with c_btn2:
                if st.button("🗑️ Eliminar Empleado"):
                    if u_sel != "Administrador":
                        payload = {"accion": "eliminar", "tipo_registro": "usuarios", "id_busqueda": u_sel}
                        if enviar_google(payload):
                            st.warning("Eliminado")
                            st.rerun()
                    else: st.error("No puedes eliminar al Admin principal")

# --- SECCIÓN: VENTAS ---
elif opcion == "Ventas":
    st.title("🚀 Gestión de Ventas")
    # ... (El resto de tu código de ventas se mantiene igual)
    st.info("Sección de ventas cargada correctamente.")
