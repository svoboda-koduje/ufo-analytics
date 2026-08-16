'use client';

import { useEffect, useRef } from 'react';
import 'leaflet/dist/leaflet.css';

export default function MapComponent({ cases, onMarkerClick }: { cases: any[], onMarkerClick: (c: any) => void }) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);

  useEffect(() => {
    // Dynamický import Leaflet uvnitř useEffect zajistí, že se kód nespustí na serveru (SSR)
    import('leaflet').then((L) => {
      if (!mapRef.current) return;

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

      const defaultIcon = L.icon({
        iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
        iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
        shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34],
      });

      cases.forEach((c) => {
        if (c.latitude && c.longitude) {
          const marker = L.marker([c.latitude, c.longitude], { icon: defaultIcon }).addTo(map);
          marker.bindPopup(`<b>${c.id}</b><br/>${c.title}<br/>📍 ${c.location}`);
          marker.on('click', () => {
            onMarkerClick(c);
          });
        }
      });
    });
  }, [cases, onMarkerClick]);

  return <div ref={mapRef} style={{ height: '100%', width: '100%', borderRadius: '0.5rem' }} />;
}
