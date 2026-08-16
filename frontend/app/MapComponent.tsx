// @ts-nocheck
'use client';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import React from 'react';

// Fix pro ikony markerů v React-Leaflet
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

export default function MapComponent({ cases }: { cases: any[] }) {
  return (
    <MapContainer 
      center={[25, 0]} 
      zoom={2} 
      style={{ height: '100%', width: '100%', backgroundColor: '#0f172a' }}
    >
      <TileLayer 
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" 
      />
      {cases.map((c: any) => (
        c.latitude && c.longitude && (
          <Marker key={c.id} position={[c.latitude, c.longitude]}>
            <Popup>
              <div className="text-slate-800">
                <strong className="block text-sm border-b pb-1 mb-1">{c.title}</strong>
                <span className="text-xs">Status: <b>{c.status}</b></span>
              </div>
            </Popup>
          </Marker>
        )
      ))}
    </MapContainer>
  );
}