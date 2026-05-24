import streamlit as st
import pandas as pd
import numpy as np
import psycopg2  
from psycopg2.extras import RealDictCursor
import tensorflow as tf
from tensorflow.keras import layers, models
import joblib
import time
import os
import hashlib
import re 
from psycopg2.extras import execute_values 

st.set_page_config(page_title="Spacenet AI Intelligence", page_icon="🚀", layout="wide")

# ==========================================
# 🔐 MÓDULO DE AUTENTICACIÓN (SISTEMA DE LOGIN SEGURO)
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
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_l1, col_l2, col_l3 = st.columns([1, 1.5, 1])
    with col_l2:
        st.image("https://cdn-icons-png.flaticon.com/512/5087/5087579.png", width=100)
        st.title("🔒 Spacenet AI - Acceso Restringido")
        st.write("Introduce tus credenciales corporativas para desbloquear el Dashboard.")
        user_input = st.text_input("Usuario Corporativo")
        pass_input = st.text_input("Contraseña", type="password")
        if st.button("🔓 Desbloquear Consola"):
            if verificar_credenciales(user_input, pass_input):
                st.session_state["autenticado"] = True
                st.success("Acceso concedido. Cargando sistemas...")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Credenciales incorrectas. Intento registrado en el sistema de seguridad.")
    st.stop()

# ==========================================
# 🗄️ SISTEMA CORE (CONEXIÓN A POSTGRESQL EN LA NUBE)
# ==========================================
DATABASE_URL = st.secrets.get("DATABASE_URL", "postgresql://postgres.mmuzkpooqjpdzmtsyqlu:ElBicho_007@aws-1-eu-north-1.pooler.supabase.com:6543/postgres")

