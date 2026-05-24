import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models
import joblib
import re

print("🧠 Iniciando entrenamiento del Autoencoder V2.0 (Libre de Veneno)...")

df = pd.read_csv('clientes_sucios.csv')
df['Edad'] = df['Edad'].fillna(df['Edad'].median())
df['Ingresos_Anuales'] = df['Ingresos_Anuales'].fillna(df['Ingresos_Anuales'].median())

def chequear_email(email):
    if pd.isna(email) or '@' not in str(email) or '.' not in str(email):
        return 1.0
    return 0.0

def chequear_nombre(nombre):
    if bool(re.search(r'\d', str(nombre))):
        return 1.0
    return 0.0

df['Email_Roto'] = df['Email'].apply(chequear_email)
df['Nombre_Falso'] = df['Nombre'].apply(chequear_nombre)

# 1. Preparar Escalas Globales (Para no romper las matemáticas)
X_global = df[['Edad', 'Ingresos_Anuales', 'Email_Roto', 'Nombre_Falso']].values
x_min = X_global.min(axis=0)
x_max = X_global.max(axis=0)
rango = x_max - x_min
rango[rango == 0] = 1e-5
joblib.dump((x_min, x_max), 'escalador_ia.pkl')

# 🚨 2. LA CORRECCIÓN MÁGICA: Aislar solo los datos sanos
print("🧹 Purificando el set de entrenamiento...")
df_sano = df[(df['Email_Roto'] == 0.0) & (df['Nombre_Falso'] == 0.0)].copy()

# 3. Entrenar SOLO con los datos perfectos
X_sano = df_sano[['Edad', 'Ingresos_Anuales', 'Email_Roto', 'Nombre_Falso']].values
X_sano_scaled = (X_sano - x_min) / rango

input_dim = X_sano_scaled.shape[1]
input_layer = layers.Input(shape=(input_dim,))
encoded = layers.Dense(8, activation='relu')(input_layer)
bottleneck = layers.Dense(3, activation='relu')(encoded)
decoded = layers.Dense(8, activation='relu')(bottleneck)
output_layer = layers.Dense(input_dim, activation='sigmoid')(decoded)

autoencoder = models.Model(inputs=input_layer, outputs=output_layer)
autoencoder.compile(optimizer='adam', loss='mse')

print(f"⚙️ Entrenando la red neuronal SOLO con {len(df_sano)} perfiles 100% limpios...")
autoencoder.fit(X_sano_scaled, X_sano_scaled, epochs=50, batch_size=32, shuffle=True, verbose=0)

autoencoder.save_weights('autoencoder_pesos.weights.h5')
print("✅ ¡Entrenamiento completado! Cerebro V2.0 Incorruptible guardado.")