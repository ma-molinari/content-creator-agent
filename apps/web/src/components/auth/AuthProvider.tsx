import { useEffect, type ReactNode } from 'react'

import { apiSession } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

type Props = { children: ReactNode }

export function AuthProvider({ children }: Props) {
  const setAccessToken = useAuthStore((s) => s.setAccessToken)
  const setSessionStatus = useAuthStore((s) => s.setSessionStatus)
  const clear = useAuthStore((s) => s.clear)

  useEffect(() => {
    let cancelled = false
    const run = async () => {
      try {
        const { data } = await apiSession.post<{ accessToken: string }>('/auth/refresh')
        if (!cancelled) {
          setAccessToken(data.accessToken)
        }
      } catch {
        if (!cancelled) {
          clear()
        }
      } finally {
        if (!cancelled) {
          setSessionStatus('ready')
        }
      }
    }
    void run()
    return () => {
      cancelled = true
    }
  }, [setAccessToken, setSessionStatus, clear])

  return <>{children}</>
}
