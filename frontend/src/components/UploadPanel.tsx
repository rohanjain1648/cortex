import { useRef, useState } from 'react'

interface Job {
  job_id: string
  status: 'pending' | 'parsing' | 'embedding' | 'done' | 'error'
  progress: number
  message: string
  source?: string
}

const SOURCES = [
  {
    id: 'linkedin',
    label: 'LinkedIn',
    hint: 'Settings → Data Privacy → Get a copy of your data. Select Posts, Profile, Articles.',
  },
  {
    id: 'twitter',
    label: 'Twitter / X',
    hint: 'Settings → Your account → Download an archive. Wait for the email, then download the ZIP.',
  },
  {
    id: 'instagram',
    label: 'Instagram',
    hint: 'Account Center → Your information and permissions → Download your information. Choose JSON format.',
  },
]

export default function UploadPanel({ onIngestComplete }: { onIngestComplete: () => void }) {
  const [jobs, setJobs] = useState<Job[]>([])
  const [dragging, setDragging] = useState<string | null>(null)
  const refs = useRef<Record<string, HTMLInputElement | null>>({})

  const upload = async (file: File) => {
    const form = new FormData()
    form.append('file', file)

    let data: { job_id: string }
    try {
      const res = await fetch('/api/ingest', { method: 'POST', body: form })
      if (!res.ok) throw new Error(await res.text())
      data = await res.json()
    } catch (e) {
      alert(`Upload failed: ${e}`)
      return
    }

    const { job_id } = data
    setJobs((prev) => [...prev, { job_id, status: 'pending', progress: 0, message: 'Queued...' }])

    const poll = async () => {
      const res = await fetch(`/api/ingest/${job_id}`)
      const job: Job = await res.json()
      setJobs((prev) => prev.map((j) => (j.job_id === job_id ? job : j)))
      if (job.status === 'done') {
        onIngestComplete()
        return
      }
      if (job.status !== 'error') {
        setTimeout(poll, 800)
      }
    }
    setTimeout(poll, 1000)
  }

  const handleFile = (file: File | null | undefined) => {
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.zip')) {
      alert('Please upload a ZIP file.')
      return
    }
    upload(file)
  }

  return (
    <div className="p-6 max-w-4xl mx-auto overflow-y-auto h-full">
      <div className="mb-6">
        <h2 className="text-base font-semibold mb-1">Ingest Social Data</h2>
        <p className="text-sm text-gray-500">
          Upload a ZIP export from LinkedIn, Twitter/X, or Instagram. Platform is auto-detected from the archive structure.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        {SOURCES.map((src) => (
          <label
            key={src.id}
            className={`relative flex flex-col gap-3 border-2 rounded-xl p-5 cursor-pointer transition-colors ${
              dragging === src.id ? 'border-blue-500 bg-blue-500/10' : 'border-gray-800 hover:border-gray-600'
            }`}
            onDragOver={(e) => {
              e.preventDefault()
              setDragging(src.id)
            }}
            onDragLeave={() => setDragging(null)}
            onDrop={(e) => {
              e.preventDefault()
              setDragging(null)
              handleFile(e.dataTransfer.files[0])
            }}
          >
            <input
              ref={(el) => { refs.current[src.id] = el }}
              type="file"
              accept=".zip"
              className="sr-only"
              onChange={(e) => handleFile(e.target.files?.[0])}
            />
            <span className="font-medium text-sm">{src.label}</span>
            <span className="text-xs text-gray-500 leading-relaxed flex-1">{src.hint}</span>
            <div className="text-xs text-gray-600 border border-dashed border-gray-700 rounded-lg py-2.5 text-center">
              Drop ZIP or click to browse
            </div>
          </label>
        ))}
      </div>

      {jobs.length > 0 && (
        <div>
          <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">Ingestion Jobs</h3>
          <div className="space-y-3">
            {jobs.map((job) => (
              <div key={job.job_id} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2.5">
                    <span
                      className={`w-2 h-2 rounded-full shrink-0 ${
                        job.status === 'done'
                          ? 'bg-green-500'
                          : job.status === 'error'
                          ? 'bg-red-500'
                          : 'bg-yellow-400 animate-pulse'
                      }`}
                    />
                    <span className="text-sm font-medium capitalize">
                      {job.source ?? 'Detecting…'}
                    </span>
                  </div>
                  <span className="text-xs text-gray-500">{job.progress}%</span>
                </div>
                <div className="w-full bg-gray-800 rounded-full h-1 mb-2">
                  <div
                    className={`h-1 rounded-full transition-all duration-300 ${
                      job.status === 'error' ? 'bg-red-500' : 'bg-blue-500'
                    }`}
                    style={{ width: `${job.progress}%` }}
                  />
                </div>
                <p className="text-xs text-gray-500">{job.message}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
