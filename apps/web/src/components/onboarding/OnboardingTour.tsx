import { useEffect, useRef } from 'react'

import { useOnboardingStore } from '@/stores/onboarding'

const STEPS: { title: string; description: string }[] = [
  {
    title: 'Bem-vindo ao Post Mind',
    description:
      'Crie posts para Instagram com IA em segundos, respeitando sua identidade de marca.',
  },
  {
    title: 'Configure seu perfil',
    description:
      'Antes de criar posts, preencha sua auditoria de marca e guia visual. O sistema usa essas informações para gerar conteúdo alinhado à sua identidade.',
  },
  {
    title: 'Crie seu post',
    description:
      'No chat, descreva em linguagem natural o post que deseja. A IA gera os slides HTML e os exporta em JPEG 1080×1350 prontos para o Instagram.',
  },
  {
    title: 'Baixe seus slides',
    description:
      'Após a geração, visualize os slides no chat e baixe o ZIP. Acesse posts anteriores pelo Histórico.',
  },
]

export function OnboardingTour() {
  const tourOpen = useOnboardingStore((s) => s.tourOpen)
  const tourStep = useOnboardingStore((s) => s.tourStep)
  const nextStep = useOnboardingStore((s) => s.nextStep)
  const prevStep = useOnboardingStore((s) => s.prevStep)
  const completeTour = useOnboardingStore((s) => s.completeTour)

  const primaryRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!tourOpen) return
    primaryRef.current?.focus()
  }, [tourOpen, tourStep])

  useEffect(() => {
    if (!tourOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        completeTour()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [tourOpen, completeTour])

  if (!tourOpen) return null

  const step = STEPS[tourStep]!
  const isLast = tourStep === STEPS.length - 1

  return (
    <div
      className="fixed inset-0 z-[70] flex items-center justify-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="onboarding-tour-title"
    >
      <div
        className="w-full max-w-md rounded-[var(--radius-lg)] bg-[var(--color-bg-surface)] p-6 shadow-[var(--shadow-md)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex justify-center text-[var(--color-brand-primary)]">
          <StepIcon step={tourStep} />
        </div>
        <h2
          id="onboarding-tour-title"
          className="text-center text-base font-semibold text-[var(--color-text-primary)]"
        >
          {step.title}
        </h2>
        <p className="mt-3 text-center text-sm text-[var(--color-text-secondary)]">{step.description}</p>

        <div className="mt-6 flex justify-center gap-2" aria-hidden>
          {STEPS.map((_, i) => (
            <span
              key={i}
              className={[
                'h-2 w-2 rounded-full transition-colors',
                i === tourStep
                  ? 'bg-[var(--color-brand-primary)]'
                  : 'bg-[var(--color-border-subtle)]',
              ].join(' ')}
            />
          ))}
        </div>

        <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
          <button
            type="button"
            onClick={completeTour}
            className="rounded-[var(--radius-md)] px-3 py-2 text-sm font-medium text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-muted)] hover:text-[var(--color-text-primary)]"
          >
            Pular
          </button>
          <div className="flex items-center gap-2">
            {tourStep > 0 && (
              <button
                type="button"
                onClick={prevStep}
                className="rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] px-4 py-2 text-sm font-medium text-[var(--color-text-primary)] hover:bg-[var(--color-bg-muted)]"
              >
                Anterior
              </button>
            )}
            <button
              ref={primaryRef}
              type="button"
              onClick={() => (isLast ? completeTour() : nextStep())}
              className="rounded-[var(--radius-md)] bg-[var(--color-brand-primary)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--color-brand-primary-hover)]"
            >
              {isLast ? 'Começar' : 'Próximo'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function StepIcon({ step }: { step: number }) {
  const common = { width: 48, height: 48, viewBox: '0 0 24 24' as const, fill: 'none' as const, 'aria-hidden': true }
  switch (step) {
    case 0:
      return (
        <svg {...common}>
          <path
            d="M12 3l7 4v6c0 5-3.5 8.5-7 10-3.5-1.5-7-5-7-10V7l7-4z"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
          <path
            d="M9 12l2 2 4-5"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      )
    case 1:
      return (
        <svg {...common}>
          <circle cx="12" cy="8" r="3.5" stroke="currentColor" strokeWidth="1.5" />
          <path
            d="M5.5 20.5v-.5c0-3 2.5-5.5 6.5-5.5s6.5 2.5 6.5 5.5v.5"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        </svg>
      )
    case 2:
      return (
        <svg {...common}>
          <path
            d="M8 10h8M8 14h5M5 5h14a1 1 0 011 1v12a1 1 0 01-1 1H5a1 1 0 01-1-1V6a1 1 0 011-1z"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        </svg>
      )
    default:
      return (
        <svg {...common}>
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
}
