import { NavLink } from 'react-router-dom'

type Props = {
  to: string
  icon: React.ReactNode
  label: string
  end?: boolean
}

export function NavItem({ to, icon, label, end }: Props) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        [
          'flex items-center gap-3 rounded-[var(--radius-md)] px-3 py-2 text-sm font-medium transition-[background,color] duration-[var(--transition-fast)]',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-focus-ring)]',
          isActive
            ? 'bg-[var(--color-nav-active-bg)] text-[var(--color-nav-active-fg)]'
            : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-muted)] hover:text-[var(--color-text-primary)]',
        ].join(' ')
      }
    >
      <span className="flex h-8 w-8 shrink-0 items-center justify-center">{icon}</span>
      <span>{label}</span>
    </NavLink>
  )
}
