import React from 'react';
import PlanViewer from '../components/PlanViewer';
import OverlayLayer from '../components/OverlayLayer';

const PDFViewerPage: React.FC = () => {
  return (
    <div className="w-screen h-screen">
      <PlanViewer 
        docUrl="http://localhost:8000/files/280-utility-construction-plans.pdf"
        Overlay={OverlayLayer} 
      />
    </div>
  );
};

export default PDFViewerPage;
