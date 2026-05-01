import { create } from 'zustand'

const STORAGE_TOUR_DONE = 'onboarding:tour_done'
const hintStorageKey = (id: string) => `onboarding:hint:${id}`

function readTourDone(): boolean {
  try {
    return localStorage.getItem(STORAGE_TOUR_DONE) === '1'
  } catch {
    return false
  }
}

function readDismissedHints(): Set<string> {
  const next = new Set<string>()
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i)
      if (k?.startsWith('onboarding:hint:') && localStorage.getItem(k) === '1') {
        next.add(k.slice('onboarding:hint:'.length))
      }
    }
  } catch {
    // ignore
  }
  return next
}

const tourDoneInitial = readTourDone()
const dismissedInitial = readDismissedHints()

type OnboardingState = {
  tourDone: boolean
  dismissedHints: Set<string>
  tourOpen: boolean
  tourStep: number
  openTour: () => void
  closeTour: () => void
  nextStep: () => void
  prevStep: () => void
  completeTour: () => void
  dismissHint: (id: string) => void
  isHintDismissed: (id: string) => boolean
}

export const useOnboardingStore = create<OnboardingState>((set, get) => ({
  tourDone: tourDoneInitial,
  dismissedHints: dismissedInitial,
  tourOpen: !tourDoneInitial,
  tourStep: 0,

  openTour: () => set({ tourOpen: true, tourStep: 0 }),

  closeTour: () => set({ tourOpen: false }),

  nextStep: () => {
    const { tourStep } = get()
    if (tourStep < 3) set({ tourStep: tourStep + 1 })
  },

  prevStep: () => {
    const { tourStep } = get()
    if (tourStep > 0) set({ tourStep: tourStep - 1 })
  },

  completeTour: () => {
    try {
      localStorage.setItem(STORAGE_TOUR_DONE, '1')
    } catch {
      // ignore
    }
    set({ tourDone: true, tourOpen: false, tourStep: 0 })
  },

  dismissHint: (id: string) => {
    try {
      localStorage.setItem(hintStorageKey(id), '1')
    } catch {
      // ignore
    }
    const { dismissedHints } = get()
    if (dismissedHints.has(id)) return
    const next = new Set(dismissedHints)
    next.add(id)
    set({ dismissedHints: next })
  },

  isHintDismissed: (id: string) => get().dismissedHints.has(id),
}))
