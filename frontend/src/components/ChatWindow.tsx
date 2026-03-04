import { useState, useRef, useEffect } from 'react'
import type { Message } from '../App'

interface ChatWindowProps {
  messages: Message[]
  onSend: (content: string) => void
  voiceStatus: 'idle' | 'listening' | 'processing'
  onVoiceStatusChange?: (status: 'idle' | 'listening' | 'processing') => void
}

export function ChatWindow({ messages, onSend, voiceStatus }: ChatWindowProps) {
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const text = input.trim()
    if (text) {
      onSend(text)
      setInput('')
    }
  }

  return (
    <div className="flex flex-col h-full">
      <header className="flex items-center justify-between px-6 py-4 border-b border-[var(--border)] bg-[var(--bg-secondary)]">
        <h1 className="text-xl font-semibold tracking-tight">Gerty</h1>
        <div className="flex items-center gap-2">
          <span
            className={`text-sm px-2 py-1 rounded ${
              voiceStatus === 'listening'
                ? 'bg-emerald-500/20 text-emerald-400 animate-pulse'
                : voiceStatus === 'processing'
                ? 'bg-amber-500/20 text-amber-400'
                : 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)]'
            }`}
          >
            {voiceStatus === 'listening' ? 'Listening...' : voiceStatus === 'processing' ? 'Processing...' : 'Ready'}
          </span>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto p-6 space-y-4 select-text">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-[var(--text-secondary)]">
            <p className="text-lg mb-2">Say "computer" to wake me, or type below.</p>
            <p className="text-sm">I can tell you the time, set alarms and timers, and answer questions.</p>
          </div>
        )}
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-2.5 select-text cursor-text ${
                m.role === 'user'
                  ? 'bg-[var(--accent)] text-white'
                  : 'bg-[var(--bg-tertiary)] text-[var(--text-primary)]'
              }`}
            >
              <p className="whitespace-pre-wrap text-sm leading-relaxed">{m.content}</p>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <form
        onSubmit={handleSubmit}
        className="p-4 border-t border-[var(--border)] bg-[var(--bg-secondary)]"
      >
        <div className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a message..."
            className="flex-1 bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-xl px-4 py-3 text-sm placeholder:text-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
          />
          <button
            type="submit"
            className="px-5 py-3 bg-[var(--accent)] hover:bg-[var(--accent-hover)] rounded-xl text-sm font-medium transition-colors"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  )
}
