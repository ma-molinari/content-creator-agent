import { useState } from 'react'

import { ImageLightbox } from '@/components/ui/ImageLightbox'

type Attachment = { id: string; url: string; mimeType: string }

type Props = {
  content: string
  createdAt?: string
  attachments?: Attachment[]
}

export function MessageBubbleUser({ content, createdAt, attachments }: Props) {
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null)

  const time = createdAt
    ? new Date(createdAt).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
    : undefined

  const lightboxImages =
    attachments?.map((a, i) => ({
      url: a.url,
      alt: `Anexo ${i + 1}`,
    })) ?? []

  return (
    <div className="flex justify-end">
      <div className="max-w-[75%]">
        <div className="rounded-[var(--radius-lg)] rounded-tr-[var(--radius-sm)] bg-[var(--color-brand-primary)] px-4 py-3 text-sm text-white">
          {attachments && attachments.length > 0 && (
            <div className="mb-2 grid grid-cols-2 gap-1.5 sm:grid-cols-4">
              {attachments.map((att, i) => (
                <button
                  key={att.id}
                  type="button"
                  onClick={() => setLightboxIndex(i)}
                  aria-label={`Anexo ${i + 1} de ${attachments.length}`}
                  className="overflow-hidden rounded-[var(--radius-sm)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-focus-ring)]"
                >
                  <img
                    src={att.url}
                    alt={`Anexo ${i + 1}`}
                    className="aspect-square h-full w-full object-cover"
                    onError={(e) => {
                      ;(e.currentTarget as HTMLImageElement).src = '/placeholder-image.svg'
                    }}
                  />
                </button>
              ))}
            </div>
          )}
          {content.trim().length > 0 && (
            <p className="whitespace-pre-wrap break-words">{content}</p>
          )}
        </div>
        {time && (
          <p className="mt-1 text-right text-xs text-[var(--color-text-muted)]">{time}</p>
        )}
        <ImageLightbox
          images={lightboxImages}
          index={lightboxIndex}
          onClose={() => setLightboxIndex(null)}
          onIndexChange={setLightboxIndex}
        />
      </div>
    </div>
  )
}
