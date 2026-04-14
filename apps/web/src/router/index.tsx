import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { AppShell } from '@/components/shell/AppShell'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'

const Login = lazy(() => import('@/pages/Login'))
const Register = lazy(() => import('@/pages/Register'))
const Chat = lazy(() => import('@/pages/Chat'))
const History = lazy(() => import('@/pages/History'))

function RouteFallback() {
  return (
    <div className="flex min-h-dvh items-center justify-center text-[var(--color-text-secondary)]">
      Carregando…
    </div>
  )
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <Suspense fallback={<RouteFallback />}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<AppShell />}>
              <Route path="/" element={<Chat />} />
              <Route path="/chat/:id" element={<Chat />} />
              <Route path="/history" element={<History />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
