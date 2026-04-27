import { useState } from 'react'
import { Outlet } from 'react-router-dom'

import { SidebarRail } from '@/components/shell/SidebarRail'

export function AppShell() {
  const [drawerOpen, setDrawerOpen] = useState(false)

  return (
    <div className="flex h-dvh min-h-0 w-full bg-[var(--color-bg-app)]">
      {/* Desktop sidebar */}
      <div className="hidden min-h-0 md:flex md:shrink-0">
        <SidebarRail />
      </div>

      {/* Mobile drawer backdrop */}
      {drawerOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/40 md:hidden"
          onClick={() => setDrawerOpen(false)}
          aria-hidden
        />
      )}

      {/* Mobile sidebar drawer */}
      <div
        className={[
          'fixed inset-y-0 left-0 z-40 transition-transform duration-[var(--transition-normal)] md:hidden',
          drawerOpen ? 'translate-x-0' : '-translate-x-full',
        ].join(' ')}
      >
        <SidebarRail onClose={() => setDrawerOpen(false)} />
      </div>

      <main className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        {/* Desktop-only notice (mobile viewports) */}
        <div
          className="shrink-0 border-b border-amber-200/80 bg-amber-50/90 px-4 py-2.5 text-sm text-amber-900 dark:border-amber-800/60 dark:bg-amber-950/30 dark:text-amber-200 md:hidden"
          role="status"
        >
          <p className="flex items-start gap-2">
            <span className="mt-0.5 shrink-0" aria-hidden>
              <IconDesktopHint />
            </span>
            <span>
              Esta aplicação foi pensada para ecrãs maiores. Para uma experiência completa, aceda
              a partir de um computador ou tablet.
            </span>
          </p>
        </div>
        {/* Mobile top bar */}
        <div className="flex shrink-0 items-center gap-3 border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] px-4 py-3 md:hidden">
          <button
            type="button"
            onClick={() => setDrawerOpen(true)}
            aria-label="Abrir menu"
            className="rounded-[var(--radius-sm)] p-1 text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-muted)]"
          >
            <IconMenu />
          </button>
          <span className="text-sm font-semibold text-[var(--color-text-primary)]">
            Content Creator
          </span>
        </div>
        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          <Outlet />
        </div>
      </main>
    </div>
  )
}

function IconDesktopHint() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect
        x="2.5"
        y="3.5"
        width="19"
        height="14"
        rx="1.5"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      <path d="M8 21h8M12 18v3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  )
}

function IconMenu() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M4 6h16M4 12h16M4 18h16"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  )
}
