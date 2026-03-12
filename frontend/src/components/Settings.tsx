import { useState, useEffect } from 'react'

const API_BASE = '/api'

interface SettingsProps {
  open: boolean
  onClose: () => void
  onSave?: () => void
  provider?: 'local' | 'openrouter'
  onProviderChange?: (provider: 'local' | 'openrouter') => void
}

interface SettingsData {
  local_model: string
  openrouter_model: string
  custom_prompt: string
  provider: string
  rag_enabled: boolean
  rag_chat_model: string
  rag_embed_model: string
  memory_enabled: boolean
  piper_voice: string
  tts_backend: string
  kokoro_voice: string
  stt_backend: string
  faster_whisper_model: string
  moonshine_model: string
}

interface RAGStatus {
  indexed: boolean
  file_count: number
  last_indexed: string | null
  knowledge_path?: string
  memory_count?: number
}

const RAG_CHAT_MODELS = ['llama3.1:8b', 'command-r7b', 'granite3.2:8b', 'command-r:35b']
const RAG_EMBED_MODELS = ['nomic-embed-text', 'mxbai-embed-large', 'bge-m3']

const STT_BACKENDS = [
  { value: 'auto', label: 'Auto (Groq when WiFi, else local)' },
  { value: 'moonshine', label: 'Moonshine (local, ~5x faster on short commands)' },
  { value: 'faster_whisper', label: 'faster-whisper (local)' },
  { value: 'vosk', label: 'Vosk (local, legacy)' },
  { value: 'groq', label: 'Groq (cloud, 216x real-time)' },
] as const

const MOONSHINE_MODELS = [
  { value: 'tiny', label: 'tiny', desc: '27M params, fastest' },
  { value: 'base', label: 'base', desc: '61M params, best accuracy' },
] as const

const FASTER_WHISPER_MODELS = [
  { value: 'tiny', label: 'tiny', desc: 'Fastest, ~39M params' },
  { value: 'base', label: 'base', desc: 'Good balance, ~74M params' },
  { value: 'small', label: 'small', desc: 'Better accuracy, ~244M params' },
  { value: 'medium', label: 'medium', desc: 'High accuracy, ~769M params' },
  { value: 'large-v3', label: 'large-v3', desc: 'Best accuracy, ~1.5B params' },
] as const

const KOKORO_VOICES_FALLBACK = [
  'af_sarah', 'af_bella', 'af_nicole', 'af_nova', 'af_heart', 'af_alloy',
  'af_aoede', 'af_jessica', 'af_kore', 'af_river', 'af_sky',
  'am_adam', 'am_echo', 'am_eric', 'am_fenrir', 'am_liam', 'am_michael',
  'am_onyx', 'am_puck', 'am_santa',
]

