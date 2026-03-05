import { useState, useEffect } from 'react'

const API_BASE = '/api'

interface Alarm {
  time: string
  label?: string
  datetime?: string
}

interface Timer {
  label: string
  remaining_sec: number
  duration_sec: number
}

interface SidebarProps {
  open: boolean
  onToggle: () => void
  voiceStatus?: 'idle' | 'listening' | 'processing'
}

function formatRemaining(sec: number): string {
  const m = Math.floor(sec / 60)
  const s = sec % 60
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

export function Sidebar({ open, onToggle }: SidebarProps) {
  const [alarms, setAlarms] = useState<Alarm[]>([])
  const [timers, setTimers] = useState<Timer[]>([])

  useEffect(() => {
    const fetchTools = async () => {
      try {
        const [alarmsRes, timersRes] = await Promise.all([
          fetch(`${API_BASE}/alarms`),
          fetch(`${API_BASE}/timers`),
        ])
        if (alarmsRes.ok) {
          const data = await alarmsRes.json()
          setAlarms(data.alarms || [])
        }
        if (timersRes.ok) {
          const data = await timersRes.json()
          setTimers(data.timers || [])
        }
      } catch {
        // Ignore fetch errors
      }
    }

    fetchTools()
    const interval = setInterval(fetchTools, 2000)
    return () => clearInterval(interval)
  }, [])

  const cancelAlarms = async () => {
    try {
      await fetch(`${API_BASE}/alarms/cancel`, { method: 'POST' })
      setAlarms([])
    } catch {
      // Ignore
    }
  }

  const cancelTimers = async () => {
    try {
      await fetch(`${API_BASE}/timers/cancel`, { method: 'POST' })
      setTimers([])
    } catch {
      // Ignore
    }
  }

  return (
    <aside
      className={`fixed left-0 top-0 h-full w-64 bg-[var(--bg-secondary)] border-r border-[var(--border)] z-10 transition-transform ${
        open ? 'translate-x-0' : '-translate-x-full'
      }`}
    >
      <div className="p-4 flex items-center justify-between">
        <h2 className="text-sm font-medium text-[var(--text-secondary)] uppercase tracking-wider">
          Tools
        </h2>
        <button
          onClick={onToggle}
          className="p-1.5 rounded-lg hover:bg-[var(--bg-tertiary)] text-[var(--text-secondary)]"
          aria-label="Toggle sidebar"
        >
          <svg
            className={`w-5 h-5 transition-transform ${open ? '' : 'rotate-180'}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
          </svg>
        </button>
      </div>
      <nav className="p-2 space-y-4">
        <section>
          <h3 className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider px-3 py-2">
            Alarms
          </h3>
          {alarms.length === 0 ? (
            <p className="px-3 py-2 text-sm text-[var(--text-secondary)]">No alarms set</p>
          ) : (
            <ul className="space-y-1">
              {alarms.map((a, i) => (
                <li key={i} className="px-3 py-2 text-sm flex justify-between items-center bg-[var(--bg-tertiary)] rounded-lg">
                  <span>{a.time} {a.label && `- ${a.label}`}</span>
                </li>
              ))}
              <li>
                <button
                  onClick={cancelAlarms}
                  className="text-xs text-amber-400 hover:text-amber-300 px-3 py-1"
                >
                  Cancel all
                </button>
              </li>
            </ul>
          )}
        </section>
        <section>
          <h3 className="text-xs font-medium text-[var(--text-secondary)] uppercase tracking-wider px-3 py-2">
            Timers
          </h3>
          {timers.length === 0 ? (
            <p className="px-3 py-2 text-sm text-[var(--text-secondary)]">No timers running</p>
          ) : (
            <ul className="space-y-1">
              {timers.map((t, i) => (
                <li key={i} className="px-3 py-2 text-sm flex justify-between items-center bg-[var(--bg-tertiary)] rounded-lg">
                  <span>{t.label}</span>
                  <span className="text-[var(--text-secondary)]">{formatRemaining(t.remaining_sec)}</span>
                </li>
              ))}
              <li>
                <button
                  onClick={cancelTimers}
                  className="text-xs text-amber-400 hover:text-amber-300 px-3 py-1"
                >
                  Cancel all
                </button>
              </li>
            </ul>
          )}
        </section>
      </nav>
    </aside>
  )
}
