// frontend/src/pages/UploadPage.tsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ingestFiles } from '../api/client'
import DebugCandidatesPanel from '../components/DebugCandidatesPanel'

export default function UploadPage() {
  const [pid, setPid] = useState('')
  const [files, setFiles] = useState<FileList | null>(null)
  const [busy, setBusy] = useState(false)
  const [showDebug, setShowDebug] = useState(false)
  const [debugFileRef, setDebugFileRef] = useState<string | null>(null)
  const nav = useNavigate()

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!files || !pid) return
    setBusy(true)
    try {
      // Use the legacy ingest endpoint to properly save files and create indices
      const fileArray = Array.from(files)
      const result = await ingestFiles(pid, fileArray)
      console.log('Ingest result:', result)
      
      // Navigate to project page
      nav(`/projects/${encodeURIComponent(pid)}`)
    } catch (err) {
      alert(String(err))
    } finally {
      setBusy(false)
    }
  }

  const handleDebugToggle = () => {
    if (!showDebug && files && files.length > 0) {
      // For local file, we can't use file path directly
      // User needs to provide an absolute path or upload first
      const filePath = prompt('Enter absolute path to PDF for debug (e.g., /Users/.../file.pdf):')
      if (filePath) {
        setDebugFileRef(filePath)
        setShowDebug(true)
      }
    } else {
      setShowDebug(!showDebug)
    }
  }

  return (
    <div className="grid gap-6">
      <div className="flex justify-between items-center">
        <div className="text-xl font-semibold">Upload PDFs</div>
        
        {/* Debug toggle */}
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input
            type="checkbox"
            checked={showDebug}
            onChange={handleDebugToggle}
            className="w-4 h-4"
          />
          <span className="text-gray-700">🔍 Debug: Show raw candidates</span>
        </label>
      </div>

      <form onSubmit={onSubmit} className="grid gap-4 rounded-2xl p-4 shadow bg-white">
        <label className="grid gap-1">
          <span className="text-sm opacity-80">Project ID</span>
          <input
            value={pid}
            onChange={e => setPid(e.target.value)}
            className="border rounded px-3 py-2"
            required
          />
        </label>
        <label className="grid gap-1">
          <span className="text-sm opacity-80">PDF files</span>
          <input
            type="file"
            accept="application/pdf"
            multiple
            onChange={e => setFiles(e.target.files)}
          />
        </label>
        <button disabled={busy} className="rounded-2xl px-4 py-2 bg-gray-900 text-white disabled:opacity-60">
          {busy ? 'Uploading…' : 'Ingest & Continue'}
        </button>
      </form>

      {/* Debug panel */}
      {showDebug && (
        <DebugCandidatesPanel
          fileRef={debugFileRef}
          onClose={() => {
            setShowDebug(false)
            setDebugFileRef(null)
          }}
        />
      )}
    </div>
  )
}
