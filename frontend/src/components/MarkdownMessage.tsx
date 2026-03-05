import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import type { Components } from 'react-markdown'

interface MarkdownMessageProps {
  content: string
  className?: string
}

function CodeBlock({ className, children }: { className?: string; children?: string }) {
  const match = /language-(\w+)/.exec(className || '')
  const [copied, setCopied] = useState(false)
  const text = String(children ?? '').replace(/\n$/, '')

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  if (match) {
    return (
      <div className="group relative my-3 rounded-xl overflow-hidden border border-[var(--border)]">
        <button
          type="button"
          onClick={handleCopy}
          className="absolute right-2 top-2 px-2 py-1.5 rounded-lg bg-[var(--bg-tertiary)]/90 text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-secondary)] text-xs font-medium transition-opacity opacity-0 group-hover:opacity-100 focus:opacity-100"
        >
          {copied ? '✓ Copied' : 'Copy'}
        </button>
        <SyntaxHighlighter
          language={match[1]}
          PreTag="div"
          style={oneDark}
          customStyle={{
            margin: 0,
            padding: '1rem 1.25rem',
            fontSize: '0.8125rem',
            lineHeight: 1.6,
            background: 'var(--bg-primary)',
          }}
          codeTagProps={{ style: { fontFamily: 'ui-monospace, monospace' } }}
          showLineNumbers={false}
        >
          {text}
        </SyntaxHighlighter>
      </div>
    )
  }

  return (
    <pre className="my-2 px-3 py-2 rounded-lg bg-[var(--bg-primary)] border border-[var(--border)] overflow-x-auto text-sm font-mono">
      <code>{text}</code>
    </pre>
  )
}

const components: Components = {
  h1: ({ children }) => (
    <h1 className="text-lg font-bold mt-4 mb-2 first:mt-0 text-[var(--text-primary)]">{children}</h1>
  ),
  h2: ({ children }) => (
    <h2 className="text-base font-semibold mt-4 mb-2 first:mt-0 text-[var(--text-primary)]">{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-sm font-semibold mt-3 mb-1.5 first:mt-0 text-[var(--text-primary)]">{children}</h3>
  ),
  p: ({ children }) => <p className="my-2 first:mt-0 last:mb-0 leading-relaxed">{children}</p>,
  ul: ({ children }) => <ul className="my-2 pl-5 list-disc space-y-1">{children}</ul>,
  ol: ({ children }) => <ol className="my-2 pl-5 list-decimal space-y-1">{children}</ol>,
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  blockquote: ({ children }) => (
    <blockquote className="my-2 pl-4 border-l-2 border-[var(--accent)] text-[var(--text-secondary)]">
      {children}
    </blockquote>
  ),
  pre: ({ children }) => <>{children}</>,
  code: ({ className, children, ...props }) => {
    if (className?.startsWith('language-')) {
      return <CodeBlock className={className}>{String(children ?? '').replace(/\n$/, '')}</CodeBlock>
    }
    return (
      <code
        className="px-1.5 py-0.5 rounded bg-[var(--bg-primary)] border border-[var(--border)] text-[0.8125rem] font-mono"
        {...props}
      >
        {children}
      </code>
    )
  },
  strong: ({ children }) => <strong className="font-semibold text-[var(--text-primary)]">{children}</strong>,
  table: ({ children }) => (
    <div className="my-3 overflow-x-auto rounded-lg border border-[var(--border)]">
      <table className="min-w-full text-sm">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-[var(--bg-primary)]">{children}</thead>,
  th: ({ children }) => (
    <th className="px-4 py-2 text-left font-semibold text-[var(--text-primary)] border-b border-[var(--border)]">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="px-4 py-2 border-b border-[var(--border)]">{children}</td>
  ),
  tr: ({ children }) => <tr className="last:border-b-0">{children}</tr>,
  hr: () => <hr className="my-4 border-[var(--border)]" />,
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-[var(--accent)] hover:underline"
    >
      {children}
    </a>
  ),
}

export function MarkdownMessage({ content, className = '' }: MarkdownMessageProps) {
  if (!content) return null

  return (
    <div className={`markdown-content text-sm text-[var(--text-secondary)] ${className}`}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  )
}
