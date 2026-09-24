'use client';

import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

export interface UfoCase {
  id: string | number;
  case_id?: string;
  title: string;
  asset_file_name?: string;
  search_url?: string;
  date: string;
  location: string;
  status?: string;
  translation_snippet?: string;
  original_text?: string;
  latitude: number;
  longitude: number;
}

export interface MapProps {
  cases: UfoCase[];
  selectedCase?: UfoCase | null;
  onMarkerClick: (c: UfoCase) => void;
}

const createMarkerIcon = (isSelected: boolean) => {
  return L.divIcon({
    className: 'custom-uap-pin',
    html: `<div style="
      width: ${isSelected ? '16px' : '10px'};
      height: ${isSelected ? '16px' : '10px'};
      background-color: ${isSelected ? '#38bdf8' : '#0284c7'};
      border: 2px solid ${isSelected ? '#ffffff' : '#bae6fd'};
      border-radius: 50%;
      box-shadow: 0 0 ${isSelected ? '14px #38bdf8' : '5px #0284c7'};
      cursor: pointer;
      transition: transform 0.2s ease;
    "></div>`,
    iconSize: [isSelected ? 16 : 10, isSelected ? 16 : 10],
    iconAnchor: [isSelected ? 8 : 5, isSelected ? 8 : 5],
  });
};

export default function MapComponent({ cases, selectedCase, onMarkerClick }: MapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: [30, 0],
      zoom: 2,
      minZoom: 1.5,
      maxBounds: [[-85, -180], [85, 180]],
      attributionControl: true
    });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 18,
      attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
    }).addTo(map);

    markersLayerRef.current = L.layerGroup().addTo(map);
    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapInstanceRef.current;
    const layer = markersLayerRef.current;
    if (!map || !layer) return;

    layer.clearLayers();

    const validCases = cases.filter(
      c => typeof c.latitude === 'number' && typeof c.longitude === 'number' && !isNaN(c.latitude) && !isNaN(c.longitude)
    );

    validCases.forEach((c) => {
      const lat = c.latitude;
      const lng = c.longitude;

      const isSelected = selectedCase?.id === c.id;
      const marker = L.marker([lat, lng], {
        icon: createMarkerIcon(isSelected),
        zIndexOffset: isSelected ? 1000 : 0
      });

      const popup = document.createElement('div');
      const heading = document.createElement('strong');
      heading.textContent = c.title;
      const place = document.createElement('p');
      place.textContent = c.location || 'Místo neuvedeno';
      popup.append(heading, place);
      marker.bindPopup(popup);

      marker.on('click', () => {
        onMarkerClick(c);
      });

      layer.addLayer(marker);
    });
  }, [cases, selectedCase, onMarkerClick]);

  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !selectedCase) return;

    if (
      typeof selectedCase.latitude === 'number' &&
      typeof selectedCase.longitude === 'number' &&
      !isNaN(selectedCase.latitude) &&
      !isNaN(selectedCase.longitude)
    ) {
      map.flyTo([selectedCase.latitude, selectedCase.longitude], 5, {
        duration: 1.2,
        easeLinearity: 0.25
      });
    }
  }, [selectedCase]);

  return <div ref={mapContainerRef} className="w-full h-full" />;
}
