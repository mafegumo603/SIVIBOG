from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import asyncio
import pandas as pd
import numpy as np
import json
import hashlib
import logging
import unicodedata
import httpx
from typing import Dict, List
from datetime import datetime
from sklearn.cluster import DBSCAN

# === CONFIGURACIÓN ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GEOJSON_DIR = os.path.join(BASE_DIR, "data", "processed", "geojson")
os.makedirs(GEOJSON_DIR, exist_ok=True)

app = FastAPI(title="SIVIBOG - Agentes IA Territoriales")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/geojson", StaticFiles(directory=GEOJSON_DIR), name="geojson")

# === NORMALIZACIÓN ===
def normalizar_texto(texto: str) -> str:
    """Elimina acentos, espacios extra y convierte a minúsculas."""
    if not texto:
        return ""
    texto = unicodedata.normalize('NFD', str(texto)).encode('ascii', 'ignore').decode('utf-8')
    return texto.strip().lower()

# === CARGA DE DATOS ===
DANE_PATH = os.path.join(BASE_DIR, "data", "processed", "poblacion_bogota_dane.parquet")
CLIMA_PATH = os.path.join(BASE_DIR, "data", "processed", "clima_historico_bogota.parquet")

df_poblacion = pd.read_parquet(DANE_PATH) if os.path.exists(DANE_PATH) else pd.DataFrame()
df_clima = pd.read_parquet(CLIMA_PATH) if os.path.exists(CLIMA_PATH) else pd.DataFrame()

try:
    import geopandas as gpd
    ACC_PATH = os.path.join(BASE_DIR, "data", "processed", "siniestros_viales.gpkg")
    if os.path.exists(ACC_PATH):
        gdf_accidentes = gpd.read_file(ACC_PATH, layer="accidentes_2021_2024")
        gdf_accidentes.columns = [c.lower() for c in gdf_accidentes.columns]
        gdf_accidentes['localidad_norm'] = gdf_accidentes['localidad'].apply(normalizar_texto)
        logger.info("✅ Datos de accidentes cargados")
    else:
        gdf_accidentes = None

    LOC_PATH = os.path.join(BASE_DIR, "data", "processed", "localidades_sistema.gpkg")
    if os.path.exists(LOC_PATH):
        gdf_localidades = gpd.read_file(LOC_PATH, layer="localidades")
        logger.info("✅ Datos de localidades cargados")
    else:
        gdf_localidades = None

except Exception as e:
    logger.warning(f"No se pudo cargar geopackages: {e}")
    gdf_accidentes = None
    gdf_localidades = None

# === LOCALIDADES ===
LOCALIDADES_NORM: Dict[str, str] = {
    "bogota":             "Bogotá",
    "usaquen":            "Usaquén",
    "chapinero":          "Chapinero",
    "santa fe":           "Santa Fe",
    "san cristobal":      "San Cristóbal",
    "usme":               "Usme",
    "tunjuelito":         "Tunjuelito",
    "bosa":               "Bosa",
    "kennedy":            "Kennedy",
    "fontibon":           "Fontibón",
    "engativa":           "Engativá",
    "suba":               "Suba",
    "barrios unidos":     "Barrios Unidos",
    "teusaquillo":        "Teusaquillo",
    "los martires":       "Los Mártires",
    "antonio narino":     "Antonio Nariño",
    "puente aranda":      "Puente Aranda",
    "la candelaria":      "La Candelaria",
    "rafael uribe uribe": "Rafael Uribe Uribe",
    "ciudad bolivar":     "Ciudad Bolívar",
    "sumapaz":            "Sumapaz",
}

