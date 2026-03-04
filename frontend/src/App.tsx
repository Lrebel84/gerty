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

  useEffect(() => {
    (window as unknown as { __gertyAddVoiceExchange?: (user: string, assistant: string) => void }).__gertyAddVoiceExchange = (user: string, assistant: string) => {
      setMessages((m) => [
        ...m,
        { id: crypto.randomUUID(), role: 'user', content: user, timestamp: new Date() },
        { id: crypto.randomUUID(), role: 'assistant', content: assistant, timestamp: new Date() },
      ])
    }
    return () => {
      delete (window as unknown as { __gertyAddVoiceExchange?: unknown }).__gertyAddVoiceExchange
    }
  }, [])

  const sendMessage = async (content: string): Promise<string> => {
    if (!content.trim()) return ''

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      timestamp: new Date(),
    }
    setMessages((m) => [...m, userMsg])

    try {
      if (window.pywebview?.api?.sendMessage) {
        const reply = await window.pywebview.api.sendMessage(content)
        return reply
      }
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: content }),
      })
      const data = await res.json()
      return data.reply || data.error || 'No response'
    } catch (e) {
      return `Error: ${e instanceof Error ? e.message : 'Unknown error'}`
    }
  }

  const handleSend = async (content: string) => {
    const reply = await sendMessage(content)
    if (reply) {
      const assistantMsg: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: reply,
        timestamp: new Date(),
      }
      setMessages((m) => [...m, assistantMsg])
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
          onVoiceStatusChange={setVoiceStatus}
        />
      </main>
    </div>
  )
}

export default App
