import geopandas as gpd
import os

# 1. Configura tus rutas
ruta_carpeta = r"C:\Users\Home\Documents\UNIVERSIDAD\ONCEAVO SEMESTRE\INTELIGENCIA ARTIFICIAL APLICADA AL TERRITORIO\SEPTIMO PROYECTO\codigo\data\processed" # Cambia esto por tu ruta
nombre_archivo = "localidades_sistema.gpkg"
ruta_completa = os.path.join(ruta_carpeta, nombre_archivo)

# 2. Crear la carpeta si no existe
if not os.path.exists(ruta_carpeta):
    os.makedirs(ruta_carpeta)
    print(f"Carpeta creada en: {ruta_carpeta}")

# 3. Leer tu Shapefile actual
# (Asegúrate de apuntar al archivo .shp original)
gdf = gpd.read_file(r"C:\Users\Home\Documents\UNIVERSIDAD\ONCEAVO SEMESTRE\INTELIGENCIA ARTIFICIAL APLICADA AL TERRITORIO\SEPTIMO PROYECTO\loca\Loca.shp")
# Convertir a EPSG:4326 (latitud/longitud) antes de exportar
gdf = gdf.to_crs(epsg=4326)

# 4. Guardar en la carpeta específica
# 'layer' es el nombre de la tabla dentro del GeoPackage
gdf.to_file(ruta_completa, layer='localidades', driver="GPKG")

print(f"Éxito: GeoPackage guardado en {ruta_completa}")