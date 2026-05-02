import { useRef, useState } from 'react'

import { InlineSpinner } from '@/components/ui/InlineSpinner'

type Props = {
  onSend: (text: string) => Promise<void>
  disabled?: boolean
  placeholder?: string
}

const MAX_CHARS = 2000

export function ComposerBar({
  onSend,
  disabled = false,
  placeholder = 'Descreva o post que você quer criar…',
}: Props) {
  const [text, setText] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const charCount = text.length
  const canSend = text.trim().length > 0 && !disabled && !submitting

  function autoResize() {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 120) + 'px'
  }

  function handleChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    if (e.target.value.length > MAX_CHARS) return
    setText(e.target.value)
    autoResize()
  }

  async function handleSend() {
    const trimmed = text.trim()
    if (!trimmed || submitting || disabled) return
    setSubmitting(true)
    try {
      await onSend(trimmed)
      setText('')
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
      }
    } catch {
      // Parent surfaces errors (e.g. toast); keep draft
    } finally {
      setSubmitting(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="min-h-[var(--app-bottom-shelf-min-height)] shrink-0 border-t border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] px-4 py-3">
      <div className="mx-auto max-w-3xl">
        <div className="flex items-center gap-2 rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-app)] px-3 py-2 shadow-[var(--shadow-composer)] focus-within:ring-2 focus-within:ring-[var(--color-focus-ring)]">
          <textarea
            ref={textareaRef}
            value={text}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            disabled={disabled || submitting}
            placeholder={placeholder}
            rows={1}
            aria-label="Mensagem"
            className="flex-1 resize-none bg-transparent py-2 text-sm leading-snug text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] outline-none disabled:cursor-not-allowed disabled:opacity-60"
            style={{ maxHeight: 120 }}
          />
          <div className="flex shrink-0 items-center gap-2">
            <span
              className={[
                'text-xs tabular-nums',
                charCount > MAX_CHARS * 0.9
                  ? 'text-amber-500'
                  : 'text-[var(--color-text-muted)]',
              ].join(' ')}
            >
              {charCount}/{MAX_CHARS}
            </span>
            <button
              type="button"
              onClick={handleSend}
              disabled={!canSend}
              aria-label="Enviar"
              className="flex h-8 w-8 items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-brand-primary)] text-white transition-opacity hover:bg-[var(--color-brand-primary-hover)] disabled:cursor-not-allowed disabled:opacity-40"
            >
              {submitting ? (
                <InlineSpinner size={16} ariaHidden className="text-white" />
              ) : (
                <IconSend />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function IconSend() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M22 2L11 13M22 2L15 22l-4-9-9-4 20-7z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
