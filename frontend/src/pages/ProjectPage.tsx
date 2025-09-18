import { useEffect, useState, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { 
  pipelineAsync, 
  getJob, 
  generateBid, 
  fileUrl 
} from '../api/client'
import { UploadPanel } from '../components/UploadPanel'
import { IngestSources } from '../components/IngestSources'
import type { JobResponse } from '../types/api'
import Toast from '../components/Toast'
import { useArtifacts } from '../hooks/useArtifacts'
import DebugPanel from '../components/DebugPanel'

interface ToastState {
  type: 'success' | 'error' | 'info';
  message: string;
}

export default function ProjectPage() {
  const { pid = '' } = useParams()
  
  const { items: artifacts, loading: artifactsLoading, refresh: refreshArtifacts } = useArtifacts(pid)
  const [isGeneratingBid, setIsGeneratingBid] = useState(false)
  const [isRunningPipeline, setIsRunningPipeline] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [currentJobId, setCurrentJobId] = useState<string | null>(null)
  const [toast, setToast] = useState<ToastState | null>(null)
  const [error, setError] = useState<string | null>(null)

  const showToast = useCallback((type: 'success' | 'error' | 'info', message: string) => {
    setToast({ type, message })
  }, [])
  
  // Dev assertion for missing pid
  useEffect(() => {
    if (!pid) {
      console.error('ProjectPage: No project ID found in URL params');
      showToast('error', 'No project selected—open a project first.');
    }
  }, [pid, showToast]);

  const hideToast = useCallback(() => {
    setToast(null)
  }, [])

  // Poll job status until completion
  const pollJobStatus = useCallback(async (jobId: string) => {
    const pollInterval = 1500 // 1.5 seconds
    
    const poll = async (): Promise<void> => {
      try {
        const job = await getJob(jobId)
        
        if (job.status === 'complete') {
          setIsRunningPipeline(false)
          setCurrentJobId(null)
          
          // Show success toast with PDF link if available
          const pdfPath = job.meta?.pdf_path
          const message = pdfPath 
            ? `Pipeline completed! <a href="${fileUrl(pdfPath)}" target="_blank" class="underline">View PDF</a>`
            : 'Pipeline completed successfully!'
          
          showToast('success', message)
          
          // Refresh artifacts list
          await refreshArtifacts()
          
        } else if (job.status === 'failed') {
          setIsRunningPipeline(false)
          setCurrentJobId(null)
          
          const errorMessage = job.error || job.meta?.error_message || 'Pipeline failed'
          showToast('error', errorMessage)
          
        } else {
          // Still running, continue polling
          setTimeout(poll, pollInterval)
        }
      } catch (err) {
        setIsRunningPipeline(false)
        setCurrentJobId(null)
        showToast('error', 'Failed to check job status')
      }
    }
    
    poll()
  }, [showToast, refreshArtifacts])

  async function onGenerateBid() {
    setIsGeneratingBid(true)
    setError(null)
    
    try {
      const response = await generateBid(pid)
      
      // Open the PDF in a new tab
      window.open(fileUrl(response.pdf_path), '_blank')
      
      // Refresh artifacts list
      await refreshArtifacts()
      
      showToast('success', 'Bid PDF generated successfully!')
      
    } catch (err: any) {
      const errorMessage = err.message || 'Failed to generate bid PDF'
      showToast('error', errorMessage)
      setError(errorMessage)
    } finally {
      setIsGeneratingBid(false)
    }
  }

  async function onRunFullPipeline() {
    setIsRunningPipeline(true)
    setError(null)
    
    try {
      const response = await pipelineAsync(pid)
      setCurrentJobId(response.job_id)
      
      // Start polling for job status
      pollJobStatus(response.job_id)
      
    } catch (err: any) {
      setIsRunningPipeline(false)
      const errorMessage = err.message || 'Failed to start pipeline'
      showToast('error', errorMessage)
      setError(errorMessage)
    }
  }

  const isAnyActionRunning = isGeneratingBid || isRunningPipeline || isUploading

  return (
    <div className="grid gap-6">
      <div className="flex items-center justify-between">
        <div className="text-xl font-semibold">Project: {pid}</div>
        <div className="flex gap-3">
          <button
            onClick={onGenerateBid}
            disabled={isAnyActionRunning}
            className="rounded-2xl px-4 py-2 bg-gray-900 text-white disabled:opacity-60 disabled:cursor-not-allowed hover:bg-gray-800 transition-colors"
          >
            {isGeneratingBid ? 'Generating…' : isUploading ? 'Upload in Progress…' : 'Generate Bid PDF'}
          </button>
          <button
            onClick={onRunFullPipeline}
            disabled={isAnyActionRunning}
            className="rounded-2xl px-4 py-2 bg-blue-600 text-white disabled:opacity-60 disabled:cursor-not-allowed hover:bg-blue-700 transition-colors"
          >
            {isRunningPipeline ? 'Running Pipeline…' : isUploading ? 'Upload in Progress…' : 'Run Full Pipeline'}
          </button>
        </div>
      </div>

      {/* Review Section */}
      <div className="grid gap-3">
        <div className="text-lg font-semibold">Review</div>
        <div className="flex gap-3">
          {!pid ? (
            <div className="text-sm text-red-600">No project selected</div>
          ) : (
            <>
              <Link
                to={`/projects/${pid}/review`}
                className="rounded-2xl px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 transition-colors"
              >
                Review All
              </Link>
              <Link
                to={`/projects/${pid}/review?focus=takeoff`}
                className="rounded-2xl px-4 py-2 bg-green-600 text-white hover:bg-green-700 transition-colors"
              >
                Review Quantities
              </Link>
              <Link
                to={`/projects/${pid}/review?focus=estimate`}
                className="rounded-2xl px-4 py-2 bg-purple-600 text-white hover:bg-purple-700 transition-colors"
              >
                Review Pricing
              </Link>
            </>
          )}
        </div>
      </div>

      {error && (
        <div className="rounded-xl p-4 bg-red-50 text-red-700 text-sm whitespace-pre-wrap">
          {error}
        </div>
      )}


      {/* Upload Section */}
      <UploadPanel 
        pid={pid} 
        onComplete={refreshArtifacts}
        onUploadStateChange={setIsUploading}
      />

      {/* Ingest Sources Section */}
      <IngestSources pid={pid} />

      <div className="grid gap-3">
        <div className="text-lg font-semibold">Artifacts</div>
        {artifactsLoading && (
          <div className="opacity-70">
            Loading artifacts...
          </div>
        )}
        {!artifactsLoading && artifacts.length === 0 && (
          <div className="opacity-70">
            No artifacts yet. Click "Generate Bid PDF" or "Run Full Pipeline".
          </div>
        )}
        {artifacts.map((artifact) => {
          // Extract filename from path for better display
          const filename = artifact.path.split('/').pop() || artifact.type || 'File';
          return (
            <div key={artifact.path} className="flex items-center justify-between rounded-2xl p-4 shadow bg-white">
              <div className="font-medium">{filename}</div>
              <a 
                className="underline hover:text-blue-600 transition-colors" 
                href={fileUrl(artifact.path)} 
                target="_blank" 
                rel="noreferrer"
              >
                Download
              </a>
            </div>
          );
        })}
      </div>

      {/* Toast notifications */}
      {toast && (
        <Toast
          message={toast.message}
          options={{ type: toast.type }}
          onDismiss={hideToast}
        />
      )}
      
      {/* Debug Panel */}
      <DebugPanel currentJobId={currentJobId} />
    </div>
  )
}

