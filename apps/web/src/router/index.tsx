import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { PublicOnlyRoute } from '@/components/auth/PublicOnlyRoute'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { AppShell } from '@/components/shell/AppShell'
import { RouteFallback } from '@/components/ui/RouteFallback'

const Login = lazy(() => import('@/pages/Login'))
const Register = lazy(() => import('@/pages/Register'))
const RecoverPassword = lazy(() => import('@/pages/RecoverPassword'))
const Chat = lazy(() => import('@/pages/Chat'))
const History = lazy(() => import('@/pages/History'))
const ProfileSettings = lazy(() => import('@/pages/ProfileSettings'))

export function AppRouter() {
  return (
    <BrowserRouter>
      <Suspense fallback={<RouteFallback />}>
        <Routes>
          <Route
            path="/login"
            element={
              <PublicOnlyRoute>
                <Login />
              </PublicOnlyRoute>
            }
          />
          <Route
            path="/register"
            element={
              <PublicOnlyRoute>
                <Register />
              </PublicOnlyRoute>
            }
          />
          <Route
            path="/recover-password"
            element={
              <PublicOnlyRoute>
                <RecoverPassword />
              </PublicOnlyRoute>
            }
          />
          <Route element={<ProtectedRoute />}>
            <Route element={<AppShell />}>
              <Route path="/" element={<Chat />} />
              <Route path="/chat/:id" element={<Chat />} />
              <Route path="/history" element={<History />} />
              <Route path="/profile" element={<ProfileSettings />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
