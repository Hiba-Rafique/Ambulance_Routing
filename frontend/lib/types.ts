export interface Coordinates {
  lat: number;
  lng: number;
}

export interface Hospital {
  id: string;
  name: string;
  location: Coordinates;
  beds_available: number;
  specialties: string[];
}

export interface City {
  id: string;
  name: string;
  bounds: {
    north: number;
    south: number;
    east: number;
    west: number;
  };
  center: Coordinates;
}

export interface Ambulance {
  id: string;
  current_location: Coordinates;
  status: 'available' | 'en_route' | 'at_hospital' | 'busy';
  vehicle_type: 'standard' | 'advanced_life_support';
  estimated_arrival: number; // seconds
}

export interface Route {
  distance: number;
  duration: number;
  traffic_level: 'low' | 'moderate' | 'high';
  polyline: Coordinates[];
}

export interface EmergencyRequest {
  id: string;
  patient_location: Coordinates;
  patient_name: string;
  contact_number: string;
  medical_condition: string;
  city_id: string;
  hospital_id: string;
  status: 'pending' | 'confirmed' | 'en_route' | 'arrived' | 'completed';
  created_at: string;
  ambulance_id?: string;
}

export interface RouteUpdate {
  ambulance_id: string;
  current_location: Coordinates;
  route: Route;
  estimated_arrival: number;
}
