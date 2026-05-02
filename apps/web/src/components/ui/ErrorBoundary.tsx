import { Component, type ErrorInfo, type ReactNode } from 'react'

type Props = { children: ReactNode }
type State = { hasError: boolean }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(): State {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-dvh flex-col items-center justify-center gap-4 bg-[var(--color-bg-app)] p-8 text-center">
          <p className="text-sm text-[var(--color-text-secondary)]">
            Algo deu errado. Recarregue a página para continuar.
          </p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="rounded-[var(--radius-md)] bg-[var(--color-brand-primary)] px-4 py-2 text-sm text-white"
          >
            Recarregar
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
