'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Header } from '@/components/header';
import { Footer } from '@/components/footer';
import { CitySelect } from '@/components/city-select';
import { PatientMap } from '@/components/patient-map';
import { HospitalSelect } from '@/components/hospital-select';
import { ConfirmRequest } from '@/components/confirm-request';
import { LiveMap } from '@/components/live-map';
import { DijkstraVisualizer } from '@/components/dijkstra-visualizer';
import { City, Hospital, Coordinates, EmergencyRequest, Ambulance, Route } from '@/lib/types';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { createAutoEmergencyRequest, fetchHospitalsForCity, geocodeAddress, fetchCities } from '@/lib/api';

// Hospitals will now be loaded from the backend based on the selected city.

export default function Home() {
  const [step, setStep] = useState<'city' | 'location' | 'hospital' | 'confirm' | 'live'>('city');
  const [cities, setCities] = useState<City[]>([]);
  const [selectedCity, setSelectedCity] = useState<City | undefined>();
  const [selectedLocation, setSelectedLocation] = useState<Coordinates | undefined>();
  const [selectedHospital, setSelectedHospital] = useState<Hospital | undefined>();
  const [hospitals, setHospitals] = useState<Hospital[]>([]);
  const [hospitalMode, setHospitalMode] = useState<'auto' | 'manual'>('auto');
  const [request, setRequest] = useState<EmergencyRequest | undefined>();
  const [ambulance, setAmbulance] = useState<Ambulance | undefined>();
  const [route, setRoute] = useState<Route | undefined>();
  const [isLoading, setIsLoading] = useState(false);
  const [manualLocation, setManualLocation] = useState<{ address: string; label: string }>({
    address: '',
    label: '',
  });
  const wsRef = useRef<WebSocket | null>(null);
  const [showDijkstra, setShowDijkstra] = useState(false);
  const [dijkstraOffset, setDijkstraOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDraggingDijkstra, setIsDraggingDijkstra] = useState(false);
  const dragStartRef = useRef<{ x: number; y: number } | null>(null);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDraggingDijkstra || !dragStartRef.current) return;
      const { x, y } = dragStartRef.current;
      setDijkstraOffset({ x: e.clientX - x, y: e.clientY - y });
    };

    const handleMouseUp = () => {
      if (isDraggingDijkstra) {
        setIsDraggingDijkstra(false);
      }
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDraggingDijkstra]);

  useEffect(() => {
    const loadCities = async () => {
      try {
        const backendCities = await fetchCities();
        const mapped: City[] = backendCities.map((c) => {
          // Default fallback roughly covering Pakistan
          let bounds = { north: 37.0, south: 23.0, east: 77.0, west: 60.0 };
          let center = { lat: 30.3753, lng: 69.3451 };

          const name = c.name.toLowerCase();

          if (name === 'karachi') {
            bounds = { north: 25.05, south: 24.75, east: 67.35, west: 66.85 };
            center = { lat: 24.8607, lng: 67.0011 };
          } else if (name === 'lahore') {
            bounds = { north: 31.65, south: 31.35, east: 74.45, west: 73.95 };
            center = { lat: 31.5204, lng: 74.3587 };
          } else if (name === 'islamabad') {
            bounds = { north: 33.85, south: 33.55, east: 73.35, west: 72.85 };
            center = { lat: 33.6844, lng: 73.0479 };
          } else if (name === 'rawalpindi') {
            bounds = { north: 33.65, south: 33.35, east: 73.45, west: 72.95 };
            center = { lat: 33.5731, lng: 73.1795 };
          } else if (name === 'multan') {
            bounds = { north: 30.35, south: 29.95, east: 72.05, west: 71.35 };
            center = { lat: 30.1978, lng: 71.4455 };
          }

          return {
            id: `city_${c.id}`,
            name: c.name,
            backendId: c.id,
            bounds,
            center,
          };
        });
        setCities(mapped);
      } catch (error) {
        console.error('Failed to load cities', error);
      }
    };

    loadCities();
  }, []);

  // Real WebSocket connection for live updates
  useEffect(() => {
    if (step === 'live' && request) {
      const wsUrl = `ws://localhost:8000/ws/tracking/${request.id}`;
      console.log('Connecting to WebSocket:', wsUrl);

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket Connected');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('WebSocket Message:', data);

          if (data.status === 'in-transit' || data.status === 'busy') {
            setAmbulance((prev) => {
              if (!prev) return prev;
              return {
                ...prev,
                current_location: data.current_location,
                // Update ETA if provided (converted to seconds), or decrease it roughly
                estimated_arrival: data.eta_seconds !== undefined
                  ? Math.round(data.eta_seconds)
                  : Math.max(0, prev.estimated_arrival - 2),
                status: 'en_route',
                progress: typeof data.progress === 'number'
                  ? Math.min(1, Math.max(0, data.progress))
                  : prev.progress,
              };
            });
          } else if (data.status === 'completed') {
            setAmbulance((prev) => {
              if (!prev) return prev;
              return {
                ...prev,
                current_location: data.current_location,
                estimated_arrival: 0,
                status: 'available',
                progress: 1,
              };
            });
            setRequest((prev) => prev ? { ...prev, status: 'completed', completed_at: data.completed_at } : undefined);
            // Optionally close socket or keep it open
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket Error:', error);
      };

      ws.onclose = () => {
        console.log('WebSocket Disconnected');
      };

      return () => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.close();
        }
      };
    }
  }, [step, request]);

  // Fallback client-side ETA countdown to keep the timer moving even if
  // WebSocket updates are intermittent. Backend updates (eta_seconds)
  // still take precedence whenever they arrive.
  useEffect(() => {
    if (step !== 'live' || !ambulance) return;

    const interval = setInterval(() => {
      setAmbulance((prev) => {
        if (!prev) return prev;
        if (prev.estimated_arrival <= 0) return prev;
        return {
          ...prev,
          estimated_arrival: Math.max(0, prev.estimated_arrival - 1),
        };
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [step, ambulance]);

  const handleCitySelect = async (city: City) => {
    setSelectedCity(city);
    setSelectedHospital(undefined);
    setStep('location');

    const numericCityId = city.backendId;

    if (numericCityId) {
      try {
        const loadedHospitals = await fetchHospitalsForCity(numericCityId);
        setHospitals(loadedHospitals);
      } catch (error) {
        console.error('Failed to load hospitals for city', error);
        setHospitals([]);
      }
    } else {
      setHospitals([]);
    }
  };

  const handleLocationSelect = (location: Coordinates) => {
    setSelectedLocation(location);
    setHospitalMode('auto');
    setSelectedHospital(undefined);
    setStep('hospital');
  };

  const handleHospitalSelect = (hospital: Hospital) => {
    setSelectedHospital(hospital);
    setStep('confirm');
  };

  // Compute the single nearest hospital by straight-line distance for
  // frontend display / auto-selection mode. The backend still uses the
  // full graph + Dijkstra for the true routing decision.
  const autoSelectedHospital: Hospital | undefined = React.useMemo(() => {
    if (!selectedLocation || hospitals.length === 0) return undefined;

    let best: Hospital | undefined;
    let bestDistSq: number | undefined;

    for (const h of hospitals) {
      const dLat = h.location.lat - selectedLocation.lat;
      const dLng = h.location.lng - selectedLocation.lng;
      const distSq = dLat * dLat + dLng * dLng;

      if (bestDistSq === undefined || distSq < bestDistSq) {
        bestDistSq = distSq;
        best = h;
      }
    }

    return best;
  }, [hospitals, selectedLocation]);

  const handleConfirmRequest = async (requestData: Partial<EmergencyRequest>) => {
    if (!selectedCity || !selectedLocation || !selectedHospital) return;

    setIsLoading(true);

    try {
      const numericCityId = selectedCity.backendId;

      const apiResponse = await createAutoEmergencyRequest({
        cityNumericId: numericCityId,
        location: selectedLocation,
        callerName: requestData.patient_name || '',
        callerPhone: requestData.contact_number || '',
      });

      const newRequest: EmergencyRequest = {
        id: String(apiResponse.request_id),
        patient_location: selectedLocation,
        patient_name: requestData.patient_name ?? '',
        contact_number: requestData.contact_number ?? '',
        medical_condition: requestData.medical_condition ?? '',
        city_id: selectedCity.id,
        hospital_id: selectedHospital.id,
        status: 'confirmed',
        created_at: new Date().toISOString(),
      };

      setRequest(newRequest);

      // For now we still simulate ambulance assignment and route calculation
      // on the frontend side until the backend logic for that part is wired in.
      const mockAmbulance: Ambulance = {
        id: `amb_${Math.floor(Math.random() * 1000)}`,
        current_location: selectedHospital.location,
        status: 'en_route',
        vehicle_type: 'advanced_life_support',
        // Use the estimated travel time from the backend, or fall back to 0 if null
        estimated_arrival: (apiResponse.estimated_travel_time !== null && apiResponse.estimated_travel_time !== undefined)
          ? Math.round(apiResponse.estimated_travel_time * 60)
          : 0,
      };

      const polylineFromBackend = apiResponse.route_nodes && apiResponse.route_nodes.length > 0
        ? apiResponse.route_nodes.map((n) => ({ lat: n.lat, lng: n.lon }))
        : generateMockPolyline(selectedHospital.location, selectedLocation);

      const mockRoute: Route = {
        distance: apiResponse.distance_km !== null ? apiResponse.distance_km : 0,
        duration: (apiResponse.estimated_travel_time !== null && apiResponse.estimated_travel_time !== undefined)
          ? Math.round(apiResponse.estimated_travel_time * 60)
          : 0,
        traffic_level: Math.random() > 0.5 ? 'high' : 'moderate',
        polyline: polylineFromBackend,
      };

      setAmbulance(mockAmbulance);
      setRoute(mockRoute);
      setStep('live');
    } catch (error) {
      console.error('Error confirming request:', error);
      // In a real app you might show a toast or error message to the user here.
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setStep('city');
    setSelectedCity(undefined);
    setSelectedLocation(undefined);
    setSelectedHospital(undefined);
    setRequest(undefined);
    setAmbulance(undefined);
    setRoute(undefined);
  };

  return (
    <div className="flex flex-col min-h-screen">
      <Header />

      <main className="flex-1 w-full px-4 sm:px-6 lg:px-8 py-6 md:py-8">
        <div className="max-w-7xl mx-auto">
          {step === 'city' && (
            <CitySelect cities={cities} onSelect={handleCitySelect} selectedCity={selectedCity} />
          )}

          {step === 'location' && selectedCity && (
            <div className="space-y-6 animate-slide-in-up">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="space-y-1">
                  <p className="text-xs md:text-sm text-muted-foreground uppercase tracking-wide">Step 2 of 4</p>
                  <h2 className="text-2xl md:text-3xl font-bold">Set patient pickup location</h2>
                  <p className="text-sm md:text-base text-muted-foreground max-w-2xl">
                    Either click directly on the map, or type coordinates and pin the exact pickup point.
                  </p>
                </div>
                <Button
                  variant="outline"
                  onClick={() => setStep('city')}
                  className="shrink-0"
                >
                  Back to city
                </Button>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2">
                  <PatientMap
                    city={selectedCity}
                    onLocationSelect={handleLocationSelect}
                    selectedLocation={selectedLocation}
                  />
                </div>
                <div>
                  <Card className="p-4 md:p-6 h-full flex flex-col justify-between space-y-4">
                    <div className="space-y-3">
                      <h3 className="font-semibold text-lg mb-1">Search by address</h3>
                      <p className="text-sm text-muted-foreground">
                        Type a place, street, or landmark name. We␙ll look it up and drop a marker at the best match.
                      </p>
                      <div className="space-y-1 text-sm">
                        <label className="text-xs text-muted-foreground uppercase tracking-wide">Address or place</label>
                        <input
                          type="text"
                          value={manualLocation.address}
                          onChange={(e) => setManualLocation({ ...manualLocation, address: e.target.value })}
                          className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
                          placeholder="e.g. Zainab Hostel, Indus Loop, NUST H-12"
                        />
                      </div>
                      <div className="space-y-1 text-sm">
                        <label className="text-xs text-muted-foreground uppercase tracking-wide">Location label (optional)</label>
                        <input
                          type="text"
                          value={manualLocation.label}
                          onChange={(e) => setManualLocation({ ...manualLocation, label: e.target.value })}
                          className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
                          placeholder="Apartment, street name, nearby landmark"
                        />
                      </div>
                      <Button
                        className="w-full mt-2"
                        variant="secondary"
                        disabled={!manualLocation.address}
                        onClick={async () => {
                          const coords = await geocodeAddress(manualLocation.address);
                          if (!coords) return;
                          handleLocationSelect(coords);
                        }}
                      >
                        Find and pin on map
                      </Button>
                    </div>

                    <div className="space-y-2 text-sm">
                      <p className="text-xs text-muted-foreground uppercase tracking-wide">Tips</p>
                      <ul className="text-muted-foreground text-xs md:text-sm space-y-1 list-disc list-inside">
                        <li>Click again on the map if you need to move the marker.</li>
                        <li>Use landmarks or street names in the label to help the dispatcher.</li>
                        <li>You␙ll choose the hospital (emergency or planned) in the next step.</li>
                      </ul>
                    </div>
                  </Card>
                </div>
              </div>
            </div>
          )}

          {step === 'hospital' && selectedCity && selectedLocation && (
            <div className="space-y-6 animate-slide-in-up">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="space-y-1">
                  <p className="text-xs md:text-sm text-muted-foreground uppercase tracking-wide">Step 3 of 4</p>
                  <h2 className="text-2xl md:text-3xl font-bold">Is this an emergency?</h2>
                  <p className="text-sm md:text-base text-muted-foreground max-w-2xl">
                    For emergency situations we recommend sending the patient to the nearest suitable hospital
                    automatically. For non-emergency or planned visits, you can pick a hospital yourself.
                  </p>
                </div>
                <Button
                  variant="outline"
                  onClick={() => setStep('location')}
                  className="shrink-0"
                >
                  Back to location
                </Button>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 space-y-4">
                  <Card className="p-4 md:p-6">
                    <h3 className="font-semibold mb-2">Emergency vs non-emergency</h3>
                    <p className="text-sm text-muted-foreground mb-3">
                      Choose how you want the destination hospital to be decided. You can always go back and switch modes.
                    </p>
                    <div className="flex flex-col sm:flex-row gap-3">
                      <Button
                        variant={hospitalMode === 'auto' ? 'default' : 'outline'}
                        onClick={() => {
                          setHospitalMode('auto');
                          if (autoSelectedHospital) {
                            setSelectedHospital(autoSelectedHospital);
                            setStep('confirm');
                          }
                        }}
                        className="flex-1"
                      >
                        Emergency: send to nearest hospital
                      </Button>
                      <Button
                        variant={hospitalMode === 'manual' ? 'default' : 'outline'}
                        onClick={() => setHospitalMode('manual')}
                        className="flex-1"
                      >
                        Non-emergency: I will choose hospital
                      </Button>
                    </div>
                    {hospitalMode === 'auto' && autoSelectedHospital && (
                      <p className="text-xs text-muted-foreground mt-3">
                        For emergency, we will route to the nearest hospital by distance: <span className="font-semibold">{autoSelectedHospital.name}</span>
                      </p>
                    )}
                  </Card>

                  <LiveMap
                    patientLocation={selectedLocation}
                    hospital={selectedHospital}
                  />
                </div>

                {hospitalMode === 'manual' && (
                  <div>
                    <HospitalSelect
                      hospitals={hospitals}
                      onSelect={handleHospitalSelect}
                      selectedHospital={selectedHospital}
                      patientLocation={selectedLocation}
                    />
                  </div>
                )}
              </div>
            </div>
          )}

          {step === 'confirm' && selectedCity && selectedLocation && selectedHospital && (
            <div className="space-y-6 animate-slide-in-up">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="space-y-1">
                  <p className="text-xs md:text-sm text-muted-foreground uppercase tracking-wide">Step 4 of 4</p>
                  <h2 className="text-2xl md:text-3xl font-bold">Review and confirm ambulance request</h2>
                  <p className="text-sm md:text-base text-muted-foreground max-w-2xl">
                    Check the selected hospital and location, then enter patient details to place the emergency request.
                  </p>
                </div>
                <Button
                  variant="outline"
                  onClick={() => setStep('hospital')}
                  className="shrink-0"
                >
                  Back to hospitals
                </Button>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2">
                  <LiveMap
                    patientLocation={selectedLocation}
                    hospital={selectedHospital}
                  />
                </div>
                <div className="space-y-4">
                  <Card className="p-4 md:p-6 animate-slide-in-up">
                    <h3 className="font-semibold mb-4">Summary</h3>
                    <div className="space-y-2 text-sm mb-4">
                      <p><strong>City:</strong> {selectedCity.name}</p>
                      <p><strong>Hospital:</strong> {selectedHospital.name}</p>
                      <p className="text-xs text-muted-foreground">
                        Final distance and ETA will be calculated once the request is placed.
                      </p>
                    </div>
                  </Card>
                  <ConfirmRequest
                    hospital={selectedHospital}
                    patientLocation={selectedLocation}
                    onConfirm={handleConfirmRequest}
                    isLoading={isLoading}
                  />
                </div>
              </div>
            </div>
          )}

          {step === 'live' && request && selectedLocation && selectedHospital && (
            <div className="space-y-6 animate-slide-in-up">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div className="space-y-1">
                  <p className="text-xs md:text-sm text-muted-foreground uppercase tracking-wide">Live status</p>
                  <h2 className="text-2xl md:text-3xl font-bold">Ambulance on the way</h2>
                  <p className="text-sm md:text-base text-muted-foreground max-w-2xl">
                    Track the ambulance in real time on the map. You can start a new request once this one is completed.
                  </p>
                </div>
                <div className="flex flex-col sm:flex-row gap-2 sm:gap-3">
                  <Button
                    variant="outline"
                    onClick={handleReset}
                    className="shrink-0"
                  >
                    New request
                  </Button>
                  <Button
                    variant="default"
                    onClick={() => setShowDijkstra(true)}
                    className="shrink-0 bg-accent text-accent-foreground hover:bg-accent/90 shadow-sm border border-accent/40"
                  >
                    View Dijkstra visualization
                  </Button>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                <div className="lg:col-span-3">
                  <LiveMap
                    ambulance={ambulance}
                    route={route}
                    patientLocation={selectedLocation}
                    hospital={selectedHospital}
                    request={request}
                  />
                </div>
                <div className="space-y-4">
                  <Card className="p-4 md:p-6 bg-primary/5 border-primary/20 animate-slide-in-up">
                    <h3 className="font-semibold mb-3">Request</h3>
                    <div className="space-y-2 text-sm">
                      <div>
                        <p className="text-muted-foreground">Request ID</p>
                        <p className="font-mono text-xs">{request.id}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Patient</p>
                        <p className="font-semibold">{request.patient_name}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Status</p>
                        <p className="font-semibold text-accent">{request.status.toUpperCase()}</p>
                      </div>
                    </div>
                  </Card>

                  {ambulance && (
                    <Card className="p-4 md:p-6 bg-accent/5 border-accent/20 animate-slide-in-up" style={{ animationDelay: '100ms' }}>
                      <h3 className="font-semibold mb-3">Ambulance</h3>
                      <div className="space-y-2 text-sm">
                        <div>
                          <p className="text-muted-foreground">ID</p>
                          <p className="font-mono text-xs">{ambulance.id}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">ETA</p>
                          <p className="font-semibold text-accent">
                            {Math.floor(ambulance.estimated_arrival / 60)}m {ambulance.estimated_arrival % 60}s
                          </p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Status</p>
                          <p className="font-semibold capitalize">{ambulance.status.replace('_', ' ')}</p>
                        </div>
                      </div>
                    </Card>
                  )}

                  {route && (
                    <Card className="p-4 md:p-6 animate-slide-in-up" style={{ animationDelay: '200ms' }}>
                      <h3 className="font-semibold mb-3">Route</h3>
                      <div className="space-y-2 text-sm">
                        <div>
                          <p className="text-muted-foreground">Distance</p>
                          <p className="font-semibold">{route.distance} km</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Traffic</p>
                          <p className={`font-semibold capitalize px-2 py-1 rounded text-xs w-fit ${route.traffic_level === 'high' ? 'bg-destructive/20 text-destructive' :
                            route.traffic_level === 'moderate' ? 'bg-accent/20 text-accent' :
                              'bg-primary/20 text-primary'
                            }`}>
                            {route.traffic_level}
                          </p>
                        </div>
                      </div>
                    </Card>
                  )}
                </div>
              </div>

              {request && showDijkstra && (
                <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/40 backdrop-blur-sm">
                  <div
                    className="relative w-full max-w-6xl h-[90vh] rounded-xl bg-background border border-border shadow-2xl flex flex-col"
                    style={{ transform: `translate(${dijkstraOffset.x}px, ${dijkstraOffset.y}px)` }}
                  >
                    <div
                      className="flex items-center justify-between px-4 py-3 border-b border-border bg-muted/70 cursor-move select-none"
                      onMouseDown={(e) => {
                        setIsDraggingDijkstra(true);
                        dragStartRef.current = {
                          x: e.clientX - dijkstraOffset.x,
                          y: e.clientY - dijkstraOffset.y,
                        };
                      }}
                    >
                      <div>
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">Algorithm visualization</p>
                        <h2 className="text-sm font-semibold">Dijkstra for request #{request.id}</h2>
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setShowDijkstra(false)}
                      >
                        Close
                      </Button>
                    </div>
                    <div className="flex-1 p-3 md:p-4 overflow-auto">
                      <DijkstraVisualizer requestId={Number(request.id)} />
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}

// Helper function to generate mock polyline
function generateMockPolyline(start: Coordinates, end: Coordinates): Coordinates[] {
  const points: Coordinates[] = [start];
  const steps = 20;
  for (let i = 1; i < steps; i++) {
    const progress = i / steps;
    points.push({
      lat: start.lat + (end.lat - start.lat) * progress + (Math.random() - 0.5) * 0.005,
      lng: start.lng + (end.lng - start.lng) * progress + (Math.random() - 0.5) * 0.005,
    });
  }
  points.push(end);
  return points;
}



