import { InlineSpinner } from '@/components/ui/InlineSpinner'

type Props = {
  status: 'pending' | 'processing'
  hasUserAttachments?: boolean
}

export function JobStatusIndicator({ status, hasUserAttachments }: Props) {
  const label =
    status === 'processing' && hasUserAttachments
      ? 'Aplicando imagens anexadas…'
      : status === 'processing'
        ? 'Gerando seu post…'
        : 'Aguardando…'

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
