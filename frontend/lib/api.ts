import { Coordinates, Hospital } from './types';

// Simple API helper for talking to the FastAPI backend.
// For now we hardcode the base URL; later you can move this to an env var.
const BACKEND_BASE_URL = 'http://localhost:8000';

export interface CreateAutoEmergencyRequestPayload {
  cityNumericId: number; // numeric city id from backend DB
  location: Coordinates; // patient location from map
  callerName: string;
  callerPhone: string;
}

export interface CreateAutoEmergencyRequestResponse {
  request_id: number;
  source_node_id: number;
  destination_hospital_node_id: number;
  estimated_travel_time: number | null;
  distance_km: number | null;
  route_nodes?: { id: number; lat: number; lon: number }[] | null;
}

interface BackendCity {
  id: number;
  name: string;
}

// Debug Dijkstra visualization types
export interface DebugDijkstraNode {
  id: number;
  lat: number;
  lon: number;
  name: string | null;
  type: string | null;
}

export interface DebugDijkstraEdge {
  id: number;
  from_node: number;
  to_node: number;
  weight: number;
  adjusted_weight: number | null;
  distance: number | null;
  is_blocked?: boolean | null;
  has_traffic?: boolean | null;
}

export interface DebugDijkstraStep {
  current: number | null;
  distances: Record<number, number>;
  visited: number[];
  frontier: number[];
}

export interface DebugDijkstraResponse {
  request_id: number;
  source_node_id: number;
  destination_node_id: number;
  nodes: DebugDijkstraNode[];
  edges: DebugDijkstraEdge[];
  steps: DebugDijkstraStep[];
  shortest_path: number[];
  total_distance_km: number | null;
}

export async function createAutoEmergencyRequest(
  payload: CreateAutoEmergencyRequestPayload,
): Promise<CreateAutoEmergencyRequestResponse> {
  const response = await fetch(`${BACKEND_BASE_URL}/route/requests/auto`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      city_id: payload.cityNumericId,
      latitude: payload.location.lat,
      longitude: payload.location.lng,
      caller_name: payload.callerName,
      caller_phone: payload.callerPhone,
    }),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const message = (data && (data.detail || data.message)) || 'Failed to create emergency request';
    throw new Error(message);
  }

  const data = (await response.json()) as CreateAutoEmergencyRequestResponse;
  return data;
}

export async function fetchCities(): Promise<BackendCity[]> {
  const response = await fetch(`${BACKEND_BASE_URL}/route/cities`);

  if (!response.ok) {
    throw new Error('Failed to load cities');
  }

  const data = (await response.json()) as BackendCity[];
  return data;
}

// Fetch Dijkstra debug data for a specific emergency request
export async function fetchDebugDijkstra(requestId: number): Promise<DebugDijkstraResponse> {
  const response = await fetch(`${BACKEND_BASE_URL}/route/requests/${requestId}/debug/dijkstra`);

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const message = (data && (data.detail || data.message)) || 'Failed to load Dijkstra debug data';
    throw new Error(message);
  }

  const data = (await response.json()) as DebugDijkstraResponse;
  return data;
}

interface BackendHospital {
  id: number;
  name: string | null;
  lat: number;
  lon: number;
}

export async function fetchHospitalsForCity(cityNumericId: number): Promise<Hospital[]> {
  const response = await fetch(`${BACKEND_BASE_URL}/route/cities/${cityNumericId}/hospitals`);

  if (!response.ok) {
    throw new Error('Failed to load hospitals for city');
  }

  const data = (await response.json()) as BackendHospital[];

  // Map backend hospital nodes into the UI Hospital shape.
  return data.map((h) => ({
    id: `node_${h.id}`,
    name: h.name ?? `Hospital ${h.id}`,
    location: { lat: h.lat, lng: h.lon },
    beds_available: 0,
    specialties: [],
  }));
}

// Geocode a free-form address string into coordinates using the OpenCage
// Geocoding API. The API key is read from NEXT_PUBLIC_OPENCAGE_API_KEY.
// In production you should proxy this via your backend to avoid exposing
// the key, but for now this keeps things simple for development.
export async function geocodeAddress(address: string): Promise<Coordinates | null> {
  const apiKey = process.env.NEXT_PUBLIC_OPENCAGE_API_KEY;
  if (!apiKey) {
    console.error('Missing NEXT_PUBLIC_OPENCAGE_API_KEY for geocoding');
    return null;
  }

  const params = new URLSearchParams({
    key: apiKey,
    q: address,
    limit: '1',
  });

  const response = await fetch(`https://api.opencagedata.com/geocode/v1/json?${params.toString()}`);

  if (!response.ok) {
    console.error('Failed to geocode address', await response.text());
    return null;
  }

  const data = await response.json();
  const result = data?.results?.[0];
  if (!result || !result.geometry) return null;

  return {
    lat: result.geometry.lat,
    lng: result.geometry.lng,
  };
}
