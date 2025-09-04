import React, { useState } from 'react';
import { ingestAsync, getJob } from '../api/client';

interface SampleFilesProps {
  pid: string;
  onComplete?: () => void;
}

const SAMPLE_FILES = [
  "sample.pdf",
  "sample.docx", 
  "sample.xlsx",
  "sample.csv",
  "sample.jpg"
];

export const SampleFiles: React.FC<SampleFilesProps> = ({ pid, onComplete }) => {
  const [uploading, setUploading] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);

  const handleSampleClick = async (filename: string) => {
    if (uploading) return; // Prevent multiple uploads
    
    setUploading(filename);
    
    try {
      // Fetch the sample file from the static samples endpoint
      const response = await fetch(`/static/samples/${filename}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch sample: ${response.statusText}`);
      }
      
      // Convert to blob and then to File
      const blob = await response.blob();
      const file = new File([blob], filename, { type: blob.type || 'application/octet-stream' });
      
      // Use the async ingest method
      const result = await ingestAsync(pid, [file]);
      setJobId(result.job_id);
      
      // Poll for job completion
      const pollJob = async () => {
        try {
          const job = await getJob(result.job_id);
          
          if (job.status === 'complete') {
            // Success - show toast and refresh
            showToast('Sample uploaded successfully!', 'success');
            setUploading(null);
            setJobId(null);
            onComplete?.();
          } else if (job.status === 'failed') {
            // Failed - show error
            showToast(`Sample upload failed: ${job.error || 'Unknown error'}`, 'error');
            setUploading(null);
            setJobId(null);
          } else {
            // Still running, poll again
            setTimeout(pollJob, 1500);
          }
        } catch (error) {
          showToast(`Error checking job status: ${error}`, 'error');
          setUploading(null);
          setJobId(null);
        }
      };
      
      // Start polling
      pollJob();
      
    } catch (error) {
      showToast(`Failed to upload sample: ${error}`, 'error');
      setUploading(null);
    }
  };

  const showToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    // Simple toast implementation - you can replace with your preferred toast library
    const toast = document.createElement('div');
    toast.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      padding: 12px 20px;
      border-radius: 4px;
      color: white;
      font-weight: 500;
      z-index: 1000;
      background-color: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    `;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
      if (document.body.contains(toast)) {
        document.body.removeChild(toast);
      }
    }, 3000);
  };

  return (
    <div className="mb-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-3">
        No file handy? Try a sample
      </h3>
      <div className="flex flex-wrap gap-2">
        {SAMPLE_FILES.map((filename) => (
          <button
            key={filename}
            onClick={() => handleSampleClick(filename)}
            disabled={uploading !== null}
            className={`
              px-4 py-2 rounded-lg border text-sm font-medium transition-colors
              ${uploading === filename
                ? 'bg-blue-100 border-blue-300 text-blue-700 cursor-not-allowed'
                : uploading !== null
                ? 'bg-gray-100 border-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50 hover:border-gray-400'
              }
            `}
          >
            {uploading === filename ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                    fill="none"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                Uploading...
              </span>
            ) : (
              filename
            )}
          </button>
        ))}
      </div>
      {jobId && (
        <div className="mt-2 text-sm text-gray-600">
          Processing job: {jobId}
        </div>
      )}
    </div>
  );
};
