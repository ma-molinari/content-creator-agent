import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { isAxiosError, type AxiosResponse } from 'axios'

import { api } from './client'

const JPEG_SOI_MARKER = Object.freeze([0xff, 0xd8, 0xff] as const)

/** Local file header start of a ZIP (PK\x03\x04). */
const ZIP_LOCAL_FILE_HEADER = Object.freeze([0x50, 0x4b, 0x03, 0x04] as const)

const ZIP_BLOB_INVALID_MSG =
  'A resposta do servidor não parece um ficheiro ZIP válido. Tente novamente.' as const

async function assertValidZipBlob(blob: Blob): Promise<void> {
  if (!(blob instanceof Blob) || blob.size === 0) {
    throw new Error(ZIP_BLOB_INVALID_MSG)
  }
  const head = await blob.slice(0, ZIP_LOCAL_FILE_HEADER.length).arrayBuffer()
  const bytes = new Uint8Array(head)
  for (let i = 0; i < ZIP_LOCAL_FILE_HEADER.length; i++) {
    if (bytes[i] !== ZIP_LOCAL_FILE_HEADER[i]) {
      throw new Error(ZIP_BLOB_INVALID_MSG)
    }
  }
}

/** User-facing errors for invalid slide payloads (routing/HTML/JSON posing as JPEG). */
const SLIDE_BLOB_INVALID_MSG = 'Resposta inválida ao carregar o slide.' as const

function normalizeContentType(raw: unknown): string | undefined {
  if (typeof raw !== 'string') return undefined
  const trimmed = raw.split(';')[0]?.trim().toLowerCase()
  return trimmed || undefined
}

function isClearlyNonImageContentType(ct: string): boolean {
  if (ct.startsWith('image/')) return false
  if (ct === 'application/octet-stream') return false
  return (
    ct.startsWith('text/') ||
    ct === 'application/json' ||
    ct.endsWith('+json') ||
    ct === 'application/xml' ||
    ct === 'text/xml'
  )
}

/**
 * Validates a successful blob response from GET `/chats/:id/files/:fileId` contains JPEG magic bytes.
 * Rejects SPA fallbacks/HTML/JSON and empty bodies even when status is 2xx.
 */
async function assertValidSlideJpegResponse(
  res: AxiosResponse<Blob>,
): Promise<Blob> {
  const { status, data: blob } = res
  if (status < 200 || status >= 300) {
    throw new Error(SLIDE_BLOB_INVALID_MSG)
  }
  if (!(blob instanceof Blob)) {
    throw new Error(SLIDE_BLOB_INVALID_MSG)
  }
  if (blob.size === 0) {
    throw new Error(SLIDE_BLOB_INVALID_MSG)
  }

  const ct = normalizeContentType(res.headers?.['content-type'])
  if (ct && isClearlyNonImageContentType(ct)) {
    throw new Error(SLIDE_BLOB_INVALID_MSG)
  }

  const head = await blob.slice(0, 3).arrayBuffer()
  const bytes = new Uint8Array(head)
  if (
    bytes.length < JPEG_SOI_MARKER.length ||
    bytes[0] !== JPEG_SOI_MARKER[0] ||
    bytes[1] !== JPEG_SOI_MARKER[1] ||
    bytes[2] !== JPEG_SOI_MARKER[2]
  ) {
    throw new Error(SLIDE_BLOB_INVALID_MSG)
  }

  return blob
}

export async function fetchChatSlideJpeg(
  chatId: string,
  fileId: string,
  signal?: AbortSignal,
): Promise<Blob> {
  const axiosRes = await api.get<Blob>(`/chats/${chatId}/files/${fileId}`, {
    responseType: 'blob',
    signal,
  })
  return assertValidSlideJpegResponse(axiosRes)
}

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

type ZipDownloadScope = 'chat' | 'message'

/** Generic HTTP 404 (e.g. Echo "Not Found") — user-facing fallback instead of the English body. */
const ZIP_404_ROUTE_OR_GENERIC_MSG =
  'Não foi possível iniciar o download. Tente novamente mais tarde.' as const

