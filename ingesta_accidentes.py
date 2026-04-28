import pandas as pd
import geopandas as gpd
import os
from shapely.geometry import Point

def procesar_archivo_excel_siniestros(ruta_archivo):
    print(f"📂 Iniciando procesamiento de: {ruta_archivo}")
    
    # 1. Cargar el archivo (usa read_excel si es .xlsx o read_csv si es .csv)
    if ruta_archivo.endswith('.xlsx'):
        df = pd.read_excel(ruta_archivo)
    else:
        df = pd.read_csv(ruta_archivo, low_memory=False)

    if df.empty:
        print("❌ El archivo está vacío.")
        return

    # 2. Limpieza de Coordenadas
    # Convertimos a numérico y eliminamos filas que no tengan ubicación válida
    df['Latitud'] = pd.to_numeric(df['Latitud'], errors='coerce')
    df['Longitud'] = pd.to_numeric(df['Longitud'], errors='coerce')
    
    df_limpio = df.dropna(subset=['Latitud', 'Longitud'])
    
    # 3. Filtrado por años (2021 a 2024 según tu columna AA_Acc)
    # Asegúrate que la columna se llama AA_Acc
    df_filtrado = df_limpio[df_limpio['AA_Acc'].isin([2021, 2022, 2023, 2024])].copy()

    if df_filtrado.empty:
        print("⚠️ No se encontraron registros para los años 2021-2024. Verifica la columna 'AA_Acc'.")
        return

    # 4. Conversión Espacial
    print(f"📍 Creando geometrías para {len(df_filtrado)} registros...")
    geometry = [Point(xy) for xy in zip(df_filtrado['Longitud'], df_filtrado['Latitud'])]
    gdf = gpd.GeoDataFrame(df_filtrado, geometry=geometry, crs="EPSG:4326")

    # 5. Guardar el resultado para la IA
    # Creamos las carpetas si no existen
    os.makedirs("data/processed", exist_ok=True)
    
    output_path = "data/processed/siniestros_viales.gpkg"
    
    # Guardamos como GeoPackage. La capa se llamará 'accidentes'
    gdf.to_file(output_path, driver="GPKG", layer="accidentes_2021_2024")
    
    print(f"✅ ¡Éxito! GeoPackage creado en: {output_path}")
    print(f"📊 Resumen por Localidad:\n{gdf['Localidad'].value_counts().head()}")

if __name__ == "__main__":
    # Cambia esto por el nombre real de tu archivo
    ARCHIVO_USUARIO = r"C:\Users\Home\Documents\UNIVERSIDAD\ONCEAVO SEMESTRE\INTELIGENCIA ARTIFICIAL APLICADA AL TERRITORIO\SEPTIMO PROYECTO\documentos\ACCIDENTES 2021 - 2024.xlsx" 
    
    if os.path.exists(ARCHIVO_USUARIO):
        procesar_archivo_excel_siniestros(ARCHIVO_USUARIO)
    else:
        print(f"❌ No se encontró el archivo {ARCHIVO_USUARIO} en la carpeta actual.")