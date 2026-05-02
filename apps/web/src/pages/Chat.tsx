import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { type QueryClient, useQueryClient } from '@tanstack/react-query'
import { isAxiosError } from 'axios'

import { api } from '@/api/client'
import type { Chat as ChatType, JobStatus } from '@/api/chats'
import {
  fetchChatFilesZip,
  useChat,
  useDeleteChat,
  useJobStatus,
  useSetupStatus,
} from '@/api/chats'
import { downloadBlob } from '@/lib/downloadBlob'
import { IconDownload, IconTrash } from '@/components/ui/action-icons'
import { InlineSpinner } from '@/components/ui/InlineSpinner'
import { AlertDialog } from '@/components/ui/AlertDialog'
import { ChatThread } from '@/components/chat/ChatThread'
import { ComposerBar } from '@/components/composer/ComposerBar'
import { EmptyChatState } from '@/components/chat/EmptyChatState'
import { OnboardingHint } from '@/components/onboarding'
import { toast } from '@/lib/toast'
import { useOnboardingStore } from '@/stores/onboarding'

type ActiveJob = {
  chatId: string
  jobId: string
  pendingText: string
}

type LastJobFailure = {
  error: string
  pendingText: string
}

/** Survives remount after `/` → `/chat/:id` where router `state.pendingJob` may be stripped before rerender. */
function activeJobHydrateKey(chatId: string) {
  return ['hydrate-active-job', chatId] as const
}

function removeActiveJobHydrate(qc: QueryClient, chatId: string | undefined) {
  if (chatId) {
    qc.removeQueries({ queryKey: activeJobHydrateKey(chatId), exact: true })
  }
}

function pendingJobFromLocationState(state: unknown): ActiveJob | null {
  const raw = (state as { pendingJob?: ActiveJob } | null | undefined)?.pendingJob
  return raw ?? null
}

function activeJobForChat(
  chatId: string,
  fromRouter: ActiveJob | null,
  fromCache: ActiveJob | null,
): ActiveJob | null {
  if (fromRouter?.chatId === chatId) return fromRouter
  if (fromCache?.chatId === chatId) return fromCache
  return null
}

const UNKNOWN_JOB_ERROR = 'Erro desconhecido'

function messageFromApiError(err: unknown, fallback: string): string {
  if (isAxiosError(err)) {
    const data = err.response?.data as { message?: string } | undefined
    if (typeof data?.message === 'string' && data.message.length > 0) {
      return data.message
    }
  }
  return fallback
}

function resolveJobError(
  activeJob: ActiveJob | null,
  currentStatus: JobStatus | undefined,
  pollError: string | null | undefined,
  lastFailure: LastJobFailure | null,
): string | null {
  if (activeJob && currentStatus === 'failed') {
    return pollError ?? UNKNOWN_JOB_ERROR
  }
  return lastFailure?.error ?? null
}

