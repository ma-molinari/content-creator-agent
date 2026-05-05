import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

import postMindLogo from '@/assets/post-mind-logo.png'

type Props = {
  children: ReactNode
  /** Marketing / hero panel (desktop right); defaults to centered brand logo */
  aside?: ReactNode
}

function BrandLogoLink() {
  return (
    <Link
      to="/login"
      className="inline-flex outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-focus-ring)] focus-visible:ring-offset-4 focus-visible:ring-offset-[var(--color-bg-app)] md:focus-visible:ring-offset-white "
    >
      <img
        src={postMindLogo}
        alt="Post Mind"
        className="h-auto max-w-[min(100%,380px)] md:max-w-[min(92vw,600px)] "
      />
    </Link>
  )
}

/** Split layout: form column + branded aside on md+ screens. */
export function AuthSplitLayout({ children, aside }: Props) {
  return (
    <div className="grid min-h-dvh md:grid-cols-2">
      <div className="flex flex-col justify-center px-6 py-10 md:px-12">{children}</div>
      <div className="hidden border-l border-[var(--color-border-subtle)] bg-white md:flex md:items-center md:justify-center md:px-10 md:py-12">
        {aside ?? <BrandLogoLink />}
      </div>
    </div>
  )
}
