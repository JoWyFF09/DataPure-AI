import pandas as pd
import numpy as np
from faker import Faker
import random

# Inicializamos Faker en español
fake = Faker('es_ES')
Faker.seed(42)
np.random.seed(42)

def generar_datos_empresariales(n=2000):
    datos = []
    print(f"⚙️ Generando {n} perfiles de clientes corporativos...")
    
    for i in range(n):
        # Datos normales y legítimos
        nombre = fake.name()
        email = fake.ascii_free_email()
        edad = np.random.normal(40, 12)  # Edad media 40
        ingresos = np.random.normal(45000, 15000) # Ingresos medios 45k
        telefono = fake.phone_number()

        # 🚨 INYECCIÓN DE ANOMALÍAS (15% de probabilidad de que el dato esté corrupto)
        if random.random() < 0.15:
            tipo_error = random.choice(['edad_loca', 'ingreso_loco', 'nombre_falso', 'nulos', 'email_roto'])
            
            if tipo_error == 'edad_loca':
                edad = random.choice([150, -10, 5]) # Edades imposibles
            elif tipo_error == 'ingreso_loco':
                ingresos = random.choice([2500000, -5000, 0]) # Millonarios absurdos o deudas
            elif tipo_error == 'nombre_falso':
                nombre = nombre + str(random.randint(0, 99)) + "_Fake!" # Nombres con símbolos
            elif tipo_error == 'nulos':
                edad = np.nan
                ingresos = np.nan
            elif tipo_error == 'email_roto':
                email = "no_email.com" # Formato inválido

        datos.append([i+1, nombre, email, edad, ingresos, telefono])

    # Guardar en CSV
    df = pd.DataFrame(datos, columns=['ID_Cliente', 'Nombre', 'Email', 'Edad', 'Ingresos_Anuales', 'Telefono'])
    df.to_csv('clientes_sucios.csv', index=False)
    print("✅ ¡Éxito! Archivo 'clientes_sucios.csv' sobreescrito con datos empresariales realistas.")

if __name__ == "__main__":
    generar_datos_empresariales()