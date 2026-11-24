# SIVIBOG: Inteligencia Territorial y Seguridad Vial en Bogotá

Plataforma de análisis territorial, seguridad vial y consulta asistida mediante agentes de inteligencia artificial para **Bogotá D.C.** y sus localidades. Combina un backend en **FastAPI** con clustering espacial (**DBSCAN**), datos demográficos del **DANE**, redes viales (**OSMnx**), bases vectoriales (**ChromaDB**) y un modelo local vía **Ollama** (`phi3.5:latest`), junto con un visor cartográfico interactivo en **React + Leaflet**.

---

## Arquitectura del sistema

El proyecto está organizado en tres capas principales:

1. **Ingesta y preprocesamiento de datos (`ingesta_*.py`, `index_chroma.py`, `generador_mapas.py`):**
   * **`ingesta_accidentes.py`**: Limpia coordenadas (`Latitud`, `Longitud`), filtra siniestros viales por año (`AA_Acc` entre `2021` y `2024`) y exporta la capa `accidentes_2021_2024` en `data/processed/siniestros_viales.gpkg` (`EPSG:4326`).
   * **`ingesta_dane.py`**: Consolida datos poblacionales de las 20 localidades de Bogotá (`poblacion_total`, `menores_14`, `mayores_60`), calcula el porcentaje de vulnerabilidad etaria y guarda `data/processed/poblacion_bogota_dane.parquet`.
   * **`ingesta_localidades.py`**: Reproyecta el shapefile de localidades (`Loca.shp`) a `EPSG:4326` y genera la capa `localidades` en `data/processed/localidades_sistema.gpkg`.
   * **`ingesta_vias.py`**: Descarga el grafo vial vehicular (`network_type='drive'`, `simplify=True`) de Bogotá con **OSMnx** y exporta las capas `vias` y `nodos` en `data/processed/red_vial_bogota.gpkg`.
   * **`index_chroma.py`**: Extrae texto de documentos PDF (`documentos/`), genera fragmentos de 800 caracteres con 100 de traslape, calcula embeddings con `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` y persiste la colección `conocimiento_siniestralidad` en `data/chromadb`.
   * **`generador_mapas.py`**: Aplica `DBSCAN` (`metric='haversine'`, radio aproximado de 100 m, `min_samples=5`) para exportar capas GeoJSON de puntos críticos (`clusters_<localidad>.geojson`) y datos para mapas de calor (`heat_<localidad>.geojson`).

2. **Backend y orquestación de agentes (`main.py`):**
   * Expone servicios REST con **FastAPI** en el puerto `8000` y sirve archivos estáticos GeoJSON en `/geojson`.
   * **`AgenteAnalistaEspacial`**: Filtra siniestros por localidad o ciudad completa (`Bogotá`), realiza recorte espacial (`within`) contra la geometría de localidades, guarda límites (`limite_<localidad>.geojson`), ejecuta `DBSCAN` para identificar zonas críticas y genera las capas de puntos críticos y calor.
   * **`AgentePlanificadorUrbano`**: Evalúa vulnerabilidad etaria con base en los datos del DANE y propone medidas de seguridad vial (zonas escolares a 20 km/h, pasos peatonales elevados, tiempos semafóricos, rampas, auditorías viales o mejoras de iluminación/señalización).
   * **`AgenteIALiviano`**: Consulta un modelo local en **Ollama** (`http://localhost:11434/api/generate`, modelo `phi3.5:latest`) con respuesta de respaldo automática si el servicio no está disponible.
   * **`OrquestadorAgentes`**: Coordina el análisis espacial y demográfico, aplica caché por consulta y localidad, y determina las capas cartográficas activas.

3. **Frontend interactivo (`App.jsx`, `main.jsx`, `index.html`, `index.css`):**
   * Interfaz construida con **React** y **Leaflet** (`MapContainer`, `TileLayer` oscuro de CARTO, `GeoJSON`) para explorar la localidad activa, visualizar límites administrativos y capas de puntos críticos/siniestros con popups informativos, y consultar al asistente IA mediante chat.

---

## Endpoints principales del API (`main.py`)

| Método | Ruta | Descripción |
| :--- | :--- | :--- |
| `POST` | `/consulta` | Recibe `pregunta` y `localidad` (detectando automáticamente si se menciona una localidad en el texto), ejecuta los agentes y devuelve `respuesta`, `archivo_mapa`, `herramientas_usadas` y `localidad_usada`. |
| `GET` | `/localidades` | Devuelve la lista ordenada de localidades disponibles en Bogotá (más `"Bogotá"`). |
| `GET` | `/mapa-data/{localidad}/{tipo}` | Retorna el GeoJSON correspondiente (`limite`, `clusters` o `heat`) y lo genera bajo demanda si aún no existe. |

---

## Estructura de carpetas esperada

```text
SIVIBOG/
├── App.jsx
├── main.jsx
├── index.html
├── index.css
├── main.py
├── generador_mapas.py
├── index_chroma.py
├── ingesta_accidentes.py
├── ingesta_dane.py
├── ingesta_localidades.py
├── ingesta_vias.py
├── documentos/                  # PDFs normativos / técnicos para ChromaDB
└── data/
    ├── chromadb/                # Base vectorial persistente
    └── processed/
        ├── siniestros_viales.gpkg
        ├── poblacion_bogota_dane.parquet
        ├── localidades_sistema.gpkg
        ├── red_vial_bogota.gpkg
        └── geojson/
