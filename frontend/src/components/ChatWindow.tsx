import { useState, useRef, useEffect } from 'react'
import type { Message } from '../App'
import { MarkdownMessage } from './MarkdownMessage'
import { SKILLS } from '../skills'

const API_BASE = '/api'

interface Alarm {
  id?: string
  time: string
  label?: string
  datetime?: string
  sounding?: boolean
  recurring?: string | null
}

interface Timer {
  id?: string
  label: string
  remaining_sec: number
  duration_sec: number
}

interface ChatWindowProps {
  messages: Message[]
  onSend: (content: string, provider?: string) => void
  onNewChat?: () => void
  voiceStatus: 'idle' | 'listening' | 'processing'
  onVoiceStatusChange?: (status: 'idle' | 'listening' | 'processing') => void
  skillsViewOpen?: boolean
  onCloseSkills?: () => void
  alarmsTimersViewOpen?: boolean
  onCloseAlarmsTimers?: () => void
  notesViewOpen?: boolean
  onCloseNotes?: () => void
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

function formatRemaining(sec: number): string {
  const m = Math.floor(sec / 60)
  const s = sec % 60
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

export function ChatWindow({ messages, onSend, onNewChat, voiceStatus, onVoiceStatusChange, skillsViewOpen, onCloseSkills, alarmsTimersViewOpen, onCloseAlarmsTimers, notesViewOpen, onCloseNotes }: ChatWindowProps) {
  const [input, setInput] = useState('')
  const [alarms, setAlarms] = useState<Alarm[]>([])
  const [timers, setTimers] = useState<Timer[]>([])
  const [notes, setNotes] = useState<string[]>([])
  const [noteInput, setNoteInput] = useState('')
  const [alarmTime, setAlarmTime] = useState('07:00')
  const [alarmLabel, setAlarmLabel] = useState('')
  const [alarmRecurring, setAlarmRecurring] = useState(false)
  const [timerMinutes, setTimerMinutes] = useState(5)
  const [timerLabel, setTimerLabel] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const [soundingAlarm, setSoundingAlarm] = useState<{ time?: string; label?: string } | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const micClickBlockedRef = useRef(false)
  const recordingStartedAtRef = useRef<number | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const refreshAlarmsTimers = async () => {
    try {
      const [aRes, tRes] = await Promise.all([
        fetch(`${API_BASE}/alarms`),
        fetch(`${API_BASE}/timers`),
      ])
      if (aRes.ok) {
        const d = await aRes.json()
        setAlarms(d.alarms || [])
      }
      if (tRes.ok) {
        const d = await tRes.json()
        setTimers(d.timers || [])
      }
    } catch {
      /* ignore */
    }
  }

  useEffect(() => {
    if (alarmsTimersViewOpen) {
      refreshAlarmsTimers()
      const iv = setInterval(refreshAlarmsTimers, 2000)
      return () => clearInterval(iv)
    }
  }, [alarmsTimersViewOpen])

  // Refresh when messages change (e.g. after chat adds timer or alarm)
  useEffect(() => {
    if (alarmsTimersViewOpen && messages.length > 0) {
      refreshAlarmsTimers()
    }
  }, [messages.length, alarmsTimersViewOpen])

  const refreshNotes = () => {
    // Bridge fallback: Qt WebEngine can block fetch; bridge bypasses it
    const api = (window as unknown as { pywebview?: { api?: { getNotes?: () => string[] | Promise<string[]> } } }).pywebview?.api
    if (api?.getNotes) {
      Promise.resolve(api.getNotes())
        .then((notes) => setNotes(Array.isArray(notes) ? notes : []))
        .catch(() => fetchNotesFallback())
    } else {
      fetchNotesFallback()
    }
  }
  const fetchNotesFallback = () => {
    fetch(`${API_BASE}/notes`)
      .then((r) => (r.ok ? r.json() : { notes: [] }))
      .then((d) => setNotes(d.notes || []))
      .catch(() => setNotes([]))
  }

  const refreshNotesRef = useRef(refreshNotes)
  refreshNotesRef.current = refreshNotes

  // Global notes poll (like alarm check) - ensures notes stay fresh when added by voice
  useEffect(() => {
    refreshNotes()
    const iv = setInterval(refreshNotes, 2000)
    return () => clearInterval(iv)
  }, [])

  useEffect(() => {
    if (notesViewOpen) {
      refreshNotes()
    }
  }, [notesViewOpen])

  // Refresh when messages change (e.g. after voice/chat adds a note)
  useEffect(() => {
    if (notesViewOpen && messages.length > 0) {
      refreshNotes()
    }
  }, [messages.length, notesViewOpen])

  // Expose refresh for voice completion - use ref to avoid stale closure
  useEffect(() => {
    const win = window as unknown as { __gertyRefreshAlarmsTimers?: () => void; __gertyRefreshNotes?: () => void }
    win.__gertyRefreshAlarmsTimers = () => refreshAlarmsTimers()
    win.__gertyRefreshNotes = () => refreshNotesRef.current?.()
    return () => { delete win.__gertyRefreshAlarmsTimers; delete win.__gertyRefreshNotes }
  }, [])

  useEffect(() => {
    const checkAlarm = async () => {
      try {
        const r = await fetch(`${API_BASE}/alarms`)
        if (r.ok) {
          const d = await r.json()
          setSoundingAlarm(d.sounding || null)
        }
      } catch {
        /* ignore */
      }
    }
    checkAlarm()
    const iv = setInterval(checkAlarm, 2000)
    return () => clearInterval(iv)
  }, [])

  const dismissAlarm = async () => {
    try {
      await fetch(`${API_BASE}/alarms/dismiss`, { method: 'POST' })
      setSoundingAlarm(null)
    } catch {
      /* ignore */
    }
  }

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

  const sendFromInput = () => {
    const text = (inputRef.current?.value ?? input).trim()
    if (text) {
      onSend(text)
      setInput('')
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    sendFromInput()
  }

  const handleInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendFromInput()
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
        <div className="flex items-center gap-3">
          <img src="/gerty.png" alt="Gerty" className="h-9 w-9 object-contain" />
          <span className="text-sm font-medium text-[var(--text-primary)]">Local. Loyal. Always.</span>
        </div>
        {onNewChat && (
          <button
            type="button"
            onClick={onNewChat}
            className="p-2 rounded-lg text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]"
            title="New chat"
            aria-label="New chat"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
          </button>
        )}
      </header>

      {soundingAlarm && (
        <div className="px-6 py-3 bg-amber-500/20 border-b border-amber-500/40 flex items-center justify-between gap-4">
          <span className="text-sm text-amber-400">
            <strong>{soundingAlarm.time}</strong> alarm – Say &quot;cancel&quot; or &quot;stop&quot;, or use wake word
          </span>
          <button
            type="button"
            onClick={dismissAlarm}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-amber-500/40 text-amber-400 hover:bg-amber-500/60"
          >
            Stop alarm
          </button>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-6 space-y-4 select-text relative">
        {skillsViewOpen && (
          <div className="absolute inset-0 z-10 bg-[var(--bg-primary)] overflow-y-auto flex flex-col">
            <div className="sticky top-0 z-20 flex items-center justify-between px-4 py-3 bg-[var(--bg-primary)] border-b border-[var(--border)] shrink-0">
              <h2 className="text-sm font-medium text-[var(--text-primary)]">Skills &amp; Tools</h2>
              {onCloseSkills && (
                <button
                  type="button"
                  onClick={onCloseSkills}
                  className="p-2 rounded-lg text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]"
                  title="Close"
                  aria-label="Close skills"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
            </div>
            <div className="flex-1 p-6 overflow-y-auto">
            <div className="max-w-2xl mx-auto space-y-6">
              {Array.from(new Set(SKILLS.map((s) => s.category))).map((cat) => (
                <section key={cat}>
                  <h3 className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider mb-3">
                    {cat}
                  </h3>
                  <ul className="space-y-3">
                    {SKILLS
                      .filter((s) => s.category === cat)
                      .map((s, i) => (
                        <li
                          key={`${cat}-${s.name}-${i}`}
                          className="p-4 rounded-xl bg-[var(--bg-tertiary)] border border-[var(--border)]"
                        >
                          <h4 className="font-medium text-[var(--text-primary)]">{s.name}</h4>
                          <p className="text-sm text-[var(--text-secondary)] mt-1">{s.description}</p>
                          {s.examples.length > 0 && (
                            <p className="text-xs text-[var(--text-secondary)]/80 mt-2">
                              e.g. &quot;{s.examples[0]}&quot;
                              {s.examples.length > 1 && `, "${s.examples[1]}"`}
                            </p>
                          )}
                        </li>
                      ))}
                  </ul>
                </section>
              ))}
            </div>
            </div>
          </div>
        )}
        {alarmsTimersViewOpen && (
          <div className="absolute inset-0 z-10 bg-[var(--bg-primary)] overflow-y-auto flex flex-col">
            <div className="sticky top-0 z-20 flex items-center justify-between px-4 py-3 bg-[var(--bg-primary)] border-b border-[var(--border)] shrink-0">
              <h2 className="text-sm font-medium text-[var(--text-primary)]">Alarms &amp; Timers</h2>
              {onCloseAlarmsTimers && (
                <button type="button" onClick={onCloseAlarmsTimers} className="p-2 rounded-lg text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]" title="Close" aria-label="Close">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                </button>
              )}
            </div>
            <div className="flex-1 p-6 overflow-y-auto">
              <div className="max-w-2xl mx-auto space-y-6">
                <section>
                  <h3 className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider mb-3">Alarms</h3>
                  <form onSubmit={async (e) => { e.preventDefault(); const r = await fetch(`${API_BASE}/alarms`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ time: alarmTime, label: alarmLabel.trim() || undefined, recurring: alarmRecurring ? 'daily' : undefined }) }); const d = await r.json(); if (d.added) { setAlarmLabel(''); setAlarmRecurring(false); refreshAlarmsTimers(); } }} className="flex flex-wrap gap-2 mb-4">
                    <input type="time" value={alarmTime} onChange={(e) => setAlarmTime(e.target.value)} className="bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]" />
                    <input type="text" value={alarmLabel} onChange={(e) => setAlarmLabel(e.target.value)} placeholder="Label (optional)" className="flex-1 min-w-[120px] bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-xl px-4 py-2 text-sm placeholder:text-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]" />
                    <label className="flex items-center gap-2 px-3 py-2 rounded-xl bg-[var(--bg-tertiary)] border border-[var(--border)] cursor-pointer hover:bg-[var(--bg-secondary)]">
                      <input type="checkbox" checked={alarmRecurring} onChange={(e) => setAlarmRecurring(e.target.checked)} className="rounded" />
                      <span className="text-sm">Daily</span>
                    </label>
                    <button type="submit" className="px-4 py-2 bg-[var(--accent)] hover:bg-[var(--accent-hover)] rounded-xl text-sm font-medium">Add alarm</button>
                  </form>
                  {alarms.length === 0 ? (
                    <p className="text-sm text-[var(--text-secondary)]">No alarms set. Say &quot;set alarm for 7am&quot; to add one.</p>
                  ) : (
                    <ul className="space-y-2">
                      {alarms.map((a) => (
                        <li key={a.id ?? a.datetime ?? a.time} className={`flex justify-between items-center gap-2 p-3 rounded-xl ${a.sounding ? 'bg-amber-500/20 border border-amber-500/40' : 'bg-[var(--bg-tertiary)] border border-[var(--border)]'}`}>
                          <span className="flex items-center gap-2">
                            {a.time} {a.label && `– ${a.label}`} {a.sounding && '(sounding)'}
                            {a.recurring === 'daily' && <span className="px-1.5 py-0.5 text-xs font-medium rounded bg-[var(--accent)]/30 text-[var(--accent)]">Daily</span>}
                          </span>
                          <span className="flex items-center gap-1">
                            {(a.id ?? a.datetime) && !a.sounding && (
                              <button onClick={async () => { await fetch(`${API_BASE}/alarms/toggle-recurring`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: a.id ?? a.datetime }) }); refreshAlarmsTimers(); }} className="px-2 py-1 text-xs rounded hover:bg-[var(--bg-secondary)] text-[var(--text-secondary)]" title={a.recurring === 'daily' ? 'Switch to one-time' : 'Switch to daily'}>{a.recurring === 'daily' ? 'One-time' : 'Daily'}</button>
                            )}
                            {a.sounding ? (
                              <button onClick={async () => { await fetch(`${API_BASE}/alarms/dismiss`, { method: 'POST' }); refreshAlarmsTimers(); }} className="px-3 py-1 text-xs font-medium rounded bg-amber-500/40 text-amber-400 hover:bg-amber-500/60">Stop</button>
                            ) : (
                              (a.id ?? a.datetime) && (
                                <button onClick={async () => { await fetch(`${API_BASE}/alarms/cancel`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: a.id ?? a.datetime }) }); refreshAlarmsTimers(); }} className="p-1 rounded hover:bg-[var(--bg-secondary)] text-[var(--text-secondary)]" aria-label="Cancel alarm">
                                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                                </button>
                              )
                            )}
                          </span>
                        </li>
                      ))}
                      <li>
                        <button onClick={async () => { await fetch(`${API_BASE}/alarms/cancel`, { method: 'POST' }); refreshAlarmsTimers(); }} className="text-xs text-amber-400 hover:text-amber-300">Cancel all alarms</button>
                      </li>
                    </ul>
                  )}
                </section>
                <section>
                  <h3 className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider mb-3">Timers</h3>
                  <form onSubmit={async (e) => { e.preventDefault(); const duration_sec = timerMinutes * 60; const r = await fetch(`${API_BASE}/timers`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ duration_sec, label: timerLabel.trim() || undefined }) }); const d = await r.json(); if (d.added) { setTimerLabel(''); refreshAlarmsTimers(); } }} className="flex flex-wrap gap-2 mb-4">
                    <div className="flex gap-1">
                      {[1, 5, 10, 15, 30].map((m) => (
                        <button key={m} type="button" onClick={() => setTimerMinutes(m)} className={`px-3 py-2 rounded-xl text-sm font-medium ${timerMinutes === m ? 'bg-[var(--accent)]' : 'bg-[var(--bg-tertiary)] border border-[var(--border)] hover:bg-[var(--bg-secondary)]'}`}>{m}m</button>
                      ))}
                    </div>
                    <input type="number" min={1} max={120} value={timerMinutes} onChange={(e) => setTimerMinutes(Math.max(1, Math.min(120, parseInt(e.target.value, 10) || 1)))} className="w-16 bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-xl px-3 py-2 text-sm text-center focus:outline-none focus:ring-2 focus:ring-[var(--accent)]" />
                    <span className="self-center text-sm text-[var(--text-secondary)]">min</span>
                    <input type="text" value={timerLabel} onChange={(e) => setTimerLabel(e.target.value)} placeholder="Label (optional)" className="flex-1 min-w-[120px] bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-xl px-4 py-2 text-sm placeholder:text-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]" />
                    <button type="submit" className="px-4 py-2 bg-[var(--accent)] hover:bg-[var(--accent-hover)] rounded-xl text-sm font-medium">Start timer</button>
                  </form>
                  {timers.length === 0 ? (
                    <p className="text-sm text-[var(--text-secondary)]">No timers running. Say &quot;timer 5 minutes&quot; to start one.</p>
                  ) : (
                    <ul className="space-y-2">
                      {timers.map((t) => (
                        <li key={t.id ?? t.label} className="flex justify-between items-center gap-2 p-3 rounded-xl bg-[var(--bg-tertiary)] border border-[var(--border)]">
                          <span>{t.label}</span>
                          <span className="text-[var(--text-secondary)] text-sm">{formatRemaining(t.remaining_sec)}</span>
                          {t.id && (
                            <button onClick={async () => { await fetch(`${API_BASE}/timers/cancel`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: t.id }) }); refreshAlarmsTimers(); }} className="p-1 rounded hover:bg-[var(--bg-secondary)] text-[var(--text-secondary)]" aria-label="Cancel timer">
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                            </button>
                          )}
                        </li>
                      ))}
                      <li>
                        <button onClick={async () => { await fetch(`${API_BASE}/timers/cancel`, { method: 'POST' }); refreshAlarmsTimers(); }} className="text-xs text-amber-400 hover:text-amber-300">Cancel all timers</button>
                      </li>
                    </ul>
                  )}
                </section>
              </div>
            </div>
          </div>
        )}
        {notesViewOpen && (
          <div className="absolute inset-0 z-10 bg-[var(--bg-primary)] overflow-y-auto flex flex-col">
            <div className="sticky top-0 z-20 flex items-center justify-between px-4 py-3 bg-[var(--bg-primary)] border-b border-[var(--border)] shrink-0">
              <h2 className="text-sm font-medium text-[var(--text-primary)]">Notes</h2>
              {onCloseNotes && (
                <button type="button" onClick={onCloseNotes} className="p-2 rounded-lg text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]" title="Close" aria-label="Close">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                </button>
              )}
            </div>
            <div className="flex-1 p-6 overflow-y-auto">
              <div className="max-w-2xl mx-auto space-y-4">
                <form onSubmit={(e) => { e.preventDefault(); const t = noteInput.trim(); if (t) { fetch(`${API_BASE}/notes`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: t }) }).then(() => { setNoteInput(''); refreshNotes(); }); } }} className="flex gap-2">
                  <input type="text" value={noteInput} onChange={(e) => setNoteInput(e.target.value)} placeholder="Add a note…" className="flex-1 bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-xl px-4 py-2 text-sm placeholder:text-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]" />
                  <button type="submit" className="px-4 py-2 bg-[var(--accent)] hover:bg-[var(--accent-hover)] rounded-xl text-sm font-medium">Add</button>
                </form>
                {notes.length === 0 ? (
                  <p className="text-sm text-[var(--text-secondary)]">No notes yet. Add one above or say &quot;note: buy milk&quot; in chat.</p>
                ) : (
                  <ul className="space-y-2">
                    {notes.map((n, i) => (
                      <li key={i} className="flex items-center gap-2 p-3 rounded-xl bg-[var(--bg-tertiary)] border border-[var(--border)]">
                        <span className="flex-1">• {n}</span>
                        <button
                          type="button"
                          onClick={async () => {
                            const api = (window as unknown as { pywebview?: { api?: { deleteNote?: (idx: number) => boolean } } }).pywebview?.api
                            if (api?.deleteNote) {
                              api.deleteNote(i)
                              refreshNotes()
                            } else {
                              await fetch(`${API_BASE}/notes/${i}`, { method: 'DELETE' })
                              refreshNotes()
                            }
                          }}
                          className="p-1 rounded text-[var(--text-secondary)] hover:text-red-400 hover:bg-red-500/20 shrink-0"
                          title="Delete note"
                          aria-label="Delete note"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
                {notes.length > 0 && (
                  <button onClick={async () => { await fetch(`${API_BASE}/notes`, { method: 'DELETE' }); refreshNotes(); }} className="text-xs text-amber-400 hover:text-amber-300">Clear all notes</button>
                )}
              </div>
            </div>
          </div>
        )}
        {!skillsViewOpen && !alarmsTimersViewOpen && !notesViewOpen && messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-[var(--text-secondary)]">
            <p className="text-lg mb-2">
              {hasVoiceAPI()
                ? "Click the mic to speak—I'll detect when you stop, or click again to stop early. Or type below."
                : 'Type a message below.'}
            </p>
            <p className="text-sm">I can tell you the time, set alarms and timers, and answer questions.</p>
          </div>
        )}
        {!skillsViewOpen && !alarmsTimersViewOpen && !notesViewOpen && messages.map((m) => (
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
            ref={inputRef}
            type="text"
            name="chat-message"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleInputKeyDown}
            autoComplete="off"
            placeholder='Type a message, Say "Our Gurt" or click mic to chat'
            className="flex-1 bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-xl px-4 py-3 text-sm placeholder:text-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
          />
          {hasVoiceAPI() && (
            <>
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
              {voiceStatus === 'processing' && onVoiceStatusChange && (
                <button
                  type="button"
                  onClick={async () => {
                    await cancelVoiceProcessing()
                    onVoiceStatusChange('idle')
                  }}
                  className="px-3 py-2 text-xs rounded-xl bg-amber-500/20 text-amber-400 hover:bg-amber-500/30"
                >
                  Cancel
                </button>
              )}
            </>
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
