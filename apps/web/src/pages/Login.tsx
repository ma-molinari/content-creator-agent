import { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import type { AxiosError } from 'axios'

import { AuthSplitLayout } from '@/components/auth/AuthSplitLayout'
import { useLogin } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import { preparePasswordForTransport } from '@/lib/crypto'

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const returnTo = (location.state as { from?: string } | null)?.from ?? '/'
  const { setAccessToken } = useAuthStore()
  const login = useLogin()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function validate() {
    if (!email.trim()) return 'Email é obrigatório.'
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return 'Email inválido.'
    if (!password) return 'Senha é obrigatória.'
    return null
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    const err = validate()
    if (err) {
      setError(err)
      return
    }
    try {
      const result = await login.mutateAsync({
        email: email.trim(),
        password: preparePasswordForTransport(password),
      })
      setAccessToken(result.accessToken)
      navigate(returnTo, { replace: true })
    } catch (e) {
      const status = (e as AxiosError)?.response?.status
      if (status === 401) setError('Email ou senha incorretos.')
      else setError('Não foi possível conectar. Tente novamente.')
    }
  }

  return (
    <AuthSplitLayout>
      <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-5">
        <div>
          <h1 className="text-2xl font-semibold text-[var(--color-text-primary)]">Entrar</h1>
          <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
            Acesse sua conta para criar posts.
          </p>
        </div>

        {error && (
          <p
            role="alert"
            className="rounded-[var(--radius-md)] bg-red-50 px-4 py-2 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400"
          >
            {error}
          </p>
        )}

        <div className="flex flex-col gap-1.5">
          <label htmlFor="email" className="text-sm font-medium text-[var(--color-text-primary)]">
            Email
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] px-3 py-2 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] outline-none focus:ring-2 focus:ring-[var(--color-focus-ring)]"
            placeholder="voce@exemplo.com"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="password"
            className="text-sm font-medium text-[var(--color-text-primary)]"
          >
            Senha
          </label>
          <div className="relative">
            <input
              id="password"
              type={showPw ? 'text' : 'password'}
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] px-3 py-2 pr-10 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] outline-none focus:ring-2 focus:ring-[var(--color-focus-ring)]"
              placeholder="••••••••"
            />
            <button
              type="button"
              onClick={() => setShowPw(!showPw)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"
              aria-label={showPw ? 'Ocultar senha' : 'Mostrar senha'}
            >
              {showPw ? <IconEyeOff /> : <IconEye />}
            </button>
          </div>
        </div>

        <button
          type="submit"
          disabled={login.isPending}
          className="rounded-[var(--radius-md)] bg-[var(--color-brand-primary)] px-4 py-2.5 text-sm font-medium text-white hover:bg-[var(--color-brand-primary-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-focus-ring)] disabled:opacity-60"
        >
          {login.isPending ? 'Entrando…' : 'Entrar'}
        </button>

        <p className="text-center text-sm text-[var(--color-text-secondary)]">
          Não tem conta?{' '}
          <Link
            to="/register"
            className="font-medium text-[var(--color-brand-primary)] hover:text-[var(--color-brand-primary-hover)]"
          >
            Cadastrar
          </Link>
        </p>
      </form>
    </AuthSplitLayout>
  )
}

function IconEye() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  )
}

function IconEyeOff() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24M1 1l22 22"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  )
}