MAPEO_SHP_LOCALIDADES: Dict[str, str] = {
    "antonio nario":      "Antonio Nariño",
    "tunjuelito":         "Tunjuelito",
    "rafael uribe uribe": "Rafael Uribe Uribe",
    "candelaria":         "La Candelaria",
    "barrios unidos":     "Barrios Unidos",
    "teusaquillo":        "Teusaquillo",
    "puente aranda":      "Puente Aranda",
    "los martires":       "Los Mártires",
    "sumapaz":            "Sumapaz",
    "usaquen":            "Usaquén",
    "chapinero":          "Chapinero",
    "santa fe":           "Santa Fe",
    "san cristobal":      "San Cristóbal",
    "usme":               "Usme",
    "ciudad bolivar":     "Ciudad Bolívar",
    "bosa":               "Bosa",
    "kennedy":            "Kennedy",
    "fontibon":           "Fontibón",
    "engativa":           "Engativá",
    "suba":               "Suba",
}

def detectar_localidad_en_texto(texto: str) -> str | None:
    """
    Detecta el nombre de una localidad en un texto libre.
    """
    texto_norm = normalizar_texto(texto)
    # Ordenar por longitud desc para priorizar nombres compuestos
    claves = sorted(LOCALIDADES_NORM.keys(), key=len, reverse=True)
    for clave in claves:
        if clave in texto_norm:
            return LOCALIDADES_NORM[clave]
    return None


# === MODELO IA - OLLAMA (phi3.5) ===
class AgenteIALiviano:
    def __init__(self):
        self.ollama_url = "http://localhost:11434/api/generate"
        self.modelo = "phi3.5:latest"
        self.modelo_cargado = True  # Ollama gestiona el modelo externamente

    def cargar(self):
        pass  # No se necesita carga en memoria

    def generar(self, prompt: str, max_tokens: int = 300) -> str:
        try:
            payload = {
                "model": self.modelo,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "num_ctx": 2048,      # Contexto suficiente sin sobrecargar RAM
                    "num_thread": 4,      # Ryzen 3 2200U tiene 4 hilos
                }
            }
            response = httpx.post(
                self.ollama_url,
                json=payload,
                timeout=120.0  # phi3.5 en CPU puede tardar más que phi
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "Sin respuesta del modelo.").strip()

        except httpx.ConnectError:
            logger.error("Ollama no disponible")
            return None  # Retorna None para que el orquestador use fallback
        except httpx.TimeoutException:
            logger.warning("Timeout en Ollama")
            return None
        except Exception as e:
            logger.error(f"Error al consultar Ollama: {e}")
            return None


