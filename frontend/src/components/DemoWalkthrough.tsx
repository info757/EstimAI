import React, { useState, useEffect } from 'react';

interface DemoWalkthroughProps {}

interface Step {
  id: number;
  text: string;
  completed: boolean;
}

export const DemoWalkthrough: React.FC<DemoWalkthroughProps> = () => {
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const [steps, setSteps] = useState<Step[]>([
    { id: 1, text: "Click Use sample", completed: false },
    { id: 2, text: "Run Full Pipeline", completed: false },
    { id: 3, text: "Open Bid PDF", completed: false }
  ]);
  const [showHelp, setShowHelp] = useState(false);

  // Check localStorage on mount
  useEffect(() => {
    const dismissed = localStorage.getItem('estimai.demo.banner.dismissed') === 'true';
    setBannerDismissed(dismissed);
  }, []);

  // Check for sample files (Step 1)
  useEffect(() => {
    const checkSampleFiles = () => {
      // This will be updated by the parent component to check actual file list
      const hasFiles = document.querySelector('[data-demo-files-count]')?.getAttribute('data-demo-files-count') !== '0';
      if (hasFiles && !steps[0].completed) {
        setSteps(prev => prev.map(step => 
          step.id === 1 ? { ...step, completed: true } : step
        ));
        console.info('DEMO_STEP_1_SAMPLES_USED');
      }
    };

    // Check periodically for file changes
    const interval = setInterval(checkSampleFiles, 1000);
    return () => clearInterval(interval);
  }, [steps]);

  // Check for pipeline success (Step 2)
  useEffect(() => {
    const checkPipelineSuccess = () => {
      // This will be updated by the parent component to check job status
      const pipelineSucceeded = document.querySelector('[data-demo-pipeline-status]')?.getAttribute('data-demo-pipeline-status') === 'succeeded';
      if (pipelineSucceeded && !steps[1].completed) {
        setSteps(prev => prev.map(step => 
          step.id === 2 ? { ...step, completed: true } : step
        ));
        console.info('DEMO_STEP_2_PIPELINE_SUCCEEDED');
      }
    };

    const interval = setInterval(checkPipelineSuccess, 1000);
    return () => clearInterval(interval);
  }, [steps]);

  // Check for PDF opened (Step 3)
  useEffect(() => {
    const checkPdfOpened = () => {
      // This will be updated by the parent component when PDF is opened
      const pdfOpened = localStorage.getItem('estimai.demo.pdf.opened') === 'true';
      if (pdfOpened && !steps[2].completed) {
        setSteps(prev => prev.map(step => 
          step.id === 3 ? { ...step, completed: true } : step
        ));
        console.info('DEMO_STEP_3_PDF_OPENED');
      }
    };

    const interval = setInterval(checkPdfOpened, 1000);
    return () => clearInterval(interval);
  }, [steps]);

  const dismissBanner = () => {
    setBannerDismissed(true);
    localStorage.setItem('estimai.demo.banner.dismissed', 'true');
  };

  const resetSteps = () => {
    setSteps(prev => prev.map(step => ({ ...step, completed: false })));
    localStorage.removeItem('estimai.demo.pdf.opened');
  };

  // Reset steps when component unmounts or resets
  useEffect(() => {
    return () => {
      // Clean up any demo-specific localStorage on unmount
      localStorage.removeItem('estimai.demo.pdf.opened');
    };
  }, []);

  if (bannerDismissed) {
    return null;
  }

  return (
    <div className="mb-6">
      {/* Top Banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <p className="text-blue-800 text-sm">
              You're viewing EstimAI in Demo Mode. Uploads are limited to our sample files, and data resets periodically.
            </p>
          </div>
                      <button
              onClick={dismissBanner}
              className="ml-4 text-blue-400 hover:text-blue-600 transition-colors text-lg font-bold"
              aria-label="Dismiss banner"
            >
              ×
            </button>
        </div>
      </div>

      {/* 3-Step Checklist */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-medium text-gray-900">Demo Walkthrough</h3>
          <div className="relative">
            <button
              onClick={() => setShowHelp(!showHelp)}
              className="text-gray-400 hover:text-gray-600 transition-colors text-lg font-bold"
              aria-label="Help"
            >
              ?
            </button>
            
            {/* Help Popover */}
            {showHelp && (
              <div className="absolute right-0 top-8 w-80 bg-white border border-gray-200 rounded-lg shadow-lg p-3 z-10">
                <div className="text-sm text-gray-700 space-y-2">
                  <p><strong>If a sample fails to upload:</strong> it's rate-limited or temporarily unavailable—try again.</p>
                  <p><strong>Pipeline stuck?</strong> Click retry, or refresh the page; jobs are safe.</p>
                  <p><strong>Want a clean slate?</strong> Use the Reset Demo button.</p>
                </div>
                <div className="absolute -top-2 right-4 w-4 h-4 bg-white border-l border-t border-gray-200 transform rotate-45"></div>
              </div>
            )}
          </div>
        </div>

        <div className="space-y-3">
          {steps.map((step) => (
            <div key={step.id} className="flex items-center space-x-3">
              <div className={`flex-shrink-0 w-6 h-6 rounded-full border-2 flex items-center justify-center ${
                step.completed 
                  ? 'bg-green-500 border-green-500' 
                  : 'bg-gray-100 border-gray-300'
              }`}>
                {step.completed ? (
                  <span className="text-white text-sm">✓</span>
                ) : (
                  <span className="text-xs text-gray-500">{step.id}</span>
                )}
              </div>
              <span className={`text-sm ${
                step.completed ? 'text-green-700 line-through' : 'text-gray-700'
              }`}>
                {step.text}
              </span>
            </div>
          ))}
        </div>

        {/* CTA Sequence */}
        <div className="mt-4 pt-3 border-t border-gray-100">
          <div className="flex items-center justify-center space-x-2 text-sm text-gray-600">
            <span>1) Use sample</span>
            <span className="text-gray-400">→</span>
            <span>2) Run Full Pipeline</span>
            <span className="text-gray-400">→</span>
            <span>3) Open Bid PDF</span>
          </div>
        </div>
      </div>

      {/* Reset Steps Button */}
      <div className="mt-3 text-center">
        <button
          onClick={resetSteps}
          className="text-xs text-gray-500 hover:text-gray-700 underline"
        >
          Reset progress
        </button>
      </div>
    </div>
  );
};

export default DemoWalkthrough;
