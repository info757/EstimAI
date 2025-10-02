import { useEffect, useRef, useState } from 'react';
import WebViewer from '@pdftron/webviewer';
import OverlayLayer from './components/OverlayLayer';
import { Totals } from './components/Totals';
import { QAList } from './components/QAList';
import ErrorBoundary from './components/ErrorBoundary';
import { TakeoffMVPOut } from './lib/api';

export default function App() {
  const [mvpData, setMvpData] = useState<TakeoffMVPOut | null>(null);
  const [calibrationMode, setCalibrationMode] = useState(false);
  const viewerRef = useRef<HTMLDivElement>(null);
  const [instance, setInstance] = useState<any>(null);

  const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
  
  // 1) Read page from URL ONCE (default to 6)
  const sp = new URLSearchParams(window.location.search);
  const initialPage = Math.max(1, Number(sp.get('page')) || 6);
  console.log('[Parent] initialPage from URL =', initialPage);

  useEffect(() => {
    if (!viewerRef.current) return;
    WebViewer(
      {
        path: '/lib/webviewer',
        licenseKey: import.meta.env.VITE_APRYSE_KEY,
        initialDoc: `${API}/files/280-utility-construction-plans.pdf`,
        fullAPI: true
      },
      viewerRef.current
    ).then((inst) => {
      setInstance(inst);

      // 2) As soon as the doc loads, GO TO initialPage
      inst.Core.documentViewer.addEventListener('documentLoaded', () => {
        console.log('[Parent] documentLoaded → setCurrentPage', initialPage);
        inst.Core.documentViewer.setCurrentPage(initialPage);
        console.log('[Parent] now at page', inst.Core.documentViewer.getCurrentPage());
      });
    });
  }, [API, initialPage]);

  if (!instance) return <div ref={viewerRef} style={{ height: '100vh' }} />;

  return (
    <div className="w-screen h-screen relative">
      <div ref={viewerRef} style={{ height: '100vh' }} />
      
      {/* 3) PASS THE PAGE NUMBER DOWN */}
      <ErrorBoundary>
        <OverlayLayer 
          instance={instance} 
          pageNumber={initialPage}
          onWaterData={setMvpData}
          calibrationMode={calibrationMode}
          onCalibrationModeChange={setCalibrationMode}
        />
      </ErrorBoundary>
      
      {/* Debug info */}
      <div className="absolute top-4 left-4 bg-black/70 text-white text-xs p-2 rounded">
        <div>Backend: <a href={`${API}/files/280-utility-construction-plans.pdf`} target="_blank" className="text-blue-300">Test PDF</a></div>
        <div>Page: {initialPage}</div>
        <div>MVP Data: {mvpData ? `${mvpData.lines.length} lines` : 'Loading...'}</div>
      </div>

      <Totals mvp={mvpData ?? undefined} />
      <QAList qa={mvpData?.qa ?? []} />
      
      {/* Calibration button */}
      <div className="absolute bottom-4 left-4">
        <button
          onClick={() => setCalibrationMode(!calibrationMode)}
          className={`px-4 py-2 rounded font-medium ${
            calibrationMode 
              ? 'bg-red-500 text-white' 
              : 'bg-blue-500 text-white hover:bg-blue-600'
          }`}
        >
          {calibrationMode ? 'Exit Calibration' : 'Calibrate Scale'}
        </button>
      </div>
    </div>
  );
}