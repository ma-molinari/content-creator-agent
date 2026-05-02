type InlineSpinnerProps = {
  size?: number
  className?: string
  /** When true, element is omitted from the accessibility tree. */
  ariaHidden?: boolean
  /** Overrides default label when not `ariaHidden`. */
  ariaLabel?: string
}

const DEFAULT_TAILWIND = 'text-[var(--color-text-muted)]'

/** SVG loading indicator used inline in buttons and lists. */
export function InlineSpinner({
  size = 20,
  className,
  ariaHidden,
  ariaLabel = 'Carregando',
}: InlineSpinnerProps) {
  const mergedClass =
    className !== undefined && className.trim().length > 0
      ? `animate-spin ${className.trim()}`
      : `animate-spin ${DEFAULT_TAILWIND}`

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden={ariaHidden ? true : undefined}
      aria-label={ariaHidden ? undefined : ariaLabel}
      role={ariaHidden ? undefined : 'img'}
      className={mergedClass}
    >
      <circle
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeDasharray="40 60"
      />
    </svg>
  )
}
