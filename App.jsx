import React, { useState, useEffect, useCallback } from "react";
import { MapContainer, TileLayer, GeoJSON, useMap } from "react-leaflet";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from "recharts";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "./index.css";

// --- CORRECCIÓN DE ICONOS ---
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

let DefaultIcon = L.icon({
    iconUrl: icon,
    shadowUrl: iconShadow,
    iconSize: [25, 41],
    iconAnchor: [12, 41]
});
L.Marker.prototype.options.icon = DefaultIcon;

const CENTROIDES_BOGOTA = {
  "Bogotá": [4.598888, -74.080833],
  "Usaquén": [4.7082, -74.0308],
  "Chapinero": [4.6486, -74.0595],
  "Santa Fe": [4.6042, -74.0672],
  "San Cristóbal": [4.5739, -74.0861],
  "Usme": [4.4705, -74.1131],
  "Tunjuelito": [4.5755, -74.1371],
  "Bosa": [4.6218, -74.1930],
  "Kennedy": [4.6307, -74.1535],
  "Fontibón": [4.6732, -74.1457],
  "Engativá": [4.7011, -74.1132],
  "Suba": [4.7411, -74.0848],
  "Barrios Unidos": [4.6675, -74.0792],
  "Teusaquillo": [4.6414, -74.0852],
  "Los Mártires": [4.6041, -74.0872],
  "Antonio Nariño": [4.5882, -74.1012],
  "Puente Aranda": [4.6162, -74.1162],
  "La Candelaria": [4.5968, -74.0747],
  "Rafael Uribe Uribe": [4.5714, -74.1137],
  "Ciudad Bolívar": [4.5152, -74.1552],
  "Sumapaz": [4.0116, -74.2255]
};

// Componente para ajustar la vista del mapa automáticamente
function ChangeView({ data }) {
  const map = useMap();
  useEffect(() => {
    // Forzar recalcular tamaño para evitar que el mapa cargue incompleto (baldosas grises)
    const timer = setTimeout(() => {
      map.invalidateSize();
    }, 400);

    if (data && data.features && data.features.length > 0) {
      try {
        const geojsonLayer = L.geoJSON(data);
        map.fitBounds(geojsonLayer.getBounds(), { padding: [20, 20], maxZoom: 15 });
      } catch (e) {
        console.error("Error ajustando vista:", e);
      }
    }
    return () => clearTimeout(timer);
  }, [data, map]);
  return null;
}

