import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'

import { api } from '@/api/client'
import type { Chat as ChatType, JobStatus } from '@/api/chats'
import { useChat, useDeleteChat, useJobStatus, useSetupStatus } from '@/api/chats'
import { AlertDialog } from '@/components/ui/AlertDialog'
import { ChatThread } from '@/components/chat/ChatThread'
import { ComposerBar } from '@/components/composer/ComposerBar'
import { EmptyChatState } from '@/components/chat/EmptyChatState'
import { toast } from '@/lib/toast'

type ActiveJob = {
  chatId: string
  jobId: string
  pendingText: string
}

export default function Chat() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const [activeJob, setActiveJob] = useState<ActiveJob | null>(null)
  const [confirmDelete, setConfirmDelete] = useState(false)

  const setup = useSetupStatus()
  const chat = useChat(id)
  const deleteChat = useDeleteChat()

  const jobStatus = useJobStatus(activeJob?.chatId ?? null, activeJob?.jobId ?? null)
  const currentStatus: JobStatus | undefined = jobStatus.data?.status

  // Detect job terminal state and clear
  const prevStatusRef = useRef<JobStatus | undefined>(undefined)
  useEffect(() => {
    if (prevStatusRef.current === currentStatus) return
    prevStatusRef.current = currentStatus

    if (currentStatus === 'done' || currentStatus === 'failed') {
      if (currentStatus === 'done' && activeJob) {
        qc.invalidateQueries({ queryKey: ['chats', activeJob.chatId] })
        qc.invalidateQueries({ queryKey: ['files', activeJob.chatId] })
      }
      queueMicrotask(() => setActiveJob(null))
    }
  }, [currentStatus, activeJob, qc])

  const isJobActive =
    !!activeJob &&
    (currentStatus === 'pending' || currentStatus === 'processing' || currentStatus === undefined)

  const handleSend = useCallback(
    async (text: string) => {
      let chatId = id

      if (!chatId) {
        const { data: newChat } = await api.post<ChatType>('/chats', { postType: 'carousel' })
        chatId = newChat.id
        qc.invalidateQueries({ queryKey: ['chats'] })
        navigate(`/chat/${chatId}`, { replace: true })
      }

      const { data } = await api.post<{ jobId: string }>(`/chats/${chatId}/messages`, {
        content: text,
      })

      setActiveJob({ chatId, jobId: data.jobId, pendingText: text })
    },
    [id, navigate, qc],
  )

  const handleChipClick = useCallback(
    (text: string) => {
      void handleSend(text)
    },
    [handleSend],
  )

  const handleRetry = useCallback(() => {
    const text = activeJob?.pendingText
    setActiveJob(null)
    if (text) void handleSend(text)
  }, [activeJob, handleSend])

  async function handleDelete() {
    if (!id) return
    setConfirmDelete(false)
    try {
      await deleteChat.mutateAsync(id)
      toast.success('Chat excluído.')
      navigate('/', { replace: true })
    } catch {
      toast.error('Não foi possível excluir. Tente novamente.')
    }
  }

  if (setup.isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center py-20">
        <Spinner />
      </div>
    )
  }

  const setupConfigured = setup.data?.configured ?? true

  return (
    <>
      <div className="flex flex-1 flex-col overflow-hidden">
        {!setupConfigured && (
          <div className="shrink-0 border-b border-amber-200 bg-amber-50 px-6 py-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-300">
            Perfil não configurado.{' '}
            <Link
              to="/profile"
              className="font-medium underline underline-offset-2 hover:text-amber-900 dark:hover:text-amber-200"
            >
              Abrir configuração do perfil
            </Link>{' '}
            para colar AUDIT e BRAND e habilitar a geração de posts.
          </div>
        )}

        {/* Chat header — only when viewing an existing chat */}
        {id && (
          <div className="flex shrink-0 items-center justify-between border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] px-4 py-2">
            <p className="line-clamp-1 text-sm font-medium text-[var(--color-text-secondary)]">
              {chat.data?.title ?? 'Chat'}
            </p>
            <div className="flex items-center gap-1">
              <a
                href={`/api/chats/${id}/files/download`}
                download
                title="Baixar todos os slides (ZIP)"
                className="flex h-8 w-8 items-center justify-center rounded-[var(--radius-md)] text-[var(--color-text-muted)] hover:bg-[var(--color-bg-muted)] hover:text-[var(--color-text-primary)]"
              >
                <IconDownload />
              </a>
              <button
                type="button"
                onClick={() => setConfirmDelete(true)}
                title="Excluir chat"
                className="flex h-8 w-8 items-center justify-center rounded-[var(--radius-md)] text-[var(--color-text-muted)] hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20"
              >
                <IconTrash />
              </button>
            </div>
          </div>
        )}

        <div className="flex-1 overflow-y-auto">
          {!id ? (
            <EmptyChatState onChipClick={setupConfigured ? handleChipClick : undefined} />
          ) : chat.isLoading ? (
            <div className="flex items-center justify-center py-20">
              <Spinner />
            </div>
          ) : (
            <ChatThread
              chat={chat.data}
              pendingText={isJobActive ? (activeJob?.pendingText ?? null) : null}
              jobStatus={isJobActive ? currentStatus : undefined}
              jobError={
                currentStatus === 'failed'
                  ? (jobStatus.data?.error ?? 'Erro desconhecido')
                  : null
              }
              onRetry={currentStatus === 'failed' ? handleRetry : undefined}
            />
          )}
        </div>

        <ComposerBar onSend={handleSend} disabled={isJobActive || !setupConfigured} />
      </div>

      <AlertDialog
        open={confirmDelete}
        title="Excluir chat"
        description="Esta ação não pode ser desfeita. O chat e todos os slides gerados serão removidos permanentemente."
        confirmLabel="Excluir"
        loading={deleteChat.isPending}
        onConfirm={handleDelete}
        onCancel={() => setConfirmDelete(false)}
      />
    </>
  )
}

function Spinner() {
  return (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      aria-label="Carregando"
      className="animate-spin text-[var(--color-text-muted)]"
    >
      <circle
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeDasharray="40 60"
      />
    </svg>
  )
}

function IconDownload() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function IconTrash() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M3 6h18M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6M10 11v6M14 11v6M9 6V4a1 1 0 011-1h4a1 1 0 011 1v2"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
