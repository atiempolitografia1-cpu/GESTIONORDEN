import streamlit as st
import pandas as pd
from datetime import datetime, timedelta # Agregamos timedelta aquí
import requests
import io
import re
from fpdf import FPDF

# --- 1. CONFIGURACIÓN Y ESTILOS ---
st.set_page_config(page_title="Gestión Negocio Pro", layout="centered", initial_sidebar_state="expanded")

# VARIABLE GLOBAL PARA FECHA COLOMBIA (Soluciona el error de las 7:00 PM)
fecha_hoy_col = (datetime.now() - timedelta(hours=5)).date()

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
URL_SCRIPT = "https://script.google.com/macros/s/AKfycbzsd0qJS2AZP0TYPemtqEFX-uRni7oojNQDw69OtgVQXDvfWr_MTlwyv4KEDFsIXOdL7w/exec"

# --- 2. FUNCIONES DE FORMATO Y DATOS ---
def formato_pesos(valor):
    try:
        val = float(valor)
        return f"$ {val:,.0f}".replace(",", ".")
    except:
        return "$ 0"

def generar_recibo_pdf(datos):
    pdf = FPDF(orientation='P', unit='mm', format='A5')
    pdf.add_page()
    
    # --- Encabezado ---
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "RECIBO DE CAJA", ln=True, align="C")
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 5, "LITOGRAFIA ATIEMPO SAS", ln=True, align="C")
    pdf.ln(5)
    
    # --- Datos del Cliente ---
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 7, f"Comprobante: RC-{datos['n_orden']}", ln=True)
    pdf.cell(0, 7, f"Cliente: {datos['cliente']}", ln=True)
    pdf.cell(0, 7, f"Fecha: {datos['fecha']}", ln=True)
    pdf.ln(5)
    
    # --- Tabla de Conceptos (CON DESCRIPCIÓN) ---
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(90, 8, "CONCEPTO / DESCRIPCIÓN", 1, 0, "C", True)
    pdf.cell(35, 8, "VALOR", 1, 1, "C", True)
    
    pdf.set_font("Arial", "", 9)
    # Combinamos el texto del abono con la descripción del trabajo
    texto_concepto = f"Abono a orden N° {datos['n_orden']}\nTrabajo: {datos.get('descripcion', 'N/A')}"
    
    # Usamos multi_cell para que si la descripción es larga, salte de línea automáticamente
    x_actual = pdf.get_x()
    y_actual = pdf.get_y()
    pdf.multi_cell(90, 7, texto_concepto, 1, "L")
    
    # Colocamos el valor al lado de la celda de descripción
    pdf.set_xy(x_actual + 90, y_actual)
    # Calculamos la altura que tomó la multi_cell para que el cuadro del valor coincida
    altura_celda = pdf.get_y() - y_actual if pdf.get_y() - y_actual > 10 else 10
    pdf.set_xy(x_actual + 90, y_actual)
    pdf.cell(35, altura_celda, f"{formato_pesos(datos['abono_hoy'])}", 1, 1, "R")
    
    # --- Historial de Pagos ---
    if 'historial_pagos' in datos and datos['historial_pagos']:
        pdf.ln(3)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(0, 5, "Historial de abonos:", ln=True)
        pdf.set_font("Arial", "I", 8)
        pdf.multi_cell(0, 5, datos['historial_pagos'].replace("|", "\n"), align="L")
    
    # --- Resumen Financiero ---
    pdf.ln(5)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(90, 7, "VALOR TOTAL DE LA ORDEN:", 0, 0, "R")
    pdf.cell(35, 7, f"{formato_pesos(datos['total'])}", 0, 1, "R")
    
    pdf.cell(90, 7, "TOTAL ABONADO:", 0, 0, "R")
    pdf.cell(35, 7, f"{formato_pesos(datos['total_abonado'])}", 0, 1, "R")
    
    pdf.set_font("Arial", "B", 11)
    pdf.cell(90, 10, "SALDO PENDIENTE:", 0, 0, "R")
    pdf.cell(35, 10, f"{formato_pesos(datos['saldo_pendiente'])}", 0, 1, "R")
    
    pdf.ln(10)
    pdf.set_font("Arial", "I", 8)
    pdf.multi_cell(0, 5, "Soporte interno de pago - Atiempo litografia SAS ", align="C")
    pdf.ln(4)
    pdf.set_font("Arial", "I", 8)
    pdf.multi_cell(0, 5, "ESTE DOCUMENTO NO REMPLAZA LA FACTURA DE VENTA ", align="C")
    
    return bytes(pdf.output())
        

