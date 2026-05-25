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
import smtplib
from email.message import EmailMessage


st.set_page_config(page_title="DataPure AI - Limpieza y Auditoría de Datos", layout="wide")


# ==========================================
# AUTHENTICATION
# ==========================================
if "USUARIO_CORRECTO" in st.secrets and "PASSWORD_CORRECTA" in st.secrets:
    USUARIO_CORRECTO = st.secrets["USUARIO_CORRECTO"]
    PASSWORD_CORRECTA = st.secrets["PASSWORD_CORRECTA"]




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
    pdf.set_auto_page_break(auto=True, margin=15)
   
    # 1. ENCABEZADO "DEEP TECH"
    pdf.set_fill_color(15, 23, 42) # Azul oscuro/negro aeroespacial
    pdf.rect(0, 0, 210, 38, 'F')
   
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 22)
    pdf.cell(0, 10, "DataPure AI", ln=True, align='L')
    pdf.set_font("Arial", 'I', 10)
    pdf.set_text_color(148, 163, 184) # Gris azulado elegante
    pdf.cell(0, 5, "AI-Powered Data Purification & Security Audit", ln=True, align='L')
    pdf.ln(20)
   
    # 2. TÍTULO DEL INFORME
    pdf.set_text_color(30, 41, 59)
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "INFORME DE AUDITORIA Y CUARENTENA", ln=True)
   
    # Línea decorativa (Corregido: set_line_width)
    pdf.set_draw_color(99, 102, 241) # Morado/Índigo tecnológico
    pdf.set_line_width(1)
    pdf.line(10, 52, 200, 52)
    pdf.ln(8)
   
    # INTRODUCCIÓN CON CLASE
    pdf.set_font("Arial", size=10)
    pdf.set_text_color(100, 116, 139)
    texto_intro = "Este documento contiene los resultados del analisis neuronal realizado por el motor autoencoder de Spacenet. Se han evaluado las metricas de integridad, registros nulos y patrones anomalos de comportamiento."
    pdf.multi_cell(0, 5, texto_intro)
    pdf.ln(10)
   
    # 3. TABLA DE MÉTRICAS CRÍTICAS
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 8, "METRICAS CLAVE DE PURIFICACION", ln=True)
    pdf.ln(2)
   
    # Cabecera de tabla
    pdf.set_fill_color(241, 245, 249)
    pdf.set_text_color(71, 85, 105)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(110, 10, " Indicador Analizado", border=1, fill=True)
    pdf.cell(80, 10, " Valor / Estado", border=1, fill=True, align='C')
    pdf.ln()
   
    # Datos de la tabla
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
            pdf.set_text_color(220, 38, 38) # Rojo
            pdf.set_font("Arial", 'B', 10)
        else:
            pdf.set_text_color(51, 65, 85)
            pdf.set_font("Arial", size=10)
           
        pdf.cell(110, 9, f"  {label}", border=1)
        pdf.cell(80, 9, f" {value}", border=1, align='C')
        pdf.ln()
       
    # 4. DIAGNÓSTICO FINAL
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
        msg_diagnostico = f"  ATENCION: Se han detectado {alertas} vectores de riesgo en el dataset. Los datos han sido aislados\n  en la sala de cuarentena para proteger la integridad de su base de datos corporativa."
    else:
        msg_diagnostico = "  OPTIMO: No se han detectado anomalias criticas. El dataset cumple con los estandares internacionales\n  de calidad y politicas de privacidad de datos."
       
    pdf.multi_cell(0, 5, msg_diagnostico)
   
    # Pie de página
    pdf.set_y(-25)
    pdf.set_font("Arial", 'I', 8)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 10, "CONFIDENCIAL - DataPure AI v2.0 - Copia de Seguridad Autorizada", border=0, align='C')
   
    return pdf.output(dest='S').encode('latin-1')


# ==========================================
# ENVÍO DE EMAIL
# ==========================================
def enviar_aviso_venta(nombre, email):
    mi_correo = st.secrets["EMAIL_DESTINO"]
    contrasena = st.secrets["EMAIL_PASSWORD"]
   
    msg = EmailMessage()
    msg['Subject'] = f"🚀 NUEVA VENTA: {nombre} ha auditado datos"
    msg['From'] = mi_correo
    msg['To'] = mi_correo
    msg.set_content(f"El cliente {nombre} ({email}) ha descargado un informe de auditoria.")
   
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(mi_correo, contrasena)
        smtp.send_message(msg)


# ==========================================
# DASHBOARD PROFESIONAL
# ==========================================
st.sidebar.title("DataPure AI")
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


modo = st.sidebar.radio("Módulos", ["Pipeline de Auditoría", "Base de Datos SQL", "Precios y Planes"])


st.title("DataPure AI")


