import { useEffect, useRef, useState } from 'react'
import { ChatWindow } from './components/ChatWindow'
import { Sidebar } from './components/Sidebar'

const API_BASE = '/api'

const SIDEBAR_MIN = 220
const SIDEBAR_MAX = 480
const SIDEBAR_DEFAULT = 300

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
  const messagesRef = useRef<Message[]>([])
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    try {
      const w = parseInt(localStorage.getItem('gerty_sidebar_width') || '', 10)
      if (w >= SIDEBAR_MIN && w <= SIDEBAR_MAX) return w
    } catch {}
    return SIDEBAR_DEFAULT
  })
  const [voiceStatus, setVoiceStatus] = useState<'idle' | 'listening' | 'processing'>('idle')
  const [provider, setProvider] = useState<'local' | 'openrouter'>('local')
  const [localModel, setLocalModel] = useState('')
  const [openrouterModel, setOpenrouterModel] = useState('')

  useEffect(() => {
    fetch(`${API_BASE}/settings`)
      .then((r) => r.json())
      .then((d) => {
        if (d.provider === 'openrouter' || d.provider === 'local') {
          setProvider(d.provider)
        }
        setLocalModel(d.local_model || '')
        setOpenrouterModel(d.openrouter_model || '')
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    fetch(`${API_BASE}/chat/history`)
      .then((r) => r.json())
      .then((d) => {
        const msgs = d.messages || []
        if (msgs.length > 0) {
          setMessages(msgs.map((m: { id?: string; role?: string; content?: string; timestamp?: string }) => ({
            id: m.id || crypto.randomUUID(),
            role: (m.role === 'assistant' ? 'assistant' : 'user') as 'user' | 'assistant',
            content: m.content || '',
            timestamp: m.timestamp ? new Date(m.timestamp) : new Date(),
          })))
        }
      })
      .catch(() => {})
  }, [])

  const saveHistory = (msgs: Message[], keepalive = false, skipExtract = false) => {
    const body = JSON.stringify({
      messages: msgs.map((m) => ({
        id: m.id,
        role: m.role,
        content: m.content,
        timestamp: m.timestamp?.toISOString?.(),
      })),
    })
    const url = skipExtract ? `${API_BASE}/chat/history?skip_extract=true` : `${API_BASE}/chat/history`
    fetch(url, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body,
      keepalive,
    }).catch(() => {})
  }

  useEffect(() => {
    messagesRef.current = messages
  }, [messages])

  useEffect(() => {
    const win = window as unknown as {
      __gertyAddVoiceExchange?: (user: string, assistant: string) => void
      __gertySetVoiceStatus?: (status: string) => void
      __gertyGetMessages?: () => Message[]
      __gertySaveHistory?: () => void
    }
    win.__gertyGetMessages = () => messagesRef.current
    win.__gertySaveHistory = () => saveHistory(messagesRef.current)
    const onBeforeUnload = () => saveHistory(messagesRef.current, true, true)
    window.addEventListener('beforeunload', onBeforeUnload)
    return () => {
      delete win.__gertyGetMessages
      delete win.__gertySaveHistory
      window.removeEventListener('beforeunload', onBeforeUnload)
    }
  }, [])

  const streamingAssistantIdRef = useRef<string | null>(null)

  useEffect(() => {
    const win = window as unknown as {
      __gertyAddVoiceExchange?: (user: string, assistant: string) => void
      __gertyAddVoiceUserMessage?: (user: string) => void
      __gertySetVoiceAssistantContent?: (content: string) => void
      __gertySetVoiceStatus?: (status: string) => void
    }
    win.__gertyAddVoiceExchange = (user: string, assistant: string) => {
      setMessages((m) => [
        ...m,
        { id: crypto.randomUUID(), role: 'user', content: user, timestamp: new Date() },
        { id: crypto.randomUUID(), role: 'assistant', content: assistant, timestamp: new Date() },
      ])
    }
    win.__gertyAddVoiceUserMessage = (user: string) => {
      streamingAssistantIdRef.current = crypto.randomUUID()
      setMessages((m) => [
        ...m,
        { id: crypto.randomUUID(), role: 'user', content: user, timestamp: new Date() },
        { id: streamingAssistantIdRef.current!, role: 'assistant', content: '', timestamp: new Date() },
      ])
    }
    win.__gertySetVoiceAssistantContent = (content: string) => {
      setMessages((m) => {
        const idx = m.findIndex((msg) => msg.id === streamingAssistantIdRef.current)
        if (idx >= 0) {
          const next = [...m]
          next[idx] = { ...next[idx], content }
          return next
        }
        return m
      })
    }
    win.__gertySetVoiceStatus = (status: string) => {
      if (['idle', 'listening', 'processing'].includes(status)) {
        setVoiceStatus(status as 'idle' | 'listening' | 'processing')
      }
    }
    return () => {
      delete win.__gertyAddVoiceExchange
      delete win.__gertyAddVoiceUserMessage
      delete win.__gertySetVoiceAssistantContent
      delete win.__gertySetVoiceStatus
    }
  }, [])

  const refetchSettings = () => {
    fetch(`${API_BASE}/settings`)
      .then((r) => r.json())
      .then((d) => {
        if (d.provider === 'openrouter' || d.provider === 'local') setProvider(d.provider)
        setLocalModel(d.local_model || '')
        setOpenrouterModel(d.openrouter_model || '')
      })
      .catch(() => {})
  }

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

    const requestBody = {
      message: content,
      history: messages.slice(-10).map((m) => ({ role: m.role, content: m.content })),
      provider: useProvider ?? provider,
      local_model: localModel || undefined,
      openrouter_model: openrouterModel || undefined,
    }

    const tryStream = async (): Promise<boolean> => {
      const res = await fetch(`${API_BASE}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
      })
      if (!res.ok || !res.body) {
        const text = await res.text().catch(() => 'Request failed')
        setMessages((m) => {
          const updated = m.map((msg) =>
            msg.id === assistantId ? { ...msg, content: text || 'Request failed' } : msg
          )
          saveHistory(updated)
          return updated
        })
        return true
      }
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let acc = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        acc += decoder.decode(value, { stream: true })
        setMessages((m) =>
          m.map((msg) => (msg.id === assistantId ? { ...msg, content: acc } : msg))
        )
      }
      setMessages((m) => {
        saveHistory(m)
        return m
      })
      return true
    }

    const tryNonStreaming = async (): Promise<void> => {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
      })
      const data = await res.json().catch(() => ({}))
      const reply = data.reply ?? data.error ?? 'Request failed'
      setMessages((m) => {
        const updated = m.map((msg) =>
          msg.id === assistantId ? { ...msg, content: reply } : msg
        )
        saveHistory(updated)
        return updated
      })
    }

    try {
      await tryStream()
    } catch (e) {
      try {
        await tryNonStreaming()
      } catch (fallbackErr) {
        setMessages((m) => {
          const updated = m.map((msg) =>
            msg.id === assistantId
              ? {
                  ...msg,
                  content: `Error: ${e instanceof Error ? e.message : 'Unknown error'} (stream failed; non-streaming fallback also failed)`,
                }
              : msg
          )
          saveHistory(updated)
          return updated
        })
      }
    }
  }

  const handleSidebarResize = (w: number) => {
    const clamped = Math.min(SIDEBAR_MAX, Math.max(SIDEBAR_MIN, w))
    setSidebarWidth(clamped)
    try {
      localStorage.setItem('gerty_sidebar_width', String(clamped))
    } catch {}
  }

  return (
    <div className="flex h-screen bg-[var(--bg-primary)] text-[var(--text-primary)]">
      <Sidebar
        open={sidebarOpen}
        width={sidebarWidth}
        onResize={handleSidebarResize}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        voiceStatus={voiceStatus}
        onSettingsSave={refetchSettings}
      />
      <main
        className="flex-1 flex flex-col transition-[margin] duration-200"
        style={{ marginLeft: sidebarOpen ? sidebarWidth : 0 }}
      >
        <ChatWindow
          messages={messages}
          onSend={handleSend}
          localModel={localModel}
          onNewChat={() => {
            setMessages([])
            fetch(`${API_BASE}/chat/history`, { method: 'DELETE' }).catch(() => {})
          }}
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
