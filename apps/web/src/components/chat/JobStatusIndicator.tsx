import { InlineSpinner } from '@/components/ui/InlineSpinner'

type Props = {
  status: 'pending' | 'processing'
}

export function JobStatusIndicator({ status }: Props) {
  const label = status === 'processing' ? 'Gerando seu post…' : 'Aguardando…'

  return (
    <div className="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
      <InlineSpinner
        size={16}
        ariaHidden
        className="text-[var(--color-brand-primary)]"
      />
      <span>{label}</span>
    </div>
  )
}
