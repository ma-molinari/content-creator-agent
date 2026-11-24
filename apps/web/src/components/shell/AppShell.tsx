import { useState } from 'react'
import { Outlet } from 'react-router-dom'

import { OnboardingTour } from '@/components/onboarding'
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
      {drawerOpen && (
        <div className="fixed inset-y-0 left-0 z-40 transition-transform duration-[var(--transition-normal)] md:hidden">
          <SidebarRail onClose={() => setDrawerOpen(false)} />
        </div>
      )}

      <main className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
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
            Post Mind
          </span>
        </div>
        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          <Outlet />
        </div>
        <p className="shrink-0 border-t border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] px-4 py-2 text-center text-xs text-[var(--color-text-secondary)]">
          Post Mind usa o{' '}
          <a className="underline" href="https://openverse.org/" target="_blank" rel="noopener noreferrer">Openverse</a>
          {' '}e não é endossado nem certificado por ele.
        </p>
      </main>
      <OnboardingTour />
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
