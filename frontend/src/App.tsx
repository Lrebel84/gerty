import { useState, useEffect } from 'react'
import { ChatWindow } from './components/ChatWindow'
import { Sidebar } from './components/Sidebar'

const API_BASE = '/api'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

export interface GertyAPI {
  sendMessage: (message: string) => Promise<string>
  getHistory: () => Message[]
}

declare global {
  interface Window {
    pywebview?: {
      api?: GertyAPI
    }
  }
}

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [voiceStatus, setVoiceStatus] = useState<'idle' | 'listening' | 'processing'>('idle')
  const [provider, setProvider] = useState<'local' | 'openrouter'>('local')

  useEffect(() => {
    fetch(`${API_BASE}/settings`)
      .then((r) => r.json())
      .then((d) => {
        if (d.provider === 'openrouter' || d.provider === 'local') {
          setProvider(d.provider)
        }
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    const win = window as unknown as {
      __gertyAddVoiceExchange?: (user: string, assistant: string) => void
      __gertySetVoiceStatus?: (status: string) => void
    }
    win.__gertyAddVoiceExchange = (user: string, assistant: string) => {
      setMessages((m) => [
        ...m,
        { id: crypto.randomUUID(), role: 'user', content: user, timestamp: new Date() },
        { id: crypto.randomUUID(), role: 'assistant', content: assistant, timestamp: new Date() },
      ])
    }
    win.__gertySetVoiceStatus = (status: string) => {
      if (['idle', 'listening', 'processing'].includes(status)) {
        setVoiceStatus(status as 'idle' | 'listening' | 'processing')
      }
    }
    return () => {
      delete win.__gertyAddVoiceExchange
      delete win.__gertySetVoiceStatus
    }
  }, [])

  const handleProviderChange = (p: 'local' | 'openrouter') => {
    setProvider(p)
    fetch(`${API_BASE}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider: p }),
    }).catch(() => {})
  }

  const handleSend = async (content: string, useProvider?: string) => {
    if (!content.trim()) return

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      timestamp: new Date(),
    }
    setMessages((m) => [...m, userMsg])

    const assistantId = crypto.randomUUID()
    const assistantMsg: Message = {
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
    }
    setMessages((m) => [...m, assistantMsg])

    try {
      const history = messages
        .slice(-10)
        .map((m) => ({ role: m.role, content: m.content }))
      const res = await fetch(`${API_BASE}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: content,
          history,
          provider: useProvider ?? provider,
        }),
      })
      if (!res.ok || !res.body) {
        const text = await res.text().catch(() => 'Request failed')
        setMessages((m) =>
          m.map((msg) =>
            msg.id === assistantId ? { ...msg, content: text || 'Request failed' } : msg
          )
        )
        return
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let acc = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        acc += decoder.decode(value, { stream: true })
        setMessages((m) =>
          m.map((msg) =>
            msg.id === assistantId ? { ...msg, content: acc } : msg
          )
        )
      }
    } catch (e) {
      setMessages((m) =>
        m.map((msg) =>
          msg.id === assistantId
            ? { ...msg, content: `Error: ${e instanceof Error ? e.message : 'Unknown error'}` }
            : msg
        )
      )
    }
  }

  return (
    <div className="flex h-screen bg-[var(--bg-primary)] text-[var(--text-primary)]">
      <Sidebar
        open={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        voiceStatus={voiceStatus}
      />
      <main className={`flex-1 flex flex-col transition-all ${sidebarOpen ? 'ml-64' : 'ml-0'}`}>
        <ChatWindow
          messages={messages}
          onSend={handleSend}
          voiceStatus={voiceStatus}
          provider={provider}
          onProviderChange={handleProviderChange}
          onVoiceStatusChange={setVoiceStatus}
        />
      </main>
    </div>
  )
}

export default App
