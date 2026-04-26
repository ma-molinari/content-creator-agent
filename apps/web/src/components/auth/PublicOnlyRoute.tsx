import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'

import { RouteFallback } from '@/components/ui/RouteFallback'
import { useAuthStore } from '@/stores/auth'

type Props = { children: ReactNode }

/** Login/register: wait for session bootstrap, then redirect home if a refresh cookie yielded an access token. */
export function PublicOnlyRoute({ children }: Props) {
  const sessionStatus = useAuthStore((s) => s.sessionStatus)
  const token = useAuthStore((s) => s.accessToken)

  if (sessionStatus === 'unknown') {
    return <RouteFallback />
  }
  if (token) {
    return <Navigate to="/" replace />
  }
  return <>{children}</>
}
