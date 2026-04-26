import { useState, type MouseEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import type { Chat } from '@/api/chats'
import { fetchChatFilesZip, useChats, useDeleteChat } from '@/api/chats'
import { downloadBlob } from '@/lib/downloadBlob'
import { AlertDialog } from '@/components/ui/AlertDialog'
import { toast } from '@/lib/toast'

export default function History() {
  const { data: chats, isLoading } = useChats()
  const deleteChat = useDeleteChat()
  const navigate = useNavigate()

  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [confirmId, setConfirmId] = useState<string | null>(null)

  async function handleDelete() {
    if (!confirmId) return
    const id = confirmId
    setConfirmId(null)
    setDeletingId(id)
    try {
      await deleteChat.mutateAsync(id)
      toast.success('Chat excluído.')
    } catch {
      toast.error('Não foi possível excluir. Tente novamente.')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <>
      <div className="mx-auto max-w-3xl px-4 py-6">
        <div className="mb-6 flex items-center gap-3">
          <Link
            to="/"
            className="text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
          >
            ← Início
          </Link>
          <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">Histórico</h1>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-16">
            <Spinner />
          </div>
        ) : !chats || chats.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <p className="text-[var(--color-text-secondary)]">Nenhum post criado ainda.</p>
            <Link
              to="/"
              className="mt-3 text-sm font-medium text-[var(--color-brand-primary)] hover:text-[var(--color-brand-primary-hover)]"
            >
              Comece pelo chat →
            </Link>
          </div>
        ) : (
          <ul className="flex flex-col gap-2">
            {chats.map((chat) => (
              <ChatListItem
                key={chat.id}
                chat={chat}
                deleting={deletingId === chat.id}
                onOpen={() => navigate(`/chat/${chat.id}`)}
                onDelete={() => setConfirmId(chat.id)}
              />
            ))}
          </ul>
        )}
      </div>

      <AlertDialog
        open={!!confirmId}
        title="Excluir chat"
        description="Esta ação não pode ser desfeita. O chat e todos os slides gerados serão removidos permanentemente."
        confirmLabel="Excluir"
        loading={deleteChat.isPending}
        onConfirm={handleDelete}
        onCancel={() => setConfirmId(null)}
      />
    </>
  )
}

type ChatListItemProps = {
  chat: Chat
  deleting: boolean
  onOpen: () => void
  onDelete: () => void
}

function ChatListItem({ chat, deleting, onOpen, onDelete }: ChatListItemProps) {
  const [isDownloadingZip, setIsDownloadingZip] = useState(false)

  async function handleDownloadZip(e: MouseEvent<HTMLButtonElement>) {
    e.stopPropagation()
    if (isDownloadingZip) return
    setIsDownloadingZip(true)
    try {
      const { blob, filename } = await fetchChatFilesZip(chat.id)
      downloadBlob(blob, filename)
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : 'Não foi possível baixar o ZIP. Tente novamente.'
      toast.error(msg)
    } finally {
      setIsDownloadingZip(false)
    }
  }

  const date = new Date(chat.createdAt).toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
  const postTypeLabel = chat.postType === 'carousel' ? 'Carrossel' : 'Post único'
  const title = chat.title ?? 'Chat sem título'

  return (
    <li className="flex items-center gap-3 rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] px-4 py-3 transition-shadow hover:shadow-[var(--shadow-sm)]">
      <button
        type="button"
        onClick={onOpen}
        className="flex flex-1 flex-col items-start gap-0.5 text-left"
      >
        <span className="line-clamp-1 text-sm font-medium text-[var(--color-text-primary)]">
          {title}
        </span>
        <span className="text-xs text-[var(--color-text-muted)]">
          {postTypeLabel} · {date}
        </span>
      </button>

      <button
        type="button"
        onClick={(e) => void handleDownloadZip(e)}
        disabled={isDownloadingZip}
        title="Baixar ZIP"
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[var(--radius-md)] text-[var(--color-text-muted)] hover:bg-[var(--color-bg-muted)] hover:text-[var(--color-text-primary)] disabled:opacity-40"
      >
        {isDownloadingZip ? <Spinner size={14} /> : <IconDownload />}
      </button>

      <button
        type="button"
        onClick={onDelete}
        disabled={deleting}
        title="Excluir"
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[var(--radius-md)] text-[var(--color-text-muted)] hover:bg-red-50 hover:text-red-600 disabled:opacity-40 dark:hover:bg-red-900/20"
      >
        {deleting ? <Spinner size={14} /> : <IconTrash />}
      </button>
    </li>
  )
}

function Spinner({ size = 20 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      aria-label="Carregando"
      className="animate-spin"
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