function App() {
  const [localidades, setLocalidades] = useState([]);
  const [localidadActiva, setLocalidadActiva] = useState("Bogotá");
  const [pregunta, setPregunta] = useState("");
  const [respuestas, setRespuestas] = useState([]);
  const [geoData, setGeoData] = useState(null);
  const [limiteData, setLimiteData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch("http://localhost:8000/localidades")
      .then(r => r.json())
      .then(d => setLocalidades(d.localidades || []))
      .catch(e => console.error("Error cargando localidades:", e));
  }, []);

  const cargarLimite = async (loc) => {
    try {
      const res = await fetch(`http://localhost:8000/mapa-data/${loc}/limite`);
      if (res.ok) {
        const d = await res.json();
        if (!d.error) {
          setLimiteData(d);
        } else {
          console.warn("Límite no encontrado:", d.error);
          setLimiteData(null);
        }
      }
    } catch (err) {
      console.error("Error cargando límite espacial:", err);
      setLimiteData(null);
    }
  };

  useEffect(() => {
    cargarLimite(localidadActiva);
  }, [localidadActiva]);

  const consultarAgente = async () => {
    if (!pregunta) return;
    setLoading(true);
    setRespuestas(prev => [...prev, { role: "user", text: pregunta }]);
    
    // Ya no limpiamos capas automáticamente para permitir persistencia
    // setGeoData(null);
    
    try {
      const res = await fetch("http://localhost:8000/consulta", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pregunta, localidad: localidadActiva })
      });
      const data = await res.json();
      setRespuestas(prev => [...prev, { role: "agente", text: data.respuesta }]);
      
      if (data.localidad_usada && data.localidad_usada !== localidadActiva) {
        setLocalidadActiva(data.localidad_usada);
        setLimiteData(null); // Forzar recarga del límite
      }
      
      if (data.herramientas_usadas?.includes("clusters")) {
        cargarCapa("clusters", data.localidad_usada || localidadActiva);
      } else if (data.herramientas_usadas?.includes("heat")) {
        cargarCapa("heat", data.localidad_usada || localidadActiva);
      }
    } catch (err) {
      setRespuestas(prev => [...prev, { role: "agente", text: "Error de conexión con el agente." }]);
    }
    setLoading(false);
    setPregunta("");
  };

  const cargarCapa = async (tipo, loc) => {
    try {
      const res = await fetch(`http://localhost:8000/mapa-data/${loc}/${tipo}`);
      if (res.ok) {
        const d = await res.json();
        if (d.error) {
          console.log("Capa no disponible aún");
        } else {
          setGeoData(d);
        }
      }
    } catch (err) {
      console.error("Error cargando capa espacial:", err);
    }
  };

  const onEachFeature = (feature, layer) => {
    if (feature.properties && feature.properties.total_accidentes) {
        layer.bindPopup(`<b>${feature.properties.tipo}</b><br/>Siniestros: ${feature.properties.total_accidentes}`);
    }
  };

  const mockKpiData = [
    { name: 'Peatones', victimas: 120 },
    { name: 'Ciclistas', victimas: 85 },
    { name: 'Motociclistas', victimas: 310 },
  ];

  return (
    <div className="layout">
      <header className="header">
        <h1>SIVIBOG: Inteligencia Territorial</h1>
      </header>

      <main className="grid">
        <section className="chat-section card">
          <h2>Agentes Especialistas IA</h2>
          <div className="chat-box">
             {respuestas.map((r, i) => (
               <div key={i} className={`message ${r.role}`}>{r.text}</div>
             ))}
             {loading && <div className="message agente">Procesando análisis territorial...</div>}
          </div>
          <div className="chat-input">
            <input 
               type="text" 
               placeholder="Ej: ¿Cuáles son los puntos críticos en Usaquén?" 
               value={pregunta} 
               onChange={e => setPregunta(e.target.value)}
               onKeyPress={e => e.key === 'Enter' && consultarAgente()}
            />
            <button onClick={consultarAgente} className="btn primary">Consultar</button>
          </div>
        </section>

        <section className="map-section card">
          <h2>Visor Cartográfico - {localidadActiva}</h2>
          <div className="map-container" style={{ background: "#1a1a1a" }}>
            <MapContainer 
                center={CENTROIDES_BOGOTA[localidadActiva] || [4.6097, -74.0817]} 
                zoom={localidadActiva === "Bogotá" ? 11 : 13} 
                style={{ height: "100%", width: "100%" }}
            >
              <ChangeView data={limiteData} />
              <TileLayer 
                  url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                  attribution="&copy; CARTO"
              />
              {limiteData && (
                <GeoJSON 
                  data={limiteData} 
                  key={`limite-${localidadActiva}-${limiteData.features?.length}`} 
                  style={{ 
                    color: localidadActiva === "Bogotá" ? "#f1c40f" : "#3498db", 
                    weight: localidadActiva === "Bogotá" ? 4 : 3, 
                    fillOpacity: 0.05, 
                    dashArray: localidadActiva === "Bogotá" ? "" : "5, 5" 
                  }} 
                />
              )}
              {geoData && (
                <GeoJSON 
                  data={geoData} 
                  key={`geo-${localidadActiva}-${geoData.features?.length}-${geoData.features?.[0]?.properties?.tipo || 'capa'}`} 
                  onEachFeature={onEachFeature}
                  style={(feature) => ({
                    color: feature.properties?.tipo === "Zona Crítica" ? "#e74c3c" : "#f1c40f",
                    weight: 2,
                    fillColor: feature.properties?.tipo === "Zona Crítica" ? "#e74c3c" : "#f1c40f",
                    fillOpacity: 0.6,
                    radius: 6
                  })}
                  pointToLayer={(feature, latlng) => {
                    return L.circleMarker(latlng);
                  }}
                />
              )}
            </MapContainer>
          </div>
        </section>
        
      </main>
    </div>
  );
}

export default App;