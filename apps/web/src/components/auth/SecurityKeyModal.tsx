import { useState } from 'react'

type Props = {
  securityKey: string
  onClose: () => void
}

export function SecurityKeyModal({ securityKey, onClose }: Props) {
  const [copied, setCopied] = useState(false)
  const [confirmed, setConfirmed] = useState(false)

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(securityKey)
      setCopied(true)
      setTimeout(() => setCopied(false), 2_000)
    } catch {
      // clipboard unavailable — user can copy manually
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div
        className="w-full max-w-md rounded-[var(--radius-lg)] bg-[var(--color-bg-surface)] p-6 shadow-[var(--shadow-md)]"
        role="alertdialog"
        aria-modal
        aria-labelledby="sk-title"
      >
        <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-full bg-amber-100 text-amber-600">
          <IconKey />
        </div>

        <h2
          id="sk-title"
          className="text-lg font-semibold text-[var(--color-text-primary)]"
        >
          Sua chave de segurança
        </h2>
        <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
          Guarde-a em local seguro. Ela{' '}
          <strong className="text-[var(--color-text-primary)]">
            não poderá ser exibida novamente.
          </strong>{' '}
          Use-a para recuperar sua conta caso esqueça a senha.
        </p>

        <div className="mt-4 flex items-start gap-2 rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-muted)] px-3 py-3">
          <code className="flex-1 break-all font-mono text-sm leading-relaxed text-[var(--color-text-primary)]">
            {securityKey}
          </code>
          <button
            type="button"
            onClick={handleCopy}
            className="shrink-0 rounded-[var(--radius-sm)] px-2 py-1 text-xs font-medium text-[var(--color-brand-primary)] hover:bg-[var(--color-bg-surface)]"
          >
            {copied ? '✓ Copiado' : 'Copiar'}
          </button>
        </div>

        <label className="mt-4 flex cursor-pointer items-start gap-2.5 text-sm text-[var(--color-text-secondary)]">
          <input
            type="checkbox"
            checked={confirmed}
            onChange={(e) => setConfirmed(e.target.checked)}
            className="mt-0.5 accent-[var(--color-brand-primary)]"
          />
          Confirmo que salvei minha chave de segurança em local seguro.
        </label>

        <button
          type="button"
          disabled={!confirmed}
          onClick={onClose}
          className="mt-5 w-full rounded-[var(--radius-md)] bg-[var(--color-brand-primary)] px-4 py-2.5 text-sm font-medium text-white hover:bg-[var(--color-brand-primary-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-focus-ring)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          Continuar para o login
        </button>
      </div>
    </div>
  )
}

function IconKey() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="7" cy="17" r="4" stroke="currentColor" strokeWidth="1.5" />
      <path
        d="M10.83 13.17L20 4"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <path d="M17 7l2 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  )
}
