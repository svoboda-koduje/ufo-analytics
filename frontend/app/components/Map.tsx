'use client';

import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Oprava výchozí ikony markeru v Next.js
const defaultIcon = L.icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

export default function Map({ cases, onMarkerClick }: { cases: any[], onMarkerClick: (c: any) => void }) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);

  useEffect(() => {
    if (!mapRef.current) return;

    // Inicializace mapy pouze jednou
    if (!mapInstanceRef.current) {
      mapInstanceRef.current = L.map(mapRef.current).setView([37.2350, -115.8111], 3);
      L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="https://carto.com/">CARTO</a>'
      }).addTo(mapInstanceRef.current);
    }

    const map = mapInstanceRef.current;

    // Vyčištění starých markerů
    map.eachLayer((layer: any) => {
      if (layer instanceof L.Marker) {
        map.removeLayer(layer);
      }
    });

    // Vykreslení všech platných bodů z katalogu
    cases.forEach((c) => {
      if (c.latitude && c.longitude) {
        const marker = L.marker([c.latitude, c.longitude], { icon: defaultIcon }).addTo(map);
        marker.bindPopup(`<b>${c.id}</b><br/>${c.title}<br/>📍 ${c.location}`);
        marker.on('click', () => {
          onMarkerClick(c);
        });
      }
    });
  }, [cases, onMarkerClick]);

  return <div ref={mapRef} style={{ height: '100%', width: '100%', borderRadius: '0.5rem' }} />;
}
