import { create } from 'zustand'

export type SessionStatus = 'unknown' | 'ready'

type AuthState = {
  accessToken: string | null
  sessionStatus: SessionStatus
  setAccessToken: (token: string | null) => void
  setSessionStatus: (status: SessionStatus) => void
  clear: () => void
}

/** Access token only in memory — never persist (see design). */
export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  sessionStatus: 'unknown',
  setAccessToken: (accessToken) => set({ accessToken }),
  setSessionStatus: (sessionStatus) => set({ sessionStatus }),
  clear: () => set({ accessToken: null }),
}))
