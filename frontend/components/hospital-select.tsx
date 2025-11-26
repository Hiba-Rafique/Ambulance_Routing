'use client';

import React from 'react';
import { Hospital, Coordinates } from '@/lib/types';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

interface HospitalSelectProps {
  hospitals: Hospital[];
  onSelect: (hospital: Hospital) => void;
  selectedHospital?: Hospital;
  patientLocation?: Coordinates;
}

export const HospitalSelect: React.FC<HospitalSelectProps> = ({ 
  hospitals, 
  onSelect, 
  selectedHospital,
  patientLocation,
}) => {
  // If we have the patient location, compute a simple distance to each
  // hospital and keep only the top 3 nearest ones for display. This
  // makes the UI match the "nearest hospitals" idea, while the backend
  // still does the final DSA-based shortest-path routing.
  const hospitalsToShow = React.useMemo(() => {
    if (!patientLocation) return hospitals;

    const withDistance = hospitals.map((h) => {
      const dLat = h.location.lat - patientLocation.lat;
      const dLng = h.location.lng - patientLocation.lng;
      const distSq = dLat * dLat + dLng * dLng; // squared distance
      return { hospital: h, distSq };
    });

    return withDistance
      .sort((a, b) => a.distSq - b.distSq)
      .slice(0, 3)
      .map((x) => x.hospital);
  }, [hospitals, patientLocation]);

  return (
    <Card className="w-full p-4 md:p-6 animate-slide-in-up">
      <h3 className="font-semibold text-lg mb-4">Select Destination Hospital</h3>
      <div className="space-y-2 max-h-64 md:max-h-96 overflow-y-auto">
        {hospitalsToShow.map((hospital, index) => (
          <button
            key={hospital.id}
            onClick={() => onSelect(hospital)}
            className={`w-full p-3 md:p-4 text-left rounded-lg border transition-all animate-fade-in ${
              selectedHospital?.id === hospital.id
                ? 'border-accent bg-accent/10 shadow-md'
                : 'border-border hover:border-primary'
            }`}
            style={{ animationDelay: `${index * 50}ms` }}
          >
            <div className="flex justify-between items-start gap-2">
              <div className="flex-1">
                <h4 className="font-semibold text-sm md:text-base">{hospital.name}</h4>
                {hospital.beds_available > 0 && (
                  <p className="text-xs md:text-sm text-muted-foreground mt-1">
                    {hospital.beds_available} beds available
                  </p>
                )}
                <div className="flex flex-wrap gap-1 mt-2">
                  {hospital.specialties.slice(0, 2).map((spec) => (
                    <span key={spec} className="text-xs bg-primary/10 text-primary px-2 py-1 rounded">
                      {spec}
                    </span>
                  ))}
                  {hospital.specialties.length > 2 && (
                    <span className="text-xs bg-primary/10 text-primary px-2 py-1 rounded">
                      +{hospital.specialties.length - 2} more
                    </span>
                  )}
                </div>
              </div>
            </div>
          </button>
        ))}
      </div>
    </Card>
  );
};
