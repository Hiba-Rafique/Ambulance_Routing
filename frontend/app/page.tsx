'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Header } from '@/components/header';
import { Footer } from '@/components/footer';
import { CitySelect } from '@/components/city-select';
import { PatientMap } from '@/components/patient-map';
import { HospitalSelect } from '@/components/hospital-select';
import { ConfirmRequest } from '@/components/confirm-request';
import { LiveMap } from '@/components/live-map';
import { City, Hospital, Coordinates, EmergencyRequest, Ambulance, Route } from '@/lib/types';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

const MOCK_CITIES: City[] = [
  {
    id: 'city_karachi',
    name: 'Karachi',
    bounds: { north: 25.05, south: 24.75, east: 67.35, west: 66.85 },
    center: { lat: 24.8607, lng: 67.0011 },
  },
  {
    id: 'city_lahore',
    name: 'Lahore',
    bounds: { north: 31.65, south: 31.35, east: 74.45, west: 73.95 },
    center: { lat: 31.5204, lng: 74.3587 },
  },
  {
    id: 'city_islamabad',
    name: 'Islamabad',
    bounds: { north: 33.85, south: 33.55, east: 73.35, west: 72.85 },
    center: { lat: 33.6844, lng: 73.0479 },
  },
  {
    id: 'city_rawalpindi',
    name: 'Rawalpindi',
    bounds: { north: 33.65, south: 33.35, east: 73.45, west: 72.95 },
    center: { lat: 33.5731, lng: 73.1795 },
  },
  {
    id: 'city_multan',
    name: 'Multan',
    bounds: { north: 30.35, south: 29.95, east: 72.05, west: 71.35 },
    center: { lat: 30.1978, lng: 71.4455 },
  },
];

const MOCK_HOSPITALS: Hospital[] = [
  {
    id: 'hospital_aga_khan_karachi',
    name: 'Aga Khan University Hospital (Karachi)',
    location: { lat: 24.7890, lng: 67.0735 },
    beds_available: 15,
    specialties: ['Trauma', 'Cardiology', 'Emergency Medicine', 'Neurology'],
  },
  {
    id: 'hospital_civil_karachi',
    name: 'Civil Hospital Karachi',
    location: { lat: 24.8516, lng: 67.0073 },
    beds_available: 12,
    specialties: ['General Surgery', 'Orthopedics', 'Emergency'],
  },
  {
    id: 'hospital_mayo_lahore',
    name: 'Mayo Hospital Lahore',
    location: { lat: 31.5589, lng: 74.3303 },
    beds_available: 18,
    specialties: ['Emergency', 'Trauma', 'Critical Care', 'Cardiology'],
  },
  {
    id: 'hospital_services_lahore',
    name: 'Services Hospital Lahore',
    location: { lat: 31.5403, lng: 74.3198 },
    beds_available: 14,
    specialties: ['General Medicine', 'Surgery', 'Emergency'],
  },
  {
    id: 'hospital_pims_islamabad',
    name: 'Pakistan Institute of Medical Sciences (PIMS)',
    location: { lat: 33.7158, lng: 73.2196 },
    beds_available: 20,
    specialties: ['Emergency', 'Trauma', 'Critical Care', 'Neurology', 'Cardiology'],
  },
  {
    id: 'hospital_shifa_islamabad',
    name: 'Shifa International Hospital Islamabad',
    location: { lat: 33.7447, lng: 73.1902 },
    beds_available: 16,
    specialties: ['Emergency', 'Cardiac Surgery', 'Trauma', 'Critical Care'],
  },
  {
    id: 'hospital_benazir_rawalpindi',
    name: 'Benazir Bhutto Hospital Rawalpindi',
    location: { lat: 33.5932, lng: 73.1872 },
    beds_available: 13,
    specialties: ['Emergency', 'Surgery', 'Orthopedics'],
  },
  {
    id: 'hospital_nishtar_multan',
    name: 'Nishtar Hospital Multan',
    location: { lat: 30.1918, lng: 71.4409 },
    beds_available: 11,
    specialties: ['General Surgery', 'Medicine', 'Emergency'],
  },
];

