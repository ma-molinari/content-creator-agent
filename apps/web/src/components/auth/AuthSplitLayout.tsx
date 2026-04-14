import type { ReactNode } from 'react'

type Props = {
  children: ReactNode
  /** Marketing / hero side (right on desktop) */
  aside?: ReactNode
}

/** Split auth layout — full implementation in T25/T26. */
export function AuthSplitLayout({ children, aside }: Props) {
  return (
    <div className="grid min-h-dvh md:grid-cols-2">
      <div className="flex flex-col justify-center px-6 py-10 md:px-12">
        {children}
      </div>
      <div className="hidden bg-[var(--color-cta-emphasis)] text-[var(--color-cta-emphasis-contrast)] md:flex md:flex-col md:justify-center md:px-12">
        {aside ?? (
          <p className="text-xl font-semibold leading-snug">
            Crie posts e carrosséis com assistência de IA.
          </p>
        )}
      </div>
    </div>
  )
}
