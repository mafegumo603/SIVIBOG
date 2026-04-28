import osmnx as ox
import geopandas as gpd
import os

# Configuración OSMnx
ox.settings.use_cache = True
ox.settings.log_console = True

def ingestar_red_vial_bogota():
    print("🛤️ Descargando grafo de la red vial de Bogotá D.C. usando OSMnx...")
    lugar = "Bogotá, Colombia"
    
    try:
        # Descargamos el grafo (graph) de Calles (sólo conducción)
        # simplify=True es vital para que el archivo no pese gigas
        G = ox.graph_from_place(lugar, network_type='drive', simplify=True)
        
        # Convertimos el grafo en GeoDataFrames
        nodos, vias = ox.graph_to_gdfs(G)
        
        # --- CAMBIO IMPORTANTE: Conversión de listas a strings ---
        # Usamos apply en lugar de applymap para evitar advertencias de versiones futuras
        vias = vias.apply(lambda col: col.map(lambda x: str(x) if isinstance(x, list) else x))
        nodos = nodos.apply(lambda col: col.map(lambda x: str(x) if isinstance(x, list) else x))
        
        # --- CAMBIO SUGERIDO: Filtrar columnas para evitar errores de GeoPackage ---
        columnas_vias = ['osmid', 'name', 'highway', 'oneway', 'length', 'geometry']
        vias_filtradas = vias[vias.columns.intersection(columnas_vias)].copy()
        
        out_path = "data/processed/red_vial_bogota.gpkg"
        
        # Guardar Vías (Capa principal para el análisis territorial)
        vias_filtradas.to_file(out_path, layer='vias', driver="GPKG")
        
        # Guardar Nodos (Opcional, por si necesitas intersecciones)
        nodos.to_file(out_path, layer='nodos', driver="GPKG")
        
        print(f"✅ Red vial guardada en {out_path}")
        print(f"📊 Vías procesadas: {len(vias_filtradas)}")

    except Exception as e:
        print(f"❌ Error descargando la red vial: {e}")

if __name__ == "__main__":
    os.makedirs("data/processed", exist_ok=True)
    ingestar_red_vial_bogota()