# === AGENTE 1: ANALISTA ESPACIAL ===
class AgenteAnalistaEspacial:
    def analizar(self, localidad: str) -> Dict:
        if gdf_accidentes is None or gdf_accidentes.empty:
            return {"error": "Datos no disponibles"}

        loc_norm = normalizar_texto(localidad)
        logger.info(f"Analizando localidad: {localidad} (norm: {loc_norm})")

        # --- Caso Especial: Bogotá (Ciudad Completa) ---
        if loc_norm == "bogota":
            df_loc = gdf_accidentes.copy()
            min_samples_dbscan = 50
        else:
            # Búsqueda más flexible en los datos de accidentes
            # Usamos str.contains para manejar mejor casos donde el nombre en el dato tenga basura
            df_loc = gdf_accidentes[gdf_accidentes['localidad_norm'].str.contains(loc_norm, na=False)].copy()
            min_samples_dbscan = 5

        if df_loc.empty and loc_norm != "bogota":
            logger.warning(f"Sin datos para localidad: '{localidad}' (norm: '{loc_norm}')")
            return {"total_accidentes": 0, "zonas_criticas": [], "error": f"No se encontraron datos para {localidad}"}

        # --- Búsqueda de Límite Espacial ---
        nombre_loc = loc_norm.replace(' ', '_')
        nombre_archivo_limite = f"limite_{nombre_loc}.geojson"
        ruta_limite = os.path.join(GEOJSON_DIR, nombre_archivo_limite)

        limite_poly = None
        if gdf_localidades is not None and not gdf_localidades.empty:
            if loc_norm == "bogota":
                limite_poly = gdf_localidades.union_all()
            else:
                for idx, row in gdf_localidades.iterrows():
                    raw_name = str(row['LocNombre'])
                    shp_norm = normalizar_texto(raw_name)
                    # Coincidencia flexible: si el buscado está en el shape o viceversa
                    if shp_norm == loc_norm or loc_norm in shp_norm or shp_norm in loc_norm:
                        limite_poly = row.geometry
                        logger.info(f"Límite encontrado para {localidad} usando {raw_name}")
                        break

        # Filtrar puntos por el polígono si se encontró (clipping espacial real)
        if limite_poly is not None:
            try:
                # Asegurar mismo CRS si es posible (asumimos 4326 por default)
                df_loc = df_loc[df_loc.geometry.within(limite_poly)]
                
                # Guardar el GeoJSON del límite para el frontend
                gdf_limite = gpd.GeoDataFrame(
                    [{"localidad": localidad, "tipo": "Límite"}], 
                    geometry=[limite_poly], 
                    crs="EPSG:4326"
                )
                gdf_limite.to_file(ruta_limite, driver="GeoJSON")
            except Exception as e:
                logger.error(f"Error en clipping espacial: {e}")
        else:
            logger.warning(f"No se pudo determinar el polígono para {localidad}")
            if os.path.exists(ruta_limite): os.remove(ruta_limite)

        if df_loc.empty:
            return {"total_accidentes": 0, "zonas_criticas": [], "error": "No hay puntos dentro de la geometría"}

        # --- Clustering (zonas críticas) ---
        coords = np.radians(np.column_stack((df_loc.geometry.y, df_loc.geometry.x)))
        epsilon = (100 / 1000) / 6371.0088
        clustering = DBSCAN(eps=epsilon, min_samples=min_samples_dbscan, metric='haversine').fit(coords)
        df_loc['cluster'] = clustering.labels_

        clusters = df_loc[df_loc['cluster'] != -1].groupby('cluster').size().sort_values(ascending=False)

        nombre_archivo_clusters = f"clusters_{nombre_loc}.geojson"
        ruta_clusters = os.path.join(GEOJSON_DIR, nombre_archivo_clusters)
        
        try:
            df_criticos = df_loc[df_loc['cluster'] != -1]
            if not df_criticos.empty:
                # El usuario no quiere polígonos de agrupación (convex hull), prefiere ver los puntos críticos
                df_criticos = df_criticos.copy()
                df_criticos['tipo'] = "Zona Crítica"
                counts = df_criticos.groupby('cluster').size().to_dict()
                df_criticos['total_accidentes'] = df_criticos['cluster'].map(counts)
                
                # Guardar como puntos para que el frontend los renderice individualmente con estilo de zona crítica
                df_criticos[['geometry', 'localidad', 'tipo', 'total_accidentes', 'cluster']].to_file(ruta_clusters, driver="GeoJSON")
            else:
                if os.path.exists(ruta_clusters): os.remove(ruta_clusters)
        except Exception as e:
            logger.error(f"Error guardando clusters: {e}")

        # --- Mapa de calor / Puntos ---
        nombre_archivo_calor = f"heat_{nombre_loc}.geojson"
        ruta_calor = os.path.join(GEOJSON_DIR, nombre_archivo_calor)
        try:
            # Mantener columnas mínimas para reducir peso
            columnas = ['geometry', 'localidad']
            for c in ['gravedad', 'clase']: 
                if c in df_loc.columns: columnas.append(c)
            df_loc[columnas].to_file(ruta_calor, driver="GeoJSON")
        except Exception as e:
            logger.error(f"Error guardando heat: {e}")

        return {
            "total_accidentes": int(len(df_loc)),
            "clusters_detectados": len(clusters),
            "zona_mas_critica": f"Cluster {clusters.index[0]}" if not clusters.empty else "Sin clusters",
            "archivo_mapa": nombre_archivo_calor,
            "densidad_accidentes": round(len(df_loc) / 10, 2)
        }


