import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  useDeleteReference,
  useProfile,
  useSaveProfile,
  useUploadReference,
} from '@/api/profile'
import { ProfileBrandGuide } from '@/components/profile/ProfileBrandGuide'
import { toast } from '@/lib/toast'

export default function ProfileSettings() {
  const profile = useProfile()
  const save = useSaveProfile()
  const uploadRef = useUploadReference()
  const deleteRef = useDeleteReference()

  const [auditDraft, setAuditDraft] = useState<string | null>(null)
  const [brandDraft, setBrandDraft] = useState<string | null>(null)
  const auditText = auditDraft !== null ? auditDraft : (profile.data?.auditText ?? '')
  const brandText = brandDraft !== null ? brandDraft : (profile.data?.brandText ?? '')

  const handleFile = useCallback(
    (which: 'audit' | 'brand', file: File | null) => {
      if (!file) return
      if (!file.name.toLowerCase().endsWith('.md')) {
        toast.error('Use um arquivo .md.')
        return
      }
      const reader = new FileReader()
      reader.onload = () => {
        const text = typeof reader.result === 'string' ? reader.result : ''
        if (which === 'audit') setAuditDraft(text)
        else setBrandDraft(text)
      }
      reader.readAsText(file)
    },
    [],
  )

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    try {
      await save.mutateAsync({ auditText, brandText })
      setAuditDraft(null)
      setBrandDraft(null)
      toast.success('Perfil salvo.')
    } catch {
      toast.error('Não foi possível salvar. Tente novamente.')
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <div className="mb-6 flex items-center gap-3">
        <Link
          to="/"
          className="text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
        >
          ← Início
        </Link>
        <h1 className="text-xl font-semibold text-[var(--color-text-primary)]">Perfil da marca</h1>
      </div>

      <p className="mb-4 text-sm text-[var(--color-text-secondary)]">
        Cole o conteúdo de <code className="rounded bg-[var(--color-bg-muted)] px-1">AUDIT.md</code> e{' '}
        <code className="rounded bg-[var(--color-bg-muted)] px-1">BRAND.md</code> da sua auditoria de
        Instagram, ou envie arquivos .md para preencher os campos. Texto em linguagem natural é bem-vindo; os
        títulos dos campos são só orientação.
      </p>
      <ProfileBrandGuide />

      {profile.isLoading ? (
        <div className="flex justify-center py-16">
          <Spinner />
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-col gap-6">
          <div>
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <label
                htmlFor="audit-md"
                className="text-sm font-medium text-[var(--color-text-primary)]"
              >
                AUDIT (markdown)
              </label>
              <label className="cursor-pointer text-sm text-[var(--color-brand-primary)] hover:text-[var(--color-brand-primary-hover)]">
                Enviar .md
                <input
                  type="file"
                  accept=".md,text/markdown"
                  className="sr-only"
                  onChange={(e) => handleFile('audit', e.target.files?.[0] ?? null)}
                />
              </label>
            </div>
            <textarea
              id="audit-md"
              value={auditText}
              onChange={(e) => setAuditDraft(e.target.value)}
              rows={12}
              className="w-full min-h-[200px] resize-y rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] px-3 py-2 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:border-[var(--color-focus-ring)] focus:outline-none focus:ring-1 focus:ring-[var(--color-focus-ring)]"
              placeholder="Conteúdo do AUDIT.md…"
            />
          </div>

          <div>
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <label
                htmlFor="brand-md"
                className="text-sm font-medium text-[var(--color-text-primary)]"
              >
                BRAND (markdown)
              </label>
              <label className="cursor-pointer text-sm text-[var(--color-brand-primary)] hover:text-[var(--color-brand-primary-hover)]">
                Enviar .md
                <input
                  type="file"
                  accept=".md,text/markdown"
                  className="sr-only"
                  onChange={(e) => handleFile('brand', e.target.files?.[0] ?? null)}
                />
              </label>
            </div>
            <textarea
              id="brand-md"
              value={brandText}
              onChange={(e) => setBrandDraft(e.target.value)}
              rows={12}
              className="w-full min-h-[200px] resize-y rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] px-3 py-2 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:border-[var(--color-focus-ring)] focus:outline-none focus:ring-1 focus:ring-[var(--color-focus-ring)]"
              placeholder="Conteúdo do BRAND.md…"
            />
          </div>

          <div className="border-t border-[var(--color-border-subtle)] pt-6">
            <h2 className="mb-1 text-sm font-medium text-[var(--color-text-primary)]">
              Referências de design (opcional)
            </h2>
            <p className="mb-3 text-sm text-[var(--color-text-secondary)]">
              Até 8 imagens (JPEG, PNG, WebP ou GIF), máx. 5&nbsp;MB cada. A equipa gera resumo de estilo para
              alinhar o carrossel. Use apenas imagens e direitos de uso que possa reutilizar (ex.: tua própria
              marca, stock licenciado).
            </p>
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <label className="cursor-pointer rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] px-3 py-1.5 text-sm font-medium text-[var(--color-text-primary)] hover:bg-[var(--color-bg-muted)]">
                {uploadRef.isPending ? 'A enviar…' : 'Adicionar imagem'}
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp,image/gif"
                  className="sr-only"
                  disabled={uploadRef.isPending}
                  onChange={async (e) => {
                    const f = e.target.files?.[0]
                    e.target.value = ''
                    if (!f) return
                    try {
                      await uploadRef.mutateAsync(f)
                      toast.success('Referência adicionada.')
                    } catch {
                      toast.error('Não foi possível enviar. Verifica formato e tamanho.')
                    }
                  }}
                />
              </label>
            </div>
            {profile.data?.references && profile.data.references.length > 0 && (
              <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
                {profile.data.references.map((r) => (
                  <li
                    key={r.id}
                    className="group relative aspect-square overflow-hidden rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-muted)]"
                  >
                    <img src={r.url} alt="" className="h-full w-full object-cover" />
                    <button
                      type="button"
                      title="Remover"
                      className="absolute right-1 top-1 rounded bg-black/50 px-2 py-0.5 text-xs text-white opacity-0 transition-opacity hover:bg-black/70 group-hover:opacity-100"
                      disabled={deleteRef.isPending}
                      onClick={async () => {
                        if (!window.confirm('Remover esta referência?')) return
                        try {
                          await deleteRef.mutateAsync(r.id)
                          toast.success('Removida.')
                        } catch {
                          toast.error('Não foi possível remover.')
                        }
                      }}
                    >
                      Remover
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={save.isPending}
              className="rounded-[var(--radius-md)] bg-[var(--color-brand-primary)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--color-brand-primary-hover)] disabled:opacity-50"
            >
              {save.isPending ? 'Salvando…' : 'Salvar'}
            </button>
            {profile.data?.configured && (
              <span className="text-sm text-[var(--color-text-secondary)]">Perfil completo para geração.</span>
            )}
          </div>
        </form>
      )}
    </div>
  )
}

function Spinner() {
  return (
    <div
      className="h-8 w-8 animate-spin rounded-full border-2 border-[var(--color-border-subtle)] border-t-[var(--color-brand-primary)]"
      aria-hidden
    />
  )
}
