import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
import os

# Coordenadas aproximadas para un punto central de Bogotá
LAT_BOGOTA = 4.6097
LON_BOGOTA = -74.0817

def ingestar_clima_historico(start_date="2021-01-01", end_date="2024-12-31"):
    print(f"☁️ Descargando datos climáticos históricos ({start_date} a {end_date})...")
    
    # 1. Configuración de cliente con caché y reintentos
    cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": LAT_BOGOTA,
        "longitude": LON_BOGOTA,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ["temperature_2m", "precipitation"],
        "timezone": "America/Bogota"
    }
    
    try:
        responses = openmeteo.weather_api(url, params=params)
        response = responses[0]
        
        # 2. Extracción de variables
        hourly = response.Hourly()
        hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
        hourly_precipitation = hourly.Variables(1).ValuesAsNumpy()

        # 3. Creación directa del DataFrame (El cambio sugerido)
        # Esto asegura que la fecha y los valores coincidan perfectamente
        df = pd.DataFrame({
            "fecha_hora": pd.date_range(
                start=pd.to_datetime(hourly.Time(), unit="s", utc=False),
                periods=len(hourly_temperature_2m),
                freq=pd.Timedelta(seconds=hourly.Interval())
            ),
            "temperatura_2m": hourly_temperature_2m,
            "precipitacion": hourly_precipitation
        })

        # 4. Exportación
        os.makedirs("data/processed", exist_ok=True)
        out_path = "data/processed/clima_historico_bogota.parquet"
        df.to_parquet(out_path)
        
        print(f"✅ ¡Éxito! Datos guardados en: {out_path}")
        print(f"📊 Registros totales: {len(df)}")
        print(df.head()) # Muestra las primeras filas para verificar

    except Exception as e:
        print(f"❌ Error durante la descarga del clima: {e}")

if __name__ == "__main__":
    ingestar_clima_historico()