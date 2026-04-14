type Props = {
  status: 'pending' | 'processing'
}

export function JobStatusIndicator({ status }: Props) {
  const label = status === 'processing' ? 'Gerando seu post…' : 'Aguardando…'

  return (
    <div className="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
      <Spinner />
      <span>{label}</span>
    </div>
  )
}

function Spinner() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      aria-label="Carregando"
      className="animate-spin text-[var(--color-brand-primary)]"
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
