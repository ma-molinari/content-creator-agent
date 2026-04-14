import { useState } from 'react'

import type { FileListItem } from '@/api/chats'

type Props = {
  files: FileListItem[]
}

export function SlideViewer({ files }: Props) {
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null)

  if (files.length === 0) return null

  const sorted = [...files].sort((a, b) => {
    const na = parseInt(a.fileName.replace(/\D/g, '')) || 0
    const nb = parseInt(b.fileName.replace(/\D/g, '')) || 0
    return na - nb
  })

  function openLightbox(i: number) {
    setLightboxIndex(i)
  }

  function closeLightbox() {
    setLightboxIndex(null)
  }

  function prev() {
    setLightboxIndex((i) => (i !== null ? Math.max(0, i - 1) : null))
  }

  function next() {
    setLightboxIndex((i) => (i !== null ? Math.min(sorted.length - 1, i + 1) : null))
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Escape') closeLightbox()
    if (e.key === 'ArrowLeft') prev()
    if (e.key === 'ArrowRight') next()
  }

  return (
    <>
      <div className="mt-3 flex gap-2 overflow-x-auto pb-2">
        {sorted.map((file, i) => (
          <button
            key={file.id}
            type="button"
            onClick={() => openLightbox(i)}
            className="group relative shrink-0 overflow-hidden rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-focus-ring)]"
            style={{ width: 96, aspectRatio: '768 / 1376' }}
            aria-label={`Abrir slide ${i + 1} de ${sorted.length}`}
          >
            <img
              src={file.downloadUrl}
              alt={`Slide ${i + 1} de ${sorted.length}`}
              loading="lazy"
              className="h-full w-full object-cover transition-opacity group-hover:opacity-90"
            />
          </button>
        ))}
      </div>

      {lightboxIndex !== null && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/90"
          onClick={closeLightbox}
          onKeyDown={handleKeyDown}
          role="dialog"
          aria-modal
          aria-label={`Slide ${lightboxIndex + 1} de ${sorted.length}`}
          tabIndex={-1}
        >
          {/* Prev */}
          {lightboxIndex > 0 && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                prev()
              }}
              aria-label="Slide anterior"
              className="absolute left-4 top-1/2 -translate-y-1/2 rounded-full bg-white/10 p-2 text-white hover:bg-white/20"
            >
              <IconChevronLeft />
            </button>
          )}

          <img
            src={sorted[lightboxIndex].downloadUrl}
            alt={`Slide ${lightboxIndex + 1} de ${sorted.length}`}
            className="max-h-[90vh] max-w-[90vw] rounded-[var(--radius-md)] object-contain"
            onClick={(e) => e.stopPropagation()}
          />

          {/* Next */}
          {lightboxIndex < sorted.length - 1 && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                next()
              }}
              aria-label="Próximo slide"
              className="absolute right-4 top-1/2 -translate-y-1/2 rounded-full bg-white/10 p-2 text-white hover:bg-white/20"
            >
              <IconChevronRight />
            </button>
          )}

          {/* Close */}
          <button
            type="button"
            onClick={closeLightbox}
            aria-label="Fechar"
            className="absolute right-4 top-4 rounded-full bg-white/10 p-2 text-white hover:bg-white/20"
          >
            <IconX />
          </button>

          <p className="absolute bottom-4 left-1/2 -translate-x-1/2 text-sm text-white/60">
            {lightboxIndex + 1} / {sorted.length}
          </p>
        </div>
      )}
    </>
  )
}

function IconChevronLeft() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M15 18l-6-6 6-6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function IconChevronRight() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M9 18l6-6-6-6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function IconX() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  )
}
