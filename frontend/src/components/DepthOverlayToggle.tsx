import React from 'react';

interface DepthOverlayToggleProps {
  isVisible: boolean;
  onToggle: (visible: boolean) => void;
  className?: string;
}

export default function DepthOverlayToggle({ 
  isVisible, 
  onToggle, 
  className = '' 
}: DepthOverlayToggleProps) {
  return (
    <div className={`fixed top-4 left-4 z-50 ${className}`}>
      <button
        onClick={() => onToggle(!isVisible)}
        className={`
          px-4 py-2 rounded-lg shadow-lg transition-all duration-200
          ${isVisible 
            ? 'bg-blue-500 text-white hover:bg-blue-600' 
            : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }
        `}
        title={isVisible ? 'Hide depth overlay' : 'Show depth overlay'}
      >
        <div className="flex items-center space-x-2">
          <div className="flex space-x-1">
            <div className="w-2 h-2 rounded-full bg-green-500"></div>
            <div className="w-2 h-2 rounded-full bg-yellow-500"></div>
            <div className="w-2 h-2 rounded-full bg-red-500"></div>
            <div className="w-2 h-2 rounded-full bg-purple-500"></div>
          </div>
          <span className="text-sm font-medium">
            {isVisible ? 'Depth ON' : 'Depth OFF'}
          </span>
        </div>
      </button>
    </div>
  );
}
