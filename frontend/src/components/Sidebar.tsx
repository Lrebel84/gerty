import { useState, useEffect, useRef, useCallback } from 'react'
import { Settings } from './Settings'

interface SidebarProps {
  open: boolean
  width: number
  onResize: (width: number) => void
  onToggle: () => void
  onSkillsClick?: () => void
  onAlarmsTimersClick?: () => void
  onNotesClick?: () => void
  voiceStatus?: 'idle' | 'listening' | 'processing'
  onSettingsSave?: () => void
  provider?: 'local' | 'openrouter'
  onProviderChange?: (provider: 'local' | 'openrouter') => void
}

export function Sidebar({ open, width, onResize, onToggle, onSkillsClick, onAlarmsTimersClick, onNotesClick, onSettingsSave, provider, onProviderChange }: SidebarProps) {
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [resizing, setResizing] = useState(false)
  const startXRef = useRef(0)
  const startWidthRef = useRef(0)

  const handleResizeStart = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault()
      setResizing(true)
      startXRef.current = e.clientX
      startWidthRef.current = width
    },
    [width]
  )

  useEffect(() => {
    if (!resizing) return
    const onMove = (e: MouseEvent) => {
      const delta = e.clientX - startXRef.current
      onResize(startWidthRef.current + delta)
    }
    const onEnd = () => setResizing(false)
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onEnd)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onEnd)
    }
  }, [resizing, onResize])

  return (
    <aside
      className={`fixed left-0 top-0 h-full bg-[var(--bg-secondary)] border-r border-[var(--border)] z-10 transition-transform overflow-hidden flex flex-col ${
        open ? 'translate-x-0' : '-translate-x-full'
      }`}
      style={{ width: open ? width : 0 }}
    >
      <div className="p-4 flex items-center justify-between shrink-0">
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
      <nav className="p-2 space-y-4 overflow-y-auto overflow-x-hidden min-w-0 flex-1">
        {onSkillsClick && (
          <section>
            <button
              onClick={onSkillsClick}
              className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg hover:bg-[var(--bg-tertiary)] text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              Skills
            </button>
          </section>
        )}
        {onAlarmsTimersClick && (
          <section>
            <button
              onClick={onAlarmsTimersClick}
              className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg hover:bg-[var(--bg-tertiary)] text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Alarms &amp; Timers
            </button>
          </section>
        )}
        {onNotesClick && (
          <section>
            <button
              onClick={onNotesClick}
              className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg hover:bg-[var(--bg-tertiary)] text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              Notes
            </button>
          </section>
        )}
        <section>
          <button
            onClick={() => setSettingsOpen(true)}
            className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg hover:bg-[var(--bg-tertiary)] text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Settings
          </button>
        </section>
      </nav>
      {open && (
        <div
          onMouseDown={handleResizeStart}
          className={`absolute right-0 top-0 w-3 h-full cursor-col-resize hover:bg-[var(--accent)]/30 transition-colors ${
            resizing ? 'bg-[var(--accent)]/50' : ''
          }`}
          aria-label="Resize sidebar"
        />
      )}
      <Settings open={settingsOpen} onClose={() => setSettingsOpen(false)} onSave={onSettingsSave} provider={provider} onProviderChange={onProviderChange} />
    </aside>
  )
}
