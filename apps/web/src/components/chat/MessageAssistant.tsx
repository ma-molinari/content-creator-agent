import type { ChatContent } from '@/api/chats'
import { useFiles } from '@/api/chats'
import { SlideViewer } from '@/components/slides/SlideViewer'

type Props = {
  message: ChatContent
  chatId: string
}

export function MessageAssistant({ message, chatId }: Props) {
  const files = useFiles(chatId)
  const hasImages = message.images && message.images.length > 0

  const time = new Date(message.createdAt).toLocaleTimeString('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
  })

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%]">
        <div className="rounded-[var(--radius-lg)] rounded-tl-[var(--radius-sm)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] px-4 py-3">
          <p className="whitespace-pre-wrap break-words text-sm text-[var(--color-text-primary)]">
            {message.content}
          </p>

          {hasImages && (
            <div className="mt-3">
              {files.isLoading ? (
                <SlideSkeleton count={message.images.length} />
              ) : files.data && files.data.length > 0 ? (
                <SlideViewer files={files.data} />
              ) : null}
            </div>
          )}
        </div>
        <p className="mt-1 text-xs text-[var(--color-text-muted)]">{time}</p>
      </div>
    </div>
  )
}

function SlideSkeleton({ count }: { count: number }) {
  return (
    <div className="flex gap-2">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="shrink-0 animate-pulse rounded-[var(--radius-md)] bg-[var(--color-bg-muted)]"
          style={{ width: 96, aspectRatio: '768 / 1376' }}
          aria-hidden
        />
      ))}
    </div>
  )
}
