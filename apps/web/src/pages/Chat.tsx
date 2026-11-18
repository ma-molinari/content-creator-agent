import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { type QueryClient, useQueryClient } from '@tanstack/react-query'
import { isAxiosError } from 'axios'

import { api } from '@/api/client'
import type { Chat as ChatType, GenerationOptions, JobStatus } from '@/api/chats'
import {
  fetchChatFilesZip,
  postChatMessage,
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
  generation?: GenerationOptions
  pendingAttachments: { id: string; url: string; mimeType: string; file?: File }[]
}

function normalizeActiveJob(
  job: Pick<ActiveJob, 'chatId' | 'jobId' | 'pendingText'> & {
    pendingAttachments?: ActiveJob['pendingAttachments']
  },
): ActiveJob {
  return {
    ...job,
    pendingAttachments: job.pendingAttachments ?? [],
  }
}

type LastJobFailure = {
  error: string
  errorCode?: string | null
  generation?: GenerationOptions
  pendingText: string
  pendingAttachments: ActiveJob['pendingAttachments']
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
  if (!raw) return null
  return normalizeActiveJob(raw)
}

function activeJobForChat(
  chatId: string,
  fromRouter: ActiveJob | null,
  fromCache: ActiveJob | null,
): ActiveJob | null {
  if (fromRouter?.chatId === chatId) return normalizeActiveJob(fromRouter)
  if (fromCache?.chatId === chatId) return normalizeActiveJob(fromCache)
  return null
}

const UNKNOWN_JOB_ERROR = 'Erro desconhecido'

