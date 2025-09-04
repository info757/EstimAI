import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { UploadPanel } from '../components/UploadPanel';
import { IngestSources } from '../components/IngestSources';
import { SampleFiles } from '../components/SampleFiles';
import { DemoWalkthrough } from '../components/DemoWalkthrough';
import { useArtifacts } from '../hooks/useArtifacts';
import { resetDemo } from '../api/client';

export default function DemoProjectPage() {
  const { pid } = useParams<{ pid: string }>();
  const { items: artifacts, loading: artifactsLoading, refresh: refreshArtifacts } = useArtifacts(pid || 'demo');
  const [isUploading, setIsUploading] = useState(false);
  const [pipelineStatus, setPipelineStatus] = useState<string>('idle');

  // Track demo-specific state
  const [demoFilesCount, setDemoFilesCount] = useState(0);
  const [pdfOpened, setPdfOpened] = useState(false);

  // Update demo files count when artifacts change
  useEffect(() => {
    if (artifacts) {
      setDemoFilesCount(artifacts.length);
    }
  }, [artifacts]);

  // Handle demo reset
  const handleResetDemo = async () => {
    try {
      await resetDemo();
      toast.success('Demo reset. Samples are ready.');
      
      // Clear demo localStorage
      localStorage.removeItem('estimai.demo.banner.dismissed');
      localStorage.removeItem('estimai.demo.pdf.opened');
      
      // Refresh artifacts
      refreshArtifacts();
      
      // Reset local state
      setPipelineStatus('idle');
      setPdfOpened(false);
      
      // Force page reload to reset all components
      window.location.reload();
    } catch (error) {
      toast.error('Failed to reset demo');
      console.error('Demo reset failed:', error);
    }
  };

  // Track PDF opening
  const handlePdfOpen = () => {
    setPdfOpened(true);
    localStorage.setItem('estimai.demo.pdf.opened', 'true');
  };

  // Add data attributes for DemoWalkthrough to monitor
  useEffect(() => {
    // Update data attributes for step tracking
    const filesCountElement = document.querySelector('[data-demo-files-count]');
    if (filesCountElement) {
      filesCountElement.setAttribute('data-demo-files-count', demoFilesCount.toString());
    }

    const pipelineStatusElement = document.querySelector('[data-demo-pipeline-status]');
    if (pipelineStatusElement) {
      pipelineStatusElement.setAttribute('data-demo-pipeline-status', pipelineStatus);
    }
  }, [demoFilesCount, pipelineStatus]);

  if (!pid) {
    return <div>Project ID required</div>;
  }

  return (
    <div className="grid gap-6">
      {/* Demo Walkthrough */}
      <DemoWalkthrough />

      {/* Project Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Demo Project</h1>
          <p className="text-gray-600">Try out EstimAI with sample files</p>
        </div>
        
        {/* Demo Actions */}
        <div className="flex items-center space-x-3">
          <button
            onClick={handleResetDemo}
            className="px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors"
          >
            Reset Demo
          </button>
        </div>
      </div>

      {/* CTA Sequence Banner */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-center justify-center space-x-4 text-sm font-medium text-blue-800">
          <span>1) Use sample</span>
          <span className="text-blue-400">→</span>
          <span>2) Run Full Pipeline</span>
          <span className="text-blue-400">→</span>
          <span>3) Open Bid PDF</span>
        </div>
      </div>

      {/* Sample Files */}
      <SampleFiles pid={pid} onComplete={refreshArtifacts} />

      {/* Upload Panel */}
      <UploadPanel 
        pid={pid} 
        onComplete={refreshArtifacts}
        onUploadStateChange={setIsUploading}
      />

      {/* Ingest Sources */}
      <IngestSources pid={pid} onComplete={refreshArtifacts} />

      {/* Artifacts List */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Project Artifacts</h2>
        {artifactsLoading ? (
          <div className="text-gray-500">Loading artifacts...</div>
        ) : artifacts && artifacts.length > 0 ? (
          <div className="space-y-2">
            {artifacts.map((artifact, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-white border border-gray-200 rounded-lg">
                <div className="flex items-center space-x-3">
                  <span className="text-gray-900">{artifact.name || `Artifact ${index + 1}`}</span>
                  {artifact.type && (
                    <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                      {artifact.type}
                    </span>
                  )}
                </div>
                
                {/* PDF Open Button */}
                {artifact.type === 'pdf' && (
                  <button
                    onClick={handlePdfOpen}
                    className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                  >
                    Open PDF
                  </button>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-gray-500 text-center py-8">
            No artifacts yet. Use the sample files above to get started!
          </div>
        )}
      </div>

      {/* Hidden elements for DemoWalkthrough monitoring */}
      <div 
        data-demo-files-count={demoFilesCount} 
        className="hidden"
      />
      <div 
        data-demo-pipeline-status={pipelineStatus} 
        className="hidden"
      />
    </div>
  );
}
