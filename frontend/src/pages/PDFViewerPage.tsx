import React, { useState } from 'react';
import PlanViewer from '../components/PlanViewer';
import OverlayLayer from '../components/OverlayLayer';
import EstimAIOverlay from '../components/EstimAIOverlay';
import DepthOverlayToggle from '../components/DepthOverlayToggle';

const PDFViewerPage: React.FC = () => {
  const [depthOverlayVisible, setDepthOverlayVisible] = useState(false);
  const [webViewerInstance, setWebViewerInstance] = useState<any>(null);

  const handleInstanceReady = (instance: any) => {
    setWebViewerInstance(instance);
  };

  return (
    <div className="w-screen h-screen relative">
      <PlanViewer 
        docUrl="http://localhost:8000/files/280-utility-construction-plans.pdf"
        Overlay={OverlayLayer}
        onInstance={handleInstanceReady}
      />
      
      {/* Depth Overlay Toggle */}
      <DepthOverlayToggle
        isVisible={depthOverlayVisible}
        onToggle={setDepthOverlayVisible}
      />
      
      {/* Depth Overlay */}
      {webViewerInstance && (
        <EstimAIOverlay
          instance={webViewerInstance}
          pageNumber={6}
          isVisible={depthOverlayVisible}
          onToggle={setDepthOverlayVisible}
        />
      )}
    </div>
  );
};

export default PDFViewerPage;
