import { useState, useRef, useEffect } from 'react'
import type { Message } from '../App'
import { MarkdownMessage } from './MarkdownMessage'

const API_BASE = '/api'

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

// Use BOTH HTTP and bridge - Qt WebEngine can block fetch; bridge can fail to invoke. One will get through.
async function startVoiceRecording(): Promise<void> {
  try {
    await fetch(`${API_BASE}/voice/start`, { method: 'POST' })
  } catch {
    /* fetch may fail under PyWebView */
  }
  try {
    ;(window as unknown as { pywebview?: { api?: { startVoiceRecording?: () => void } } }).pywebview?.api?.startVoiceRecording?.()
  } catch {
    /* bridge fallback */
  }
}

async function stopVoiceRecording(): Promise<void> {
  try {
    await fetch(`${API_BASE}/voice/stop`, { method: 'POST' })
  } catch {
    /* fetch may fail under PyWebView */
  }
  try {
    ;(window as unknown as { pywebview?: { api?: { stopVoiceRecording?: () => void } } }).pywebview?.api?.stopVoiceRecording?.()
  } catch {
    /* bridge fallback */
  }
}

async function cancelVoiceProcessing(): Promise<void> {
  try {
    await fetch(`${API_BASE}/voice/cancel`, { method: 'POST' })
  } catch {
    /* ignore */
  }
}

function hasVoiceAPI(): boolean {
  return true
}

const MIC_DEBOUNCE_MS = 400

export function ChatWindow({ messages, onSend, onNewChat, localModel, voiceStatus, provider, onProviderChange, onVoiceStatusChange }: ChatWindowProps) {
  const [input, setInput] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const micClickBlockedRef = useRef(false)
  const recordingStartedAtRef = useRef<number | null>(null)

  useEffect(() => {
    if (voiceStatus === 'idle' || voiceStatus === 'processing') {
      // Ignore 'idle' within 600ms of starting - backend may send stale/erroneous idle
      if (voiceStatus === 'idle' && recordingStartedAtRef.current) {
        const elapsed = Date.now() - recordingStartedAtRef.current
        if (elapsed < 600) return
      }
      recordingStartedAtRef.current = null
      setIsRecording(false)
    }
  }, [voiceStatus])

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

  const handleMicClick = async () => {
    if (micClickBlockedRef.current) return
    micClickBlockedRef.current = true
    setTimeout(() => { micClickBlockedRef.current = false }, MIC_DEBOUNCE_MS)

    if (isRecording) {
      await stopVoiceRecording()
      setIsRecording(false)
      onVoiceStatusChange?.('processing')
    } else {
      recordingStartedAtRef.current = Date.now()
      await startVoiceRecording()
      setIsRecording(true)
      onVoiceStatusChange?.('listening')
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
            className={`text-sm px-2 py-1 rounded flex items-center gap-2 ${
              voiceStatus === 'listening'
                ? 'bg-emerald-500/20 text-emerald-400 animate-pulse'
                : voiceStatus === 'processing'
                ? 'bg-amber-500/20 text-amber-400'
                : 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)]'
            }`}
          >
            {voiceStatus === 'listening' ? 'Listening...' : voiceStatus === 'processing' ? 'Processing...' : 'Ready'}
            {voiceStatus === 'processing' && onVoiceStatusChange && (
              <button
                type="button"
                onClick={async () => {
                  await cancelVoiceProcessing()
                  onVoiceStatusChange('idle')
                }}
                className="text-xs underline hover:no-underline ml-1"
              >
                Cancel
              </button>
            )}
          </span>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto p-6 space-y-4 select-text">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-[var(--text-secondary)]">
            <p className="text-lg mb-2">
              {hasVoiceAPI()
                ? "Click the mic to speak—I'll detect when you stop, or click again to stop early. Or type below."
                : 'Type a message below.'}
            </p>
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
          {hasVoiceAPI() && (
            <button
              type="button"
              onClick={handleMicClick}
              disabled={voiceStatus === 'processing'}
              className={`p-3 rounded-xl transition-colors disabled:opacity-70 disabled:cursor-not-allowed ${
                voiceStatus === 'listening' || isRecording
                  ? 'bg-emerald-500 text-white'
                  : voiceStatus === 'processing'
                  ? 'bg-amber-500/30 text-amber-400'
                  : 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)] hover:bg-[var(--border)] hover:text-[var(--text-primary)]'
              }`}
              title={isRecording ? 'Click to stop early' : 'Click to speak'}
              aria-label={isRecording ? 'Stop recording' : 'Start recording'}
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
                <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
              </svg>
            </button>
          )}
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
