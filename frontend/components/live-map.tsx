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
  const animationFrameRef = useRef<number | null>(null);

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
      const coords = route.polyline.map((p) => [p.lat, p.lng] as [number, number]);

      if (routePolylineRef.current) {
        routePolylineRef.current.setLatLngs(coords);
      } else {
        routePolylineRef.current = L.polyline(coords, {
          color: route.traffic_level === 'high' ? '#ea580c' : '#3b82f6',
          weight: 4,
          opacity: 0.8,
          className: 'route-line',
        }).addTo(map);
      }

      // Position ambulance along the polyline using a local smooth
      // animation so the marker always moves steadily towards the goal.
      // We intentionally ignore backend progress here to avoid the
      // marker snapping backwards if timings diverge.
      if (ambulance && coords.length > 1) {
        if (!ambulanceMarkerRef.current) {
          ambulanceMarkerRef.current = L.marker(coords[0], {
            icon: L.divIcon({
              html: '<span style="font-size: 34px; line-height: 1;">🚑</span>',
              className: 'ambulance-marker',
              iconSize: [34, 34],
              iconAnchor: [17, 17],
            }),
          }).addTo(map);
        }

        // Local animation: move from start to end over a reasonable
        // duration based on route.duration.
        const durationSeconds = route.duration > 0 ? route.duration : 30;
        const totalDurationMs = Math.min(Math.max(durationSeconds * 1000, 15000), 60000); // 15–60s

        const start = performance.now();

        const animate = (now: number) => {
          const elapsed = now - start;
          const t = Math.min(1, elapsed / totalDurationMs);

          const pathPos = t * (coords.length - 1);
          const idx = Math.floor(pathPos);
          const frac = pathPos - idx;

          let lat: number;
          let lng: number;

          if (idx >= coords.length - 1) {
            [lat, lng] = coords[coords.length - 1];
          } else {
            const [lat1, lng1] = coords[idx];
            const [lat2, lng2] = coords[idx + 1];
            lat = lat1 + (lat2 - lat1) * frac;
            lng = lng1 + (lng2 - lng1) * frac;
          }

          if (ambulanceMarkerRef.current) {
            ambulanceMarkerRef.current.setLatLng([lat, lng]);
          }

          if (t < 1) {
            animationFrameRef.current = requestAnimationFrame(animate);
          }
        };

        if (animationFrameRef.current !== null) {
          cancelAnimationFrame(animationFrameRef.current);
        }
        animationFrameRef.current = requestAnimationFrame(animate);
      }
    }

    return () => {
      patientMarker.remove();
      hospitalMarker?.remove();
      if (animationFrameRef.current !== null) {
        cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = null;
      }
    };
  }, [route, patientLocation, hospital, ambulance]);

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