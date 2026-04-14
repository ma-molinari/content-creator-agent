import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from './client'

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

// ── Files ──────────────────────────────────────────────────────────────────

export function useFiles(chatId: string | undefined) {
  return useQuery({
    queryKey: ['files', chatId],
    queryFn: () =>
      api.get<FileListItem[]>(`/chats/${chatId}/files`).then((r) => r.data),
    enabled: !!chatId,
    staleTime: 5 * 60_000,
  })
}
