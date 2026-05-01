import { useOnboardingStore } from '@/stores/onboarding'

export function HelpButton() {
  const openTour = useOnboardingStore((s) => s.openTour)

  return (
    <button
      type="button"
      onClick={openTour}
      title="Ajuda / Como usar"
      aria-label="Ajuda / Como usar"
      className="flex h-10 w-10 shrink-0 cursor-pointer items-center justify-center rounded-[var(--radius-md)] text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-bg-muted)] hover:text-[var(--color-text-primary)]"
    >
      <IconHelp />
    </button>
  )
}

function IconHelp() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.5" />
      <path
        d="M9.5 9.5a2.5 2.5 0 015 0c0 2-2.5 1.5-2.5 3.5M12 17h.01"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  )
}
