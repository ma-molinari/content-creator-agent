import { useState } from 'react'

import { downloadContentZip, type ChatContent, type ChatContentImage, type FileListItem } from '@/api/chats'
import { SlideViewer } from '@/components/slides/SlideViewer'
import { IconDownload } from '@/components/ui/action-icons'
import { downloadBlob } from '@/lib/downloadBlob'

type Props = {
  message: ChatContent
  isLatestVersion: boolean
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

export function MessageAssistant({ message, isLatestVersion }: Props) {
  const hasImages = message.images && message.images.length > 0
  const files = hasImages ? imagesToFileListItems(message.images) : []
  const [downloading, setDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState<string | null>(null)

  const time = new Date(message.createdAt).toLocaleTimeString('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
  })

  async function handleDownloadZip() {
    setDownloadError(null)
    setDownloading(true)
    try {
      const { blob, filename } = await downloadContentZip(message.chatId, message.id)
      downloadBlob(blob, filename)
    } catch (e) {
      setDownloadError(
        e instanceof Error ? e.message : 'Não foi possível baixar o ZIP. Tente novamente.',
      )
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%]">
        <div className="rounded-[var(--radius-lg)] rounded-tl-[var(--radius-sm)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] px-4 py-3">
          <p className="whitespace-pre-wrap break-words text-sm text-[var(--color-text-primary)]">
            {message.content}
          </p>

          {files.length > 0 && (
            <div className="mt-3">
              {!isLatestVersion && (
                <div className="mb-2">
                  <span className="inline-flex rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-muted)] px-2 py-0.5 text-xs font-medium text-[var(--color-text-muted)]">
                    Versão anterior
                  </span>
                </div>
              )}
              <SlideViewer chatId={message.chatId} files={files} />
              <button
                type="button"
                disabled={downloading}
                onClick={() => void handleDownloadZip()}
                className="mt-3 inline-flex items-center gap-1.5 rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] px-3 py-1.5 text-xs font-medium text-[var(--color-text-primary)] hover:bg-[var(--color-bg-muted)] disabled:pointer-events-none disabled:opacity-50"
              >
                <IconDownload size={14} />
                {downloading ? 'A baixar…' : 'Baixar ZIP'}
              </button>
              {downloadError !== null ? (
                <p className="mt-1 text-xs text-red-600 dark:text-red-400">{downloadError}</p>
              ) : null}
            </div>
          )}
        </div>
        <p className="mt-1 text-xs text-[var(--color-text-muted)]">{time}</p>
      </div>
    </div>
  )
}
