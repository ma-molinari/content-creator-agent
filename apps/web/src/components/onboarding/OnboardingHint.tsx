import { useOnboardingStore } from '@/stores/onboarding'

type Props = {
  id: string
  title: string
  description: string
  side?: 'top' | 'bottom'
  /** Narrow card (e.g. profile/history). Use false when aligned with ComposerBar max-w-3xl column. */
  narrow?: boolean
  /** Arrow horizontal anchor; center matches textarea in composer stack. */
  arrowAlign?: 'start' | 'center'
}

export function OnboardingHint({
  id,
  title,
  description,
  side = 'bottom',
  narrow = true,
  arrowAlign = 'start',
}: Props) {
  const dismissed = useOnboardingStore((s) => s.dismissedHints.has(id))
  const dismissHint = useOnboardingStore((s) => s.dismissHint)

  if (dismissed) return null

  /** Arrow on bottom edge (points down) when card sits above the target; top edge when below. */
  const arrowBottom = side === 'bottom'
  const arrowPosition = arrowAlign === 'center' ? 'left-1/2 -translate-x-1/2' : 'left-6'

  return (
    <div
      className={[
        'relative z-10 rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] p-4 shadow-[var(--shadow-sm)]',
        narrow ? 'max-w-md' : 'w-full',
        arrowBottom ? 'mb-3' : 'mt-3',
      ].join(' ')}
      role="region"
      aria-label={title}
    >
      {!arrowBottom && (
        <div
          className={[
            'absolute -top-2 h-3 w-3 rotate-45 border-l border-t border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)]',
            arrowPosition,
          ].join(' ')}
          aria-hidden
        />
      )}
      {arrowBottom && (
        <div
          className={[
            'absolute -bottom-2 h-3 w-3 rotate-45 border-b border-r border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)]',
            arrowPosition,
          ].join(' ')}
          aria-hidden
        />
      )}
      <button
        type="button"
        onClick={() => dismissHint(id)}
        aria-label="Fechar dica"
        className="absolute right-2 top-2 flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-text-muted)] hover:bg-[var(--color-bg-muted)] hover:text-[var(--color-text-secondary)]"
      >
        <IconX />
      </button>
      <h3 className="pr-8 text-sm font-semibold text-[var(--color-text-primary)]">{title}</h3>
      <p className="mt-1 text-sm text-[var(--color-text-secondary)]">{description}</p>
      <button
        type="button"
        onClick={() => dismissHint(id)}
        className="mt-3 rounded-[var(--radius-md)] bg-[var(--color-brand-primary)] px-3 py-1.5 text-sm font-medium text-white hover:bg-[var(--color-brand-primary-hover)]"
      >
        Entendi
      </button>
    </div>
  )
}

function IconX() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  )
}
