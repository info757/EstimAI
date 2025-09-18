// frontend/src/pages/UploadPage.tsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { post } from '../api/client'

export default function UploadPage() {
  const [pid, setPid] = useState('')
  const [files, setFiles] = useState<FileList | null>(null)
  const [busy, setBusy] = useState(false)
  const nav = useNavigate()

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!files || !pid) return
    setBusy(true)
    try {
      const fd = new FormData()
      // Many FastAPI handlers use: files: List[UploadFile]
      Array.from(files).forEach(f => fd.append('files', f))
      // Some use: file: UploadFile (singular) — add first file as fallback
      if (files.length > 0) fd.append('file', files[0])

      await post<void>(`/projects/${encodeURIComponent(pid)}/ingest`, fd)
      nav(`/projects/${encodeURIComponent(pid)}`)
    } catch (err) {
      alert(String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid gap-6">
      <div className="text-xl font-semibold">Upload PDFs</div>

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
    </div>
  )
}


