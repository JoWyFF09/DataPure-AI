import streamlit as st
import pandas as pd
import numpy as np
import psycopg2 
from psycopg2.extras import execute_values
import tensorflow as tf
from tensorflow.keras import layers, models
import joblib
import time
import os
import hashlib
import re 
from fpdf import FPDF
import io

st.set_page_config(page_title="Spacenet AI | Control de Misiones", layout="wide")

# ==========================================
# AUTHENTICATION
# ==========================================
if "USUARIO_CORRECTO" in st.secrets and "PASSWORD_CORRECTA" in st.secrets:
    USUARIO_CORRECTO = st.secrets["USUARIO_CORRECTO"]
    PASSWORD_CORRECTA = st.secrets["PASSWORD_CORRECTA"]
else:
    USUARIO_CORRECTO = "admin"
    PASSWORD_CORRECTA = "Spacenet2026"

def verificar_credenciales(usuario, password):
    return usuario.strip() == USUARIO_CORRECTO and password.strip() == PASSWORD_CORRECTA

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("Acceso al Sistema")
        user_input = st.text_input("Usuario Corporativo")
        pass_input = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            if verificar_credenciales(user_input, pass_input):
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("Credenciales inválidas.")
    st.stop()

# ==========================================
# CORE DE DATOS Y AI
# ==========================================
DATABASE_URL = st.secrets.get("DATABASE_URL", "postgresql://postgres.mmuzkpooqjpdzmtsyqlu:ElBicho_007@aws-1-eu-north-1.pooler.supabase.com:6543/postgres")

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
# LÓGICA DE PURIFICACIÓN (IA + PRIVACIDAD)
# ==========================================
def anonimizar_texto(texto):
    return hashlib.sha256(str(texto).encode('utf-8')).hexdigest()[:12]

def blindar_telefono(telefono):
    tel_str = str(telefono).strip()
    if len(tel_str) < 7: return "*******"
    return f"{tel_str[:3]} ****** {tel_str[-3:]}"

def purificar_datos_con_ia(df_sucio):
    df_limpio = df_sucio.copy()
    
    # Rellenar nulos
    df_limpio['Edad'] = df_limpio['Edad'].fillna(df_limpio['Edad'].median() if not df_limpio['Edad'].dropna().empty else 40)
    df_limpio['Ingresos_Anuales'] = df_limpio['Ingresos_Anuales'].fillna(df_limpio['Ingresos_Anuales'].median())
    
    # Funciones de validación
    df_limpio['Email_Roto'] = df_limpio['Email'].apply(lambda x: 1.0 if pd.isna(x) or '@' not in str(x) else 0.0)
    df_limpio['Nombre_Falso'] = df_limpio['Nombre'].apply(lambda x: 1.0 if bool(re.search(r'\d', str(x))) else 0.0)
    
    # Escalado y Predicción
    X_nuevos = df_limpio[['Edad', 'Ingresos_Anuales', 'Email_Roto', 'Nombre_Falso']].values
    x_min, x_max = scaler
    X_nuevos_scaled = (X_nuevos - x_min) / (x_max - x_min + 1e-5)
    
    X_reconstruido = autoencoder.predict(X_nuevos_scaled, verbose=0)
    errores_reconstruccion = np.mean(np.power(X_nuevos_scaled - X_reconstruido, 2), axis=1)
    
    # Lógica de anomalías
    UMBRAL_IA = 0.05
    df_sucio['Error_IA'] = errores_reconstruccion
    df_aprobado = df_limpio[errores_reconstruccion <= UMBRAL_IA].copy()
    
    # Anonimización y Blindaje final
    df_aprobado['Nombre'] = df_aprobado['Nombre'].apply(anonimizar_texto)
    df_aprobado['Email'] = df_aprobado['Email'].apply(anonimizar_texto)
    df_aprobado['Telefono'] = df_aprobado['Telefono'].apply(blindar_telefono)
    
    return df_aprobado, len(df_sucio), df_sucio['Edad'].isnull().sum(), len(df_sucio[errores_reconstruccion > UMBRAL_IA]), df_sucio
