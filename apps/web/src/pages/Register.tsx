import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import type { AxiosError } from 'axios'

import { AuthSplitLayout } from '@/components/auth/AuthSplitLayout'
import { SecurityKeyModal } from '@/components/auth/SecurityKeyModal'
import { useRegister } from '@/api/auth'
import { preparePasswordForTransport } from '@/lib/crypto'

export default function Register() {
  const navigate = useNavigate()
  const register = useRegister()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [securityKey, setSecurityKey] = useState<string | null>(null)

  function validate() {
    if (!email.trim()) return 'Email é obrigatório.'
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return 'Email inválido.'
    if (!password) return 'Senha é obrigatória.'
    if (password.length < 8) return 'Senha deve ter ao menos 8 caracteres.'
    if (password !== confirm) return 'As senhas não coincidem.'
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
      const result = await register.mutateAsync({
        email: email.trim(),
        password: preparePasswordForTransport(password),
      })
      setSecurityKey(result.securityKey)
    } catch (e) {
      const status = (e as AxiosError)?.response?.status
      if (status === 409) setError('Este email já está cadastrado.')
      else setError('Não foi possível criar sua conta. Tente novamente.')
    }
  }

  if (securityKey) {
    return (
      <SecurityKeyModal
        securityKey={securityKey}
        onClose={() => navigate('/login', { replace: true })}
      />
    )
  }

  return (
    <AuthSplitLayout>
      <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-5">
        <div>
          <h1 className="text-2xl font-semibold text-[var(--color-text-primary)]">Criar conta</h1>
          <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
            Preencha os dados para começar.
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
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] px-3 py-2 pr-10 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] outline-none focus:ring-2 focus:ring-[var(--color-focus-ring)]"
              placeholder="mín. 8 caracteres"
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

        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="confirm"
            className="text-sm font-medium text-[var(--color-text-primary)]"
          >
            Confirmar senha
          </label>
          <input
            id="confirm"
            type={showPw ? 'text' : 'password'}
            autoComplete="new-password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            className="rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] px-3 py-2 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] outline-none focus:ring-2 focus:ring-[var(--color-focus-ring)]"
            placeholder="••••••••"
          />
        </div>

        <button
          type="submit"
          disabled={register.isPending}
          className="rounded-[var(--radius-md)] bg-[var(--color-brand-primary)] px-4 py-2.5 text-sm font-medium text-white hover:bg-[var(--color-brand-primary-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-focus-ring)] disabled:opacity-60"
        >
          {register.isPending ? 'Criando conta…' : 'Criar conta'}
        </button>

        <p className="text-center text-sm text-[var(--color-text-secondary)]">
          Já tem conta?{' '}
          <Link
            to="/login"
            className="font-medium text-[var(--color-brand-primary)] hover:text-[var(--color-brand-primary-hover)]"
          >
            Entrar
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
