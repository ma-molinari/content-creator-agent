import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import { api } from '@/api/client'

type Props = {
  chatId: string
  fileId: string
  alt: string
  className?: string
  loading?: 'eager' | 'lazy'
}

/**
 * Renders a slide JPEG via GET /chats/:id/files/:fileId (Bearer auth), not presigned S3 URLs.
 * Uses React Query to dedupe fetches; revokes the object URL for this mount on cleanup.
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
    queryFn: async ({ signal }) => {
      const res = await api.get<Blob>(`/chats/${chatId}/files/${fileId}`, {
        responseType: 'blob',
        signal,
      })
      return res.data
    },
    enabled: !!chatId && !!fileId,
    staleTime: Number.POSITIVE_INFINITY,
    gcTime: 1000 * 60 * 60,
  })

  const [objectUrl, setObjectUrl] = useState<string | null>(null)

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

  if (isError) {
    return (
      <div
        className={className}
        style={{ minHeight: 48, background: 'var(--color-bg-muted)' }}
        role="img"
        aria-label={alt}
      />
    )
  }

  if (isPending || !objectUrl) {
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
