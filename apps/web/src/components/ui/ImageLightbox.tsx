import { useEffect, useRef } from 'react'

export type ImageLightboxItem = { url: string; alt: string }

type Props = {
  images: ImageLightboxItem[]
  index: number | null
  onClose: () => void
  onIndexChange?: (i: number) => void
}

export function ImageLightbox({ images, index, onClose, onIndexChange }: Props) {
  const dialogRef = useRef<HTMLDivElement>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)
  const prevIndexRef = useRef<number | null>(null)

  useEffect(() => {
    if (index === null) {
      previousFocusRef.current?.focus()
      prevIndexRef.current = null
      return
    }
    if (prevIndexRef.current === null) {
      if (document.activeElement instanceof HTMLElement) {
        previousFocusRef.current = document.activeElement
      } else {
        previousFocusRef.current = null
      }
    }
    prevIndexRef.current = index
    dialogRef.current?.focus()
  }, [index])

  if (index === null || images.length === 0) return null

  const safeIndex = Math.min(Math.max(0, index), images.length - 1)
  const item = images[safeIndex]

  function prev() {
    if (safeIndex <= 0) return
    onIndexChange?.(safeIndex - 1)
  }

  function next() {
    if (safeIndex >= images.length - 1) return
    onIndexChange?.(safeIndex + 1)
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Escape') onClose()
    if (e.key === 'ArrowLeft') prev()
    if (e.key === 'ArrowRight') next()
  }

  return (
    <div
      ref={dialogRef}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/90"
      onClick={onClose}
      onKeyDown={handleKeyDown}
      role="dialog"
      aria-modal
      aria-label={`Imagem ${safeIndex + 1} de ${images.length}`}
      tabIndex={-1}
    >
      {safeIndex > 0 && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation()
            prev()
          }}
          aria-label="Imagem anterior"
          className="absolute left-4 top-1/2 -translate-y-1/2 rounded-full bg-white/10 p-2 text-white hover:bg-white/20"
        >
          <IconChevronLeft />
        </button>
      )}

      <div className="max-h-[90vh] max-w-[90vw]" onClick={(e) => e.stopPropagation()}>
        <img
          src={item.url}
          alt={item.alt}
          className="max-h-[90vh] max-w-[90vw] rounded-[var(--radius-md)] object-contain"
        />
      </div>

      {safeIndex < images.length - 1 && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation()
            next()
          }}
          aria-label="Próxima imagem"
          className="absolute right-4 top-1/2 -translate-y-1/2 rounded-full bg-white/10 p-2 text-white hover:bg-white/20"
        >
          <IconChevronRight />
        </button>
      )}

      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation()
          onClose()
        }}
        aria-label="Fechar"
        className="absolute right-4 top-4 rounded-full bg-white/10 p-2 text-white hover:bg-white/20"
      >
        <IconX />
      </button>

      {images.length > 1 && (
        <p className="absolute bottom-4 left-1/2 -translate-x-1/2 text-sm text-white/60">
          {safeIndex + 1} / {images.length}
        </p>
      )}
    </div>
  )
}

function IconChevronLeft() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M15 18l-6-6 6-6"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function IconChevronRight() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M9 18l6-6-6-6"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function IconX() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M18 6L6 18M6 6l12 12"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  )
}
