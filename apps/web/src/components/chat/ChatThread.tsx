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
  jobStatus: JobStatus | undefined
  /** Error message from a failed job. */
  jobError: string | null | undefined
  onRetry?: () => void
}

export function ChatThread({ chat, pendingText, jobStatus, jobError, onRetry }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chat?.contents?.length, pendingText])

  const contents = chat?.contents ?? []
  const showPendingBubble =
    pendingText != null &&
    pendingText.length > 0 &&
    !serverUserMessageCoversPending(contents, pendingText)

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-6">
      {contents.map((msg) =>
        msg.role === 'user' ? (
          <MessageBubbleUser key={msg.id} content={msg.content} createdAt={msg.createdAt} />
        ) : (
          <MessageAssistant key={msg.id} message={msg} />
        ),
      )}

      {/* Optimistic user bubble (hidden once GET /chats has the same last user row) */}
      {showPendingBubble && <MessageBubbleUser content={pendingText} />}

      {/* Job indicator or error */}
      {jobStatus === 'pending' || jobStatus === 'processing' ? (
        <div className="flex justify-start">
          <div className="rounded-[var(--radius-lg)] rounded-tl-[var(--radius-sm)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] px-4 py-3">
            <JobStatusIndicator status={jobStatus} />
          </div>
        </div>
      ) : jobError !== undefined && jobError !== null ? (
        <div className="flex justify-start">
          <div className="rounded-[var(--radius-lg)] rounded-tl-[var(--radius-sm)] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
            <p>Ocorreu um erro ao gerar o post. Tente enviar novamente.</p>
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