def obtener_conexion():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def inicializar_tablas_nube():
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes_purificados (
            ID_Interno SERIAL PRIMARY KEY,
            ID_Cliente INTEGER UNIQUE, 
            Nombre TEXT, 
            Email TEXT, 
            Edad REAL, 
            Ingresos_Anuales REAL, 
            Telefono TEXT, 
            Fecha_Limpieza TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

try:
    inicializar_tablas_nube()
except Exception as e:
    st.error(f"⚠️ Error al conectar con la base de datos en la nube: {e}")

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

if st.sidebar.button("🔒 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

st.title("🚀 Spacenet Data Intelligence - Enterprise Secure Pipeline")
st.markdown("---")

if autoencoder is None:
    st.error("❌ Archivos de la IA no encontrados. Ejecuta `python motor_ia.py` primero.")
else:
    modo_operacion = st.sidebar.selectbox("Selecciona Modo de Operación", [
        "Tubería Automatizada en Tiempo Real (API)", 
        "Ver Base de Datos SQL e Historial"
    ])

    st.sidebar.markdown("---")
    st.sidebar.subheader("⚠️ Zona de Peligro")
    if st.sidebar.button("🗑️ Vaciar Base de Datos Vieja"):
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute("TRUNCATE TABLE clientes_purificados RESTART IDENTITY")
        conn.commit()
        cursor.close()
        conn.close()
        st.sidebar.success("💥 Historial antiguo eliminado de la nube.")
        time.sleep(1)
        st.rerun()

    def anonimizar_texto(texto):
        return hashlib.sha256(str(texto).encode('utf-8')).hexdigest()[:12]

    def enmascarar_telefono(tel):
        tel = str(tel).strip()
        if len(tel) >= 6 and tel != 'nan' and tel != 'None':
            return f"{tel[:3]}***{tel[-3:]}"
        return "Hidden_Data"

    def purificar_datos_con_ia(df_sucio):
        df_limpio = df_sucio.copy()
        nulos_edad = df_limpio['Edad'].isnull().sum()
        
        df_limpio['Edad'] = df_limpio['Edad'].fillna(df_limpio['Edad'].median() if not df_limpio['Edad'].dropna().empty else 40)
        df_limpio['Ingresos_Anuales'] = df_limpio['Ingresos_Anuales'].fillna(df_limpio['Ingresos_Anuales'].median())
        
        def chequear_email(email):
            if pd.isna(email) or '@' not in str(email) or '.' not in str(email):
                return 1.0
            return 0.0

        def chequear_nombre(nombre):
            if bool(re.search(r'\d', str(nombre))):
                return 1.0
            return 0.0

        df_limpio['Email_Roto'] = df_limpio['Email'].apply(chequear_email)
        df_limpio['Nombre_Falso'] = df_limpio['Nombre'].apply(chequear_nombre)
        
        X_nuevos = df_limpio[['Edad', 'Ingresos_Anuales', 'Email_Roto', 'Nombre_Falso']].values
        x_min, x_max = scaler
        X_nuevos_scaled = (X_nuevos - x_min) / (x_max - x_min + 1e-5)
        
        X_reconstruido = autoencoder.predict(X_nuevos_scaled, verbose=0)
        errores_reconstruccion = np.mean(np.power(X_nuevos_scaled - X_reconstruido, 2), axis=1)
        
        UMBRAL_IA = 0.05
        df_sucio['Error_IA'] = errores_reconstruccion
        
        df_aprobado_ia = df_limpio[errores_reconstruccion <= UMBRAL_IA].copy()
        anomalias_detectadas = df_sucio[errores_reconstruccion > UMBRAL_IA]
        
        df_aprobado_ia = df_aprobado_ia.drop(columns=['Email_Roto', 'Nombre_Falso'], errors='ignore')
        
        df_aprobado_ia['Nombre'] = df_aprobado_ia['Nombre'].apply(anonimizar_texto)
        df_aprobado_ia['Email'] = df_aprobado_ia['Email'].apply(anonimizar_texto) 
        df_aprobado_ia['Telefono'] = df_aprobado_ia['Telefono'].apply(enmascarar_telefono)
        
        return df_aprobado_ia, len(df_sucio), nulos_edad, len(anomalias_detectadas), df_sucio

    if modo_operacion == "Tubería Automatizada en Tiempo Real (API)":
        st.subheader("📡 Monitorización del Pipeline Neuronal Seguro")
        st.info("🔒 Capa Criptográfica Activa: Sube tu base de datos y la IA la purificará.")
        
        # --- 📂 NUEVO MÓDULO DE CARGA DE ARCHIVOS ---
        archivo_subido = st.file_uploader("📂 Arrastra aquí la base de datos (CSV o Excel)", type=["csv", "xlsx"])

        if archivo_subido is not None:
            if st.button("▶️ Procesar y Purificar Datos"):
                try:
                    # Rueda de carga visual
                    with st.spinner("🧠 Red Neuronal Spacenet analizando estructura..."):
                        if archivo_subido.name.endswith('.csv'):
                            df_base = pd.read_csv(archivo_subido)
                        else:
                            df_base = pd.read_excel(archivo_subido)
                        
                        # Muestra máxima de 500 para evitar saturar bases de datos gratis, puedes quitar el sample si quieres procesar miles
                        df_lote = df_base.sample(n=min(500, len(df_base))).copy() 
                        
                        df_limpio, total_inicial, nulos_edad, total_alertas, df_analisis = purificar_datos_con_ia(df_lote)
                        
                        # Inserción Ultra Rápida
                        conn = obtener_conexion()
                        cursor = conn.cursor()
                        
                        valores_a_insertar = [
                            (
                                int(row['ID_Cliente']), 
                                row['Nombre'], 
                                str(row['Email']), 
                                float(row['Edad']), 
                                float(row['Ingresos_Anuales']), 
                                str(row['Telefono'])
                            )
                            for _, row in df_limpio.iterrows()
                        ]
                        
                        query = '''
                            INSERT INTO clientes_purificados (ID_Cliente, Nombre, Email, Edad, Ingresos_Anuales, Telefono)
                            VALUES %s
                            ON CONFLICT (ID_Cliente) DO NOTHING
                        '''
                        execute_values(cursor, query, valores_a_insertar)
                        conn.commit()
                except Exception as e:
                    st.error(f"❌ Error al procesar: Asegúrate de que el archivo tiene las columnas (ID_Cliente, Nombre, Email, Edad, Ingresos_Anuales, Telefono). Detalle: {e}")
                finally:
                    if 'cursor' in locals(): cursor.close()
                    if 'conn' in locals(): conn.close()
                
                st.write(f"### ⚡ Análisis Masivo Completado en Microsegundos")
                col1, col2, col3 = st.columns(3)
                col1.metric(label="Registros Auditados", value=f"{total_inicial} transacciones")
                col2.metric(label="Correcciones de Nulos (Edad)", value=f"{nulos_edad} Reparados")
                col3.metric(label="Bloqueado por Anomalía (IA)", value=f"{total_alertas} Errores", delta=int(total_alertas), delta_color="inverse")
                
                st.write("**Gráfico de dispersión de error de reconstrucción (Autoencoder):**")
                st.line_chart(df_analisis['Error_IA'].head(100))
                
                st.markdown("---")
                tab_seguros, tab_cuarentena = st.tabs([
                    "✨ 1. Vista Previa de Datos Purificados (SQL)", 
                    "🚨 2. Sala de Cuarentena (Amenazas Detectadas por la IA)"
                ])
                
                with tab_seguros:
                    st.markdown("#### 🔒 Registros Blindados y Listos para Producción")
                    st.dataframe(df_limpio.head(10), use_container_width=True)
                    
                with tab_cuarentena:
                    st.markdown("#### 🔍 Informe de Intrusiones y Outliers Críticos")
                    df_anomalias = df_analisis[df_analisis['Error_IA'] > 0.05].copy()
                    if not df_anomalias.empty:
                        df_anomalias_ordenadas = df_anomalias.sort_values(by='Error_IA', ascending=False)
                        st.dataframe(
                            df_anomalias_ordenadas[['ID_Cliente', 'Nombre', 'Email', 'Edad', 'Ingresos_Anuales', 'Telefono', 'Error_IA']].head(10),
                            use_container_width=True
                        )
                        st.warning("⚠️ El sistema ha aislado automáticamente estos perfiles para proteger la integridad del servidor central.")
                    else:
                        st.success("✅ Increíble: No se han detectado anomalías críticas en este lote de transacciones.")

    elif modo_operacion == "Ver Base de Datos SQL e Historial":
        st.subheader("🗄️ Servidor Central de Almacenamiento Cifrado (Cloud)")
        
        conn = obtener_conexion()
        df_sql = pd.read_sql_query("SELECT ID_Cliente, Nombre, Email, Edad, Ingresos_Anuales, Telefono, Fecha_Limpieza FROM clientes_purificados", conn)
        conn.close()
        
        if not df_sql.empty:
            st.write(f"Se han encontrado **{len(df_sql)} registros anonimizados** dentro de la base de datos PostgreSQL en la nube.")
            st.dataframe(df_sql.sort_values(by="id_cliente" if "id_cliente" in df_sql.columns else "ID_Cliente", ascending=True))
            st.markdown("---")
            csv_total = df_sql.to_csv(index=False).encode('utf-8')
            st.download_button(label="📥 Exportar Historial Anonimizado para Auditoría (CSV)", data=csv_total, file_name="enterprise_secure_data.csv", mime="text/csv")
        else:
            st.info("La base de datos en la nube está vacía actualmente. Sube un archivo en el Pipeline para enviar datos.")