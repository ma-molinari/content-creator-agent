type Props = {
  open: boolean
  title: string
  description: string
  confirmLabel?: string
  cancelLabel?: string
  loading?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export function AlertDialog({
  open,
  title,
  description,
  confirmLabel = 'Confirmar',
  cancelLabel = 'Cancelar',
  loading = false,
  onConfirm,
  onCancel,
}: Props) {
  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onCancel}
    >
      <div
        className="w-full max-w-sm rounded-[var(--radius-lg)] bg-[var(--color-bg-surface)] p-6 shadow-[var(--shadow-md)]"
        onClick={(e) => e.stopPropagation()}
        role="alertdialog"
        aria-modal
        aria-labelledby="alert-dialog-title"
        aria-describedby="alert-dialog-desc"
      >
        <h2
          id="alert-dialog-title"
          className="text-base font-semibold text-[var(--color-text-primary)]"
        >
          {title}
        </h2>
        <p
          id="alert-dialog-desc"
          className="mt-2 text-sm text-[var(--color-text-secondary)]"
        >
          {description}
        </p>
        <div className="mt-5 flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={loading}
            className="rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] px-4 py-2 text-sm font-medium text-[var(--color-text-primary)] hover:bg-[var(--color-bg-muted)] disabled:opacity-50"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={loading}
            className="rounded-[var(--radius-md)] bg-[#dc2626] px-4 py-2 text-sm font-medium text-white hover:bg-[#b91c1c] disabled:opacity-50"
          >
            {loading ? 'Aguarde…' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
