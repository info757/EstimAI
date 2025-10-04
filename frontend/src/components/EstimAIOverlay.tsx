import { useEffect, useRef, useState } from 'react';
import type { WebViewerInstance } from '@pdftron/webviewer';

// Depth bucket configuration
const DEPTH_BUCKETS = [
  { range: '<5', min: 0, max: 5, color: '#10b981', label: 'Shallow' },
  { range: '5-8', min: 5, max: 8, color: '#f59e0b', label: 'Medium' },
  { range: '8-12', min: 8, max: 12, color: '#ef4444', label: 'Deep' },
  { range: '12+', min: 12, max: Infinity, color: '#7c3aed', label: 'Very Deep' }
];

// Pipe depth data type
type PipeDepthData = {
  id: string;
  x: number;
  y: number;
  length_ft: number;
  dia_in: number;
  material: string;
  min_depth_ft: number;
  max_depth_ft: number;
  avg_depth_ft: number;
  p95_depth_ft: number;
  buckets_lf: {
    '0-5': number;
    '5-8': number;
    '8-12': number;
    '12+': number;
  };
  trench_volume_cy: number;
  cover_ok: boolean;
  deep_excavation: boolean;
};

// Tooltip component
function DepthTooltip({ data, x, y }: { data: PipeDepthData; x: number; y: number }) {
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
function DepthLegend({ isVisible }: { isVisible: boolean }) {
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

// Main overlay component
type EstimAIOverlayProps = {
  instance: WebViewerInstance;
  pageNumber?: number;
  isVisible?: boolean;
  onToggle?: (visible: boolean) => void;
};

export default function EstimAIOverlay({ 
  instance, 
  pageNumber, 
  isVisible = true,
  onToggle 
}: EstimAIOverlayProps) {
  const overlayRef = useRef<HTMLDivElement>(null);
  const [depthData, setDepthData] = useState<PipeDepthData[]>([]);
  const [hoveredPipe, setHoveredPipe] = useState<PipeDepthData | null>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [isDocumentReady, setIsDocumentReady] = useState(false);

  // Fetch depth data from the API
  useEffect(() => {
    if (!isDocumentReady || !isVisible) return;

    const fetchDepthData = async () => {
      try {
        const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
        
        // First, get the takeoff data
        const takeoffResponse = await fetch(`${API}/v1/takeoff/pdf`, {
          method: 'POST',
          body: new FormData().append('file', 'bid_test.pdf')
        });
        
        if (!takeoffResponse.ok) {
          console.error('Failed to fetch takeoff data');
          return;
        }
        
        const takeoffData = await takeoffResponse.json();
        
        // Extract pipe data with depth information
        const pipes: PipeDepthData[] = [];
        
        // Process storm pipes
        if (takeoffData.networks?.storm?.pipes) {
          takeoffData.networks.storm.pipes.forEach((pipe: any) => {
            if (pipe.extra) {
              pipes.push({
                id: pipe.id,
                x: 100 + Math.random() * 400, // Mock coordinates for demo
                y: 100 + Math.random() * 400,
                length_ft: pipe.length_ft,
                dia_in: pipe.dia_in,
                material: pipe.mat,
                min_depth_ft: pipe.extra.min_depth_ft || 0,
                max_depth_ft: pipe.extra.max_depth_ft || 0,
                avg_depth_ft: pipe.avg_depth_ft || 0,
                p95_depth_ft: pipe.extra.p95_depth_ft || 0,
                buckets_lf: pipe.extra.buckets_lf || { '0-5': 0, '5-8': 0, '8-12': 0, '12+': 0 },
                trench_volume_cy: pipe.extra.trench_volume_cy || 0,
                cover_ok: pipe.extra.cover_ok || false,
                deep_excavation: pipe.extra.deep_excavation || false
              });
            }
          });
        }
        
        // Process sanitary pipes
        if (takeoffData.networks?.sanitary?.pipes) {
          takeoffData.networks.sanitary.pipes.forEach((pipe: any) => {
            if (pipe.extra) {
              pipes.push({
                id: pipe.id,
                x: 100 + Math.random() * 400,
                y: 100 + Math.random() * 400,
                length_ft: pipe.length_ft,
                dia_in: pipe.dia_in,
                material: pipe.mat,
                min_depth_ft: pipe.extra.min_depth_ft || 0,
                max_depth_ft: pipe.extra.max_depth_ft || 0,
                avg_depth_ft: pipe.avg_depth_ft || 0,
                p95_depth_ft: pipe.extra.p95_depth_ft || 0,
                buckets_lf: pipe.extra.buckets_lf || { '0-5': 0, '5-8': 0, '8-12': 0, '12+': 0 },
                trench_volume_cy: pipe.extra.trench_volume_cy || 0,
                cover_ok: pipe.extra.cover_ok || false,
                deep_excavation: pipe.extra.deep_excavation || false
              });
            }
          });
        }
        
        // Process water pipes
        if (takeoffData.networks?.water?.pipes) {
          takeoffData.networks.water.pipes.forEach((pipe: any) => {
            if (pipe.extra) {
              pipes.push({
                id: pipe.id,
                x: 100 + Math.random() * 400,
                y: 100 + Math.random() * 400,
                length_ft: pipe.length_ft,
                dia_in: pipe.dia_in,
                material: pipe.mat,
                min_depth_ft: pipe.extra.min_depth_ft || 0,
                max_depth_ft: pipe.extra.max_depth_ft || 0,
                avg_depth_ft: pipe.avg_depth_ft || 0,
                p95_depth_ft: pipe.extra.p95_depth_ft || 0,
                buckets_lf: pipe.extra.buckets_lf || { '0-5': 0, '5-8': 0, '8-12': 0, '12+': 0 },
                trench_volume_cy: pipe.extra.trench_volume_cy || 0,
                cover_ok: pipe.extra.cover_ok || false,
                deep_excavation: pipe.extra.deep_excavation || false
              });
            }
          });
        }
        
        setDepthData(pipes);
        console.log('Loaded depth data for', pipes.length, 'pipes');
        
      } catch (error) {
        console.error('Error fetching depth data:', error);
      }
    };

    fetchDepthData();
  }, [isDocumentReady, isVisible]);

  // Set up document viewer events
  useEffect(() => {
    const { documentViewer } = instance.Core;

    const onLoaded = () => {
      console.log('Document loaded, setting ready state');
      setIsDocumentReady(true);
    };

    documentViewer.addEventListener('documentLoaded', onLoaded);
    if (documentViewer.getDocument()) onLoaded();

    return () => {
      documentViewer.removeEventListener('documentLoaded', onLoaded);
    };
  }, [instance]);

  // Position overlay
  useEffect(() => {
    if (!isDocumentReady) return;

    const { documentViewer } = instance.Core;
    const target = Number.isFinite(Number(pageNumber)) && Number(pageNumber) >= 1
      ? Number(pageNumber)
      : documentViewer.getCurrentPage();

    const update = () => {
      if (!documentViewer.getDocument()) return;

      const dm = documentViewer.getDisplayModeManager().getDisplayMode();
      if (!dm || typeof dm.getPageTransform !== 'function') return;
      
      const t = dm.getPageTransform(target);
      const el = overlayRef.current;
      if (!el) return;

      const parent = documentViewer.getScrollViewElement() as HTMLElement;
      if (getComputedStyle(parent).position === 'static') parent.style.position = 'relative';
      
      Object.assign(el.style, {
        position: 'absolute',
        left: `${t.x}px`,
        top: `${t.y}px`,
        width: `${t.width}px`,
        height: `${t.height}px`,
        pointerEvents: 'none',
        zIndex: '99999',
      });
      
      if (!parent.contains(el)) parent.appendChild(el);
    };

    const onLayout = () => update();
    const onZoom = () => update();
    const onPage = () => update();

    documentViewer.addEventListener('layoutChanged', onLayout);
    documentViewer.addEventListener('zoomUpdated', onZoom);
    documentViewer.addEventListener('pageNumberUpdated', onPage);

    update();

    return () => {
      documentViewer.removeEventListener('layoutChanged', onLayout);
      documentViewer.removeEventListener('zoomUpdated', onZoom);
      documentViewer.removeEventListener('pageNumberUpdated', onPage);
    };
  }, [instance, pageNumber, isDocumentReady]);

  // Get color for pipe based on dominant depth bucket
  const getPipeColor = (pipe: PipeDepthData) => {
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

  const handleMouseEnter = (pipe: PipeDepthData) => {
    setHoveredPipe(pipe);
  };

  const handleMouseLeave = () => {
    setHoveredPipe(null);
  };

  if (!isVisible) return null;

  return (
    <div ref={overlayRef} onMouseMove={handleMouseMove}>
      {/* Render pipes with depth-based colors */}
      <svg width="100%" height="100%" style={{ position: 'absolute', top: 0, left: 0 }}>
        {depthData.map((pipe) => (
          <g key={pipe.id}>
            {/* Pipe line */}
            <line
              x1={pipe.x}
              y1={pipe.y}
              x2={pipe.x + pipe.length_ft * 2} // Scale for visualization
              y2={pipe.y}
              stroke={getPipeColor(pipe)}
              strokeWidth="4"
              opacity="0.8"
              onMouseEnter={() => handleMouseEnter(pipe)}
              onMouseLeave={handleMouseLeave}
              style={{ cursor: 'pointer' }}
            />
            
            {/* Pipe endpoints */}
            <circle
              cx={pipe.x}
              cy={pipe.y}
              r="3"
              fill={getPipeColor(pipe)}
              opacity="0.9"
            />
            <circle
              cx={pipe.x + pipe.length_ft * 2}
              cy={pipe.y}
              r="3"
              fill={getPipeColor(pipe)}
              opacity="0.9"
            />
          </g>
        ))}
      </svg>

      {/* Tooltip */}
      {hoveredPipe && (
        <DepthTooltip 
          data={hoveredPipe} 
          x={mousePos.x} 
          y={mousePos.y} 
        />
      )}

      {/* Legend */}
      <DepthLegend isVisible={true} />
    </div>
  );
}
