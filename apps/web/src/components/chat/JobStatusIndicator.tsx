import { InlineSpinner } from '@/components/ui/InlineSpinner'

type Props = {
  status: 'pending' | 'processing'
  hasUserAttachments?: boolean
  stage?: string
  progress?: number
}

const STAGE_LABELS: Record<string, string> = {
  dispatching: 'Preparando geração…',
  preparing_input: 'Preparando pedido…',
  validating_prompt: 'Validando instruções…',
  reading_profile: 'Lendo perfil da marca…',
  detecting_intent: 'Entendendo o pedido…',
  loading_existing_slides: 'Carregando versão anterior…',
  analyzing_attachments: 'Analisando anexos…',
  planning_generation: 'Planejando os slides…',
  generating_slides: 'Gerando seu post…',
  validating_output: 'Validando estrutura…',
  validating_design: 'Revisando design…',
  validating_attachments: 'Aplicando imagens anexadas…',
  rendering_slides: 'Renderizando imagens…',
  uploading_assets: 'Enviando arquivos…',
  finalizing: 'Finalizando…',
}

export function JobStatusIndicator({
  status,
  hasUserAttachments,
  stage,
  progress,
}: Props) {
  let label = 'Aguardando…'
  if (stage && STAGE_LABELS[stage]) {
    label = STAGE_LABELS[stage]
  } else if (status === 'processing' && hasUserAttachments) {
    label = 'Aplicando imagens anexadas…'
  } else if (status === 'processing') {
    label = 'Gerando seu post…'
  }
  const pct =
    typeof progress === 'number' && Number.isFinite(progress)
      ? Math.max(0, Math.min(100, progress))
      : null

  return (
    <div className="min-w-[220px] text-sm text-[var(--color-text-secondary)]">
      <div className="flex items-center gap-2">
        <InlineSpinner
          size={16}
          ariaHidden
          className="text-[var(--color-brand-primary)]"
        />
        <span>{label}</span>
        {pct !== null && <span className="text-xs tabular-nums">{pct}%</span>}
      </div>
      {pct !== null && (
        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-[var(--color-bg-muted)]">
          <div
            className="h-full rounded-full bg-[var(--color-brand-primary)] transition-[width] duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>
      )}
    </div>
  )
}
