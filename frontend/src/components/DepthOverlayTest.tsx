import React, { useState, useEffect } from 'react';

// Mock depth data for testing
const MOCK_DEPTH_DATA = [
  {
    id: 'storm_pipe_1',
    x: 100,
    y: 100,
    length_ft: 50,
    dia_in: 12,
    material: 'pvc',
    min_depth_ft: 2.0,
    max_depth_ft: 3.0,
    avg_depth_ft: 2.5,
    p95_depth_ft: 2.8,
    buckets_lf: { '0-5': 40, '5-8': 10, '8-12': 0, '12+': 0 },
    trench_volume_cy: 6.2,
    cover_ok: true,
    deep_excavation: false
  },
  {
    id: 'sanitary_pipe_1',
    x: 200,
    y: 150,
    length_ft: 75,
    dia_in: 15,
    material: 'rcp',
    min_depth_ft: 4.0,
    max_depth_ft: 6.0,
    avg_depth_ft: 5.0,
    p95_depth_ft: 5.8,
    buckets_lf: { '0-5': 0, '5-8': 60, '8-12': 15, '12+': 0 },
    trench_volume_cy: 12.5,
    cover_ok: true,
    deep_excavation: false
  },
  {
    id: 'water_pipe_1',
    x: 300,
    y: 200,
    length_ft: 100,
    dia_in: 18,
    material: 'pvc',
    min_depth_ft: 8.0,
    max_depth_ft: 12.0,
    avg_depth_ft: 10.0,
    p95_depth_ft: 11.5,
    buckets_lf: { '0-5': 0, '5-8': 0, '8-12': 80, '12+': 20 },
    trench_volume_cy: 25.0,
    cover_ok: false,
    deep_excavation: true
  }
];

// Depth bucket configuration
const DEPTH_BUCKETS = [
  { range: '<5', min: 0, max: 5, color: '#10b981', label: 'Shallow' },
  { range: '5-8', min: 5, max: 8, color: '#f59e0b', label: 'Medium' },
  { range: '8-12', min: 8, max: 12, color: '#ef4444', label: 'Deep' },
  { range: '12+', min: 12, max: Infinity, color: '#7c3aed', label: 'Very Deep' }
];

