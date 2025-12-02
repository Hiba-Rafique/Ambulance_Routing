'use client';

import React, { useEffect, useRef, useState } from 'react';
import type * as Leaflet from 'leaflet';
import { Coordinates, City } from '@/lib/types';
import { Card } from '@/components/ui/card';

interface PatientMapProps {
  city: City;
  onLocationSelect: (location: Coordinates) => void;
  selectedLocation?: Coordinates;
}

export const PatientMap: React.FC<PatientMapProps> = ({ 
  city, 
  onLocationSelect, 
  selectedLocation 
}) => {
  const mapRef = useRef<Leaflet.Map | null>(null);
  const markerRef = useRef<Leaflet.Marker | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Leaflet depends on the `window` object, so we load it only on the
    // client inside this effect. This avoids the "window is not defined"
    // error during Next.js server-side rendering.
    if (typeof window === 'undefined' || !containerRef.current) return;

    // Dynamically import Leaflet only on the client.
    const L = require('leaflet') as typeof Leaflet;

    // Initialize map
    mapRef.current = L.map(containerRef.current).setView(
      [city.center.lat, city.center.lng],
      12
    );

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors',
      maxZoom: 19,
    }).addTo(mapRef.current);

    // Add click event to map
    mapRef.current.on('click', (e) => {
      const { lat, lng } = e.latlng;
      onLocationSelect({ lat, lng });

      // Update marker
      if (markerRef.current) {
        markerRef.current.setLatLng([lat, lng]);
      } else {
        markerRef.current = L.marker([lat, lng], {
          icon: L.icon({
            iconUrl: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="rgb(255, 107, 53)"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8z"/></svg>',
            iconSize: [40, 40],
            iconAnchor: [20, 20],
            popupAnchor: [0, -20],
          }),
        }).addTo(mapRef.current!);

        markerRef.current.bindPopup('Patient Location', { className: 'dark-popup' }).openPopup();
      }
    });

    // Add existing marker if location provided
    if (selectedLocation && !markerRef.current && mapRef.current) {
      markerRef.current = L.marker([selectedLocation.lat, selectedLocation.lng]).addTo(mapRef.current);
      markerRef.current.bindPopup('Patient Location').openPopup();
    }

    return () => {
      mapRef.current?.remove();
    };
  }, [city, onLocationSelect]);

  return (
    <Card className="w-full border-border/50 animate-slide-in-up">
      <div className="p-4 md:p-6 space-y-4">
        <div>
          <h3 className="font-bold text-lg md:text-xl mb-1">Select Patient Location</h3>
          <p className="text-sm text-muted-foreground">Click on the map to mark the emergency location</p>
        </div>
        <div ref={containerRef} className="w-full h-80 md:h-96 rounded-lg border border-border overflow-hidden shadow-lg" />
        {selectedLocation && (
          <div className="p-3 md:p-4 bg-accent/15 border border-accent/30 rounded-lg animate-fade-in">
            <p className="text-xs text-muted-foreground mb-2 uppercase tracking-wide font-semibold">Location Selected</p>
            <p className="text-xs md:text-sm text-accent font-semibold">Emergency coordinates marked on map</p>
          </div>
        )}
      </div>
    </Card>
  );
};
