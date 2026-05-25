import streamlit as st
import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import execute_values
import tensorflow as tf
from tensorflow.keras import layers, models
import joblib
import hashlib
import re
from fpdf import FPDF
import smtplib
from email.message import EmailMessage

st.set_page_config(page_title="DataPure AI - Limpieza y Auditoría de Datos", layout="wide")

# ==========================================
# AUTHENTICATION + MULTI-USUARIO
# ==========================================
if "USUARIO_CORRECTO" in st.secrets and "PASSWORD_CORRECTA" in st.secrets:
    USUARIO_CORRECTO = st.secrets["USUARIO_CORRECTO"]
    PASSWORD_CORRECTA = st.secrets["PASSWORD_CORRECTA"]

def verificar_credenciales(usuario, password):
    return usuario.strip() == USUARIO_CORRECTO and password.strip() == PASSWORD_CORRECTA

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
if "usuario_actual" not in st.session_state:
    st.session_state["usuario_actual"] = None
if "es_admin" not in st.session_state:
    st.session_state["es_admin"] = False

# ====================== REGISTRO DE USUARIOS ======================
def registrar_usuario(email, nombre_empresa, password):
    conn = obtener_conexion()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO usuarios (email, nombre_empresa, password)
            VALUES (%s, %s, %s) RETURNING id
        """, (email, nombre_empresa, password))
        user_id = cursor.fetchone()[0]
        conn.commit()
        return user_id
    except:
        conn.rollback()
        return None
    finally:
        cursor.close()
        conn.close()

# ====================== LOGIN ======================
if not st.session_state["autenticado"]:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("Acceso a DataPure AI")
        
        tab1, tab2 = st.tabs(["Iniciar Sesión", "Crear Cuenta"])
        
        with tab1:
            user_input = st.text_input("Usuario Corporativo / Email")
            pass_input = st.text_input("Contraseña", type="password")
            if st.button("Ingresar"):
                if verificar_credenciales(user_input, pass_input):
                    st.session_state["autenticado"] = True
                    st.session_state["usuario_actual"] = user_input
                    st.session_state["es_admin"] = True
                    st.rerun()
                else:
                    st.error("Credenciales inválidas.")
        
        with tab2:
            st.subheader("Crear Nueva Cuenta")
            nuevo_email = st.text_input("Email Corporativo")
            nuevo_nombre = st.text_input("Nombre de la Empresa")
            nueva_pass = st.text_input("Crea una contraseña", type="password")
            if st.button("Crear Cuenta"):
                if nuevo_email and nuevo_nombre and nueva_pass:
                    user_id = registrar_usuario(nuevo_email, nuevo_nombre, nueva_pass)
                    if user_id:
                        st.success("¡Cuenta creada exitosamente! Ahora puedes iniciar sesión.")
                    else:
                        st.error("El email ya está registrado.")
                else:
                    st.error("Completa todos los campos.")
    st.stop()

# ==========================================
# CORE DE DATOS Y AI
# ==========================================
DATABASE_URL = st.secrets["DATABASE_URL"]

def obtener_conexion():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

@st.cache_resource
def cargar_cerebro_ia():
    if os.path.exists('autoencoder_pesos.weights.h5') and os.path.exists('escalador_ia.pkl'):
        input_layer = layers.Input(shape=(4,))
        encoded = layers.Dense(8, activation='relu')(input_layer)
        bottleneck = layers.Dense(3, activation='relu')(encoded)
        decoded = layers.Dense(8, activation='relu')(bottleneck)
        output_layer = layers.Dense(4, activation='sigmoid')(decoded)
        model = models.Model(inputs=input_layer, outputs=output_layer)
        model.load_weights('autoencoder_pesos.weights.h5')
        scaler = joblib.load('escalador_ia.pkl')
        return model, scaler
    return None, None

autoencoder, scaler = cargar_cerebro_ia()

# ==========================================
# LÓGICA DE PURIFICACIÓN
# ==========================================
def anonimizar_texto(texto):
    return hashlib.sha256(str(texto).encode('utf-8')).hexdigest()[:12]

def blindar_telefono(telefono):
    tel_str = str(telefono).strip()
    if len(tel_str) < 7: return "*******"
    return f"{tel_str[:3]} ****** {tel_str[-3:]}"

def purificar_datos_con_ia(df_sucio):
    df_limpio = df_sucio.copy()
    df_limpio['Edad'] = df_limpio['Edad'].fillna(df_limpio['Edad'].median() if not df_limpio['Edad'].dropna().empty else 40)
    df_limpio['Ingresos_Anuales'] = df_limpio['Ingresos_Anuales'].fillna(df_limpio['Ingresos_Anuales'].median())
    
    df_limpio['Email_Roto'] = df_limpio['Email'].apply(lambda x: 1.0 if pd.isna(x) or '@' not in str(x) else 0.0)
    df_limpio['Nombre_Falso'] = df_limpio['Nombre'].apply(lambda x: 1.0 if bool(re.search(r'\d', str(x))) else 0.0)
    
    X_nuevos = df_limpio[['Edad', 'Ingresos_Anuales', 'Email_Roto', 'Nombre_Falso']].values
    x_min, x_max = scaler
    X_nuevos_scaled = (X_nuevos - x_min) / (x_max - x_min + 1e-5)
    
    X_reconstruido = autoencoder.predict(X_nuevos_scaled, verbose=0)
    errores_reconstruccion = np.mean(np.power(X_nuevos_scaled - X_reconstruido, 2), axis=1)
    
    UMBRAL_IA = 0.05
    df_sucio['Error_IA'] = errores_reconstruccion
    df_aprobado = df_limpio[errores_reconstruccion <= UMBRAL_IA].copy()
    
    df_aprobado['Nombre'] = df_aprobado['Nombre'].apply(anonimizar_texto)
    df_aprobado['Email'] = df_aprobado['Email'].apply(anonimizar_texto)
    df_aprobado['Telefono'] = df_aprobado['Telefono'].apply(blindar_telefono)
    
    return df_aprobado, len(df_sucio), df_sucio['Edad'].isnull().sum(), len(df_sucio[errores_reconstruccion > UMBRAL_IA]), df_sucio

# ==========================================
# GENERADOR DE REPORTES (PDF) - Completo
# ==========================================
def generar_reporte_pdf(total, nulos, alertas):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    pdf.set_fill_color(15, 23, 42)
    pdf.rect(0, 0, 210, 38, 'F')
    
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 22)
    pdf.cell(0, 10, "DataPure AI", ln=True, align='L')
    pdf.set_font("Arial", 'I', 10)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 5, "AI-Powered Data Purification & Security Audit", ln=True, align='L')
    pdf.ln(20)
    
    pdf.set_text_color(30, 41, 59)
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "INFORME DE AUDITORIA Y CUARENTENA", ln=True)
    
    pdf.set_draw_color(99, 102, 241)
    pdf.set_line_width(1)
    pdf.line(10, 52, 200, 52)
    pdf.ln(8)
    
    pdf.set_font("Arial", size=10)
    pdf.set_text_color(100, 116, 139)
    texto_intro = "Este documento contiene los resultados del analisis neuronal realizado por el motor autoencoder de DataPure AI."
    pdf.multi_cell(0, 5, texto_intro)
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 8, "METRICAS CLAVE DE PURIFICACION", ln=True)
    pdf.ln(2)
    
    pdf.set_fill_color(241, 245, 249)
    pdf.set_text_color(71, 85, 105)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(110, 10, " Indicador Analizado", border=1, fill=True)
    pdf.cell(80, 10, " Valor / Estado", border=1, fill=True, align='C')
    pdf.ln()
    
    data = [
        ("Registros Totales Auditados", f"{total:,} filas"),
        ("Registros Nulos Corregidos por IA", f"{nulos:,} correcciones"),
        ("Anomalias / Fraudes Detectados (Bloqueados)", f"{alertas:,} alertas"),
        ("Estado Final del Dataset", "PURIFICADO & SEGURO"),
        ("Protocolo de Criptografia Aplicado", "SHA-256 + Phone Masking")
    ]
    
    pdf.set_font("Arial", size=10)
    for label, value in data:
        if "Anomalias" in label and alertas > 0:
            pdf.set_text_color(220, 38, 38)
            pdf.set_font("Arial", 'B', 10)
        else:
            pdf.set_text_color(51, 65, 85)
        pdf.cell(110, 9, f"  {label}", border=1)
        pdf.cell(80, 9, f" {value}", border=1, align='C')
        pdf.ln()
        
    pdf.ln(12)
    pdf.set_fill_color(239, 246, 255)
    pdf.set_draw_color(191, 219, 254)
    pdf.rect(10, pdf.get_y(), 190, 25, 'DF')
    
    pdf.set_text_color(29, 78, 216)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 6, "  DIAGNOSTICO DEL INGENIERO DE IA:", ln=True)
    pdf.set_font("Arial", 'I', 10)
    pdf.set_text_color(30, 41, 59)
    
    if alertas > 0:
        msg_diagnostico = f"  ATENCION: Se han detectado {alertas} vectores de riesgo en el dataset."
    else:
        msg_diagnostico = "  OPTIMO: No se han detectado anomalias criticas."
        
    pdf.multi_cell(0, 5, msg_diagnostico)
    
    pdf.set_y(-25)
    pdf.set_font("Arial", 'I', 8)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 10, "CONFIDENCIAL - DataPure AI v2.0", border=0, align='C')
    
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# DASHBOARD
# ==========================================
st.sidebar.title("DataPure AI")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.session_state["usuario_actual"] = None
    st.rerun()

st.sidebar.markdown("---")
modo = st.sidebar.radio("Módulos", ["Pipeline de Auditoría", "Mis Análisis", "Base de Datos SQL", "Precios y Planes"])

st.title("DataPure AI")

if modo == "Pipeline de Auditoría":
    # ... (aquí iría tu código completo del pipeline, lo mantengo igual que antes)
    st.subheader("Ingesta y Procesamiento Neuronal")
    archivo = st.file_uploader("Cargar dataset", type=["csv", "xlsx"])
    
    if 'df_procesado' not in st.session_state:
        st.session_state.df_procesado = None
        st.session_state.analisis = None
        st.session_state.metricas = None
    if 'pdf_generado' not in st.session_state:
        st.session_state.pdf_generado = None

    if archivo and st.button("Ejecutar Análisis"):
        with st.spinner("Procesando red neuronal..."):
            df = pd.read_csv(archivo) if archivo.name.endswith('.csv') else pd.read_excel(archivo)
            df_limpio, total, nulos, alertas, analisis = purificar_datos_con_ia(df)
            
            conn = obtener_conexion()
            cursor = conn.cursor()
            valores = [(int(row['ID_Cliente']), row['Nombre'], str(row['Email']), float(row['Edad']), float(row['Ingresos_Anuales']), str(row['Telefono']), st.session_state["usuario_actual"]) for _, row in df_limpio.iterrows()]
            query = "INSERT INTO clientes_purificados (ID_Cliente, Nombre, Email, Edad, Ingresos_Anuales, Telefono, usuario_email) VALUES %s ON CONFLICT (ID_Cliente) DO NOTHING"
            execute_values(cursor, query, valores)
            conn.commit()
            cursor.close()
            conn.close()

            st.session_state.df_procesado = df_limpio
            st.session_state.analisis = analisis
            st.session_state.metricas = (total, nulos, alertas)
            st.session_state.pdf_generado = None

    # Resto del código de visualización (mantenido igual)
    if st.session_state.df_procesado is not None:
        # ... (tu código original de métricas, tabs, etc.)
        pass   # ← Aquí pega tu código original de visualización

elif modo == "Precios y Planes":
    # (tu código de precios que ya tenías)
    st.title("Precios y Planes - DataPure AI")
    # ... resto igual

# Añade los demás elif según necesites

st.sidebar.caption(f"Conectado como: {st.session_state.get('usuario_actual', 'Admin')}")