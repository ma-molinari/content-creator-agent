import { NavItem } from '@/components/shell/NavItem'

type Props = {
  onClose?: () => void
}

export function SidebarRail({ onClose }: Props) {
  return (
    <aside
      className="flex h-full w-[220px] shrink-0 flex-col border-r border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)]"
      aria-label="Navegação principal"
    >
      <div className="flex items-center justify-between p-4">
        <span className="text-sm font-semibold text-[var(--color-text-primary)]">
          Content Creator
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
      <nav className="flex flex-1 flex-col gap-1 px-3 py-2">
        <NavItem to="/" icon={<IconHome />} label="Início" end />
        <NavItem to="/history" icon={<IconHistory />} label="Histórico" />
      </nav>
      <div className="border-t border-[var(--color-border-subtle)] p-3">
        <div
          className="flex h-10 w-10 items-center justify-center rounded-full bg-[var(--color-bg-muted)] text-xs font-medium text-[var(--color-text-secondary)]"
          aria-hidden
        >
          U
        </div>
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

function IconX() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  )
}
