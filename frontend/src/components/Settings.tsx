import { useState, useEffect } from 'react'

const API_BASE = '/api'

interface SettingsProps {
  open: boolean
  onClose: () => void
  onSave?: () => void
}

interface SettingsData {
  local_model: string
  openrouter_model: string
  custom_prompt: string
  provider: string
  rag_chat_model: string
  rag_embed_model: string
}

interface RAGStatus {
  indexed: boolean
  file_count: number
  last_indexed: string | null
  knowledge_path?: string
}

const RAG_CHAT_MODELS = ['command-r7b', 'granite3.2:8b', 'command-r:35b']
const RAG_EMBED_MODELS = ['nomic-embed-text', 'mxbai-embed-large', 'bge-m3']

export function Settings({ open, onClose, onSave }: SettingsProps) {
  const [localModel, setLocalModel] = useState('')
  const [openrouterModel, setOpenrouterModel] = useState('')
  const [customPrompt, setCustomPrompt] = useState('')
  const [ollamaModels, setOllamaModels] = useState<string[]>([])
  const [openrouterModels, setOpenrouterModels] = useState<string[]>([])
  const [ragChatModel, setRagChatModel] = useState('command-r7b')
  const [ragEmbedModel, setRagEmbedModel] = useState('nomic-embed-text')
  const [ragStatus, setRagStatus] = useState<RAGStatus | null>(null)
  const [ragIndexing, setRagIndexing] = useState(false)
  const [ragIndexMessage, setRagIndexMessage] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (open) {
      fetch(`${API_BASE}/settings`)
        .then((r) => r.json())
        .then((d: SettingsData) => {
          setLocalModel(d.local_model || '')
          setOpenrouterModel(d.openrouter_model || '')
          setCustomPrompt(d.custom_prompt || '')
          setRagChatModel(d.rag_chat_model || 'command-r7b')
          setRagEmbedModel(d.rag_embed_model || 'nomic-embed-text')
        })
        .catch(() => {})
      fetch(`${API_BASE}/ollama/models`)
        .then((r) => r.json())
        .then((d) => setOllamaModels(d.models || []))
        .catch(() => setOllamaModels([]))
      fetch(`${API_BASE}/openrouter/models`)
        .then((r) => r.json())
        .then((d) => setOpenrouterModels(d.models || []))
        .catch(() => setOpenrouterModels([]))
      fetch(`${API_BASE}/rag/status`)
        .then((r) => r.json())
        .then((d) => setRagStatus(d))
        .catch(() => setRagStatus(null))
    }
  }, [open])

  const handleRagIndex = async () => {
    setRagIndexing(true)
    setRagIndexMessage(null)
    try {
      const res = await fetch(`${API_BASE}/rag/index`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ embed_model: ragEmbedModel }),
      })
      const data = await res.json()
      if (data.indexed) {
        const count = data.file_count ?? 0
        const chunks = data.chunks_added ?? 0
        setRagStatus({
          indexed: true,
          file_count: count,
          last_indexed: data.last_indexed ?? null,
        })
        let msg = count > 0 ? `Indexed ${count} file${count === 1 ? '' : 's'} (${chunks} chunks)` : 'No files to index'
        if (data.parse_errors?.length) {
          msg += `. ${data.parse_errors.length} file(s) failed to parse`
        }
        setRagIndexMessage(msg)
      } else {
        setRagIndexMessage(data.error ?? 'Indexing failed')
      }
      setTimeout(() => setRagIndexMessage(null), 4000)
    } catch {
      setRagIndexMessage('Indexing failed')
      setTimeout(() => setRagIndexMessage(null), 4000)
    } finally {
      setRagIndexing(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    setSaved(false)
    try {
      await fetch(`${API_BASE}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          local_model: localModel,
          openrouter_model: openrouterModel,
          custom_prompt: customPrompt,
          rag_chat_model: ragChatModel,
          rag_embed_model: ragEmbedModel,
        }),
      })
      setSaved(true)
      onSave?.()
      setTimeout(() => setSaved(false), 2000)
    } catch {
      // ignore
    } finally {
      setSaving(false)
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-20 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-2xl bg-[var(--bg-secondary)] border border-[var(--border)] shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold">Settings</h2>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-[var(--bg-tertiary)] text-[var(--text-secondary)]"
              aria-label="Close"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <section className="space-y-4 mb-6">
            <h3 className="text-sm font-medium text-[var(--text-secondary)] uppercase tracking-wider">
              Local model (Ollama)
            </h3>
            <select
              value={localModel}
              onChange={(e) => setLocalModel(e.target.value)}
              className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
            >
              <option value="">Select model</option>
              {ollamaModels.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
            {ollamaModels.length === 0 && (
              <p className="text-xs text-[var(--text-secondary)]">Start Ollama and pull a model: ollama pull qwen2.5:7b</p>
            )}
          </section>

          <section className="space-y-4 mb-6">
            <h3 className="text-sm font-medium text-[var(--text-secondary)] uppercase tracking-wider">
              OpenRouter model
            </h3>
            <select
              value={openrouterModel}
              onChange={(e) => setOpenrouterModel(e.target.value)}
              className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
            >
              <option value="">Select model</option>
              {openrouterModels.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
            {openrouterModels.length === 0 && (
              <p className="text-xs text-[var(--text-secondary)]">Add OPENROUTER_API_KEY to .env to load models</p>
            )}
          </section>

          <section className="space-y-4 mb-6">
            <h3 className="text-sm font-medium text-[var(--text-secondary)] uppercase tracking-wider">
              Knowledge base (RAG)
            </h3>
            <p className="text-xs text-[var(--text-secondary)]">
              Ollama must be running with the embedding model pulled (e.g. <code className="bg-[var(--bg-tertiary)] px-1 rounded">ollama pull nomic-embed-text</code>). Drop PDF, Excel, Word, or text files into the folder below, then click Index.
            </p>
            {ragStatus?.knowledge_path && (
              <p className="text-xs text-[var(--text-secondary)] font-mono truncate" title={ragStatus.knowledge_path}>
                {ragStatus.knowledge_path}
              </p>
            )}
            <p className="text-xs text-[var(--text-secondary)]">
              To test from terminal: <code className="bg-[var(--bg-tertiary)] px-1 rounded">python3 -m gerty.rag</code>
            </p>
            <div className="flex flex-col gap-2">
              <div className="flex items-center gap-3 flex-wrap">
                <span className="text-sm text-[var(--text-secondary)]">
                  {ragStatus?.indexed
                    ? `${ragStatus.file_count} file${ragStatus.file_count === 1 ? '' : 's'} indexed`
                    : 'Not indexed'}
                </span>
                <button
                  onClick={handleRagIndex}
                  disabled={ragIndexing}
                  className="px-3 py-1.5 bg-[var(--accent)] hover:bg-[var(--accent-hover)] disabled:opacity-50 rounded-lg text-xs font-medium"
                >
                  {ragIndexing ? 'Indexing...' : 'Index now'}
                </button>
              </div>
              {ragIndexMessage && (
                <p className={`text-xs ${ragIndexMessage.startsWith('Indexed') ? 'text-green-500' : 'text-amber-500'}`}>
                  {ragIndexMessage}
                </p>
              )}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-[var(--text-secondary)] block mb-1">RAG chat model</label>
                <select
                  value={ragChatModel}
                  onChange={(e) => setRagChatModel(e.target.value)}
                  className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm"
                >
                  <option value="__use_chat__">Use chat model</option>
                  {RAG_CHAT_MODELS.filter((m) => m !== '__use_chat__').map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-[var(--text-secondary)] block mb-1">Embedding model</label>
                <select
                  value={ragEmbedModel}
                  onChange={(e) => setRagEmbedModel(e.target.value)}
                  className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm"
                >
                  {RAG_EMBED_MODELS.map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>
            </div>
          </section>

          <section className="space-y-4 mb-6">
            <h3 className="text-sm font-medium text-[var(--text-secondary)] uppercase tracking-wider">
              Custom system prompt
            </h3>
            <textarea
              value={customPrompt}
              onChange={(e) => setCustomPrompt(e.target.value)}
              placeholder="Instructions for the model (e.g. format, tone). Leave empty for default."
              rows={4}
              className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-xl px-4 py-3 text-sm placeholder:text-[var(--text-secondary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)] resize-none"
            />
          </section>

          <div className="flex gap-3">
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2.5 bg-[var(--accent)] hover:bg-[var(--accent-hover)] disabled:opacity-50 rounded-xl text-sm font-medium"
            >
              {saving ? 'Saving...' : saved ? 'Saved' : 'Save'}
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2.5 bg-[var(--bg-tertiary)] hover:bg-[var(--border)] rounded-xl text-sm"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
