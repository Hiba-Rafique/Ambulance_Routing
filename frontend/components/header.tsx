import React from 'react';

export const Header: React.FC = () => {
  return (
    <header className="bg-gradient-to-r from-background to-secondary border-b border-border/50 sticky top-0 z-40 backdrop-blur-sm">
      <div className="max-w-7xl mx-auto px-4 py-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-accent to-accent/60 rounded-xl flex items-center justify-center shadow-lg shadow-accent/20">
            <span className="text-lg font-bold text-accent-foreground">🚑</span>
          </div>
          <div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-foreground to-foreground/80 bg-clip-text text-transparent">Emergency Response</h1>
            <p className="text-xs text-muted-foreground">Pakistan</p>
          </div>
        </div>
        <nav className="hidden md:flex gap-8">
          <a href="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Request Ambulance</a>
          <a href="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Track Status</a>
        </nav>
      </div>
    </header>
  );
};
