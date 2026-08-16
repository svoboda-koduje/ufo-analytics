'use client';

import dynamic from 'next/dynamic';

const MapComponent = dynamic(() => import('./MapComponent'), { 
  ssr: false, 
  loading: () => <div className="flex h-full items-center justify-center text-slate-500">Načítám GIS modul...</div> 
});

interface MapWrapperProps {
  cases: any[];
  onMarkerClick?: (c: any) => void;
}

export default function MapWrapper({ cases, onMarkerClick }: MapWrapperProps) {
  return <MapComponent cases={cases} onMarkerClick={onMarkerClick || (() => {})} />;
}
