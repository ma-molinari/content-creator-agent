import { useEffect, useRef } from 'react'

import type { Chat, JobStatus } from '@/api/chats'
import { JobStatusIndicator } from '@/components/chat/JobStatusIndicator'
import { MessageAssistant } from '@/components/chat/MessageAssistant'
import { MessageBubbleUser } from '@/components/chat/MessageBubbleUser'
import { serverUserMessageCoversPending } from '@/lib/sanitizeUserInput'

type Props = {
  chat: Chat | undefined
  /** Text the user just sent while a job is in-flight (optimistic). */
  pendingText: string | null
  /** Local preview URLs for attachments sent with the pending message. */
  pendingAttachments?: { id: string; url: string; mimeType: string }[]
  jobStatus: JobStatus | undefined
  jobStage?: string
  jobProgress?: number
  /** Error message from a failed job. */
  jobError: string | null | undefined
  onRetry?: () => void
}

export function ChatThread({
  chat,
  pendingText,
  pendingAttachments,
  jobStatus,
  jobStage,
  jobProgress,
  jobError,
  onRetry,
}: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chat?.contents?.length, pendingText, pendingAttachments?.length])

  const contents = chat?.contents ?? []
  const lastAssistantWithImagesId = [...contents]
    .reverse()
    .find((m) => m.role === 'assistant' && (m.images?.length ?? 0) > 0)?.id

  const lastUserHasAttachments =
    (pendingAttachments?.length ?? 0) > 0 ||
    !!(
      [...contents].reverse().find((c) => c.role === 'user')?.attachments?.length
    )

  const showPendingBubble =
    pendingText != null &&
    pendingText.length > 0 &&
    !serverUserMessageCoversPending(contents, pendingText, pendingAttachments?.length ?? 0)

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-6">
      {contents.map((msg) =>
        msg.role === 'user' ? (
          <MessageBubbleUser
            key={msg.id}
            content={msg.content}
            createdAt={msg.createdAt}
            attachments={msg.attachments}
          />
        ) : (
          <MessageAssistant
            key={msg.id}
            message={msg}
            isLatestVersion={
              (msg.images?.length ?? 0) === 0 ||
              (chat?.postFormat === 'structured_v1'
                ? msg.versionId === chat.currentVersionId
                : msg.id === lastAssistantWithImagesId)
            }
          />
        ),
      )}

      {/* Optimistic user bubble (hidden once GET /chats has the same last user row) */}
      {showPendingBubble && (
        <MessageBubbleUser
          content={pendingText ?? ''}
          attachments={pendingAttachments}
        />
      )}

      {/* Job indicator or error */}
      {jobStatus === 'pending' || jobStatus === 'processing' ? (
        <div className="flex justify-start">
          <div className="rounded-[var(--radius-lg)] rounded-tl-[var(--radius-sm)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] px-4 py-3">
            <JobStatusIndicator
              status={jobStatus}
              hasUserAttachments={lastUserHasAttachments}
              stage={jobStage}
              progress={jobProgress}
            />
          </div>
        </div>
      ) : jobError !== undefined && jobError !== null && jobError !== '' ? (
        <div className="flex justify-start">
          <div className="rounded-[var(--radius-lg)] rounded-tl-[var(--radius-sm)] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
            <p>Ocorreu um erro ao gerar o post. Tente enviar novamente.</p>
            {jobError !== 'Erro desconhecido' && (
              <p className="mt-1 line-clamp-3 break-words text-xs text-red-600/90 dark:text-red-400/90">
                {jobError.length > 280 ? `${jobError.slice(0, 280)}…` : jobError}
              </p>
            )}
            {onRetry && (
              <button
                type="button"
                onClick={onRetry}
                className="mt-2 font-medium underline hover:no-underline"
              >
                Tentar novamente
              </button>
            )}
          </div>
        </div>
      ) : null}

      <div ref={bottomRef} />
    </div>
  )
}
