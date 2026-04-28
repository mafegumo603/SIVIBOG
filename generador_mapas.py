import geopandas as gpd
import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
import os

# Detectar la ruta base del proyecto de forma automática
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def cargar_datos_localidad(localidad: str) -> gpd.GeoDataFrame:
    """Carga siniestros de una localidad específica desde el geopackage"""
    ruta_gpkg = os.path.join(BASE_DIR, "data", "processed", "siniestros_viales.gpkg")
    
    if not os.path.exists(ruta_gpkg):
        print(f"ERROR: No se encuentra el archivo en: {ruta_gpkg}")
        return gpd.GeoDataFrame()
        
    gdf = gpd.read_file(ruta_gpkg, layer="accidentes_2021_2024")
    
    if 'localidad' in gdf.columns:
        # Filtro robusto para nombres de localidades
        gdf = gdf[gdf['localidad'].str.strip().str.upper() == localidad.strip().upper()]
    return gdf

def generar_clusters_dbscan(localidad: str) -> str:
    """Aplica DBSCAN y genera un GeoJSON en minúsculas"""
    print(f"Generando clusters DBSCAN para {localidad}...")
    gdf = cargar_datos_localidad(localidad)
    if gdf.empty: return ""
        
    coords = np.radians(np.column_stack((gdf.geometry.y, gdf.geometry.x)))
    kms_per_radian = 6371.0088
    epsilon = (100 / 1000) / kms_per_radian 
    
    db = DBSCAN(eps=epsilon, min_samples=5, algorithm='ball_tree', metric='haversine').fit(coords)
    gdf['cluster_id'] = db.labels_
    
    gdf_clusters = gdf[gdf['cluster_id'] != -1]
    
    # Nombre de archivo estandarizado en minúsculas
    nombre_loc = localidad.lower().replace(' ', '_')
    out_path = os.path.join(BASE_DIR, "data", "processed", "geojson", f"clusters_{nombre_loc}.geojson")
    
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    gdf_clusters.to_file(out_path, driver='GeoJSON')
    print(f"Puntos críticos guardados en {out_path}")
    return out_path

def generar_mapa_calor_datos(localidad: str) -> str:
    """Exporta GeoJSON para el mapa de calor en minúsculas"""
    gdf = cargar_datos_localidad(localidad)
    if gdf.empty: return ""
        
    columnas_mantener = ['geometry']
    if 'gravedad' in gdf.columns:
        columnas_mantener.append('gravedad')
        
    gdf_heat = gdf[columnas_mantener]
    
    nombre_loc = localidad.lower().replace(' ', '_')
    out_path = os.path.join(BASE_DIR, "data", "processed", "geojson", f"heat_{nombre_loc}.geojson")
    
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    gdf_heat.to_file(out_path, driver='GeoJSON')
    print(f"Mapa de calor guardado en {out_path}")
    return out_path