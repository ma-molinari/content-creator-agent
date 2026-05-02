import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import { fetchChatSlideJpeg } from '@/api/chats'

type Props = {
  chatId: string
  fileId: string
  alt: string
  className?: string
  loading?: 'eager' | 'lazy'
}

/**
 * Renders a slide JPEG via GET /chats/:id/files/:fileId (Bearer auth), not presigned S3 URLs.
 * Uses React Query to dedupe fetches.
 *
 * createObjectURL / revokeObjectURL run in useEffect (not useMemo): pairing blob URLs with React
 * commit lifecycle avoids side effects during render and flaky img loads under Strict Mode.
 */
export function AuthenticatedSlideImage({
  chatId,
  fileId,
  alt,
  className,
  loading = 'lazy',
}: Props) {
  const { data: blob, isPending, isError } = useQuery({
    queryKey: ['chat-file', chatId, fileId],
    queryFn: ({ signal }) => fetchChatSlideJpeg(chatId, fileId, signal),
    enabled: !!chatId && !!fileId,
    staleTime: Number.POSITIVE_INFINITY,
    gcTime: 1000 * 60 * 60,
  })

  const [objectUrl, setObjectUrl] = useState<string | null>(null)

  /* Blob URLs must be created/revoked in an effect paired with DOM usage; putting createObjectURL in useMemo
     side-effects during render and was brittle under Strict Mode. setState-here intentionally syncs display URL with blob. */
  /* eslint-disable react-hooks/set-state-in-effect -- createObjectURL + revoke lifecycle */
  useEffect(() => {
    if (!blob) {
      setObjectUrl(null)
      return
    }
    const url = URL.createObjectURL(blob)
    setObjectUrl(url)
    return () => {
      URL.revokeObjectURL(url)
    }
  }, [blob])
  /* eslint-enable react-hooks/set-state-in-effect */

  if (isError) {
    return (
      <div
        className={className}
        style={{ minHeight: 48, background: 'var(--color-bg-muted)' }}
        role="img"
        aria-label={`Falha ao carregar imagem: ${alt}`}
        title="Falha ao carregar imagem"
      />
    )
  }

  if (isPending || !blob || !objectUrl) {
    return (
      <div
        className={className}
        style={{ minHeight: 48, background: 'var(--color-bg-muted)' }}
        aria-hidden
      />
    )
  }

  return <img src={objectUrl} alt={alt} loading={loading} className={className} />
}