# === AGENTE 2: PLANIFICADOR URBANO ===
class AgentePlanificadorUrbano:
    def __init__(self, modelo_ia):
        self.ia = modelo_ia

    def analizar_vulnerabilidad(self, localidad: str) -> Dict:
        if df_poblacion.empty:
            return {"error": "No hay datos DANE"}
        loc_norm = normalizar_texto(localidad)

        if loc_norm == "bogota":
            return {
                "poblacion_total": int(df_poblacion['poblacion_total'].sum()),
                "porcentaje_vulnerable": round(df_poblacion['porcentaje_vulnerabilidad_etaria'].mean(), 2),
                "grupo_vulnerable": "Mixto (Ciudad)"
            }

        df_loc = df_poblacion[df_poblacion['localidad'].apply(normalizar_texto) == loc_norm]
        if df_loc.empty:
            return {"error": "Localidad no encontrada"}
        row = df_loc.iloc[0]
        return {
            "poblacion_total": int(row.get('poblacion_total', 0)),
            "porcentaje_vulnerable": round(row.get('porcentaje_vulnerabilidad_etaria', 0), 2),
            "poblacion_infantil": int(row.get('menores_14', 0)),
            "poblacion_adulto_mayor": int(row.get('mayores_60', 0)),
            "grupo_vulnerable": "infancia" if row.get('menores_14', 0) > row.get('mayores_60', 0) else "adulto_mayor"
        }

    def generar_mecanismos(self, localidad: str, vulnerabilidad: Dict, datos_espaciales: Dict) -> str:
        mecanismos = []
        if vulnerabilidad.get("grupo_vulnerable") == "infancia":
            mecanismos.extend([
                "Instalación de zonas escolares seguras a 20km/h",
                "Pasos peatonales elevados",
                "Señalización vertical para cuidado infantil"
            ])
        else:
            mecanismos.extend([
                "Ampliación de tiempos semafóricos para peatones",
                "Rampas de acceso universal",
                "Reducción de velocidad a 30km/h en zonas de alto flujo"
            ])
        if datos_espaciales.get("clusters_detectados", 0) > 50:
            mecanismos.append("Auditoría intensiva de infraestructura y rediseño vial en puntos críticos")
        else:
            mecanismos.append("Mejora de iluminación y señalización en intersecciones clave")
        return "\n".join([f"{i+1}. {m}" for i, m in enumerate(mecanismos)])


