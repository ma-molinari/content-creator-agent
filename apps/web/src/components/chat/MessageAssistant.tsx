import type { ChatContent, ChatContentImage, FileListItem } from '@/api/chats'
import { SlideViewer } from '@/components/slides/SlideViewer'

type Props = {
  message: ChatContent
}

function imagesToFileListItems(images: ChatContentImage[]): FileListItem[] {
  return [...images]
    .sort((a, b) => a.slideNumber - b.slideNumber)
    .map((img) => ({
      id: img.id,
      fileName: `slide-${img.slideNumber}.jpg`,
      mimeType: 'image/jpeg',
      downloadUrl: img.url,
    }))
}

export function MessageAssistant({ message }: Props) {
  const hasImages = message.images && message.images.length > 0
  const files = hasImages ? imagesToFileListItems(message.images) : []

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

          {files.length > 0 && (
            <div className="mt-3">
              <SlideViewer files={files} />
            </div>
          )}
        </div>
        <p className="mt-1 text-xs text-[var(--color-text-muted)]">{time}</p>
      </div>
    </div>
  )
}
