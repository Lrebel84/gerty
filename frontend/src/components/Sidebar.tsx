interface SidebarProps {
  open: boolean
  onToggle: () => void
  voiceStatus?: 'idle' | 'listening' | 'processing'
}

export function Sidebar({ open, onToggle }: SidebarProps) {
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
      <nav className="p-2">
        <div className="text-xs text-[var(--text-secondary)] px-3 py-2">Coming soon</div>
        <div className="px-3 py-2 text-sm text-[var(--text-secondary)]">
          Alarms, timers, and more tools will appear here.
        </div>
      </nav>
    </aside>
  )
}
