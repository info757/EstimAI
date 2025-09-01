import { useEffect, useState, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { 
  pipelineAsync, 
  getJob, 
  listArtifacts, 
  generateBid, 
  fileUrl 
} from '../api/client'
import type { JobResponse, ArtifactsResponse } from '../types/api'
import Toast, { type ToastType } from '../components/Toast'

interface ToastState {
  type: ToastType;
  message: string;
}

export default function ProjectPage() {
  const { pid = '' } = useParams()
  const [artifacts, setArtifacts] = useState<ArtifactsResponse | null>(null)
  const [isGeneratingBid, setIsGeneratingBid] = useState(false)
  const [isRunningPipeline, setIsRunningPipeline] = useState(false)
  const [currentJobId, setCurrentJobId] = useState<string | null>(null)
  const [toast, setToast] = useState<ToastState | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Load existing artifacts on page load
  useEffect(() => {
    fetchArtifacts()
  }, [pid])

  const fetchArtifacts = useCallback(async () => {
    try {
      const data = await listArtifacts(pid)
      setArtifacts(data)
      setError(null)
    } catch (err) {
      console.error('Failed to fetch artifacts:', err)
      setError('Failed to load artifacts')
    }
  }, [pid])

  const showToast = useCallback((type: ToastType, message: string) => {
    setToast({ type, message })
  }, [])

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
          await fetchArtifacts()
          
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
  }, [showToast, fetchArtifacts])

  async function onGenerateBid() {
    setIsGeneratingBid(true)
    setError(null)
    
    try {
      const response = await generateBid(pid)
      
      // Open the PDF in a new tab
      window.open(fileUrl(response.pdf_path), '_blank')
      
      // Refresh artifacts list
      await fetchArtifacts()
      
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

  const isAnyActionRunning = isGeneratingBid || isRunningPipeline

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
            {isGeneratingBid ? 'Generating…' : 'Generate Bid PDF'}
          </button>
          <button
            onClick={onRunFullPipeline}
            disabled={isAnyActionRunning}
            className="rounded-2xl px-4 py-2 bg-blue-600 text-white disabled:opacity-60 disabled:cursor-not-allowed hover:bg-blue-700 transition-colors"
          >
            {isRunningPipeline ? 'Running Pipeline…' : 'Run Full Pipeline'}
          </button>
        </div>
      </div>

      {/* Review Section */}
      <div className="grid gap-3">
        <div className="text-lg font-semibold">Review</div>
        <div className="flex gap-3">
          <a
            href={`/projects/${pid}/review/takeoff`}
            className="rounded-2xl px-4 py-2 bg-green-600 text-white hover:bg-green-700 transition-colors"
          >
            Review Quantities
          </a>
          <a
            href={`/projects/${pid}/review/estimate`}
            className="rounded-2xl px-4 py-2 bg-purple-600 text-white hover:bg-purple-700 transition-colors"
          >
            Review Pricing
          </a>
        </div>
      </div>

      {error && (
        <div className="rounded-xl p-4 bg-red-50 text-red-700 text-sm whitespace-pre-wrap">
          {error}
        </div>
      )}

      <div className="grid gap-3">
        <div className="text-lg font-semibold">Artifacts</div>
        {!artifacts && !error && (
          <div className="opacity-70">
            No artifacts yet. Click "Generate Bid PDF" or "Run Full Pipeline".
          </div>
        )}
        {artifacts && Object.entries(artifacts.artifacts).map(([key, path]) => (
          <div key={key} className="flex items-center justify-between rounded-2xl p-4 shadow bg-white">
            <div className="font-medium">{key}</div>
            <a 
              className="underline hover:text-blue-600 transition-colors" 
              href={fileUrl(path)} 
              target="_blank" 
              rel="noreferrer"
            >
              Download
            </a>
          </div>
        ))}
      </div>

      {/* Toast notifications */}
      {toast && (
        <Toast
          type={toast.type}
          message={toast.message}
          onClose={hideToast}
        />
      )}
    </div>
  )
}

