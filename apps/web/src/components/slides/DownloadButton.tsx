import { IconDownload } from '@/components/ui/action-icons'

type Props = {
  href: string
  fileName: string
  label?: string
}

export function DownloadButton({ href, fileName, label = 'Baixar' }: Props) {
  return (
    <a
      href={href}
      download={fileName}
      className="inline-flex items-center gap-1.5 rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] px-3 py-1.5 text-xs font-medium text-[var(--color-text-primary)] hover:bg-[var(--color-bg-muted)]"
    >
      <IconDownload size={14} />
      {label}
    </a>
  )
}