export default function Chat() {
  const { id } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const chatHintDismissed = useOnboardingStore((s) => s.dismissedHints.has('chat-composer'))
  const prevChatIdRef = useRef<string | undefined>(undefined)

  const [activeJob, setActiveJob] = useState<ActiveJob | null>(null)
  const [lastJobFailure, setLastJobFailure] = useState<LastJobFailure | null>(null)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [isDownloadingZip, setIsDownloadingZip] = useState(false)

  const setup = useSetupStatus()
  const chat = useChat(id)
  const deleteChat = useDeleteChat()

  useEffect(() => {
    if (!id) return
    const onPageShow = (e: PageTransitionEvent) => {
      if (e.persisted) {
        void qc.invalidateQueries({ queryKey: ['chats', id] })
      }
    }
    window.addEventListener('pageshow', onPageShow)
    return () => window.removeEventListener('pageshow', onPageShow)
  }, [id, qc])

  /** Apply route transition + hydrate `activeJob` before paint so the first `/chat/:id` frame tracks the new job (lazy route + stripping `location.state`). */
  useLayoutEffect(() => {
    const prev = prevChatIdRef.current
    if (prev !== undefined && prev !== id) {
      qc.removeQueries({ queryKey: activeJobHydrateKey(prev), exact: true })
      setActiveJob(null)
      setLastJobFailure(null)
    }
    prevChatIdRef.current = id

    if (!id || id.length === 0) return

    const picked = activeJobForChat(
      id,
      pendingJobFromLocationState(location.state),
      qc.getQueryData<ActiveJob>(activeJobHydrateKey(id)) ?? null,
    )
    if (picked !== null) {
      setActiveJob(picked)
    }
  }, [id, qc, location.key, location.state])

  useEffect(() => {
    if (pendingJobFromLocationState(location.state) !== null) {
      navigate(location.pathname, { replace: true, state: null })
    }
    // Intentionally once on mount: strip pendingJob from history so refresh does not restore it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const jobStatus = useJobStatus(activeJob?.chatId ?? null, activeJob?.jobId ?? null)
  const currentStatus: JobStatus | undefined = jobStatus.data?.status

  // Detect job terminal state: persist failure for UI, then clear active job
  const prevStatusRef = useRef<JobStatus | undefined>(undefined)
  useEffect(() => {
    if (prevStatusRef.current === currentStatus) return
    prevStatusRef.current = currentStatus

    const clearActiveJobSoon = (hydrateId: string | undefined) => {
      queueMicrotask(() => {
        removeActiveJobHydrate(qc, hydrateId)
        setActiveJob(null)
      })
    }

    if (currentStatus === 'done') {
      const hydrateId = activeJob?.chatId
      if (activeJob) {
        void qc.invalidateQueries({ queryKey: ['chats', activeJob.chatId] })
        setLastJobFailure(null)
      }
      clearActiveJobSoon(hydrateId)
    } else if (currentStatus === 'failed' && activeJob) {
      const err = jobStatus.data?.error ?? UNKNOWN_JOB_ERROR
      const hydrateId = activeJob.chatId
      setLastJobFailure({ error: err, pendingText: activeJob.pendingText })
      toast.error('Não foi possível gerar o post.')
      clearActiveJobSoon(hydrateId)
    }
  }, [currentStatus, activeJob, qc, jobStatus.data?.error])

  const showJobLoading =
    !!activeJob &&
    (currentStatus === 'pending' || currentStatus === 'processing' || currentStatus === undefined)

  /** Normalize for thread UI: first poll frame has no `status` yet; show same pending bubble as upstream. */
  const assistantThreadJobStatus: JobStatus | undefined = showJobLoading
    ? (currentStatus ?? 'pending')
    : undefined

  const jobError = resolveJobError(
    activeJob,
    currentStatus,
    jobStatus.data?.error,
    lastJobFailure,
  )

  const handleSend = useCallback(
    async (text: string, options?: { postType?: 'single' | 'carousel' }) => {
      const postTypeForNew = options?.postType ?? 'carousel'
      let chatId = id

      if (!chatId) {
        try {
          const { data: newChat } = await api.post<ChatType>('/chats', {
            postType: postTypeForNew,
          })
          chatId = newChat.id
          void qc.invalidateQueries({ queryKey: ['chats'] })
        } catch (err) {
          toast.error(messageFromApiError(err, 'Não foi possível criar o chat.'))
          throw err
        }
      }

      setLastJobFailure(null)

      let jobId: string
      try {
        const { data } = await api.post<{ jobId: string }>(`/chats/${chatId}/messages`, {
          content: text,
        })
        jobId = data.jobId
      } catch (err) {
        toast.error(
          messageFromApiError(
            err,
            'Não foi possível enviar a mensagem. Você pode tentar novamente.',
          ),
        )
        throw err
      }

      void qc.invalidateQueries({ queryKey: ['chats', chatId] })

      const pending: ActiveJob = { chatId, jobId, pendingText: text }
      if (!id) {
        qc.setQueryData(activeJobHydrateKey(chatId), pending)
        navigate(`/chat/${chatId}`, {
          replace: true,
          state: { pendingJob: pending },
        })
      } else {
        setActiveJob(pending)
      }
    },
    [id, navigate, qc],
  )

  const handleChipClick = useCallback(
    (text: string, postType: 'single' | 'carousel') => {
      void handleSend(text, { postType }).catch(() => undefined)
    },
    [handleSend],
  )

  const handleRetry = useCallback(() => {
    const text = activeJob?.pendingText ?? lastJobFailure?.pendingText
    setLastJobFailure(null)
    setActiveJob(null)
    if (text) {
      void handleSend(text).catch(() => undefined)
    }
  }, [activeJob, lastJobFailure, handleSend])

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

  async function handleDownloadZip() {
    if (!id || isDownloadingZip) return
    setIsDownloadingZip(true)
    try {
      const { blob, filename } = await fetchChatFilesZip(id)
      downloadBlob(blob, filename)
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Não foi possível baixar o ZIP. Tente novamente.'
      toast.error(msg)
    } finally {
      setIsDownloadingZip(false)
    }
  }

  if (setup.isLoading) {
    return (
      <div className="flex min-h-0 flex-1 items-center justify-center py-20">
        <InlineSpinner size={24} />
      </div>
    )
  }

  const setupConfigured = setup.data?.configured ?? true

  const chatLoading = !!id && (chat.isLoading || chat.isFetching)
  const messageCount = id ? (chat.data?.contents.length ?? 0) : 0
  const showComposerHint =
    !chatHintDismissed &&
    !showJobLoading &&
    !chatLoading &&
    messageCount === 0

  return (
    <>
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
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

        {id && (
          <div className="flex shrink-0 items-center justify-between border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] px-4 py-2">
            <p className="line-clamp-1 text-sm font-medium text-[var(--color-text-secondary)]">
              {chat.data?.title ?? 'Chat'}
            </p>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => void handleDownloadZip()}
                disabled={isDownloadingZip}
                title="Baixar todos os slides (ZIP)"
                className="flex h-8 w-8 items-center justify-center rounded-[var(--radius-md)] text-[var(--color-text-muted)] hover:bg-[var(--color-bg-muted)] hover:text-[var(--color-text-primary)] disabled:opacity-40"
              >
                {isDownloadingZip ? (
                  <InlineSpinner size={16} ariaLabel="A baixar" />
                ) : (
                  <IconDownload />
                )}
              </button>
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

        <div className="min-h-0 flex-1 overflow-y-auto">
          {!id ? (
            <EmptyChatState onChipClick={setupConfigured ? handleChipClick : undefined} />
          ) : chat.isLoading && !showJobLoading ? (
            <div className="flex items-center justify-center py-20">
              <InlineSpinner size={24} />
            </div>
          ) : (
            <ChatThread
              chat={chat.data}
              pendingText={showJobLoading ? (activeJob?.pendingText ?? null) : null}
              jobStatus={assistantThreadJobStatus}
              jobError={jobError}
              onRetry={jobError != null ? handleRetry : undefined}
            />
          )}
        </div>

        <div className="relative shrink-0">
          {showComposerHint && (
            <div className="px-4 pt-3">
              <div className="mx-auto w-full max-w-3xl">
                <OnboardingHint
                  id="chat-composer"
                  title="Comece por aqui"
                  description="Descreva o post que quer criar — tipo, tema, tom. A IA cuida do resto."
                  narrow={false}
                  arrowAlign="center"
                />
              </div>
            </div>
          )}
          <ComposerBar
            onSend={handleSend}
            disabled={showJobLoading || !setupConfigured}
          />
        </div>
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
