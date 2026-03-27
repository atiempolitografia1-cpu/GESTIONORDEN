import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import io

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Gestión Litografía Pro", layout="wide")

# TUS CONEXIONES (YA CONFIGURADAS)
SHEET_ID = "1UGxbXTQhXKJ-JmKxpzglccDJrZgpCsTDflKO9N8RMTc"
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbxOEP-5jAU8RE76-5DsUp2iyn_zXr54kEXY0_H3Dw-BNqPSW5-1W_oGlr48W94o-RqLSA/exec"

def traer_datos(pestana):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={pestana}"
    res = requests.get(url)
    return pd.read_csv(io.StringIO(res.text))

# --- LOGIN (Ya funcionando) ---
df_usuarios = traer_datos("usuarios")
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.title("🔐 Acceso Sistema")
    u_log = st.selectbox("Usuario", df_usuarios['nombre'].tolist())
    p_log = st.text_input("Contraseña", type="password")
    if st.button("INGRESAR"):
        user_row = df_usuarios[df_usuarios['nombre'] == u_log].iloc[0]
        if str(user_row['clave']) == p_log:
            st.session_state.update({"autenticado": True, "usuario": u_log, "rol": user_row['rol']})
            st.rerun()
        else: st.error("Clave incorrecta")
    st.stop()

# --- INTERFAZ DE VENTAS ---
st.title("🚀 Gestión de Ventas e Inventario")
with st.form("nueva_orden", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        n_ord = st.text_input("N° Orden / Factura")
        v_cli = st.text_input("Nombre del Cliente")
        v_nit = st.text_input("NIT o Cédula")
    with col2:
        v_cel = st.text_input("Celular")
        v_cor = st.text_input("Correo")
        v_fac = st.radio("¿Factura?", ["SÍ", "NO"], horizontal=True)
    with col3:
        v_tot = st.number_input("Valor Total ($)", min_value=0.0)
        v_abo = st.number_input("Abono Inicial ($)", min_value=0.0)
        v_est = st.selectbox("Estado", ["EN PROCESO", "TERMINADO", "PAGADO"])
        v_pag = st.selectbox("Método de Pago", ["EFECTIVO", "NEQUI", "DAVIPLATA", "BANCOLOMBIA"])
    
    v_desc = st.text_area("Descripción del trabajo")
    
    if st.form_submit_button("💾 GUARDAR ORDEN"):
        # PAQUETE DE DATOS
        datos = {
            "fecha": datetime.now().strftime("%d/%m/%Y"),
            "n_orden": n_ord,
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
        
        # ENVÍO REAL AL EXCEL
        try:
            r = requests.post(URL_SCRIPT, json=datos)
            if r.status_code == 200:
                st.success(f"✅ ¡Orden {n_ord} guardada en Google Sheets!")
                st.balloons()
            else:
                st.error("Error en el puente de Google. Revisa la implementación del script.")
        except Exception as e:
            st.error(f"Error de conexión: {e}")

st.divider()
st.subheader("📊 Historial de Ventas")
st.dataframe(traer_datos("ventas"), use_container_width=True)
