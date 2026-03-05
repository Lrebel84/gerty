import { useState, useRef, useEffect } from 'react'
import type { Message } from '../App'
import { MarkdownMessage } from './MarkdownMessage'

interface ChatWindowProps {
  messages: Message[]
  onSend: (content: string, provider?: string) => void
  onNewChat?: () => void
  localModel?: string
  voiceStatus: 'idle' | 'listening' | 'processing'
  provider: 'local' | 'openrouter'
  onProviderChange: (provider: 'local' | 'openrouter') => void
  onVoiceStatusChange?: (status: 'idle' | 'listening' | 'processing') => void
}

export function ChatWindow({ messages, onSend, onNewChat, localModel, voiceStatus, provider, onProviderChange }: ChatWindowProps) {
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const text = input.trim()
    if (text) {
      onSend(text, provider)
      setInput('')
    }
  }

  return (
    <div className="flex flex-col h-full">
      <header className="flex items-center justify-between px-6 py-4 border-b border-[var(--border)] bg-[var(--bg-secondary)]">
        <div className="flex items-center">
          <img src="/gerty.png" alt="Gerty" className="h-9 w-9 object-contain" />
        </div>
        <div className="flex items-center gap-3">
          {onNewChat && messages.length > 0 && (
            <button
              type="button"
              onClick={onNewChat}
              className="px-3 py-1.5 rounded-lg text-xs font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]"
            >
              New chat
            </button>
          )}
          <div className="flex rounded-lg bg-[var(--bg-tertiary)] p-0.5">
            <button
              type="button"
              onClick={() => onProviderChange('local')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                provider === 'local' ? 'bg-[var(--accent)] text-white' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
              }`}
            >
              Local
            </button>
            <button
              type="button"
              onClick={() => onProviderChange('openrouter')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                provider === 'openrouter' ? 'bg-[var(--accent)] text-white' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
              }`}
            >
              OpenRouter
            </button>
          </div>
          {localModel && provider === 'local' && (
            <span className="text-xs text-[var(--text-secondary)] truncate max-w-[120px]" title={localModel}>
              {localModel}
            </span>
          )}
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
              className={`max-w-[85%] rounded-2xl px-4 py-3 select-text cursor-text ${
                m.role === 'user'
                  ? 'bg-[var(--accent)] text-white'
                  : 'bg-[var(--bg-tertiary)] text-[var(--text-primary)]'
              }`}
            >
              {m.role === 'user' ? (
                <p className="whitespace-pre-wrap text-sm leading-relaxed">{m.content}</p>
              ) : m.content ? (
                <MarkdownMessage content={m.content} />
              ) : (
                <span className="inline-block w-2 h-4 bg-[var(--accent)] animate-pulse" />
              )}
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