# ==========================================
# GENERADOR DE REPORTES (PDF)
# ==========================================
def generar_reporte_pdf(total, nulos, alertas):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Informe de Auditoria - Spacenet AI", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Total Registros Auditados: {total}", ln=True)
    pdf.cell(200, 10, txt=f"Nulos Corregidos: {nulos}", ln=True)
    pdf.cell(200, 10, txt=f"Anomalias Bloqueadas (Cuarentena): {alertas}", ln=True)
    pdf.ln(10)
    pdf.cell(200, 10, txt="Estado: Proteccion de datos activada (SHA256 + Masking)", ln=True)
    
    # Retornamos el PDF como binario para el botón
    return pdf.output(dest='S').encode('latin-1')
# ==========================================
# DASHBOARD PROFESIONAL
# ==========================================
st.sidebar.title("Consola de Operaciones")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("Gestión de Servidor")
if st.sidebar.button("Vaciar Base de Datos"):
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("TRUNCATE TABLE clientes_purificados RESTART IDENTITY")
    conn.commit()
    cursor.close()
    conn.close()
    st.sidebar.success("Servidor purgado.")

modo = st.sidebar.radio("Módulos", ["Pipeline de Auditoría", "Base de Datos SQL"])

st.title("Spacenet Data Intelligence")

if modo == "Pipeline de Auditoría":
    st.subheader("Ingesta y Procesamiento Neuronal")
    archivo = st.file_uploader("Cargar dataset", type=["csv", "xlsx"])
    
    if archivo and st.button("Ejecutar Análisis"):
        with st.spinner("Procesando red neuronal..."):
            df = pd.read_csv(archivo) if archivo.name.endswith('.csv') else pd.read_excel(archivo)
            df_limpio, total, nulos, alertas, analisis = purificar_datos_con_ia(df)
            
            # Inserción
            conn = obtener_conexion()
            cursor = conn.cursor()
            valores = [(int(row['ID_Cliente']), row['Nombre'], str(row['Email']), float(row['Edad']), float(row['Ingresos_Anuales']), str(row['Telefono'])) for _, row in df_limpio.iterrows()]
            query = "INSERT INTO clientes_purificados (ID_Cliente, Nombre, Email, Edad, Ingresos_Anuales, Telefono) VALUES %s ON CONFLICT (ID_Cliente) DO NOTHING"
            execute_values(cursor, query, valores)
            conn.commit()
            cursor.close()
            conn.close()

            # Métricas
            col1, col2, col3 = st.columns(3)
            col1.metric("Registros Auditados", f"{total:,}")
            col2.metric("Nulos Corregidos", f"{nulos:,}")
            col3.metric("Anomalías Bloqueadas", f"{alertas:,}")
            
            st.write("Gráfico de dispersión de error (Autoencoder):")
            st.line_chart(analisis['Error_IA'].head(100))
            
            # TABS DE VISTA
            tab1, tab2 = st.tabs(["Datos Purificados", "Sala de Cuarentena"])
            with tab1:
                st.dataframe(df_limpio.drop(columns=['Email_Roto', 'Nombre_Falso']), use_container_width=True)
            with tab2:
                st.dataframe(analisis[analisis['Error_IA'] > 0.05], use_container_width=True)
    # Métricas
            col1, col2, col3 = st.columns(3)
            col1.metric("Registros Auditados", f"{total:,}")
            col2.metric("Nulos Corregidos", f"{nulos:,}")
            col3.metric("Anomalías Bloqueadas", f"{alertas:,}")
            
            # BOTÓN DE DESCARGA PDF
            pdf_data = generar_reporte_pdf(total, nulos, alertas)
            st.download_button(
                label="📥 Descargar Informe de Auditoria (PDF)",
                data=pdf_data,
                file_name="reporte_auditoria.pdf",
                mime="application/pdf"
            )
elif modo == "Base de Datos SQL":
    st.subheader("Registros Almacenados en Servidor")
    conn = obtener_conexion()
    df_sql = pd.read_sql_query("SELECT * FROM clientes_purificados", conn)
    conn.close()
    
    st.dataframe(df_sql, use_container_width=True)
    
    if not df_sql.empty:
        csv = df_sql.to_csv(index=False).encode('utf-8')
        st.download_button("Exportar Historial (CSV)", data=csv, file_name="auditoria_completa.csv", mime="text/csv")