def a_numero(valor):
    try:
        if not valor: return 0.0
        s = re.sub(r'[^\d,]', '', str(valor)).replace(',', '.')
        return float(s) if s else 0.0
    except: return 0.0

def leer_datos(pestana):
    try:
        # Usamos microsegundos para evitar el caché de Google
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
            df['fecha_dt'] = pd.to_datetime(df['fecha'], dayfirst=True, errors='coerce')
            df['solo_dia'] = df['fecha_dt'].dt.date
            
        elif pestana == "usuarios":
            df.columns = ['nombre', 'clave', 'rol'] + list(df.columns[3:])
            
        elif pestana == "caja":
            cols_caja = ['fecha', 'n_orden', 'valor', 'metodo', 'empleado']
            df = df.iloc[:, :len(cols_caja)]
            df.columns = cols_caja
            
            # Aseguramos que el valor sea numérico
            df['valor_n'] = df['valor'].apply(a_numero)
            
            # Convertimos la fecha. IMPORTANTE: dayfirst=True para formato DD/MM/YYYY
            df['fecha_dt'] = pd.to_datetime(df['fecha'], dayfirst=True, errors='coerce')
            
            # Eliminamos filas con fechas rotas
            df = df.dropna(subset=['fecha_dt'])
            
            # FORZAMOS el formato de fecha pura (sin horas) para comparar con date_input
            df['solo_dia'] = df['fecha_dt'].dt.date

        
        elif pestana == "horarios":
            if not df.empty:
                df = df.iloc[:, :4] # Forzamos solo las 4 columnas necesarias
                df.columns = ['fecha', 'empleado', 'evento', 'hora']
            else:
                return pd.DataFrame(columns=['fecha', 'empleado', 'evento', 'hora'])
            
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
    # 1. Colocamos el logo al principio de la barra lateral
    st.image("logo atiempo.png", use_container_width=True)
    
    # 2. Debajo aparecerá el nombre del usuario
    st.markdown(f"### 👤 {st.session_state['usuario'].upper()}")
    
    menu = ["Ventas", "Gestión de Empleados"] if st.session_state['rol'] == 'admin' else ["Ventas"]
    opcion = st.radio("Menú:", menu)
    
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state['autenticado'] = False
        st.rerun()

