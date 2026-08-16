'use client';

import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

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
        attribution: '&copy; CARTO'
      }).addTo(mapInstanceRef.current);
    }

    const map = mapInstanceRef.current;

    // Odstranění starých markerů před vykreslením nových
    map.eachLayer((layer: any) => {
      if (layer instanceof L.Marker) {
        map.removeLayer(layer);
      }
    });

    // Přidání markerů pro aktuální filtrované případy
    cases.forEach((c) => {
      if (c.latitude && c.longitude) {
        const marker = L.marker([c.latitude, c.longitude]).addTo(map);
        marker.bindPopup(`<b>${c.title}</b><br/>${c.location}`);
        marker.on('click', () => {
          onMarkerClick(c);
        });
      }
    });

  }, [cases, onMarkerClick]);

  return <div ref={mapRef} style={{ height: '100%', width: '100%', borderRadius: '0.5rem' }} />;
}