function mapZip404UserMessage(scope: ZipDownloadScope, serverMsg: string | null): string {
  const trimmed = typeof serverMsg === 'string' ? serverMsg.trim() : ''
  if (!trimmed || trimmed === 'no files') {
    return scope === 'chat'
      ? 'Não há ficheiros neste chat para baixar.'
      : 'Não há ficheiros nesta mensagem para baixar.'
  }
  if (trimmed.toLowerCase() === 'not found') {
    return ZIP_404_ROUTE_OR_GENERIC_MSG
  }
  return trimmed
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
    await assertValidZipBlob(res.data)
    return { blob: res.data, filename }
  } catch (err) {
    if (isAxiosError(err) && err.response?.data instanceof Blob) {
      const status = err.response.status
      const serverMsg = await messageFromErrorBlob(err.response.data)
      if (status === 404) {
        throw new Error(mapZip404UserMessage('chat', serverMsg))
      }
      throw new Error(serverMsg ?? 'Não foi possível baixar o ZIP. Tente novamente.')
    }
    throw new Error('Não foi possível baixar o ZIP. Tente novamente.')
  }
}

/**
 * Fetches a ZIP of slides for one assistant message. Rejects with Error (user-facing message) on failure.
 */
export async function downloadContentZip(
  chatId: string,
  contentId: string,
): Promise<{ blob: Blob; filename: string }> {
  try {
    const res = await api.get<Blob>(
      `/chats/${chatId}/contents/${contentId}/download`,
      { responseType: 'blob' },
    )
    const headerVal = res.headers['content-disposition']
    const fromHeader = parseFilenameFromContentDisposition(
      typeof headerVal === 'string' ? headerVal : undefined,
    )
    const filename = fromHeader ?? `slides-${contentId}.zip`
    await assertValidZipBlob(res.data)
    return { blob: res.data, filename }
  } catch (err) {
    if (isAxiosError(err) && err.response?.data instanceof Blob) {
      const status = err.response.status
      const serverMsg = await messageFromErrorBlob(err.response.data)
      if (status === 404) {
        throw new Error(mapZip404UserMessage('message', serverMsg))
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

export type ChatContentAttachment = {
  id: string
  url: string
  mimeType: string
  sortOrder: number
}

export type ChatContent = {
  id: string
  chatId: string
  role: 'user' | 'assistant'
  content: string
  createdAt: string
  updatedAt: string
  images: ChatContentImage[]
  attachments?: ChatContentAttachment[]
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

export async function postChatMessage(
  chatId: string,
  content: string,
  attachments?: File[],
): Promise<{ jobId: string }> {
  if (!attachments || attachments.length === 0) {
    const { data } = await api.post<{ jobId: string }>(
      `/chats/${chatId}/messages`,
      { content },
    )
    return data
  }
  const form = new FormData()
  form.append('content', content)
  for (const file of attachments) {
    form.append('attachments', file, file.name)
  }
  const { data } = await api.post<{ jobId: string }>(
    `/chats/${chatId}/messages`,
    form,
  )
  return data
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

const CHAT_PRESIGN_REFRESH_MS = 45 * 60 * 1000

export function useChat(id: string | undefined) {
  return useQuery({
    queryKey: ['chats', id],
    queryFn: () => api.get<Chat>(`/chats/${id}`).then((r) => r.data),
    enabled: !!id,
    staleTime: 0,
    refetchOnMount: 'always',
    refetchInterval: CHAT_PRESIGN_REFRESH_MS,
    refetchIntervalInBackground: false,
  })
}

export function useDeleteChat() {
  const qc = useQueryClient()
  return useMutation<void, Error, string>({
    mutationFn: (id) => api.delete(`/chats/${id}`).then(() => undefined),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['chats'] }),
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
      return s === 'done' || s === 'failed' ? false : 5_000
    },
    staleTime: 0,
  })
}

