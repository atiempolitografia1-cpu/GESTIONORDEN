import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import io
import hashlib

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Gestión Negocio Pro", layout="wide")

st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stDeployButton {display:none;}
.block-container {padding-top: 1rem;}
button {border-radius: 10px !important;}
</style>
""", unsafe_allow_html=True)

SHEET_ID = "1UGxbXTQhXKJ-JmKxpzglccDJrZgpCsTDflKO9N8RMTc"
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbwefjYpHKmQNY6BY9-DXWAxk2GNN6VVeiVDxzr0xV-3Z7Ab9QLwkLulFK5d60rqQCVSSA/exec"

# --- 🔐 ENCRIPTAR ---
def encriptar_clave(clave):
    return hashlib.sha256(clave.encode()).hexdigest()

# --- ENVÍO ---
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

# --- LECTURA CON CACHE ---
@st.cache_data(ttl=10)
def leer_datos(pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={pestana}&t={datetime.now().microsecond}"
        res = requests.get(url, timeout=10)
        df = pd.read_csv(io.StringIO(res.text), dtype=str).fillna('')

        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()

        if df.empty:
            return pd.DataFrame(columns=['nombre', 'clave', 'rol']) if pestana == "usuarios" else pd.DataFrame()

        if pestana == "usuarios":
            df.columns = ['nombre', 'clave', 'rol'] + list(df.columns[3:])
        elif pestana == "ventas":
            cols_v = ['fecha', 'n_orden', 'descripcion', 'total', 'abono', 'saldo', 'metodo_pago', 'estado', 'empleado', 'cliente', 'nit', 'celular', 'correo', 'factura', 'historial_pagos']
            df = df.iloc[:, :len(cols_v)]
            df.columns = cols_v

        return df
    except Exception as e:
        st.error(f"Error leyendo {pestana}: {e}")
        return pd.DataFrame()

# --- LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

df_users_db = leer_datos("usuarios")

if not st.session_state['autenticado']:
    st.title("🔐 Acceso al Sistema")

    u_list = [u for u in df_users_db['nombre'].unique().tolist() if u != ""]
    u_input = st.selectbox("Usuario", u_list)
    p_input = st.text_input("Contraseña", type="password")

    if st.button("INGRESAR", use_container_width=True):
        match = df_users_db[df_users_db['nombre'] == u_input]

        if not match.empty:
            clave_guardada = str(match.iloc[0]['clave']).strip()

            # Permite login con claves viejas Y nuevas
            if clave_guardada == p_input or clave_guardada == encriptar_clave(p_input):
                st.session_state.update({
                    "autenticado": True,
                    "usuario": u_input,
                    "rol": str(match.iloc[0]['rol']).lower()
                })
                st.rerun()
        else:
            st.error("❌ Datos incorrectos")

    st.stop()

# --- MENÚ ---
menu = ["Ventas", "Gestión de Empleados"] if st.session_state['rol'] == 'admin' else ["Ventas"]
opcion = st.sidebar.radio("Ir a:", menu)

if st.sidebar.button("Cerrar Sesión"):
    st.session_state['autenticado'] = False
    st.rerun()

# --- EMPLEADOS ---
if opcion == "Gestión de Empleados":
    st.title("👥 Gestión de Personal")

    t1, t2 = st.tabs(["➕ Nuevo Empleado", "⚙️ Modificar / Eliminar"])

    with t1:
        n_nom = st.text_input("Nombre Completo")
        n_cla = st.text_input("Contraseña")
        n_rol = st.selectbox("Rol", ["empleado", "admin"])

        if st.button("Registrar", use_container_width=True):
            payload = {
                "accion": "insertar",
                "tipo_registro": "usuarios",
                "nombre": n_nom,
                "clave": encriptar_clave(n_cla),
                "rol": n_rol
            }
            if enviar_google(payload):
                st.success("Registrado")
                st.rerun()

# --- VENTAS ---
elif opcion == "Ventas":
    st.title("🚀 Gestión de Ventas")
    df_v = leer_datos("ventas")

    # --- DASHBOARD ---
    if not df_v.empty:
        total = pd.to_numeric(df_v['total'], errors='coerce').sum()
        abonado = pd.to_numeric(df_v['abono'], errors='coerce').sum()

        c1, c2, c3 = st.columns(3)
        c1.metric("💰 Total Ventas", f"$ {total:,.0f}")
        c2.metric("📥 Ingresos", f"$ {abonado:,.0f}")
        c3.metric("⏳ Pendiente", f"$ {total-abonado:,.0f}")

        st.subheader("🏆 Ranking empleados")
        ranking = df_v.groupby('empleado')['total'].sum().sort_values(ascending=False)
        st.dataframe(ranking)

    # --- REGISTRO ---
    if 'limp_v' not in st.session_state:
        st.session_state['limp_v'] = 0

    vs = str(st.session_state['limp_v'])

    v_ord = st.text_input("N° Orden", key="o"+vs)
    v_cli = st.text_input("Cliente", key="cl"+vs)
    v_tot = st.number_input("Total", key="t"+vs, min_value=0.0)
    v_abo = st.number_input("Abono", key="a"+vs, min_value=0.0)

    if st.button("💾 Guardar Venta", use_container_width=True):
        if v_ord in df_v['n_orden'].values:
            st.error("⚠️ Orden ya existe")
        else:
            payload = {
                "accion": "insertar",
                "tipo_registro": "ventas",
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "n_orden": v_ord,
                "descripcion": "",
                "total": v_tot,
                "abono": v_abo,
                "saldo": v_tot - v_abo,
                "metodo_pago": "EFECTIVO",
                "estado": "EN PROCESO",
                "empleado": st.session_state['usuario'],
                "cliente": v_cli,
                "nit": "",
                "celular": "",
                "correo": "",
                "factura": "NO",
                "historial_pagos": ""
            }

            if enviar_google(payload):
                st.success("Venta guardada")
                st.rerun()

    # --- EXPORTAR ---
    if not df_v.empty:
        csv = df_v.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar ventas", csv, "ventas.csv")