function messageFromApiError(err: unknown, fallback: string): string {
  if (isAxiosError(err)) {
    const data = err.response?.data as { message?: string | { message?: string } } | undefined
    const message = typeof data?.message === 'string' ? data.message : data?.message?.message
    if (message) return message
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
  const activeJobRef = useRef<ActiveJob | null>(null)

  const [activeJob, setActiveJob] = useState<ActiveJob | null>(null)
  activeJobRef.current = activeJob
  const [lastJobFailure, setLastJobFailure] = useState<LastJobFailure | null>(null)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [isDownloadingZip, setIsDownloadingZip] = useState(false)
  const [draftPostType, setDraftPostType] = useState<'single' | 'carousel'>('carousel')
  const [generationMode, setGenerationMode] = useState<'create' | 'edit'>('edit')

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

  useEffect(() => {
    return () => {
      activeJobRef.current?.pendingAttachments?.forEach((a) => URL.revokeObjectURL(a.url))
    }
  }, [])

  /** Apply route transition + hydrate `activeJob` before paint so the first `/chat/:id` frame tracks the new job (lazy route + stripping `location.state`). */
  useLayoutEffect(() => {
    const prev = prevChatIdRef.current
    if (prev !== undefined && prev !== id) {
      setGenerationMode('edit')
      setActiveJob((current) => {
        if (current?.chatId === prev) {
          current.pendingAttachments?.forEach((a) => URL.revokeObjectURL(a.url))
          return null
        }
        return current
      })
      const cached = qc.getQueryData<ActiveJob>(activeJobHydrateKey(prev))
      cached?.pendingAttachments?.forEach((a) => URL.revokeObjectURL(a.url))
      qc.removeQueries({ queryKey: activeJobHydrateKey(prev), exact: true })
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

    const clearActiveJobSoon = (job: ActiveJob | null, hydrateId: string | undefined) => {
      queueMicrotask(() => {
        job?.pendingAttachments?.forEach((a) => URL.revokeObjectURL(a.url))
        removeActiveJobHydrate(qc, hydrateId)
        setActiveJob(null)
      })
    }

    if (currentStatus === 'done') {
      const hydrateId = activeJob?.chatId
      const jobSnapshot = activeJob
      if (activeJob) {
        void qc.invalidateQueries({ queryKey: ['chats', activeJob.chatId] })
        setLastJobFailure(null)
      }
      clearActiveJobSoon(jobSnapshot, hydrateId)
    } else if (currentStatus === 'failed' && activeJob) {
      const err = jobStatus.data?.error ?? UNKNOWN_JOB_ERROR
      const hydrateId = activeJob.chatId
      const jobSnapshot = activeJob
      setLastJobFailure({
        error: err,
        errorCode: jobStatus.data?.errorCode,
        generation: activeJob.generation,
        pendingText: activeJob.pendingText,
        pendingAttachments: activeJob.pendingAttachments,
      })
      if (jobStatus.data?.errorCode === 'VERSION_CONFLICT') {
        void qc.invalidateQueries({ queryKey: ['chats', activeJob.chatId] })
      }
      toast.error('Não foi possível gerar o post.')
      clearActiveJobSoon(jobSnapshot, hydrateId)
    }
  }, [currentStatus, activeJob, qc, jobStatus.data?.error, jobStatus.data?.errorCode])

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
    async (
      text: string,
      files: File[],
      options?: { postType?: 'single' | 'carousel'; generation?: GenerationOptions },
    ) => {
      const postTypeForNew = options?.postType ?? 'carousel'
      let chatId = id
      let postFormat = chat.data?.postFormat
      let currentVersionId = chat.data?.currentVersionId

      if (!chatId) {
        try {
          const { data: newChat } = await api.post<ChatType>('/chats', {
            postType: postTypeForNew,
          })
          chatId = newChat.id
          postFormat = newChat.postFormat
          currentVersionId = newChat.currentVersionId
          void qc.invalidateQueries({ queryKey: ['chats'] })
        } catch (err) {
          toast.error(messageFromApiError(err, 'Não foi possível criar o chat.'))
          throw err
        }
      }

      setLastJobFailure(null)

      const pendingAttachments = files.map((f) => ({
        id: crypto.randomUUID(),
        url: URL.createObjectURL(f),
        mimeType: f.type,
        file: f,
      }))

      const generation: GenerationOptions | undefined = options?.generation ??
        (postFormat === 'structured_v1'
          ? (currentVersionId && generationMode === 'edit'
            ? { mode: 'edit', baseVersionId: currentVersionId }
            : { mode: 'create' })
          : undefined)
      let jobId: string
      try {
        const data = await postChatMessage(chatId, text, files, generation)
        jobId = data.jobId
      } catch (err) {
        pendingAttachments.forEach((a) => URL.revokeObjectURL(a.url))
        if (isAxiosError(err) && err.response?.status === 409) {
          void qc.invalidateQueries({ queryKey: ['chats', chatId] })
        }
        toast.error(
          messageFromApiError(
            err,
            'Não foi possível enviar a mensagem. Você pode tentar novamente.',
          ),
        )
        throw err
      }

      void qc.invalidateQueries({ queryKey: ['chats', chatId] })

      const pending: ActiveJob = { chatId, jobId, pendingText: text, pendingAttachments, generation }
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
    [id, navigate, qc, chat.data?.postFormat, chat.data?.currentVersionId, generationMode],
  )

  const handleChipClick = useCallback(
    (text: string, postType: 'single' | 'carousel') => {
      setDraftPostType(postType)
      void handleSend(text, [], { postType }).catch(() => undefined)
    },
    [handleSend],
  )

  const handleRetry = useCallback(() => {
    const failure = lastJobFailure
    if (!failure || !id) return
    const files = failure.pendingAttachments.map((a) => a.file).filter((file): file is File => file instanceof File)
    const retry = async () => {
      let generation = failure.generation
      if (failure.errorCode === 'VERSION_CONFLICT' && generation?.mode === 'edit') {
        const latest = await qc.fetchQuery({
          queryKey: ['chats', id],
          queryFn: () => api.get<ChatType>(`/chats/${id}`).then((response) => response.data),
          staleTime: 0,
        })
        if (!latest.currentVersionId) throw new Error('A versão atual não está disponível.')
        generation = { mode: 'edit', baseVersionId: latest.currentVersionId }
      }
      await handleSend(failure.pendingText, files, { generation })
    }
    void retry().catch((err: unknown) => toast.error(messageFromApiError(err, 'Não foi possível reenviar a mensagem.')))
  }, [id, lastJobFailure, handleSend, qc])

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
            setupConfigured ? (
              <EmptyChatState onChipClick={handleChipClick} />
            ) : (
              <SetupRequiredState />
            )
          ) : chat.isLoading && !showJobLoading ? (
            <div className="flex items-center justify-center py-20">
              <InlineSpinner size={24} />
            </div>
          ) : (
            <ChatThread
              chat={chat.data}
              pendingText={showJobLoading ? (activeJob?.pendingText ?? null) : null}
              pendingAttachments={
                showJobLoading ? (activeJob?.pendingAttachments ?? []) : undefined
              }
              jobStatus={assistantThreadJobStatus}
              jobStage={jobStatus.data?.stage}
              jobProgress={jobStatus.data?.progress}
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
          {id && chat.data?.postFormat === 'structured_v1' && chat.data.currentVersionId && (
            <fieldset className="mx-auto mb-2 flex max-w-3xl gap-4 px-4 text-sm text-[var(--color-text-secondary)]" disabled={showJobLoading}>
              <legend className="sr-only">Ação no post</legend>
              <label><input type="radio" name="generation-mode" checked={generationMode === 'edit'} onChange={() => setGenerationMode('edit')} /> Editar versão atual</label>
              <label><input type="radio" name="generation-mode" checked={generationMode === 'create'} onChange={() => setGenerationMode('create')} /> Criar novo post</label>
            </fieldset>
          )}
          <ComposerBar
            onSend={(text, files, options) => handleSend(text, files, options)}
            disabled={showJobLoading || !setupConfigured}
            placeholder={
              setupConfigured
                ? 'Descreva o post que você quer criar…'
                : 'Complete o perfil da marca para liberar o chat'
            }
            postType={id ? (chat.data?.postType ?? draftPostType) : draftPostType}
            onPostTypeChange={setDraftPostType}
            lockedPostType={!!id && !!chat.data}
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

function SetupRequiredState() {
  return (
    <div className="flex min-h-full flex-col items-center justify-center px-6 py-12 text-center">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
        <IconProfile />
      </div>
      <h1 className="text-2xl font-semibold text-[var(--color-text-primary)]">
        Configure sua marca primeiro
      </h1>
      <p className="mt-2 max-w-md text-sm text-[var(--color-text-secondary)]">
        O Post Mind precisa da auditoria do perfil e do guia de marca para gerar posts alinhados ao seu tom, público e visual.
      </p>
      <Link
        to="/profile"
        className="mt-6 rounded-[var(--radius-md)] bg-[var(--color-brand-primary)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--color-brand-primary-hover)]"
      >
        Configurar perfil da marca
      </Link>
    </div>
  )
}

function IconProfile() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="8" r="3.5" stroke="currentColor" strokeWidth="1.5" />
      <path
        d="M5.5 20.5v-.5c0-3 2.5-5.5 6.5-5.5s6.5 2.5 6.5 5.5v.5"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  )
}
