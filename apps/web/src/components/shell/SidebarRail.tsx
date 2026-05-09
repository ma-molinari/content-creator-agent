import { useNavigate } from 'react-router-dom'

import { logoutRemote } from '@/api/auth'
import { useChats } from '@/api/chats'
import { HelpButton } from '@/components/onboarding'
import { NavItem } from '@/components/shell/NavItem'
import { queryClient } from '@/lib/queryClient'
import { useAuthStore } from '@/stores/auth'

type Props = {
  onClose?: () => void
}

export function SidebarRail({ onClose }: Props) {
  const navigate = useNavigate()
  const { data: chats } = useChats()
  const recentChats = chats?.slice(0, 4) ?? []

  const handleLogout = async () => {
    try {
      await logoutRemote()
    } finally {
      queryClient.clear()
      useAuthStore.getState().clear()
      navigate('/login', { replace: true })
    }
  }

  return (
    <aside
      className="flex h-full w-[220px] shrink-0 flex-col border-r border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)]"
      aria-label="Navegação principal"
    >
      <div className="flex items-center justify-between p-4">
        <span className="text-sm font-semibold text-[var(--color-text-primary)]">
          Post Mind
        </span>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            aria-label="Fechar menu"
            className="rounded-[var(--radius-sm)] p-1 text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"
          >
            <IconX />
          </button>
        )}
      </div>
      <div className="px-3 pb-2">
        <button
          type="button"
          onClick={() => {
            navigate('/')
            onClose?.()
          }}
          className="flex w-full items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-cta-emphasis)] px-3 py-2 text-sm font-medium text-[var(--color-cta-emphasis-contrast)] hover:opacity-90"
        >
          Novo post
        </button>
      </div>
      <nav className="flex flex-col gap-1 px-3 py-2">
        <NavItem to="/" icon={<IconHome />} label="Início" end />
        <NavItem to="/history" icon={<IconHistory />} label="Histórico" />
        <NavItem to="/profile" icon={<IconUser />} label="Perfil" />
      </nav>
      <div className="min-h-0 flex-1 overflow-y-auto px-3 py-3">
        <div className="mb-2 flex items-center justify-between">
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--color-text-muted)]">
            Recentes
          </p>
          {recentChats.length > 0 && (
            <button
              type="button"
              onClick={() => {
                navigate('/history')
                onClose?.()
              }}
              className="text-xs font-medium text-[var(--color-brand-primary)] hover:text-[var(--color-brand-primary-hover)]"
            >
              Ver todos
            </button>
          )}
        </div>
        {recentChats.length === 0 ? (
          <p className="rounded-[var(--radius-md)] bg-[var(--color-bg-muted)] px-3 py-2 text-xs text-[var(--color-text-secondary)]">
            Seus posts aparecerão aqui.
          </p>
        ) : (
          <ul className="flex flex-col gap-1">
            {recentChats.map((chat) => (
              <li key={chat.id}>
                <button
                  type="button"
                  onClick={() => {
                    navigate(`/chat/${chat.id}`)
                    onClose?.()
                  }}
                  className="w-full rounded-[var(--radius-md)] px-3 py-2 text-left hover:bg-[var(--color-bg-muted)]"
                >
                  <span className="line-clamp-1 text-xs font-medium text-[var(--color-text-primary)]">
                    {chat.title ?? 'Chat sem título'}
                  </span>
                  <span className="text-[11px] text-[var(--color-text-muted)]">
                    {chat.postType === 'carousel' ? 'Carrossel' : 'Post único'}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="flex min-h-[var(--app-bottom-shelf-min-height)] items-center gap-1 border-t border-[var(--color-border-subtle)] p-3">
        <HelpButton />
        <button
          type="button"
          onClick={handleLogout}
          aria-label="Sair"
          className="flex h-10 w-10 shrink-0 cursor-pointer items-center justify-center rounded-[var(--radius-md)] text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-bg-muted)] hover:text-[var(--color-text-primary)]"
        >
          <IconLogout />
        </button>
      </div>
    </aside>
  )
}

function IconHome() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M4 10.5L12 4l8 6.5V20a1 1 0 01-1 1h-5v-6H10v6H5a1 1 0 01-1-1v-9.5z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function IconHistory() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.5" />
      <path d="M12 7v6l4 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  )
}

function IconUser() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
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

function IconX() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  )
}

function IconLogout() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M16 17l5-5-5-5M21 12H9"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
