const CHIPS = [
  "Crie um carrossel sobre produtividade para Instagram",
  "Post único sobre lançamento de produto",
  "Post motivacional para segunda-feira",
];

type Props = {
  onChipClick?: (text: string) => void;
};

export function EmptyChatState({ onChipClick }: Props) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 py-12 text-center">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-[var(--color-nav-active-bg)]">
        <IconSparkles />
      </div>
      <h1 className="text-2xl font-semibold text-[var(--color-text-primary)]">
        Como posso ajudar?
      </h1>
      <p className="mt-2 max-w-sm text-sm text-[var(--color-text-secondary)]">
        Descreva o post ou carrossel que você quer criar. Use uma das sugestões
        abaixo ou escreva sua própria ideia.
      </p>

      {onChipClick && (
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          {CHIPS.map((chip) => (
            <button
              key={chip}
              type="button"
              onClick={() => onChipClick(chip)}
              className="rounded-[var(--radius-pill)] border border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] px-4 py-2 text-sm text-[var(--color-text-secondary)] transition-colors hover:border-[var(--color-brand-primary)] hover:text-[var(--color-brand-primary)]"
            >
              {chip}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function IconSparkles() {
  return (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden
      className="text-[var(--color-brand-primary)]"
    >
      <path
        d="M12 2l1.5 4.5L18 8l-4.5 1.5L12 14l-1.5-4.5L6 8l4.5-1.5L12 2z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path
        d="M19 14l.75 2.25L22 17l-2.25.75L19 20l-.75-2.25L16 17l2.25-.75L19 14z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path
        d="M5 17l.5 1.5L7 19l-1.5.5L5 21l-.5-1.5L3 19l1.5-.5L5 17z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
    </svg>
  );
}
