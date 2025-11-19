'use client';

import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { Ambulance, Coordinates, Route, Hospital, EmergencyRequest } from '@/lib/types';
import { Card } from '@/components/ui/card';
import 'leaflet/dist/leaflet.css';

interface LiveMapProps {
  ambulance?: Ambulance;
  route?: Route;
  patientLocation?: Coordinates;
  hospital?: Hospital;
  request?: EmergencyRequest;
}

export const LiveMap: React.FC<LiveMapProps> = ({
  ambulance,
  route,
  patientLocation,
  hospital,
  request,
}) => {
  const mapRef = useRef<L.Map | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const ambulanceMarkerRef = useRef<L.Marker | null>(null);
  const routePolylineRef = useRef<L.Polyline | null>(null);

  const [animationIndex, setAnimationIndex] = useState(0);

  // Initialize map once
  useEffect(() => {
    if (!containerRef.current || !patientLocation) return;

    if (!mapRef.current) {
      mapRef.current = L.map(containerRef.current, {
        center: [patientLocation.lat, patientLocation.lng],
        zoom: 13,
      });

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 19,
      }).addTo(mapRef.current);
    }
  }, [patientLocation]);

  // Update markers and route
  useEffect(() => {
    if (!mapRef.current || !patientLocation) return;
    const map = mapRef.current;

    // Patient marker
    const patientMarker = L.marker([patientLocation.lat, patientLocation.lng], {
      icon: L.icon({
        iconUrl:
          'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="rgb(220, 38, 38)"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8z"/></svg>',
        iconSize: [32, 32],
        iconAnchor: [16, 16],
      }),
    }).addTo(map);
    patientMarker.bindPopup('Emergency Location').openPopup();

    // Hospital marker
    let hospitalMarker: L.Marker | null = null;
    if (hospital) {
      hospitalMarker = L.marker([hospital.location.lat, hospital.location.lng], {
        icon: L.icon({
          iconUrl:
            'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="rgb(59, 130, 246)"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 9.5h-1.5v4h-1v-4H10v-1h1.5V7h1v4.5H14v1z"/></svg>',
          iconSize: [32, 32],
          iconAnchor: [16, 16],
        }),
      }).addTo(map);
      hospitalMarker.bindPopup(hospital.name).openPopup();
    }

    // Route polyline
    if (route && route.polyline.length > 0) {
      if (routePolylineRef.current) {
        routePolylineRef.current.setLatLngs(route.polyline.map((p) => [p.lat, p.lng]));
      } else {
        routePolylineRef.current = L.polyline(
          route.polyline.map((p) => [p.lat, p.lng]),
          {
            color: route.traffic_level === 'high' ? '#ea580c' : '#3b82f6',
            weight: 4,
            opacity: 0.8,
            className: 'route-line',
          }
        ).addTo(map);
      }

      // --- Animate ambulance along route ---
      if (ambulance) {
        const coords = route.polyline.map((p) => [p.lat, p.lng] as [number, number]);
        if (!ambulanceMarkerRef.current) {
          ambulanceMarkerRef.current = L.marker(coords[0], {
            icon: L.icon({
              iconUrl:
                'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="rgb(234, 88, 12)"><path d="M18 18.5a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0M2 6h14v9H2zm16-1v7h2V5z"/></svg>',
              iconSize: [32, 32],
              iconAnchor: [16, 16],
            }),
          }).addTo(map);
        }

        let idx = 0;
        const interval = setInterval(() => {
          if (idx < coords.length && ambulanceMarkerRef.current) {
            ambulanceMarkerRef.current.setLatLng(coords[idx]);
            idx++;
          } else {
            clearInterval(interval);
          }
        }, 1000); // move every 1 second
      }
    }

    return () => {
      patientMarker.remove();
      hospitalMarker?.remove();
    };
  }, [ambulance, route, patientLocation, hospital]);

  return (
    <Card className="w-full animate-slide-in-up">
      <div className="p-4 md:p-6 space-y-4">
        <h3 className="font-semibold text-lg">Live Ambulance Tracking</h3>
        <div
          ref={containerRef}
          style={{ width: '100%', height: '400px' }}
          className="rounded-lg border border-border overflow-hidden shadow-lg"
        />

        {request && (
          <div className="p-3 md:p-4 bg-accent/15 border border-accent/30 rounded-lg animate-pulse-glow">
            <h4 className="font-semibold mb-2">
              Status: <span className="text-accent">{request.status.toUpperCase()}</span>
            </h4>
            <p className="text-sm">Patient: {request.patient_name}</p>
            <p className="text-sm">Condition: {request.medical_condition}</p>
            {ambulance && (
              <p className="text-sm mt-2">
                ETA: <strong>{Math.floor(ambulance.estimated_arrival / 60)}m {ambulance.estimated_arrival % 60}s</strong>
              </p>
            )}
          </div>
        )}
      </div>
    </Card>
  );
};