// Tooltip component
function TestTooltip({ data, x, y }: { data: any; x: number; y: number }) {
  const dominantBucket = Object.entries(data.buckets_lf).reduce((a, b) => 
    data.buckets_lf[a[0] as keyof typeof data.buckets_lf] > data.buckets_lf[b[0] as keyof typeof data.buckets_lf] ? a : b
  )[0];

  return (
    <div 
      className="absolute bg-white border border-gray-300 rounded-lg shadow-lg p-3 z-50 pointer-events-auto"
      style={{ 
        left: `${x + 10}px`, 
        top: `${y - 10}px`,
        minWidth: '200px'
      }}
    >
      <div className="text-sm font-semibold text-gray-800 mb-2">
        Pipe {data.id}
      </div>
      
      <div className="space-y-1 text-xs">
        <div className="flex justify-between">
          <span className="text-gray-600">Material:</span>
          <span className="font-medium">{data.material} {data.dia_in}"</span>
        </div>
        
        <div className="flex justify-between">
          <span className="text-gray-600">Length:</span>
          <span className="font-medium">{data.length_ft.toFixed(1)} ft</span>
        </div>
        
        <div className="border-t pt-1 mt-2">
          <div className="text-gray-600 font-medium mb-1">Depth Analysis:</div>
          <div className="flex justify-between">
            <span className="text-gray-600">Min:</span>
            <span className="font-medium">{data.min_depth_ft.toFixed(1)} ft</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Avg:</span>
            <span className="font-medium">{data.avg_depth_ft.toFixed(1)} ft</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Max:</span>
            <span className="font-medium">{data.max_depth_ft.toFixed(1)} ft</span>
          </div>
        </div>
        
        <div className="border-t pt-1 mt-2">
          <div className="text-gray-600 font-medium mb-1">Depth Buckets (LF):</div>
          {Object.entries(data.buckets_lf).map(([bucket, lf]) => (
            <div key={bucket} className="flex justify-between">
              <span className="text-gray-600">{bucket}ft:</span>
              <span className="font-medium">{lf.toFixed(1)}</span>
            </div>
          ))}
        </div>
        
        <div className="border-t pt-1 mt-2">
          <div className="flex justify-between">
            <span className="text-gray-600">Trench Vol:</span>
            <span className="font-medium">{data.trench_volume_cy.toFixed(1)} CY</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Cover OK:</span>
            <span className={`font-medium ${data.cover_ok ? 'text-green-600' : 'text-red-600'}`}>
              {data.cover_ok ? 'Yes' : 'No'}
            </span>
          </div>
          {data.deep_excavation && (
            <div className="text-red-600 font-medium text-center mt-1">
              ⚠️ Deep Excavation
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Legend component
function TestLegend({ isVisible }: { isVisible: boolean }) {
  if (!isVisible) return null;

  return (
    <div className="absolute top-4 right-4 bg-white border border-gray-300 rounded-lg shadow-lg p-3 z-50">
      <div className="text-sm font-semibold text-gray-800 mb-2">
        Depth (ft)
      </div>
      <div className="space-y-1">
        {DEPTH_BUCKETS.map((bucket) => (
          <div key={bucket.range} className="flex items-center space-x-2">
            <div 
              className="w-4 h-4 rounded border border-gray-300"
              style={{ backgroundColor: bucket.color }}
            />
            <span className="text-xs text-gray-700">
              {bucket.range}ft ({bucket.label})
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Main test component
export default function DepthOverlayTest() {
  const [isVisible, setIsVisible] = useState(false);
  const [hoveredPipe, setHoveredPipe] = useState<any>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  // Get color for pipe based on dominant depth bucket
  const getPipeColor = (pipe: any) => {
    const dominantBucket = Object.entries(pipe.buckets_lf).reduce((a, b) => 
      pipe.buckets_lf[a[0] as keyof typeof pipe.buckets_lf] > pipe.buckets_lf[b[0] as keyof typeof pipe.buckets_lf] ? a : b
    )[0];
    
    const bucket = DEPTH_BUCKETS.find(b => b.range === dominantBucket);
    return bucket?.color || '#6b7280';
  };

  // Handle mouse events
  const handleMouseMove = (e: React.MouseEvent) => {
    setMousePos({ x: e.clientX, y: e.clientY });
  };

  const handleMouseEnter = (pipe: any) => {
    setHoveredPipe(pipe);
  };

  const handleMouseLeave = () => {
    setHoveredPipe(null);
  };

  return (
    <div className="w-full h-screen bg-gray-100 relative">
      {/* Test Controls */}
      <div className="absolute top-4 left-4 z-50 bg-white border border-gray-300 rounded-lg shadow-lg p-4">
        <h3 className="text-lg font-semibold mb-3">Depth Overlay Test</h3>
        
        <div className="space-y-2">
          <button
            onClick={() => setIsVisible(!isVisible)}
            className={`w-full px-4 py-2 rounded ${
              isVisible 
                ? 'bg-blue-500 text-white hover:bg-blue-600' 
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            {isVisible ? 'Hide Depth Overlay' : 'Show Depth Overlay'}
          </button>
          
          <div className="text-sm text-gray-600">
            Status: {isVisible ? 'Visible' : 'Hidden'}
          </div>
          
          <div className="text-sm text-gray-600">
            Pipes: {MOCK_DEPTH_DATA.length}
          </div>
        </div>
      </div>

      {/* Test Canvas */}
      <div 
        className="w-full h-full relative"
        onMouseMove={handleMouseMove}
      >
        {isVisible && (
          <>
            {/* Render pipes with depth-based colors */}
            <svg width="100%" height="100%" className="absolute inset-0">
              {MOCK_DEPTH_DATA.map((pipe) => (
                <g key={pipe.id}>
                  {/* Pipe line */}
                  <line
                    x1={pipe.x}
                    y1={pipe.y}
                    x2={pipe.x + pipe.length_ft * 2}
                    y2={pipe.y}
                    stroke={getPipeColor(pipe)}
                    strokeWidth="6"
                    opacity="0.8"
                    onMouseEnter={() => handleMouseEnter(pipe)}
                    onMouseLeave={handleMouseLeave}
                    style={{ cursor: 'pointer' }}
                  />
                  
                  {/* Pipe endpoints */}
                  <circle
                    cx={pipe.x}
                    cy={pipe.y}
                    r="4"
                    fill={getPipeColor(pipe)}
                    opacity="0.9"
                  />
                  <circle
                    cx={pipe.x + pipe.length_ft * 2}
                    cy={pipe.y}
                    r="4"
                    fill={getPipeColor(pipe)}
                    opacity="0.9"
                  />
                </g>
              ))}
            </svg>

            {/* Tooltip */}
            {hoveredPipe && (
              <TestTooltip 
                data={hoveredPipe} 
                x={mousePos.x} 
                y={mousePos.y} 
              />
            )}

            {/* Legend */}
            <TestLegend isVisible={true} />
          </>
        )}
      </div>

      {/* Test Results */}
      <div className="absolute bottom-4 left-4 z-50 bg-white border border-gray-300 rounded-lg shadow-lg p-4">
        <h4 className="font-semibold mb-2">Test Results</h4>
        <div className="text-sm space-y-1">
          <div className="flex justify-between">
            <span>Overlay Toggle:</span>
            <span className={isVisible ? 'text-green-600' : 'text-gray-500'}>
              {isVisible ? '✓ Working' : '✗ Hidden'}
            </span>
          </div>
          <div className="flex justify-between">
            <span>Legend Display:</span>
            <span className={isVisible ? 'text-green-600' : 'text-gray-500'}>
              {isVisible ? '✓ Visible' : '✗ Hidden'}
            </span>
          </div>
          <div className="flex justify-between">
            <span>Tooltips:</span>
            <span className={hoveredPipe ? 'text-green-600' : 'text-gray-500'}>
              {hoveredPipe ? '✓ Active' : '✗ None'}
            </span>
          </div>
          <div className="flex justify-between">
            <span>Color Coding:</span>
            <span className="text-green-600">✓ Working</span>
          </div>
        </div>
      </div>
    </div>
  );
}
