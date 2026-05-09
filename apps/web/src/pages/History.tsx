import { useState, type MouseEvent, type ReactNode } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import type { Chat } from '@/api/chats'
import { fetchChatFilesZip, useChats, useDeleteChat } from '@/api/chats'
import { IconDownload, IconTrash } from '@/components/ui/action-icons'
import { InlineSpinner } from '@/components/ui/InlineSpinner'
import { downloadBlob } from '@/lib/downloadBlob'
import { OnboardingHint } from '@/components/onboarding'
import { AlertDialog } from '@/components/ui/AlertDialog'
import { toast } from '@/lib/toast'

export default function History() {
  const { data: chats, isLoading } = useChats()
  const deleteChat = useDeleteChat()
  const navigate = useNavigate()

  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [confirmId, setConfirmId] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState<'all' | 'single' | 'carousel'>('all')

  const filteredChats =
    chats?.filter((chat) => {
      const matchesType = typeFilter === 'all' || chat.postType === typeFilter
      const title = chat.title ?? 'Chat sem título'
      const matchesQuery = title.toLowerCase().includes(query.trim().toLowerCase())
      return matchesType && matchesQuery
    }) ?? []

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
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <div className="min-h-0 max-h-full flex-initial overflow-y-auto">
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
                <InlineSpinner />
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
              <>
                <OnboardingHint
                  id="history-list"
                  title="Os seus posts"
                  description="Aqui ficam todos os seus posts anteriores. Abra qualquer um para rever os slides ou baixar o ZIP."
                />
                <div className="mb-4 rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] p-3">
                  <div className="flex flex-col gap-3 sm:flex-row">
                    <input
                      type="search"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="Buscar por título"
                      className="min-w-0 flex-1 rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-app)] px-3 py-2 text-sm text-[var(--color-text-primary)] outline-none focus:ring-2 focus:ring-[var(--color-focus-ring)]"
                    />
                    <div className="inline-flex rounded-[var(--radius-md)] bg-[var(--color-bg-muted)] p-1">
                      <FilterButton active={typeFilter === 'all'} onClick={() => setTypeFilter('all')}>
                        Todos
                      </FilterButton>
                      <FilterButton active={typeFilter === 'carousel'} onClick={() => setTypeFilter('carousel')}>
                        Carrosséis
                      </FilterButton>
                      <FilterButton active={typeFilter === 'single'} onClick={() => setTypeFilter('single')}>
                        Únicos
                      </FilterButton>
                    </div>
                  </div>
                </div>
                {filteredChats.length === 0 ? (
                  <p className="rounded-[var(--radius-md)] bg-[var(--color-bg-surface)] px-4 py-8 text-center text-sm text-[var(--color-text-secondary)]">
                    Nenhum post encontrado com esses filtros.
                  </p>
                ) : (
                  <ul className="flex flex-col gap-2">
                    {filteredChats.map((chat) => (
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
              </>
            )}
          </div>
        </div>
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

type FilterButtonProps = {
  active: boolean
  onClick: () => void
  children: ReactNode
}

function FilterButton({ active, onClick, children }: FilterButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        'rounded-[calc(var(--radius-md)-2px)] px-3 py-1.5 text-xs font-medium transition-colors',
        active
          ? 'bg-[var(--color-bg-surface)] text-[var(--color-text-primary)] shadow-[var(--shadow-sm)]'
          : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]',
      ].join(' ')}
    >
      {children}
    </button>
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
        {isDownloadingZip ? <InlineSpinner size={14} ariaLabel="A baixar" /> : <IconDownload />}
      </button>

      <button
        type="button"
        onClick={onDelete}
        disabled={deleting}
        title="Excluir"
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[var(--radius-md)] text-[var(--color-text-muted)] hover:bg-red-50 hover:text-red-600 disabled:opacity-40 dark:hover:bg-red-900/20"
      >
        {deleting ? <InlineSpinner size={14} /> : <IconTrash />}
      </button>
    </li>
  )
}
