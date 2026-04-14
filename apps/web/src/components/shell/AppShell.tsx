import { useState } from 'react'
import { Outlet } from 'react-router-dom'

import { SidebarRail } from '@/components/shell/SidebarRail'

export function AppShell() {
  const [drawerOpen, setDrawerOpen] = useState(false)

  return (
    <div className="flex min-h-dvh w-full bg-[var(--color-bg-app)]">
      {/* Desktop sidebar */}
      <div className="hidden md:flex md:shrink-0">
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

      <main className="flex min-w-0 flex-1 flex-col overflow-auto">
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
        <Outlet />
      </main>
    </div>
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
