import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  useProfile,
  useSaveProfile,
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

const PROFILE_EXAMPLES = [
  {
    id: 'bem-estar', label: 'Bem-estar',
    description: 'Conteúdo educativo e acolhedor sobre hábitos e qualidade de vida.',
    audit: EXAMPLE_AUDIT_TEXT, brand: EXAMPLE_BRAND_TEXT,
  },
  {
    id: 'educacao', label: 'Educação',
    description: 'Explicações práticas para aprender uma nova habilidade.',
    audit: `Meu perfil reúne pessoas que querem aprender habilidades novas para o trabalho ou os estudos.

Posts com exemplos passo a passo geram mais interesse. Quero organizar melhor os carrosséis e tornar assuntos complexos mais fáceis de acompanhar.

Uso linguagem direta, visual limpo e cores contrastantes. Evito excesso de texto e siglas sem explicação.`,
    brand: `Minha marca ensina conceitos e técnicas de forma acessível, com foco na aplicação prática.

Quero um tom claro, encorajador e objetivo. Cada post deve apresentar uma ideia útil e, quando fizer sentido, um exemplo ou próximo passo.

Evitar afirmações sem contexto, promessas de aprendizado instantâneo e linguagem que desvalorize quem está começando.`,
  },
  {
    id: 'negocio-local', label: 'Negócio local',
    description: 'Produtos, serviços e novidades para a comunidade.',
    audit: `Meu perfil conversa com pessoas da comunidade interessadas em conhecer produtos e serviços de um negócio local.

Fotos dos produtos e publicações sobre os bastidores despertam interesse. Quero apresentar melhor os diferenciais e manter uma identidade consistente entre os posts.

Prefiro uma linguagem próxima e cores que representem o negócio. Evito imagens poluídas e informações não confirmadas.`,
    brand: `Minha marca oferece produtos ou serviços para a comunidade e valoriza atendimento atencioso e informações claras.

Quero uma comunicação amigável, objetiva e convidativa, destacando benefícios reais, novidades e detalhes úteis para o cliente.

Evitar descontos, preços, prazos ou características inventados e comparações que depreciem concorrentes.`,
  },
] as const

