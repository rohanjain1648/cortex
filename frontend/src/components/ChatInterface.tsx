import { useEffect, useRef, useState } from 'react'

interface Source {
  text: string
  source: string
  content_type: string
  author: string
  timestamp?: string
  score: number
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
  pending?: boolean
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async () => {
    const query = input.trim()
    if (!query || loading) return

    setInput('')
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: query },
      { role: 'assistant', content: '', pending: true },
    ])
    setLoading(true)

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      })

      if (!response.ok || !response.body) throw new Error('Request failed')

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const payload = line.slice(6).trim()
          if (!payload) continue

          try {
            const event = JSON.parse(payload)
            if (event.type === 'text') {
              setMessages((prev) => {
                const msgs = [...prev]
                const last = { ...msgs[msgs.length - 1] }
                last.content += event.content
                return [...msgs.slice(0, -1), last]
              })
            } else if (event.type === 'sources') {
              setMessages((prev) => {
                const msgs = [...prev]
                const last = { ...msgs[msgs.length - 1], sources: event.sources, pending: false }
                return [...msgs.slice(0, -1), last]
              })
            } else if (event.type === 'done') {
              setMessages((prev) => {
                const msgs = [...prev]
                const last = { ...msgs[msgs.length - 1], pending: false }
                return [...msgs.slice(0, -1), last]
              })
            }
          } catch {
            // malformed SSE line, skip
          }
        }
      }
    } catch {
      setMessages((prev) => {
        const msgs = [...prev]
        return [
          ...msgs.slice(0, -1),
          {
            role: 'assistant' as const,
            content: 'Error: could not reach the backend. Make sure the server is running and GEMINI_API_KEY is set in .env.',
          },
        ]
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-5">
        {messages.length === 0 && (
          <div className="text-center text-gray-600 mt-24 select-none">
            <p className="text-lg">Ask anything about this person</p>
            <p className="text-sm mt-1 text-gray-700">
              e.g. "What does this person think about remote work?" or "What are their career interests?"
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'user' ? (
              <div className="max-w-xl bg-blue-600 rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm">
                {msg.content}
              </div>
            ) : (
              <div className="max-w-2xl w-full">
                <p className="text-sm leading-relaxed whitespace-pre-wrap text-gray-100">
                  {msg.content}
                  {msg.pending && <span className="animate-pulse ml-0.5">▋</span>}
                </p>

                {msg.sources && msg.sources.length > 0 && (
                  <details className="mt-3 group">
                    <summary className="text-xs text-gray-600 cursor-pointer hover:text-gray-400 select-none">
                      {msg.sources.length} source{msg.sources.length !== 1 ? 's' : ''} referenced
                    </summary>
                    <div className="mt-2 space-y-2">
                      {msg.sources.map((src, j) => (
                        <div key={j} className="text-xs bg-gray-900 border border-gray-800 rounded-lg p-3">
                          <div className="flex gap-2 text-gray-500 mb-1.5">
                            <span className="capitalize font-medium text-gray-400">{src.source}</span>
                            <span>{src.content_type}</span>
                            {src.author && src.author !== 'Unknown' && <span>{src.author}</span>}
                            {src.timestamp && <span>{src.timestamp.slice(0, 10)}</span>}
                            <span className="ml-auto">{Math.round(src.score * 100)}% match</span>
                          </div>
                          <p className="text-gray-400 line-clamp-3">{src.text}</p>
                        </div>
                      ))}
                    </div>
                  </details>
                )}
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="shrink-0 border-t border-gray-800 px-4 py-4">
        <div className="flex gap-2 max-w-3xl mx-auto">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
            placeholder="Ask about views, experiences, interests..."
            disabled={loading}
            className="flex-1 bg-gray-900 border border-gray-700 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 placeholder-gray-600 disabled:opacity-50"
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed rounded-xl text-sm font-medium transition-colors"
          >
            {loading ? '...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  )
}
