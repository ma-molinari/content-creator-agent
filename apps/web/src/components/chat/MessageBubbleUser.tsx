type Props = {
  content: string
  createdAt?: string
}

export function MessageBubbleUser({ content, createdAt }: Props) {
  const time = createdAt
    ? new Date(createdAt).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
    : undefined

  return (
    <div className="flex justify-end">
      <div className="max-w-[75%]">
        <div className="rounded-[var(--radius-lg)] rounded-tr-[var(--radius-sm)] bg-[var(--color-brand-primary)] px-4 py-3 text-sm text-white">
          <p className="whitespace-pre-wrap break-words">{content}</p>
        </div>
        {time && (
          <p className="mt-1 text-right text-xs text-[var(--color-text-muted)]">{time}</p>
        )}
      </div>
    </div>
  )
}
