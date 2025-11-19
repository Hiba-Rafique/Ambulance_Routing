import React from 'react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-secondary text-secondary-foreground border-t border-border mt-12">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div>
            <h3 className="font-semibold mb-2">Emergency Services</h3>
            <p className="text-sm opacity-80">24/7 ambulance dispatch and routing service</p>
          </div>
          <div>
            <h3 className="font-semibold mb-2">Quick Links</h3>
            <ul className="text-sm space-y-1">
              <li><a href="#" className="hover:text-foreground transition">FAQ</a></li>
              <li><a href="#" className="hover:text-foreground transition">Contact</a></li>
              <li><a href="#" className="hover:text-foreground transition">Terms</a></li>
            </ul>
          </div>
          <div>
            <h3 className="font-semibold mb-2">Contact</h3>
            <p className="text-sm">Emergency: 911</p>
            <p className="text-sm">Support: 1-800-AMBULANCE</p>
          </div>
        </div>
        <div className="border-t border-border mt-8 pt-4 text-center text-sm opacity-70">
          © 2025 Emergency Response System. All rights reserved.
        </div>
      </div>
    </footer>
  );
};
