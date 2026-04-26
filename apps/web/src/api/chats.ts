import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { isAxiosError } from 'axios'

import { api } from './client'

function parseFilenameFromContentDisposition(header: string | undefined): string | null {
  if (!header) return null
  const quoted = /filename="([^"]+)"/i.exec(header)
  if (quoted?.[1]) return quoted[1]
  const unquoted = /filename=([^;\s]+)/i.exec(header)
  if (unquoted?.[1]) return unquoted[1].replace(/^"|"$/g, '')
  return null
}

async function messageFromErrorBlob(blob: Blob): Promise<string | null> {
  try {
    const text = await blob.text()
    const parsed = JSON.parse(text) as { message?: string }
    return typeof parsed.message === 'string' ? parsed.message : null
  } catch {
    return null
  }
}

/**
 * Fetches the chat slides ZIP with auth. Rejects with Error (user-facing message) on failure.
 */
export async function fetchChatFilesZip(
  chatId: string,
): Promise<{ blob: Blob; filename: string }> {
  try {
    const res = await api.get<Blob>(`/chats/${chatId}/files/download`, {
      responseType: 'blob',
    })
    const headerVal = res.headers['content-disposition']
    const fromHeader = parseFilenameFromContentDisposition(
      typeof headerVal === 'string' ? headerVal : undefined,
    )
    const filename = fromHeader ?? `slides-${chatId}.zip`
    return { blob: res.data, filename }
  } catch (err) {
    if (isAxiosError(err) && err.response?.data instanceof Blob) {
      const status = err.response.status
      const serverMsg = await messageFromErrorBlob(err.response.data)
      if (status === 404) {
        throw new Error(
          serverMsg === 'no files' || !serverMsg
            ? 'Não há ficheiros neste chat para baixar.'
            : serverMsg,
        )
      }
      throw new Error(serverMsg ?? 'Não foi possível baixar o ZIP. Tente novamente.')
    }
    throw new Error('Não foi possível baixar o ZIP. Tente novamente.')
  }
}

// ── Types ──────────────────────────────────────────────────────────────────

export type ChatContentImage = {
  id: string
  chatContentId: string
  s3Key: string
  url: string
  slideNumber: number
  createdAt: string
  updatedAt: string
}

export type ChatContent = {
  id: string
  chatId: string
  role: 'user' | 'assistant'
  content: string
  createdAt: string
  updatedAt: string
  images: ChatContentImage[]
}

export type Chat = {
  id: string
  userId: string
  postType: 'single' | 'carousel'
  title: string | null
  createdAt: string
  updatedAt: string
  contents: ChatContent[]
}

export type FileListItem = {
  id: string
  fileName: string
  mimeType: string
  downloadUrl: string
}

export type JobStatus = 'pending' | 'processing' | 'done' | 'failed'

export type JobStatusView = {
  jobId: string
  status: JobStatus
  error: string | null
}

// ── Setup ──────────────────────────────────────────────────────────────────

export function useSetupStatus() {
  return useQuery({
    queryKey: ['setup-status'],
    queryFn: () =>
      api.get<{ configured: boolean }>('/setup/status').then((r) => r.data),
    staleTime: 60_000,
  })
}

// ── Chats CRUD ─────────────────────────────────────────────────────────────

export function useChats() {
  return useQuery({
    queryKey: ['chats'],
    queryFn: () => api.get<Chat[]>('/chats').then((r) => r.data),
    staleTime: 30_000,
  })
}

export function useChat(id: string | undefined) {
  return useQuery({
    queryKey: ['chats', id],
    queryFn: () => api.get<Chat>(`/chats/${id}`).then((r) => r.data),
    enabled: !!id,
    staleTime: 30_000,
  })
}

export function useCreateChat() {
  const qc = useQueryClient()
  return useMutation<Chat, Error, { postType: 'single' | 'carousel' }>({
    mutationFn: (vars) => api.post<Chat>('/chats', vars).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['chats'] }),
  })
}

export function useDeleteChat() {
  const qc = useQueryClient()
  return useMutation<void, Error, string>({
    mutationFn: (id) => api.delete(`/chats/${id}`).then(() => undefined),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['chats'] }),
  })
}

// ── Messages ───────────────────────────────────────────────────────────────

type PostMessageResult = { jobId: string }

export function usePostMessage() {
  return useMutation<PostMessageResult, Error, { chatId: string; content: string }>({
    mutationFn: ({ chatId, content }) =>
      api
        .post<PostMessageResult>(`/chats/${chatId}/messages`, { content })
        .then((r) => r.data),
  })
}

// ── Job status (polling) ───────────────────────────────────────────────────

export function useJobStatus(chatId: string | null, jobId: string | null) {
  return useQuery({
    queryKey: ['job-status', chatId, jobId],
    queryFn: () =>
      api
        .get<JobStatusView>(`/chats/${chatId}/jobs/${jobId}/status`)
        .then((r) => r.data),
    enabled: !!chatId && !!jobId,
    refetchInterval: (query) => {
      const s = query.state.data?.status
      return s === 'done' || s === 'failed' ? false : 1_500
    },
    staleTime: 0,
  })
}

