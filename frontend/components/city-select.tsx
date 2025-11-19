'use client';

import React from 'react';
import { City } from '@/lib/types';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

interface CitySelectProps {
  cities: City[];
  onSelect: (city: City) => void;
  selectedCity?: City;
}

export const CitySelect: React.FC<CitySelectProps> = ({ cities, onSelect, selectedCity }) => {
  return (
    <div className="w-full space-y-8 animate-slide-in-up">
      <div className="space-y-2">
        <h2 className="text-4xl font-bold bg-gradient-to-r from-primary via-accent to-primary bg-clip-text text-transparent">
          Select Your City
        </h2>
        <p className="text-muted-foreground">Choose a location to request emergency services</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {cities.map((city, index) => (
          <Card 
            key={city.id}
            className={`p-6 cursor-pointer transition-all duration-300 border-2 animate-fade-in`}
            style={{ animationDelay: `${index * 100}ms` }}
            onClick={() => onSelect(city)}
          >
            <div className={`${
              selectedCity?.id === city.id 
                ? 'border-accent bg-accent/10 shadow-lg shadow-accent/20 border-2 rounded-lg p-6 mb-4 animate-pulse-glow' 
                : 'border-border hover:border-accent/50 hover:bg-secondary border-2'
            }`}>
              <h3 className="font-bold text-lg mb-3">{city.name}</h3>
            </div>
            <Button 
              className={`w-full font-semibold transition-all ${
                selectedCity?.id === city.id 
                  ? 'bg-accent text-accent-foreground hover:bg-accent/90' 
                  : 'border-accent/30 text-foreground hover:bg-accent hover:text-accent-foreground'
              }`}
              variant={selectedCity?.id === city.id ? 'default' : 'outline'}
            >
              {selectedCity?.id === city.id ? 'Selected' : 'Select'}
            </Button>
          </Card>
        ))}
      </div>
    </div>
  );
};
