import { create } from 'zustand'

type AuthState = {
  accessToken: string | null
  setAccessToken: (token: string | null) => void
  clear: () => void
}

/** Access token only in memory — never persist (see design). */
export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  setAccessToken: (accessToken) => set({ accessToken }),
  clear: () => set({ accessToken: null }),
}))
