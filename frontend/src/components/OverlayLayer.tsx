import { useEffect, useRef, useState } from 'react';
import type { WebViewerInstance } from '@pdftron/webviewer';
import { runTakeoffMVP, TakeoffMVPOut } from '../lib/api';

type CountPoint = { x: number; y: number; label?: string };

async function fetchAndRenderCounts(instance: any, file: string, page: number, scale: number) {
  const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
  const res = await fetch(`${API}/v1/run/mvp?name=${encodeURIComponent(file)}&page=${page}&scale_in_equals_ft=${scale}`);
  const data = await res.json();             // ensure it returns { points: CountPoint[] } in PDF units
  const pts: CountPoint[] = data.points ?? [];

  const { Core } = instance;
  const { Annotations, annotationManager, Math: WvMath } = Core;

  // Remove previous annotations
  const prev = (fetchAndRenderCounts as any)._last || [];
  if (prev.length) {
    annotationManager.deleteAnnotations(prev, { force: true, drawImmediately: false });
  }

  const created: any[] = [];
  for (const { x, y, label } of pts) {
    // dot
    const dot = new Annotations.EllipseAnnotation();
    dot.PageNumber = page;
    dot.StrokeThickness = 0;
    dot.FillColor = new Annotations.Color(255, 0, 0, 0.95);
    const r = 6;
    dot.setRect(new WvMath.Rect(x - r, y - r, x + r, y + r));
    created.push(dot);

    if (label) {
      const txt = new Annotations.FreeTextAnnotation();
      txt.PageNumber = page;
      txt.setContents(label);
      txt.FontSize = '10pt';
      txt.FillColor = new Annotations.Color(255, 255, 255, 0);
      txt.StrokeThickness = 0;
      txt.setRect(new WvMath.Rect(x + 8, y - 7, x + 68, y + 7));
      created.push(txt);
    }
  }
  annotationManager.addAnnotations(created);
  annotationManager.drawAnnotationsFromList(created);

  (fetchAndRenderCounts as any)._last = created;
}

type OverlayLayerProps = {
  instance: any;
  pageNumber?: number; // may be undefined if not provided
  calibrationMode?: boolean;
  onWaterData?: (payload: TakeoffMVPOut | null) => void;
  onCalibrationModeChange?: (mode: boolean) => void;
};

export default function OverlayLayer({ 
  instance, 
  pageNumber, 
  calibrationMode = false,
  onWaterData,
  onCalibrationModeChange
}: OverlayLayerProps) {
  // normalize guards
  const safeOnWaterData = typeof onWaterData === 'function' ? onWaterData : undefined;
  const safeCalibration = typeof calibrationMode === 'boolean' ? calibrationMode : false;
  const safeOnCalibrationModeChange = typeof onCalibrationModeChange === 'function' ? onCalibrationModeChange : undefined;
  
  console.log('[Overlay] pageNumber prop =', pageNumber);

  const overlayRef = useRef<HTMLDivElement>(null);
  const [mvp, setMvp] = useState<TakeoffMVPOut | null>(null);
  const [isDocumentReady, setIsDocumentReady] = useState(false);

  // Fetch MVP data when document is ready
  useEffect(() => {
    if (!isDocumentReady || !safeOnWaterData) return;
    
    // Resolve exactly one target page
    const target = Number.isFinite(Number(pageNumber)) && Number(pageNumber) >= 1
      ? Number(pageNumber)
      : 6; // fallback to page 6
    
    const scale = 50; // Default scale
    console.log('Fetching MVP data for page:', target, 'with scale:', scale);
    runTakeoffMVP('280-utility-construction-plans.pdf', target - 1, scale).then(data => {
      setMvp(data);
      safeOnWaterData(data);
      
      // Render count points as annotations
      if (data.points && data.points.length > 0) {
        console.log('Rendering count points for page:', target);
        fetchAndRenderCounts(instance, '280-utility-construction-plans.pdf', target, scale);
      }
    }).catch(console.error);
  }, [isDocumentReady, pageNumber, safeOnWaterData, instance]);

  useEffect(() => {
    const { documentViewer } = instance.Core;

    const resolvePage = () => {
      const n = Number(pageNumber);
      return Number.isFinite(n) && n >= 1 ? n : documentViewer.getCurrentPage();
    };

    const update = () => {
      if (!documentViewer.getDocument()) return;

      // Resolve exactly one target page
      const target = Number.isFinite(Number(pageNumber)) && Number(pageNumber) >= 1
        ? Number(pageNumber)
        : documentViewer.getCurrentPage();

      // Ensure viewer is on that page (single-page mode uses this)
      if (documentViewer.getCurrentPage() !== target) {
        documentViewer.setCurrentPage(target);
      }

      // Get transform for that ONE page
      const dm = documentViewer.getDisplayModeManager().getDisplayMode();
      if (!dm || typeof dm.getPageTransform !== 'function') return;
      const t = dm.getPageTransform(target); // { x, y, width, height } in CSS px
      console.log('[Overlay] transform for page', target, '=>', t);

      // Position the overlay inside the scroll view
      const parent = documentViewer.getScrollViewElement() as HTMLElement;
      const el = overlayRef.current!;
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

    const onLoaded = () => {
      console.log('Document loaded, setting ready state');
      setIsDocumentReady(true);
      update();
    };
    
    const onLayout = () => update();
    const onZoom = () => update();
    const onPage = () => update();

    documentViewer.addEventListener('documentLoaded', onLoaded);
    documentViewer.addEventListener('layoutChanged', onLayout);
    documentViewer.addEventListener('zoomUpdated', onZoom);
    documentViewer.addEventListener('pageNumberUpdated', onPage);

    if (documentViewer.getDocument()) onLoaded();

    return () => {
      documentViewer.removeEventListener('documentLoaded', onLoaded);
      documentViewer.removeEventListener('layoutChanged', onLayout);
      documentViewer.removeEventListener('zoomUpdated', onZoom);
      documentViewer.removeEventListener('pageNumberUpdated', onPage);
    };
  }, [instance, pageNumber]);

  // Render takeoff lines
  const renderTakeoffLines = () => {
    if (!mvp?.lines) return null;

    const lines = mvp.lines.slice(0, 1000); // Limit for performance
    
    return (
      <svg width="100%" height="100%" style={{ position: 'absolute', top: 0, left: 0 }}>
        {lines.map((line) => {
          const color = line.kind === 'water' ? '#0ea5e9' : 
                       line.kind === 'sewer' ? '#22c55e' : 
                       line.kind === 'storm' ? '#f59e0b' : '#6b7280';
          
          return (
            <polyline
              key={line.id}
              points={line.points.map(p => `${p[0]},${p[1]}`).join(' ')}
              fill="none"
              stroke={color}
              strokeWidth="2"
            />
          );
        })}
      </svg>
    );
  };

  return (
    <div ref={overlayRef}>
      {renderTakeoffLines()}
    </div>
  );
}