# === ORQUESTADOR ===
class OrquestadorAgentes:
    def __init__(self):
        self.agente_espacial = AgenteAnalistaEspacial()
        self.modelo_ia = AgenteIALiviano()
        self.agente_planificador = AgentePlanificadorUrbano(self.modelo_ia)
        self.cache = {}

    async def responder_pregunta(self, pregunta: str, localidad: str) -> Dict:
        cache_key = hashlib.md5(f"{localidad}:{pregunta}".encode()).hexdigest()
        if cache_key in self.cache:
            return self.cache[cache_key]

        loop = asyncio.get_event_loop()
        datos_espaciales = await loop.run_in_executor(None, self.agente_espacial.analizar, localidad)
        
        pregunta_lower = pregunta.lower()
        # Análisis selectivo: solo cargar población si es relevante
        interes_poblacion = any(w in pregunta_lower for w in ["poblacion", "vulnerable", "habitantes", "personas", "niños", "adultos"])
        interes_mecanismos = any(w in pregunta_lower for w in ["mecanismo", "medida", "reducir", "mejorar", "solucion"])

        datos_vulnerabilidad = {}
        if interes_poblacion or interes_mecanismos:
            datos_vulnerabilidad = await loop.run_in_executor(
                None, self.agente_planificador.analizar_vulnerabilidad, localidad
            )

        contexto = f"Localidad: {localidad}. Accidentes: {datos_espaciales.get('total_accidentes')}. "
        
        if interes_poblacion and "error" not in datos_vulnerabilidad:
            contexto += (
                f"Población total: {datos_vulnerabilidad.get('poblacion_total')}. "
                f"Niños (0-14): {datos_vulnerabilidad.get('poblacion_infantil')}. "
                f"Adultos mayores (60+): {datos_vulnerabilidad.get('poblacion_adulto_mayor')}. "
                f"Vulnerabilidad etaria: {datos_vulnerabilidad.get('porcentaje_vulnerable')}%. "
            )

        if interes_mecanismos:
            mecanismos = self.agente_planificador.generar_mecanismos(localidad, datos_vulnerabilidad, datos_espaciales)
            contexto += f"Medidas sugeridas: {mecanismos}. "

        # Si la pregunta es sobre zonas críticas, forzamos un formato de respuesta específico solicitado por el usuario
        if any(w in pregunta_lower for w in ["zona", "critico", "critica", "puntos criticos"]):
            n_acc = datos_espaciales.get('total_accidentes', 0)
            n_zonas = datos_espaciales.get('clusters_detectados', 0)
            resp = f"Número de accidentes: {n_acc}, Número de zonas definidas: {n_zonas}."
        else:
            prompt = (
                f"Eres un analista experto en seguridad vial de Bogotá. Tu objetivo es dar respuestas CONCRETAS, COMPLETAS y PROFESIONALES.\n"
                f"Contexto Técnico: {contexto}\n"
                f"Pregunta del usuario: {pregunta}\n"
                f"Responde de forma directa, sin introducciones innecesarias, asegurándote de terminar la idea completamente:\n"
            )
            resp = await loop.run_in_executor(None, self.modelo_ia.generar, prompt, 300)

        # Fallback
        if not resp:
            resp = f"Análisis para {localidad}: {datos_espaciales.get('total_accidentes')} siniestros detectados."

        herramientas = ["limite"]
        
        # Lógica de capas persistentes: si el archivo existe para la localidad, se marca como usada
        nombre_loc = localidad.lower().replace(' ', '_')
        if os.path.exists(os.path.join(GEOJSON_DIR, f"clusters_{nombre_loc}.geojson")):
            herramientas.append("clusters")
        elif any(w in pregunta_lower for w in ["zona", "critico", "donde"]):
            herramientas.append("clusters")

        if os.path.exists(os.path.join(GEOJSON_DIR, f"heat_{nombre_loc}.geojson")):
            herramientas.append("heat")
        elif any(w in pregunta_lower for w in ["calor", "puntos", "mapa"]):
            herramientas.append("heat")

        result = {"respuesta": resp, "archivo_mapa": datos_espaciales.get('archivo_mapa'), "herramientas_usadas": list(set(herramientas))}
        self.cache[cache_key] = result
        return result


orquestador = OrquestadorAgentes()


# === ENDPOINTS ===
@app.post("/consulta")
async def consultar(req: dict):
    pregunta = req.get("pregunta", "")

    localidad_detectada = detectar_localidad_en_texto(pregunta)

    if localidad_detectada:
        localidad = localidad_detectada
        logger.info(f"Localidad detectada en pregunta: '{localidad}'")
    else:
        localidad_body = req.get("localidad", "Bogotá")
        localidad = LOCALIDADES_NORM.get(normalizar_texto(localidad_body), localidad_body)
        logger.info(f"Localidad desde body/default: '{localidad}'")

    resultado = await orquestador.responder_pregunta(pregunta, localidad)
    resultado["localidad_usada"] = localidad
    return resultado


@app.get("/localidades")
async def listar_localidades():
    """Retorna la lista de localidades disponibles."""
    return {"localidades": sorted(list(LOCALIDADES_NORM.values()))}


@app.get("/mapa-data/{localidad}/{tipo}")
async def obtener_mapa_data(localidad: str, tipo: str):
    loc_norm = normalizar_texto(localidad).replace(' ', '_')
    nombre_archivo = f"{tipo}_{loc_norm}.geojson"
    ruta = os.path.join(GEOJSON_DIR, nombre_archivo)
    
    # Si el archivo no existe, intentamos generarlo bajo demanda
    if not os.path.exists(ruta):
        logger.info(f"Generando capa {tipo} para {localidad} bajo demanda...")
        # El analista espacial genera el límite, los clusters y el mapa de calor
        orquestador.agente_espacial.analizar(localidad)
    
    if os.path.exists(ruta):
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error leyendo geojson: {e}")
            return {"error": "Error al leer capa cartográfica"}
            
    logger.warning(f"GeoJSON no encontrado tras intento de generación: {ruta}")
    return {"error": "Capa cartográfica no disponible."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)