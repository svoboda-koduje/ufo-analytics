'use client';

import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

interface UfoCase {
  id: string | number;
  title: string;
  location: string;
  latitude: number;
  longitude: number;
}

interface MapProps {
  cases: UfoCase[];
  selectedCase: UfoCase | null;
  onMarkerClick: (c: UfoCase) => void;
}

// Vytvoření stylizované kruhové ikony
const createCustomIcon = (isSelected: boolean) => {
  return L.divIcon({
    className: 'custom-map-pin',
    html: `<div style="
      width: ${isSelected ? '18px' : '12px'};
      height: ${isSelected ? '18px' : '12px'};
      background-color: ${isSelected ? '#38bdf8' : '#0284c7'};
      border: 2px solid #ffffff;
      border-radius: 50%;
      box-shadow: 0 0 ${isSelected ? '12px #38bdf8' : '6px #0284c7'};
      transition: all 0.2s ease;
    "></div>`,
    iconSize: [isSelected ? 18 : 12, isSelected ? 18 : 12],
    iconAnchor: [isSelected ? 9 : 6, isSelected ? 9 : 6],
  });
};

export default function MapComponent({ cases, selectedCase, onMarkerClick }: MapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);

  // Inicializace mapy
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: [30, 0],
      zoom: 2,
      minZoom: 1.5,
      maxBounds: [[-85, -180], [85, 180]],
      attributionControl: false
    });

    // Tmavá CartoDB podkladová mapa
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 19,
    }).addTo(map);

    markersLayerRef.current = L.layerGroup().addTo(map);
    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Vykreslení bodů na mapě
  useEffect(() => {
    const map = mapInstanceRef.current;
    const markersLayer = markersLayerRef.current;
    if (!map || !markersLayer) return;

    markersLayer.clearLayers();

    const validCases = cases.filter(
      c => typeof c.latitude === 'number' && typeof c.longitude === 'number' && !isNaN(c.latitude) && !isNaN(c.longitude)
    );

    validCases.forEach((c, idx) => {
      // Jemný rozptyl při identických souřadnicích pro přehlednost
      const offsetLat = (idx % 5 - 2) * 0.08;
      const offsetLng = ((idx * 3) % 5 - 2) * 0.08;
      const lat = c.latitude + offsetLat;
      const lng = c.longitude + offsetLng;

      const isSelected = selectedCase?.id === c.id;
      const marker = L.marker([lat, lng], { icon: createCustomIcon(isSelected) });

      marker.bindPopup(`
        <div style="font-family: monospace; font-size: 11px; color: #0f172a;">
          <strong style="color: #0284c7;">ID: ${c.id}</strong><br/>
          <span>${c.title}</span><br/>
          <span style="color: #64748b;">📍 ${c.location}</span>
        </div>
      `);

      marker.on('click', () => {
        onMarkerClick(c);
      });

      markersLayer.addLayer(marker);
    });
  }, [cases, selectedCase, onMarkerClick]);

  // Plynulé přiblížení na vybraný případ
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !selectedCase) return;

    if (
      typeof selectedCase.latitude === 'number' && 
      typeof selectedCase.longitude === 'number' &&
      !isNaN(selectedCase.latitude) && 
      !isNaN(selectedCase.longitude)
    ) {
      map.flyTo([selectedCase.latitude, selectedCase.longitude], 6, {
        duration: 1.2,
        easeLinearity: 0.25
      });
    }
  }, [selectedCase]);

  return <div ref={mapContainerRef} className="w-full h-full" />;
}
