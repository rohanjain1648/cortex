import { useEffect, useState } from 'react'
import ChatInterface from './components/ChatInterface'
import StatsPanel from './components/StatsPanel'
import UploadPanel from './components/UploadPanel'

export interface KBStats {
  total_chunks: number
  sources: Record<string, number>
  content_types?: Record<string, number>
}

export default function App() {
  const [stats, setStats] = useState<KBStats | null>(null)
  const [tab, setTab] = useState<'chat' | 'upload'>('chat')

  const refreshStats = async () => {
    try {
      const res = await fetch('/api/stats')
      setStats(await res.json())
    } catch {
      // backend not ready yet
    }
  }

  useEffect(() => {
    refreshStats()
  }, [])

  return (
    <div className="h-full flex flex-col bg-gray-950 text-gray-100">
      <header className="shrink-0 border-b border-gray-800 px-6 py-3 flex items-center justify-between">
        <div>
          <span className="text-base font-semibold tracking-tight">Cortex</span>
          <span className="ml-3 text-sm text-gray-500">Social knowledge base</span>
        </div>
        <StatsPanel stats={stats} />
      </header>

      <nav className="shrink-0 flex border-b border-gray-800">
        {(['chat', 'upload'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-6 py-2.5 text-sm font-medium transition-colors ${
              tab === t
                ? 'text-white border-b-2 border-blue-500'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            {t === 'chat' ? 'Chat' : 'Ingest Data'}
          </button>
        ))}
      </nav>

      <main className="flex-1 min-h-0">
        {tab === 'chat' ? (
          <ChatInterface />
        ) : (
          <UploadPanel onIngestComplete={refreshStats} />
        )}
      </main>
    </div>
  )
}
