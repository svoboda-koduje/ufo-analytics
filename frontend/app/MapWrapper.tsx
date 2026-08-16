'use client';
import dynamic from 'next/dynamic';
import React from 'react';

// Zde bezpečně načteme mapu bez server-side renderingu
const MapComponent = dynamic(() => import('./MapComponent'), { ssr: false });

export default function MapWrapper({ cases }: { cases: any[] }) {
  return <MapComponent cases={cases} />;
}
