'use client';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { useEffect } from 'react';

// Oprava ikon pro Leaflet v Next.js
const icon = L.icon({
  iconUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

export default function Map({ cases, onMarkerClick }: { cases: any[], onMarkerClick: (c: any) => void }) {
  useEffect(() => {
    // Force a re-render to ensure tiles load correctly
    window.dispatchEvent(new Event('resize'));
  }, []);

  return (
    <MapContainer center={[37.2350, -115.8111]} zoom={3} style={{ height: '100%', width: '100%', borderRadius: '0.5rem' }}>
      <TileLayer 
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" 
        attribution='&copy; <a href="https://carto.com/">CARTO</a>'
      />
      {cases.map((c) => (
        <Marker key={c.id} position={[c.latitude || 37.2350, c.longitude || -115.8111]} icon={icon} eventHandlers={{ click: () => onMarkerClick(c) }}>
          <Popup>
            <strong className="text-slate-800">{c.title}</strong><br/>
            {c.location}
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}