import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { RouteFallback } from '@/components/ui/RouteFallback'
import { useAuthStore } from '@/stores/auth'

export function ProtectedRoute() {
  const sessionStatus = useAuthStore((s) => s.sessionStatus)
  const token = useAuthStore((s) => s.accessToken)
  const location = useLocation()

  if (sessionStatus === 'unknown') {
    return <RouteFallback />
  }

  if (!token) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  return <Outlet />
}