export default function Home() {
  const [step, setStep] = useState<'city' | 'location' | 'hospital' | 'confirm' | 'live'>('city');
  const [selectedCity, setSelectedCity] = useState<City | undefined>();
  const [selectedLocation, setSelectedLocation] = useState<Coordinates | undefined>();
  const [selectedHospital, setSelectedHospital] = useState<Hospital | undefined>();
  const [request, setRequest] = useState<EmergencyRequest | undefined>();
  const [ambulance, setAmbulance] = useState<Ambulance | undefined>();
  const [route, setRoute] = useState<Route | undefined>();
  const [isLoading, setIsLoading] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  // Simulate WebSocket connection for live updates
  useEffect(() => {
    if (step === 'live' && request) {
      // Simulate live ambulance updates
      const interval = setInterval(() => {
        setAmbulance((prev) => {
          if (!prev) return prev;
          // Simulate ambulance movement
          const newLat = prev.current_location.lat + (Math.random() - 0.5) * 0.001;
          const newLng = prev.current_location.lng + (Math.random() - 0.5) * 0.001;
          return {
            ...prev,
            current_location: { lat: newLat, lng: newLng },
            estimated_arrival: Math.max(0, prev.estimated_arrival - 1),
          };
        });
      }, 1000);

      return () => clearInterval(interval);
    }
  }, [step, request]);

  const handleCitySelect = (city: City) => {
    setSelectedCity(city);
    setStep('location');
  };

  const handleLocationSelect = (location: Coordinates) => {
    setSelectedLocation(location);
    setStep('hospital');
  };

  const handleHospitalSelect = (hospital: Hospital) => {
    setSelectedHospital(hospital);
    setStep('confirm');
  };

  const handleConfirmRequest = async (requestData: Partial<EmergencyRequest>) => {
    setIsLoading(true);
    
    try {
      // Simulate API call
      const newRequest: EmergencyRequest = {
        id: `req_${Date.now()}`,
        patient_location: selectedLocation!,
        city_id: selectedCity!.id,
        hospital_id: selectedHospital!.id,
        status: 'confirmed',
        created_at: new Date().toISOString(),
        ...requestData,
      };

      setRequest(newRequest);

      // Simulate ambulance assignment and route calculation
      const mockAmbulance: Ambulance = {
        id: `amb_${Math.floor(Math.random() * 1000)}`,
        current_location: selectedHospital!.location,
        status: 'en_route',
        vehicle_type: 'advanced_life_support',
        estimated_arrival: 420, // 7 minutes in seconds
      };

      const mockRoute: Route = {
        distance: 5.2,
        duration: 420,
        traffic_level: Math.random() > 0.5 ? 'high' : 'moderate',
        polyline: generateMockPolyline(selectedHospital!.location, selectedLocation!),
      };

      setAmbulance(mockAmbulance);
      setRoute(mockRoute);
      setStep('live');
    } catch (error) {
      console.error('Error confirming request:', error);
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
            <CitySelect cities={MOCK_CITIES} onSelect={handleCitySelect} selectedCity={selectedCity} />
          )}

          {step === 'location' && selectedCity && (
            <div className="space-y-6 animate-slide-in-up">
              <Button 
                variant="outline" 
                onClick={() => setStep('city')}
                className="transition-all"
              >
                Back to City Selection
              </Button>
              <PatientMap 
                city={selectedCity}
                onLocationSelect={handleLocationSelect}
                selectedLocation={selectedLocation}
              />
            </div>
          )}

          {step === 'hospital' && selectedCity && selectedLocation && (
            <div className="space-y-6 animate-slide-in-up">
              <Button 
                variant="outline" 
                onClick={() => setStep('location')}
                className="transition-all"
              >
                Back to Location Selection
              </Button>
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2">
                  <LiveMap 
                    patientLocation={selectedLocation}
                    hospital={selectedHospital}
                  />
                </div>
                <div>
                  <HospitalSelect 
                    hospitals={MOCK_HOSPITALS.filter(h => h.location.lat >= selectedCity.bounds.south && h.location.lat <= selectedCity.bounds.north && h.location.lng >= selectedCity.bounds.west && h.location.lng <= selectedCity.bounds.east)}
                    onSelect={handleHospitalSelect}
                    selectedHospital={selectedHospital}
                  />
                </div>
              </div>
            </div>
          )}

          {step === 'confirm' && selectedCity && selectedLocation && selectedHospital && (
            <div className="space-y-6 animate-slide-in-up">
              <Button 
                variant="outline" 
                onClick={() => setStep('hospital')}
                className="transition-all"
              >
                Back to Hospital Selection
              </Button>
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2">
                  <LiveMap 
                    patientLocation={selectedLocation}
                    hospital={selectedHospital}
                  />
                </div>
                <div className="space-y-4">
                  <Card className="p-4 md:p-6 animate-slide-in-up">
                    <h3 className="font-semibold mb-4">Request Summary</h3>
                    <div className="space-y-2 text-sm mb-4">
                      <p><strong>Hospital:</strong> {selectedHospital.name}</p>
                      <p><strong>Distance to Hospital:</strong> ~5.2 km</p>
                      <p><strong>Estimated Time:</strong> 7 minutes</p>
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
                <h2 className="text-2xl md:text-3xl font-bold">Live Ambulance Tracking</h2>
                <Button 
                  variant="outline"
                  onClick={handleReset}
                  className="transition-all"
                >
                  New Request
                </Button>
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
                    <h3 className="font-semibold mb-3">Details</h3>
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
                          <p className={`font-semibold capitalize px-2 py-1 rounded text-xs w-fit ${
                            route.traffic_level === 'high' ? 'bg-destructive/20 text-destructive' :
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
