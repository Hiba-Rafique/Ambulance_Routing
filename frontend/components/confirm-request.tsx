'use client';

import React, { useState } from 'react';
import { EmergencyRequest, Hospital, Coordinates } from '@/lib/types';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';

interface ConfirmRequestProps {
  hospital?: Hospital;
  patientLocation?: Coordinates;
  onConfirm: (request: Partial<EmergencyRequest>) => void;
  isLoading?: boolean;
}

export const ConfirmRequest: React.FC<ConfirmRequestProps> = ({ 
  hospital, 
  patientLocation, 
  onConfirm,
  isLoading = false 
}) => {
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({
    patient_name: '',
    contact_number: '',
    medical_condition: '',
  });

  const handleSubmit = async () => {
    onConfirm({
      ...formData,
      patient_location: patientLocation,
      hospital_id: hospital?.id,
    });
    setShowModal(false);
  };

  const isValid = formData.patient_name && formData.contact_number && hospital && patientLocation;

  return (
    <>
      <Button 
        onClick={() => setShowModal(true)}
        disabled={!isValid}
        size="lg"
        className="w-full bg-accent hover:bg-accent/90 text-accent-foreground transition-all duration-300 animate-pulse-glow"
      >
        Confirm Emergency Request
      </Button>

      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 animate-fade-in">
          <Card className="w-full max-w-md p-6 animate-slide-in-up">
            <h2 className="text-2xl font-bold mb-4">Confirm Ambulance Request</h2>
            
            <div className="space-y-4 mb-6">
              <div>
                <label className="block text-sm font-medium mb-1">Patient Name</label>
                <Input
                  value={formData.patient_name}
                  onChange={(e) => setFormData({ ...formData, patient_name: e.target.value })}
                  placeholder="Enter patient name"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Contact Number</label>
                <Input
                  type="tel"
                  value={formData.contact_number}
                  onChange={(e) => setFormData({ ...formData, contact_number: e.target.value })}
                  placeholder="Enter contact number"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Medical Condition</label>
                <Input
                  value={formData.medical_condition}
                  onChange={(e) => setFormData({ ...formData, medical_condition: e.target.value })}
                  placeholder="Brief description of condition"
                />
              </div>

              <div className="pt-2 border-t border-border space-y-1">
                <p className="text-sm"><strong>Hospital:</strong> {hospital?.name}</p>
              </div>
            </div>

            <div className="flex gap-3">
              <Button 
                variant="outline" 
                onClick={() => setShowModal(false)}
                disabled={isLoading}
              >
                Cancel
              </Button>
              <Button 
                onClick={handleSubmit}
                disabled={!isValid || isLoading}
                className="flex-1 bg-accent"
              >
                {isLoading ? 'Requesting...' : 'Request Ambulance'}
              </Button>
            </div>
          </Card>
        </div>
      )}
    </>
  );
};
