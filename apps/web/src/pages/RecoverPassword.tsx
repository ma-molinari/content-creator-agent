import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { AxiosError } from 'axios'

import { AuthSplitLayout } from '@/components/auth/AuthSplitLayout'
import { IconEye, IconEyeOff } from '@/components/ui/action-icons'
import { useRecoverPassword } from '@/api/auth'

export default function RecoverPassword() {
  const recover = useRecoverPassword()

  const [email, setEmail] = useState('')
  const [securityKey, setSecurityKey] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  function validate() {
    if (!email.trim()) return 'Email é obrigatório.'
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return 'Email inválido.'
    if (!securityKey.trim()) return 'Chave de segurança é obrigatória.'
    if (!newPassword) return 'Nova senha é obrigatória.'
    if (newPassword.length < 8) return 'Senha deve ter ao menos 8 caracteres.'
    if (newPassword !== confirm) return 'As senhas não coincidem.'
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
      await recover.mutateAsync({
        email: email.trim(),
        securityKey: securityKey.trim(),
        newPassword,
      })
      setSuccess(true)
    } catch (e) {
      const ax = e as AxiosError<{ message?: string }>
      const status = ax.response?.status
      const msg = ax.response?.data?.message
      if (status === 400 && msg) {
        setError(msg)
        return
      }
      setError('Não foi possível concluir o pedido. Tente novamente.')
    }
  }

  if (success) {
    return (
      <AuthSplitLayout>
        <div className="flex flex-col gap-5">
          <div>
            <h1 className="text-2xl font-semibold text-[var(--color-text-primary)]">Solicitação enviada</h1>
            <p
              role="status"
              className="mt-4 text-sm leading-relaxed text-[var(--color-text-secondary)]"
            >
              Se o email e a chave de segurança estiverem corretos, sua senha foi redefinida. Você
              pode entrar com a nova senha. Caso não tenha salvo a chave exibida no cadastro, será
              preciso criar uma nova conta.
            </p>
          </div>
          <Link
            to="/login"
            className="inline-flex justify-center rounded-[var(--radius-md)] bg-[var(--color-brand-primary)] px-4 py-2.5 text-center text-sm font-medium text-white hover:bg-[var(--color-brand-primary-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-focus-ring)]"
          >
            Ir para o login
          </Link>
        </div>
      </AuthSplitLayout>
    )
  }

  return (
    <AuthSplitLayout>
      <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-5">
        <div>
          <h1 className="text-2xl font-semibold text-[var(--color-text-primary)]">Redefinir senha</h1>
          <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
            Informe o mesmo email do cadastro e a <strong className="font-medium">chave de segurança</strong>{' '}
            que foi mostrada ao criar a conta. Sem essa chave não é possível redefinir a senha por aqui.
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
          <label htmlFor="recover-email" className="text-sm font-medium text-[var(--color-text-primary)]">
            Email
          </label>
          <input
            id="recover-email"
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
            htmlFor="security-key"
            className="text-sm font-medium text-[var(--color-text-primary)]"
          >
            Chave de segurança
          </label>
          <input
            id="security-key"
            type="text"
            autoComplete="off"
            spellCheck={false}
            value={securityKey}
            onChange={(e) => setSecurityKey(e.target.value)}
            className="rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] px-3 py-2 font-mono text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] outline-none focus:ring-2 focus:ring-[var(--color-focus-ring)]"
            placeholder="Cole a chave do cadastro"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="new-password"
            className="text-sm font-medium text-[var(--color-text-primary)]"
          >
            Nova senha
          </label>
          <div className="relative">
            <input
              id="new-password"
              type={showPw ? 'text' : 'password'}
              autoComplete="new-password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
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
            htmlFor="recover-confirm"
            className="text-sm font-medium text-[var(--color-text-primary)]"
          >
            Confirmar nova senha
          </label>
          <input
            id="recover-confirm"
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
          disabled={recover.isPending}
          className="rounded-[var(--radius-md)] bg-[var(--color-brand-primary)] px-4 py-2.5 text-sm font-medium text-white hover:bg-[var(--color-brand-primary-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-focus-ring)] disabled:opacity-60"
        >
          {recover.isPending ? 'Enviando…' : 'Redefinir senha'}
        </button>

        <p className="text-center text-sm text-[var(--color-text-secondary)]">
          <Link
            to="/login"
            className="font-medium text-[var(--color-brand-primary)] hover:text-[var(--color-brand-primary-hover)]"
          >
            Voltar ao login
          </Link>
        </p>
      </form>
    </AuthSplitLayout>
  )
}
