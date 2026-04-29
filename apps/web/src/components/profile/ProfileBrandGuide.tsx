export function ProfileBrandGuide() {
  return (
    <div className="mb-6 space-y-2 rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] p-4 text-sm text-[var(--color-text-secondary)]">
      <p className="text-[var(--color-text-primary)]">
        <strong>Guia rápido</strong> — Pode escrever em texto corrido. O importante é a informação ser útil e honesta;
        não precisa de estrutura rígida.
      </p>
      <details className="group">
        <summary className="cursor-pointer list-none font-medium text-[var(--color-text-primary)] hover:underline [&::-webkit-details-marker]:hidden">
          Perguntas para o primeiro campo (o seu perfil hoje)
        </summary>
        <ul className="mt-2 list-inside list-disc space-y-1 pl-0">
          <li>Quem costuma ver o seu conteúdo (idade, interesses, nicho)?</li>
          <li>Como descreveria o tom das publicações hoje — formal, leve, técnico, outro?</li>
          <li>O que já funciona bem no feed ou nos carrosséis? O que sente que falha ou falta?</li>
          <li>Há algo que quer mudar na perceção que as pessoas têm do perfil?</li>
        </ul>
      </details>
      <details className="group">
        <summary className="cursor-pointer list-none font-medium text-[var(--color-text-primary)] hover:underline [&::-webkit-details-marker]:hidden">
          Perguntas para o segundo campo (a sua marca)
        </summary>
        <ul className="mt-2 list-inside list-disc space-y-1 pl-0">
          <li>O que você oferece, em uma frase, para quem te segue ou compra?</li>
          <li>Qual é a promessa ou posição — o que esperam de você em relação aos concorrentes?</li>
          <li>Que tom quer que os posts transmitam daqui para a frente?</li>
          <li>O que deve ser evitado (palavras, temas sensíveis, tom que não combina com a marca)?</li>
        </ul>
      </details>
      <details className="group">
        <summary className="cursor-pointer list-none font-medium text-[var(--color-text-primary)] hover:underline [&::-webkit-details-marker]:hidden">
          Boa prática
        </summary>
        <p className="mt-2">
          Prefira fatos a suposições. Se faltar um dado, diga que falta; o assistente pode adaptar em vez de inventar.
          Nas referências de imagem, use arquivos e direitos alinhados com a sua marca.
        </p>
      </details>
    </div>
  )
}