export function Settings({ open, onClose, onSave, provider = 'local', onProviderChange }: SettingsProps) {
  const [localModel, setLocalModel] = useState('')
  const [openrouterModel, setOpenrouterModel] = useState('')
  const [customPrompt, setCustomPrompt] = useState('')
  const [ollamaModels, setOllamaModels] = useState<string[]>([])
  const [openrouterModels, setOpenrouterModels] = useState<string[]>([])
  const [ragEnabled, setRagEnabled] = useState(true)
  const [ragChatModel, setRagChatModel] = useState('__use_chat__')
  const [ragEmbedModel, setRagEmbedModel] = useState('nomic-embed-text')
  const [ragStatus, setRagStatus] = useState<RAGStatus | null>(null)
  const [ragIndexing, setRagIndexing] = useState(false)
  const [ragIndexMessage, setRagIndexMessage] = useState<string | null>(null)
  const [memoryEnabled, setMemoryEnabled] = useState(true)
  const [piperVoice, setPiperVoice] = useState('')
  const [piperVoices, setPiperVoices] = useState<string[]>([])
  const [ttsBackend, setTtsBackend] = useState('piper')
  const [kokoroVoice, setKokoroVoice] = useState('af_sarah')
  const [kokoroVoices, setKokoroVoices] = useState<string[]>([])
  const [sttBackend, setSttBackend] = useState('faster_whisper')
  const [fasterWhisperModel, setFasterWhisperModel] = useState('base')
  const [moonshineModel, setMoonshineModel] = useState('base')
  const [playingSample, setPlayingSample] = useState(false)
  const [sampleError, setSampleError] = useState<string | null>(null)
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
          setRagEnabled(d.rag_enabled === true)
          setRagChatModel(d.rag_chat_model || '__use_chat__')
          setRagEmbedModel(d.rag_embed_model || 'nomic-embed-text')
          setMemoryEnabled(d.memory_enabled !== false)
          setPiperVoice(d.piper_voice || '')
          setTtsBackend(d.tts_backend || 'piper')
          setKokoroVoice(d.kokoro_voice || 'af_sarah')
          setSttBackend(d.stt_backend || 'faster_whisper')
          setFasterWhisperModel(d.faster_whisper_model || 'base')
          setMoonshineModel(d.moonshine_model || 'base')
        })
        .catch(() => {})
      fetch(`${API_BASE}/voice/list`)
        .then((r) => r.json())
        .then((d) => {
          setPiperVoices(d.piper_voices || [])
          setKokoroVoices(d.kokoro_voices || [])
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

  const handlePlaySample = async () => {
    const voice = ttsBackend === 'kokoro' ? kokoroVoice : piperVoice
    if (!voice || playingSample) return
    setPlayingSample(true)
    setSampleError(null)
    try {
      const res = await fetch(`${API_BASE}/voice/sample`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ voice, tts_backend: ttsBackend }),
      })
      if (!res.ok) {
        const errText = await res.text()
        let msg = 'Sample failed'
        try {
          const errJson = JSON.parse(errText)
          if (errJson.error) msg = errJson.error
        } catch {
          if (errText) msg = errText.slice(0, 100)
        }
        throw new Error(msg)
      }
      const blob = await res.blob()
      if (blob.size === 0) throw new Error('Empty audio received')
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      await audio.play()
      audio.onended = () => URL.revokeObjectURL(url)
    } catch (e) {
      setSampleError(e instanceof Error ? e.message : 'Playback failed')
      setTimeout(() => setSampleError(null), 5000)
    } finally {
      setPlayingSample(false)
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
          rag_enabled: ragEnabled,
          rag_chat_model: ragChatModel,
          rag_embed_model: ragEmbedModel,
          memory_enabled: memoryEnabled,
          piper_voice: piperVoice,
          tts_backend: ttsBackend,
          kokoro_voice: kokoroVoice,
          stt_backend: sttBackend,
          faster_whisper_model: fasterWhisperModel,
          moonshine_model: moonshineModel,
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

          {onProviderChange && (
            <section className="space-y-4 mb-6">
              <h3 className="text-sm font-medium text-[var(--text-secondary)] uppercase tracking-wider">
                Provider
              </h3>
              <div className="flex rounded-lg bg-[var(--bg-tertiary)] p-0.5">
                <button
                  type="button"
                  onClick={() => onProviderChange('local')}
                  className={`flex-1 px-4 py-2.5 rounded-md text-sm font-medium transition-colors ${
                    provider === 'local' ? 'bg-[var(--accent)] text-white' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                  }`}
                >
                  Local
                </button>
                <button
                  type="button"
                  onClick={() => onProviderChange('openrouter')}
                  className={`flex-1 px-4 py-2.5 rounded-md text-sm font-medium transition-colors ${
                    provider === 'openrouter' ? 'bg-[var(--accent)] text-white' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                  }`}
                >
                  OpenRouter
                </button>
              </div>
            </section>
          )}

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
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="rag-enabled"
                checked={ragEnabled}
                onChange={(e) => setRagEnabled(e.target.checked)}
                className="rounded border-[var(--border)] bg-[var(--bg-tertiary)]"
              />
              <label htmlFor="rag-enabled" className="text-sm text-[var(--text-secondary)]">
                Enable RAG tool (required to search docs; say &quot;check my docs for X&quot; or &quot;search my files for Y&quot;)
              </label>
            </div>
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
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="memory-enabled"
                checked={memoryEnabled}
                onChange={(e) => setMemoryEnabled(e.target.checked)}
                className="rounded border-[var(--border)] bg-[var(--bg-tertiary)]"
              />
              <label htmlFor="memory-enabled" className="text-sm text-[var(--text-secondary)]">
                Long-term memory (extract facts from chat when summarising)
              </label>
            </div>
            {ragStatus?.memory_count != null && ragStatus.memory_count > 0 && (
              <p className="text-xs text-[var(--text-secondary)]">
                {ragStatus.memory_count} fact{ragStatus.memory_count === 1 ? '' : 's'} in memory
              </p>
            )}
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
                <label className="text-xs text-[var(--text-secondary)] block mb-1" title="When RAG context (docs/memory) is retrieved, which model to use. 'Use chat model' keeps your normal Qwen for personality and formatting.">
                  Model when RAG context is used
                </label>
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
              Voice – Speech recognition (STT)
            </h3>
            <p className="text-xs text-[var(--text-secondary)]">
              Choose how your speech is transcribed. faster-whisper (tiny/base) is fastest for voice. Restart the app after changing.
            </p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-[var(--text-secondary)] block mb-1">STT backend</label>
                <select
                  value={sttBackend}
                  onChange={(e) => setSttBackend(e.target.value)}
                  className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm"
                >
                  {STT_BACKENDS.map((b) => (
                    <option key={b.value} value={b.value}>{b.label}</option>
                  ))}
                </select>
              </div>
              {(sttBackend === 'faster_whisper' || sttBackend === 'auto') && (
                <div>
                  <label className="text-xs text-[var(--text-secondary)] block mb-1">faster-whisper model</label>
                  <select
                    value={fasterWhisperModel}
                    onChange={(e) => setFasterWhisperModel(e.target.value)}
                    className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm"
                  >
                    {FASTER_WHISPER_MODELS.map((m) => (
                      <option key={m.value} value={m.value} title={m.desc}>
                        {m.label}
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-[var(--text-secondary)] mt-1">
                    Ryzen 9: base or small recommended. Models download on first use.
                  </p>
                </div>
              )}
              {sttBackend === 'moonshine' && (
                <div>
                  <label className="text-xs text-[var(--text-secondary)] block mb-1">Moonshine model</label>
                  <select
                    value={moonshineModel}
                    onChange={(e) => setMoonshineModel(e.target.value)}
                    className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm"
                  >
                    {MOONSHINE_MODELS.map((m) => (
                      <option key={m.value} value={m.value} title={m.desc}>
                        {m.label}
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-[var(--text-secondary)] mt-1">
                    Variable-length processing, ~5x faster than Whisper on short commands. Requires: pip install &quot;transformers[torch]&quot;
                  </p>
                </div>
              )}
            </div>
          </section>

          <section className="space-y-4 mb-6">
            <h3 className="text-sm font-medium text-[var(--text-secondary)] uppercase tracking-wider">
              Voice – Text-to-speech (TTS)
            </h3>
            <p className="text-xs text-[var(--text-secondary)]">
              Piper: fast, local. Kokoro: ElevenLabs-like quality (~80MB). Restart app after changing.
            </p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-[var(--text-secondary)] block mb-1">TTS backend</label>
                <select
                  value={ttsBackend}
                  onChange={(e) => setTtsBackend(e.target.value)}
                  className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm"
                >
                  <option value="piper">Piper (fast)</option>
                  <option value="kokoro">Kokoro (ElevenLabs-like)</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-[var(--text-secondary)] block mb-1">
                  {ttsBackend === 'kokoro' ? 'Kokoro voice' : 'Piper voice'}
                </label>
                <select
                  value={ttsBackend === 'kokoro' ? kokoroVoice : piperVoice}
                  onChange={(e) => {
                    const v = e.target.value
                    if (ttsBackend === 'kokoro') setKokoroVoice(v)
                    else setPiperVoice(v)
                  }}
                  className="w-full bg-[var(--bg-tertiary)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm"
                >
                  <option value="">Select voice</option>
                  {(ttsBackend === 'kokoro'
                    ? (kokoroVoices.length > 0 ? kokoroVoices : KOKORO_VOICES_FALLBACK)
                    : (piperVoices.length > 0 ? piperVoices : ['en_US-amy-medium'])
                  ).map((v) => (
                    <option key={v} value={v}>{v}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handlePlaySample}
                disabled={!(ttsBackend === 'kokoro' ? kokoroVoice : piperVoice) || playingSample}
                className="px-4 py-3 bg-[var(--bg-tertiary)] hover:bg-[var(--border)] disabled:opacity-50 rounded-xl text-sm font-medium flex items-center gap-2"
                title="Play sample"
              >
                {playingSample ? (
                  <span className="animate-pulse">Playing…</span>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M8 5v14l11-7z" />
                    </svg>
                    Sample
                  </>
                )}
              </button>
            </div>
            {ttsBackend === 'piper' && piperVoices.length === 0 && (
              <p className="text-xs text-[var(--text-secondary)]">Run <code className="bg-[var(--bg-tertiary)] px-1 rounded">./scripts/download_models.sh</code> to install Piper voices.</p>
            )}
            {ttsBackend === 'kokoro' && (
              <p className="text-xs text-[var(--text-secondary)]">Kokoro models download via script. Set TTS_BACKEND=kokoro in .env or choose in Settings.</p>
            )}
            {sampleError && (
              <p className="text-xs text-amber-500">{sampleError}</p>
            )}
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
