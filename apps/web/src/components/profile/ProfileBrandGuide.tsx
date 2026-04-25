export function ProfileBrandGuide() {
  return (
    <div className="mb-6 space-y-2 rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] p-4 text-sm text-[var(--color-text-secondary)]">
      <p className="text-[var(--color-text-primary)]">
        <strong>Guia rápido</strong> — Pode escrever em texto corrido. Não precisa de formato de auditor
        profissional: o importante é a informação ser útil e honesta.
      </p>
      <details className="group">
        <summary className="cursor-pointer list-none font-medium text-[var(--color-text-primary)] hover:underline [&::-webkit-details-marker]:hidden">
          O que pôr em <span className="font-mono text-xs">AUDIT</span> (sente-se à vontade)
        </summary>
        <ul className="mt-2 list-inside list-disc space-y-1 pl-0">
          <li>
            Público, nicho, sensação geral do perfil; forças e fraquezas; o que a marca já acerta ou não.
          </li>
          <li>Tom de voz, prova social, padrão de ofertas se existir.</li>
        </ul>
      </details>
      <details className="group">
        <summary className="cursor-pointer list-none font-medium text-[var(--color-text-primary)] hover:underline [&::-webkit-details-marker]:hidden">
          O que pôr em <span className="font-mono text-xs">BRAND</span>
        </summary>
        <ul className="mt-2 list-inside list-disc space-y-1 pl-0">
          <li>Proposta, valores, o que a marca promete (sem inventar factos verificáveis).</li>
          <li>Restrições (o que evitar) e o tom alvo; paleta e estilo, se tiveres.</li>
        </ul>
      </details>
      <details className="group">
        <summary className="cursor-pointer list-none font-medium text-[var(--color-text-primary)] hover:underline [&::-webkit-details-marker]:hidden">
          Boa prática
        </summary>
        <p className="mt-2">
          Prefere factos a suposições. Se faltar dado, assinala; o fluxo de geração pode fazer perguntas em
          aberto em vez de preencher à sorte. Em referências de design, usa imagens e direitos alinhados com a
          tua marca.
        </p>
      </details>
    </div>
  )
}
