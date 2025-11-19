import React, { useState, useRef, useEffect } from 'react';
import { Button } from './ui/button';

interface BasemapWidgetProps {
  currentBasemap: string;
  availableBasemaps: string[];
  displayNames: Record<string, string>;
  onBasemapChange: (basemap: string) => void;
  className?: string;
}

export const BasemapWidget: React.FC<BasemapWidgetProps> = ({
  currentBasemap,
  availableBasemaps,
  displayNames,
  onBasemapChange,
  className
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Close when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const getDisplayName = (basemap: string) => {
    return displayNames[basemap] || basemap;
  };

  return (
    <div className={`relative ${className || ''}`} ref={containerRef}>
      <Button
        variant="secondary"
        size="icon"
        className="h-[29px] w-[29px] bg-white hover:bg-gray-100 shadow-md rounded-md border-0"
        onClick={() => setIsOpen(!isOpen)}
        title="切换底图"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="#333">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.94-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
        </svg>
      </Button>

      {isOpen && (
        <div
          className="absolute bottom-full left-0 mb-2 bg-[oklch(27.8%_0.033_256.848)] border border-[oklch(1_0_0_/_15%)] rounded-md shadow-xl p-2 z-50 grid grid-cols-2 gap-2 w-[280px]"
          style={{ animation: 'fadeIn 0.2s ease' }}
        >
          {availableBasemaps.map((basemap) => (
            <button
              key={basemap}
              className={`relative w-[120px] h-[120px] rounded overflow-hidden border transition-all ${currentBasemap === basemap
                  ? 'border-[#007cff]'
                  : 'border-white/20 hover:border-[#4da3ff]'
                }`}
              onClick={() => {
                onBasemapChange(basemap);
                setIsOpen(false);
              }}
            >
              <div className="w-full h-full bg-[#f5f5f5] relative">
                {/* Preview Image */}
                <img
                  src={`/api/basemaps/render.png?basemap=${basemap}`}
                  alt={getDisplayName(basemap)}
                  className="w-full h-full object-cover block"
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = 'none';
                  }}
                />

                {/* Loading/Error Placeholder */}
                <div className="absolute inset-0 flex items-center justify-center text-[10px] text-gray-500 -z-10">
                  Loading...
                </div>

                {/* Label Overlay */}
                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-2 pt-4">
                  <span className="text-white text-[10px] font-bold block text-center">
                    {getDisplayName(basemap)}
                  </span>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
