import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  useDeleteReference,
  useProfile,
  useSaveProfile,
  useUploadReference,
} from '@/api/profile'
import { InlineSpinner } from '@/components/ui/InlineSpinner'
import { OnboardingHint } from '@/components/onboarding'
import { ProfileBrandGuide } from '@/components/profile/ProfileBrandGuide'
import { toast } from '@/lib/toast'

const EXAMPLE_AUDIT_TEXT = `Falo com adultos que buscam conteúdo sobre saúde emocional e rotinas de bem-estar, em tom de parceria — como uma conversa com alguém que entende do assunto sem soar distante (principalmente entre 25 e 45 anos).

No feed há bastante carrossel com temas organizados e capas variadas entre um post e outro; nos reels prefiro vídeos curtos com uma ideia só. O que funciona bem são títulos claros e exemplos do dia a dia; o que ainda não rende tanto são vídeos longos sem gancho no início ou miniaturas que parecem todas iguais.

Quero transmitir acolhimento e clareza visual: paleta com toques de rosa e magenta e um estilo de colagem leve e legível. Evito linguagem que infantilize o leitor e termos técnicos sem contexto.`

const EXAMPLE_BRAND_TEXT = `Ajudo pessoas a nomear emoções e cuidar da rotina mental com informação responsável — sem substituir terapia nem prometer transformações instantâneas.

Promessa: cada post ou carrossel deixa uma reflexão prática ou um próximo passo realista, em tom caloroso e educativo, como autoridade gentil — nunca como guru nem como julgamento.

Evitar: promessas de cura, diagnóstico pela internet, tom sensacionalista ou legendas só pensadas para “viralizar” que desvalorizem o tema. Se for o seu caso, adapte exemplos e linguagem ao seu público e à sua formação.`

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

  const loadExample = useCallback(() => {
    const hasContent = auditText.trim() !== '' || brandText.trim() !== ''
    if (hasContent && !window.confirm('Substituir o texto atual pelos exemplos? Você pode editar depois.')) {
      return
    }
    setAuditDraft(EXAMPLE_AUDIT_TEXT)
    setBrandDraft(EXAMPLE_BRAND_TEXT)
  }, [auditText, brandText])

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
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div className="min-h-0 max-h-full flex-initial overflow-y-auto">
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
            Conte sobre o seu perfil no Instagram e a sua marca — o assistente usa essa base para alinhar o tom e o
            conteúdo dos posts gerados. Texto livre funciona muito bem; não precisa de formato específico.
          </p>
          <ProfileBrandGuide />

          {profile.isLoading ? (
            <div className="flex justify-center py-16">
              <InlineSpinner size={32} />
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="flex flex-col gap-6">
              <OnboardingHint
                id="profile-brand"
                title="Antes de usar o chat"
                description="Preencha a auditoria e o guia de marca. Sem essas informações, o chat fica bloqueado."
              />
              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  onClick={loadExample}
                  className="rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] px-3 py-1.5 text-sm font-medium text-[var(--color-text-primary)] hover:bg-[var(--color-bg-muted)]"
                >
                  Ver exemplo
                </button>
                <span className="text-xs text-[var(--color-text-muted)]">
                  Preenche os dois campos com um modelo editável (perfil profissional no Instagram — exemplo fictício em
                  bem-estar emocional).
                </span>
              </div>

              <details className="rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] px-3 py-2 text-sm text-[var(--color-text-secondary)]">
                <summary className="cursor-pointer font-medium text-[var(--color-text-primary)] hover:underline">
                  Opção avançada: importar texto de arquivos .md
                </summary>
                <p className="mt-2 text-[var(--color-text-secondary)]">
                  Se já tiver notas em Markdown, você pode carregar um arquivo por campo (formato .md).
                </p>
                <div className="mt-3 flex flex-wrap gap-4">
                  <label className="cursor-pointer text-sm text-[var(--color-brand-primary)] hover:text-[var(--color-brand-primary-hover)]">
                    Enviar .md → perfil hoje
                    <input
                      type="file"
                      accept=".md,text/markdown"
                      className="sr-only"
                      onChange={(e) => handleFile('audit', e.target.files?.[0] ?? null)}
                    />
                  </label>
                  <label className="cursor-pointer text-sm text-[var(--color-brand-primary)] hover:text-[var(--color-brand-primary-hover)]">
                    Enviar .md → marca
                    <input
                      type="file"
                      accept=".md,text/markdown"
                      className="sr-only"
                      onChange={(e) => handleFile('brand', e.target.files?.[0] ?? null)}
                    />
                  </label>
                </div>
              </details>

              <div>
                <label htmlFor="profile-today" className="mb-2 block text-sm font-medium text-[var(--color-text-primary)]">
                  Como é o seu perfil hoje?
                </label>
                <textarea
                  id="profile-today"
                  value={auditText}
                  onChange={(e) => setAuditDraft(e.target.value)}
                  rows={12}
                  className="w-full min-h-[200px] resize-y rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] px-3 py-2 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:border-[var(--color-focus-ring)] focus:outline-none focus:ring-1 focus:ring-[var(--color-focus-ring)]"
                  placeholder={
                    'Quem costuma ver o seu conteúdo? Qual o tom das publicações hoje?\n' +
                    'O que já funciona bem no feed ou nos carrosséis? O que não funciona ou o que gostaria de mudar?'
                  }
                />
              </div>

              <div>
                <label htmlFor="brand-description" className="mb-2 block text-sm font-medium text-[var(--color-text-primary)]">
                  O que é a sua marca?
                </label>
                <textarea
                  id="brand-description"
                  value={brandText}
                  onChange={(e) => setBrandDraft(e.target.value)}
                  rows={12}
                  className="w-full min-h-[200px] resize-y rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] px-3 py-2 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:border-[var(--color-focus-ring)] focus:outline-none focus:ring-1 focus:ring-[var(--color-focus-ring)]"
                  placeholder={
                    'O que oferece e a quem se dirige? Qual a promessa ou posição da marca?\n' +
                    'Que tom deseja nos posts? O que deve ser evitado (temas, palavras, estilo)?'
                  }
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
      </div>
    </div>
  )
}