if opcion == "Ventas":
    st.title("🚀 Gestión de Ventas")
    df_v_comp = leer_datos("ventas")
    
    # ... resto de tu código de lógica de ventas
    if st.session_state['rol'] == 'admin':
        df_v = df_v_comp.copy()
    else:
        df_v = df_v_comp[df_v_comp['empleado'] == st.session_state['usuario']].copy()
    
    t_labels = ["📝 Registrar", "✏️ Editar / Abonar"]
    if st.session_state['rol'] == 'admin': 
        t_labels.append("📊 Reportes Avanzados")
        t_labels.append("⏰ Horarios") 
        
    tabs = st.tabs(t_labels)
    
    # --- PESTAÑA REGISTRAR ---
    with tabs[0]:
        v = str(st.session_state.get('limp', 0)) 
        st.subheader("📝 Registrar Nueva Orden")
        c_f1, c_f2 = st.columns([1, 2])
        fecha_manual = c_f1.date_input("📅 Fecha de la Orden", value=fecha_hoy_col)
        
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
                historial_inicial = f"{formato_pesos(abo)} ({pag}) {fecha_str}"
                
                p_venta = {
                    "accion": "insertar", "tipo_registro": "ventas", "fecha": fecha_str,
                    "n_orden": str(ord), "descripcion": str(desc), "total": float(tot),
                    "abono": float(abo), "saldo": float(tot - abo), "metodo_pago": str(pag),
                    "estado": str(est), "empleado": str(st.session_state['usuario']),
                    "cliente": str(cli), "nit": str(nit), "celular": str(cel),
                    "correo": str(cor), "factura": str(fac), "historial_pagos": historial_inicial
                }
                p_caja = {
                    "accion": "insertar", "tipo_registro": "caja", "fecha": fecha_str,
                    "n_orden": str(ord), "valor": float(abo), "metodo": str(pag),
                    "empleado": str(st.session_state['usuario'])
                }
                
                if enviar_google(p_venta):
                    if abo > 0: enviar_google(p_caja)
                    
                    # --- GUARDAMOS DATOS PARA EL RECIBO ---
                    st.session_state['pdf_registro'] = {
                        "n_orden": str(ord),
                        "cliente": str(cli),
                        "nit": str(nit),
                        "fecha": fecha_str,
                        "abono_hoy": float(abo),
                        "total": float(tot),
                        "total_abonado": float(abo),
                        "saldo_pendiente": float(tot - abo),
                        "descripcion": desc,
                        "historial_pagos": historial_inicial
                    }
                    
                    st.success(f"✅ Orden {ord} registrada")
                    st.session_state['limp'] = st.session_state.get('limp', 0) + 1
                    st.rerun()

        # --- BOTÓN DE DESCARGA (FUERA DEL PROCESO DE GUARDADO) ---
        if 'pdf_registro' in st.session_state:
            dat = st.session_state['pdf_registro']
            st.write("---")
            st.info(f"📄 Recibo de entrada disponible para la orden {dat['n_orden']}")
            
            # Generamos los bytes del PDF con la función mejorada (Paso 3 anterior)
            try:
                archivo_pdf = generar_recibo_pdf(dat)
                
                c_desc, c_limp = st.columns([3, 1])
                
                c_desc.download_button(
                    label=f"📥 DESCARGAR RECIBO {dat['n_orden']}",
                    data=archivo_pdf,
                    file_name=f"Recibo_Entrada_{dat['n_orden']}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary"
                )
                
                if c_limp.button("✖️ Finalizar", key="limp_reg"):
                    del st.session_state['pdf_registro']
                    st.rerun()
            except Exception as e:
                st.error(f"Error al generar el recibo: {e}")

    # --- PESTAÑA EDITAR / ABONAR ---
    with tabs[1]:
        if not df_v.empty:
            sel = st.selectbox("Seleccione la Orden a editar:", ["Seleccionar..."] + df_v['n_orden'].tolist())
            if sel != "Seleccionar...":
                val = df_v[df_v['n_orden'] == sel].iloc[0]
                st.info(f"Orden: **{sel}** | Registrada por: **{val['empleado']}**")
                
                # 1. EL FORMULARIO (Solo para capturar datos y actualizar)
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
                    fecha_abono_manual = c_fecha_edit.date_input("📅 Fecha de este abono", value=fecha_hoy_col)
                    e_met = c_met_edit.selectbox("Medio del nuevo abono", ["EFECTIVO", "NEQUI", "BANCOLOMBIA", "DAVIPLATA"])
                    
                    nuevo_abono_total = val['abono_n'] + e_nab
                    nuevo_saldo = e_tot - nuevo_abono_total
                    st.warning(f"Saldo actual: {formato_pesos(val['saldo_n'])} | **Nuevo Saldo: {formato_pesos(nuevo_saldo)}**")
                    
                    estados_list = ["EN PROCESO", "TERMINADO", "ENTREGADO"]
                    idx_est = estados_list.index(val['estado']) if val['estado'] in estados_list else 0
                    e_est = st.selectbox("Estado de la Orden", estados_list, index=idx_est)
                    
                    submit = st.form_submit_button("💾 ACTUALIZAR ORDEN", use_container_width=True)

                    if submit:
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
                            
                            # --- ESTO ES LO QUE CAMBIA: GUARDAR TODO EL HISTORIAL ---
                            st.session_state['pdf_edicion'] = {
                                "n_orden": sel,
                                "cliente": e_cli,
                                "nit": e_nit,
                                "fecha": f_abono_str,
                                "abono_hoy": e_nab,
                                "total": e_tot,
                                "total_abonado": nuevo_abono_total,
                                "saldo_pendiente": nuevo_saldo,
                                "descripcion": e_desc,
                                "historial_pagos": h_pago  # <--- Pasamos el historial acumulado
                            }
                            
                            st.success(f"✅ Orden {sel} actualizada.")
                            st.rerun()

                # --- BOTÓN DE DESCARGA (FUERA DEL FORMULARIO) ---
                if 'pdf_edicion' in st.session_state:
                    dat = st.session_state['pdf_edicion']
                    st.divider()
                    st.info(f"📄 Recibo de Abono disponible: {dat['n_orden']}")
                    
                    try:
                        archivo_pdf = generar_recibo_pdf(dat)
                        
                        col_d, col_l = st.columns([3, 1])
                        col_d.download_button(
                            label=f"📥 DESCARGAR RECIBO DE ABONO",
                            data=archivo_pdf,
                            file_name=f"Recibo_Abono_{dat['n_orden']}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            type="primary"
                        )
                        
                        if col_l.button("✖️ Finalizar", key="limp_edit"):
                            del st.session_state['pdf_edicion']
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error al generar el recibo: {e}")

                # 3. ZONA DE PELIGRO (TAMBIÉN FUERA DEL FORM)
                if st.session_state.get('rol') == 'admin':
                    st.divider()
                    with st.expander("🗑️ Zona de Peligro"):
                        if st.button(f"ELIMINAR ORDEN {sel}", type="primary", use_container_width=True):
                            if enviar_google({"accion": "eliminar", "tipo_registro": "ventas", "id_busqueda": sel}):
                                st.success(f"✅ Orden {sel} eliminada.")
                                st.rerun()
                                
    # --- PESTAÑA REPORTES (ADMIN) ---
    if st.session_state['rol'] == 'admin':
        with tabs[2]:
            st.subheader("🧐 Auditoría de Ventas, Caja y Cartera")
            df_caja = leer_datos("caja")
            
            c1, c2, c3 = st.columns(3)
            # CAMBIO: Usamos fecha_hoy_col
            f_ini = c1.date_input("📅 Desde", value=fecha_hoy_col, key="f_ini_rep")
            f_fin = c2.date_input("📅 Hasta", value=fecha_hoy_col, key="f_fin_rep")
            lista_emp = ["TODOS"] + df_users_db['nombre'].tolist()
            e_sel = c3.selectbox("👤 Empleado", lista_emp)

            df_v_dia = df_v_comp[(df_v_comp['solo_dia'] >= f_ini) & (df_v_comp['solo_dia'] <= f_fin)]
            if e_sel != "TODOS":
                df_v_dia = df_v_dia[df_v_dia['empleado'] == e_sel]
            
            cartera_del_periodo = df_v_dia['saldo_n'].sum()
            st.warning(f"### 🚩 Cartera del Periodo Seleccionado: {formato_pesos(cartera_del_periodo)}")
            
            st.markdown("---")
            st.markdown("### 💰 Cuadre de Caja (Dinero Ingresado)")
            
            if not df_caja.empty:
                df_c_fil = df_caja[(df_caja['solo_dia'] >= f_ini) & (df_caja['solo_dia'] <= f_fin)]
                if e_sel != "TODOS": 
                    df_c_fil = df_c_fil[df_c_fil['empleado'] == e_sel]
                
                g_efe, g_neq, g_ban, g_dav = 0.0, 0.0, 0.0, 0.0
                for emp in df_c_fil['empleado'].unique():
                    with st.expander(f"📥 Ver Caja de: {emp.upper()}", expanded=True):
                        df_emp = df_c_fil[df_c_fil['empleado'] == emp]
                        col1, col2, col3, col4 = st.columns(4)
                        # Forzamos la columna a String (Texto) antes de limpiar y comparar
                        s_efe = df_emp[df_emp['metodo'].astype(str).str.upper().str.strip() == "EFECTIVO"]['valor_n'].sum()
                        s_neq = df_emp[df_emp['metodo'].astype(str).str.upper().str.strip() == "NEQUI"]['valor_n'].sum()
                        s_ban = df_emp[df_emp['metodo'].astype(str).str.upper().str.strip() == "BANCOLOMBIA"]['valor_n'].sum()
                        s_dav = df_emp[df_emp['metodo'].astype(str).str.upper().str.strip() == "DAVIPLATA"]['valor_n'].sum()
                        
                        col1.metric("💵 EFECTIVO", formato_pesos(s_efe))
                        col2.metric("📱 NEQUI", formato_pesos(s_neq))
                        col3.metric("🏦 BANCO", formato_pesos(s_ban))
                        col4.metric("📲 DAVIPLATA", formato_pesos(s_dav))
                        g_efe += s_efe; g_neq += s_neq; g_ban += s_ban; g_dav += s_dav
                        st.write(f"**Total de {emp}:** {formato_pesos(df_emp['valor_n'].sum())}")

                if e_sel == "TODOS" and not df_c_fil.empty:
                    st.divider()
                    st.markdown("### 🏆 RESUMEN TOTAL DE TODA LA TIENDA")
                    m1, m2, m3, m4 = st.columns(4)
                    m1.info(f"**Total Efectivo**\n\n{formato_pesos(g_efe)}")
                    m2.info(f"**Total Nequi**\n\n{formato_pesos(g_neq)}")
                    m3.info(f"**Total Banco**\n\n{formato_pesos(g_ban)}")
                    m4.info(f"**Total Daviplata**\n\n{formato_pesos(g_dav)}")
                    st.success(f"## **RECAUDO TOTAL GLOBAL: {formato_pesos(g_efe + g_neq + g_ban + g_dav)}**")

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
                st.dataframe(df_final.sort_values('n_orden', ascending=False), use_container_width=True, hide_index=True)

    # --- PESTAÑA 4: GESTIÓN DE ALMUERZOS (SOLO ADMIN) ---
    if st.session_state['rol'] == 'admin':
        with tabs[3]: 
            st.subheader("⏰ Control de Horarios de Almuerzo")
            with st.container(border=True):
                col1, col2 = st.columns(2)
                emp_h = col1.selectbox("Seleccionar Empleado", df_users_db['nombre'].tolist(), key="sel_emp_almuerzo")
                tipo_evento = col2.selectbox("Acción", ["Salida a Almuerzo 🍕", "Regreso de Almuerzo ✅"])
                
                if st.button("🚀 Registrar Hora Actual", use_container_width=True):
                    ahora_local = datetime.now() - timedelta(hours=5) 
                    datos_hora = {
                        "accion": "guardar_almuerzo",
                        "fecha": ahora_local.strftime("%d/%m/%Y"),
                        "empleado": emp_h,
                        "evento": tipo_evento,
                        "hora": ahora_local.strftime("%I:%M:%S %p")
                    }
                    if enviar_google(datos_hora):
                        st.success(f"✅ Registrado!")
                        st.rerun() 

            st.divider()
            st.markdown("### 📅 Registros de Hoy")
            df_h_raw = leer_datos("horarios")
            if not df_h_raw.empty:
                hoy_str = fecha_hoy_col.strftime("%d/%m/%Y")
                df_h_hoy = df_h_raw[df_h_raw['fecha'] == hoy_str].copy()
                
                if not df_h_hoy.empty:
                    event = st.dataframe(df_h_hoy[['empleado', 'evento', 'hora']], 
                                         use_container_width=True, on_select="rerun", selection_mode="single-row")
                    selection = event.get("selection", {}).get("rows", [])
                    if selection:
                        fila_data = df_h_hoy.iloc[selection[0]]
                        st.warning(f"¿Eliminar registro de **{fila_data['empleado']}**?")
                        if st.button("🗑️ Confirmar Eliminación", type="primary"):
                            if enviar_google({"accion": "eliminar_horario", "id_busqueda": fila_data['hora']}):
                                st.success("Eliminado"); st.rerun()
                else: st.info(f"Sin registros para hoy ({hoy_str})")

    # --- HISTORIAL GENERAL (Visible para todos bajo las pestañas) ---
    st.divider()
    st.subheader("📋 Historial de Órdenes")
    busq = st.text_input("🔍 Buscar Orden o Cliente:")
    df_h = df_v.copy()
    if busq:
        df_h = df_h[df_h['n_orden'].astype(str).str.contains(busq, case=False) | df_h['cliente'].astype(str).str.contains(busq, case=False)]
    st.dataframe(df_h[['fecha','n_orden','descripcion','cliente','total','abono','saldo','estado']].iloc[::-1], use_container_width=True, hide_index=True)

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
                if enviar_google({"accion": "insertar", "tipo_registro": "usuarios", "nombre": n_nom, "clave": n_cla, "rol": n_rol}):
                    st.success("Registrado"); st.rerun()
    
    with t2:
        if not df_u.empty:
            u_sel = st.selectbox("Seleccione Usuario:", df_u['nombre'].tolist())
            datos_u = df_u[df_u['nombre'] == u_sel].iloc[0]
            with st.form("edit_emp"):
                e_cla = st.text_input("Nueva Contraseña", value=datos_u['clave'])
                e_rol = st.selectbox("Rol", ["empleado", "admin"], index=0 if datos_u['rol'] == 'empleado' else 1)
                if st.form_submit_button("ACTUALIZAR DATOS"):
                    if enviar_google({"accion": "actualizar", "tipo_registro": "usuarios", "id_busqueda": u_sel, "clave": e_cla, "rol": e_rol}):
                        st.success("Actualizado"); st.rerun()