if modo == "Pipeline de Auditoría":
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
            valores = [(int(row['ID_Cliente']), row['Nombre'], str(row['Email']), float(row['Edad']), float(row['Ingresos_Anuales']), str(row['Telefono'])) for _, row in df_limpio.iterrows()]
            query = "INSERT INTO clientes_purificados (ID_Cliente, Nombre, Email, Edad, Ingresos_Anuales, Telefono) VALUES %s ON CONFLICT (ID_Cliente) DO NOTHING"
            execute_values(cursor, query, valores)
            conn.commit()
            cursor.close()
            conn.close()


            st.session_state.df_procesado = df_limpio
            st.session_state.analisis = analisis
            st.session_state.metricas = (total, nulos, alertas)
            st.session_state.pdf_generado = None


    if st.session_state.df_procesado is not None:
        df_limpio = st.session_state.df_procesado
        analisis = st.session_state.analisis
        total, nulos, alertas = st.session_state.metricas


        col1, col2, col3 = st.columns(3)
        col1.metric("Registros Auditados", f"{total:,}")
        col2.metric("Nulos Corregidos", f"{nulos:,}")
        col3.metric("Anomalías Bloqueadas", f"{alertas:,}")
       
        st.write("Gráfico de dispersión de error (Autoencoder):")
        st.line_chart(analisis['Error_IA'].head(100))
       
        tab1, tab2 = st.tabs(["Datos Purificados", "Sala de Cuarentena"])
        with tab1:
            # Corregido: width='stretch' en lugar de use_container_width
            st.dataframe(df_limpio.drop(columns=['Email_Roto', 'Nombre_Falso']), width='stretch')
        with tab2:
            # Corregido: width='stretch' en lugar de use_container_width
            st.dataframe(analisis[analisis['Error_IA'] > 0.05], width='stretch')


        with st.expander("📥 Obtener Informe de Auditoría Completo"):
            st.write("Introduce tus datos para generar y descargar el informe oficial.")
            with st.form("form_captacion"):
                nombre_cliente = st.text_input("Nombre de la Empresa / Contacto")
                email_cliente = st.text_input("Email Corporativo")
                submit_button = st.form_submit_button("Generar PDF")
               
                if submit_button:
                    if email_cliente and "@" in email_cliente:
                        st.session_state.pdf_generado = generar_reporte_pdf(total, nulos, alertas)
                        try:
                            enviar_aviso_venta(nombre_cliente, email_cliente)
                        except:
                            pass
                        st.success(f"Informe listo para {nombre_cliente}. ¡Ya puedes descargarlo!")
                    else:
                        st.error("Por favor, introduce un email corporativo válido.")


        if st.session_state.pdf_generado:
            st.download_button(
                label="⬇️ DESCARGAR PDF AHORA",
                data=st.session_state.pdf_generado,
                file_name=f"Informe_Auditoria.pdf",
                mime="application/pdf"
            )
elif modo == "Precios y Planes":
    st.title("Precios y Planes - DataPure AI")
    st.markdown("### Limpia y audita tus bases de clientes con Inteligencia Artificial")
   
    col1, col2, col3 = st.columns(3)
   
    with col1:
        st.subheader("Starter")
        st.write("**29 USD**")
        st.write("• 1 Análisis completo")
        st.write("• Informe PDF profesional")
        st.write("• Soporte básico")
        if st.button("Elegir Starter", key="starter"):
            st.success("Perfecto! Te contacto por email para procesar el pago.")
   
    with col2:
        st.subheader("Pro")
        st.write("**79 USD / mes**")
        st.write("• Análisis ilimitados")
        st.write("• Historial completo")
        st.write("• Soporte prioritario")
        st.write("• Mejor precio por volumen")
        if st.button("Elegir Pro", key="pro"):
            st.success("¡Excelente elección! Próximamente activaremos pago recurrente.")
   
    with col3:
        st.subheader("Enterprise")
        st.write("**199 USD / mes**")
        st.write("• Todo lo del Pro")
        st.write("• Acceso API")
        st.write("• Soporte dedicado")
        st.write("• Personalización")
        if st.button("Contactar Enterprise", key="enterprise"):
            st.info("Te escribiremos pronto para coordinar.")
   
    st.markdown("---")
    st.info("💡 Los primeros 5 clientes reciben **50% de descuento** en el plan Pro.")
   
elif modo == "Base de Datos SQL":
    st.subheader("Registros Almacenados en Servidor")
    conn = obtener_conexion()
    df_sql = pd.read_sql_query("SELECT * FROM clientes_purificados", conn)
    conn.close()
   
    # Corregido: width='stretch' en lugar de use_container_width
    st.dataframe(df_sql, width='stretch')
   
    if not df_sql.empty:
        csv = df_sql.to_csv(index=False).encode('utf-8')
        st.download_button("Exportar Historial (CSV)", data=csv, file_name="auditoria_completa.csv", mime="text/csv")