export default function ProfileSettings() {
  const profile = useProfile()
  const save = useSaveProfile()

  const [auditDraft, setAuditDraft] = useState<string | null>(null)
  const [brandDraft, setBrandDraft] = useState<string | null>(null)
  const [step, setStep] = useState(0)
  const auditText = auditDraft !== null ? auditDraft : (profile.data?.auditText ?? '')
  const brandText = brandDraft !== null ? brandDraft : (profile.data?.brandText ?? '')
  const auditReady = auditText.trim().length > 0
  const brandReady = brandText.trim().length > 0

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

  const loadExample = useCallback((example: (typeof PROFILE_EXAMPLES)[number]) => {
    const hasContent = auditText.trim() !== '' || brandText.trim() !== ''
    if (hasContent && !window.confirm('Substituir os dois textos pelo exemplo selecionado? Você pode editá-los antes de salvar.')) {
      return
    }
    setAuditDraft(example.audit)
    setBrandDraft(example.brand)
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

  function nextStep() {
    if (step === 0 && !auditReady) {
      toast.error('Preencha como é o seu perfil hoje para continuar.')
      return
    }
    if (step === 1 && !brandReady) {
      toast.error('Preencha o que é a sua marca para continuar.')
      return
    }
    setStep((current) => Math.min(1, current + 1))
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

          <p className="mb-4 max-w-2xl text-sm text-[var(--color-text-secondary)]">
            Configure a base que orienta tom, público e identidade visual dos posts. O fluxo tem dois passos rápidos e
            você pode voltar para ajustar qualquer parte.
          </p>

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
              <StepProgress
                step={step}
                auditReady={auditReady}
                brandReady={brandReady}
                onSelect={setStep}
              />

              <div className="rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] p-4">
                {step === 0 && (
                  <section aria-labelledby="profile-step-audit" className="space-y-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-xs font-medium uppercase tracking-wide text-[var(--color-brand-primary)]">
                          Passo 1 de 2
                        </p>
                        <h2 id="profile-step-audit" className="mt-1 text-lg font-semibold text-[var(--color-text-primary)]">
                          Perfil hoje
                        </h2>
                        <p className="mt-1 max-w-xl text-sm text-[var(--color-text-secondary)]">
                          Conte quem acompanha seu Instagram, o que já funciona e onde a comunicação precisa melhorar.
                        </p>
                      </div>

                    </div>
                    <details className="rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-app)] p-3">
                      <summary className="cursor-pointer text-sm font-medium text-[var(--color-brand-primary)] hover:underline">
                        Escolher um exemplo
                      </summary>
                      <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
                        Escolha um ponto de partida para os dois textos e adapte-o à sua marca antes de salvar.
                      </p>
                      <div className="mt-3 grid gap-2 sm:grid-cols-3">
                        {PROFILE_EXAMPLES.map((example) => (
                          <button
                            key={example.id}
                            type="button"
                            onClick={() => loadExample(example)}
                            className="rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] p-3 text-left hover:bg-[var(--color-bg-muted)] focus-visible:outline-2 focus-visible:outline-[var(--color-focus-ring)]"
                          >
                            <span className="block text-sm font-medium text-[var(--color-text-primary)]">{example.label}</span>
                            <span className="mt-1 block text-xs text-[var(--color-text-secondary)]">{example.description}</span>
                          </button>
                        ))}
                      </div>
                    </details>
                    <ProfileBrandGuide />
                    <label htmlFor="audit-md" className="block text-sm font-medium text-[var(--color-text-primary)]">
                      Como é o seu perfil hoje?
                    </label>
                    <textarea
                      id="audit-md"
                      value={auditText}
                      onChange={(e) => setAuditDraft(e.target.value)}
                      rows={10}
                      className="w-full min-h-[220px] resize-y rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-app)] px-3 py-2 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:border-[var(--color-focus-ring)] focus:outline-none focus:ring-1 focus:ring-[var(--color-focus-ring)]"
                      placeholder={
                        'Quem costuma ver o seu conteúdo? Qual o tom das publicações hoje?\n' +
                        'O que já funciona bem no feed ou nos carrosséis? O que não funciona ou o que gostaria de mudar?'
                      }
                    />
                  </section>
                )}

                {step === 1 && (
                  <section aria-labelledby="profile-step-brand" className="space-y-4">
                    <div>
                      <p className="text-xs font-medium uppercase tracking-wide text-[var(--color-brand-primary)]">
                        Passo 2 de 2
                      </p>
                      <h2 id="profile-step-brand" className="mt-1 text-lg font-semibold text-[var(--color-text-primary)]">
                        Direção da marca
                      </h2>
                      <p className="mt-1 max-w-xl text-sm text-[var(--color-text-secondary)]">
                        Defina promessa, tom, limites e o que os posts nunca devem comunicar.
                      </p>
                    </div>
                    <label htmlFor="brand-md" className="block text-sm font-medium text-[var(--color-text-primary)]">
                      O que é a sua marca?
                    </label>
                    <textarea
                      id="brand-md"
                      value={brandText}
                      onChange={(e) => setBrandDraft(e.target.value)}
                      rows={10}
                      className="w-full min-h-[220px] resize-y rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-app)] px-3 py-2 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:border-[var(--color-focus-ring)] focus:outline-none focus:ring-1 focus:ring-[var(--color-focus-ring)]"
                      placeholder={
                        'O que oferece e a quem se dirige? Qual a promessa ou posição da marca?\n' +
                        'Que tom deseja nos posts? O que deve ser evitado (temas, palavras, estilo)?'
                      }
                    />
                    <details className="rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-app)] px-3 py-2 text-sm text-[var(--color-text-secondary)]">
                      <summary className="cursor-pointer font-medium text-[var(--color-text-primary)] hover:underline">
                        Importar textos de arquivos .md
                      </summary>
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
                  </section>
                )}
              </div>

              <div className="sticky bottom-0 -mx-4 border-t border-[var(--color-border-subtle)] bg-[var(--color-bg-app)] px-4 py-3">
                <div className="mx-auto flex max-w-3xl flex-wrap items-center justify-between gap-3">
                  <div className="text-sm text-[var(--color-text-secondary)]">
                    {profile.data?.configured ? 'Perfil completo para geração.' : 'Preencha os dois textos para liberar o chat.'}
                  </div>
                  <div className="flex items-center gap-2">
                    {step > 0 && (
                      <button
                        type="button"
                        onClick={() => setStep((current) => Math.max(0, current - 1))}
                        className="rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] px-4 py-2 text-sm font-medium text-[var(--color-text-primary)] hover:bg-[var(--color-bg-muted)]"
                      >
                        Voltar
                      </button>
                    )}
                    {step < 1 ? (
                      <button
                        type="button"
                        onClick={nextStep}
                        className="rounded-[var(--radius-md)] bg-[var(--color-brand-primary)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--color-brand-primary-hover)]"
                      >
                        Continuar
                      </button>
                    ) : (
                      <button
                        type="submit"
                        disabled={save.isPending}
                        className="rounded-[var(--radius-md)] bg-[var(--color-brand-primary)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--color-brand-primary-hover)] disabled:opacity-50"
                      >
                        {save.isPending ? 'Salvando…' : 'Salvar perfil'}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}

type StepProgressProps = {
  step: number
  auditReady: boolean
  brandReady: boolean
  onSelect: (step: number) => void
}

function StepProgress({ step, auditReady, brandReady, onSelect }: StepProgressProps) {
  const items = [
    { label: 'Perfil hoje', done: auditReady },
    { label: 'Marca', done: brandReady },
  ]

  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {items.map((item, index) => {
        const active = step === index
        return (
          <button
            key={item.label}
            type="button"
            onClick={() => onSelect(index)}
            className={[
              'rounded-[var(--radius-md)] border px-3 py-2 text-left transition-colors',
              active
                ? 'border-[var(--color-brand-primary)] bg-[var(--color-nav-active-bg)]'
                : 'border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] hover:bg-[var(--color-bg-muted)]',
            ].join(' ')}
          >
            <span className="text-xs text-[var(--color-text-muted)]">Passo {index + 1}</span>
            <span className="mt-0.5 flex items-center justify-between gap-2 text-sm font-medium text-[var(--color-text-primary)]">
              {item.label}
              <span
                className={[
                  'rounded-[var(--radius-pill)] px-2 py-0.5 text-[11px] font-medium',
                  item.done
                    ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300'
                    : 'bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-300',
                ].join(' ')}
              >
                {item.done ? 'ok' : 'pendente'}
              </span>
            </span>
          </button>
        )
      })}
    </div>
  )
}
