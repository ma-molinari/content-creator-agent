import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo } from 'react'

import { api } from '@/api/client'

type Props = {
  chatId: string
  fileId: string
  alt: string
  className?: string
  loading?: 'eager' | 'lazy'
}

type BlobImgProps = {
  blob: Blob
  alt: string
  className?: string
  loading: 'eager' | 'lazy'
}

/**
 * Creates a stable object URL for the blob and revokes it when the blob identity changes or on unmount.
 * Side effect (createObjectURL) is paired with revoke in an effect cleanup — no setState in effects.
 */
function SlideBlobImage({ blob, alt, className, loading }: BlobImgProps) {
  const objectUrl = useMemo(() => URL.createObjectURL(blob), [blob])

  useEffect(() => {
    return () => {
      URL.revokeObjectURL(objectUrl)
    }
  }, [objectUrl])

  return <img src={objectUrl} alt={alt} loading={loading} className={className} />
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

  if (isPending || !blob) {
    return (
      <div
        className={className}
        style={{ minHeight: 48, background: 'var(--color-bg-muted)' }}
        aria-hidden
      />
    )
  }

  return <SlideBlobImage blob={blob} alt={alt} loading={loading} className={className} />
}
