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

  // This flag is used to validate the *request submission* inside the modal.
  // The main "Confirm Emergency Request" button should be clickable as soon
  // as a hospital and patient location are selected, so that the user can
  // open the modal and enter their details.
  const isValid = formData.patient_name && formData.contact_number && hospital && patientLocation;

  return (
    <>
      <Button 
        onClick={() => setShowModal(true)}
        // Only require hospital + patient location to open the modal. The
        // actual validation for patient name/contact happens on the inner
        // "Request Ambulance" button.
        disabled={!hospital || !patientLocation}
        size="lg"
        className="w-full bg-accent hover:bg-accent/90 text-accent-foreground transition-all duration-200 rounded-lg"
      >
        Confirm Emergency Request
      </Button>

      {showModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-[999] p-4 animate-fade-in">
          <Card className="w-full max-w-xl md:max-w-2xl p-6 md:p-8 rounded-2xl shadow-2xl bg-background animate-slide-in-up relative z-[1000] max-h-[90vh] overflow-y-auto">
            <h2 className="text-xl md:text-2xl font-bold mb-4 md:mb-6">Confirm Ambulance Request</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
              <div className="md:col-span-2 space-y-4">
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
              </div>

              <div className="border border-border/60 rounded-lg p-4 bg-muted/40 space-y-2 text-sm">
                <p className="text-xs text-muted-foreground uppercase tracking-wide">Summary</p>
                <p><strong>Hospital:</strong> {hospital?.name}</p>
                <p className="text-xs text-muted-foreground">
                  The ambulance will be routed to this hospital based on the current traffic-aware routing.
                </p>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-3 justify-end">
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
                className="flex-1 sm:flex-none bg-accent"
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
