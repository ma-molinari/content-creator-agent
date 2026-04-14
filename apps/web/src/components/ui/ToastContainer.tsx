import { useToasts } from '@/lib/toast'

export function ToastContainer() {
  const toasts = useToasts()

  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="false"
      className="pointer-events-none fixed bottom-4 right-4 z-[60] flex flex-col gap-2"
    >
      {toasts.map((t) => (
        <div
          key={t.id}
          className={[
            'pointer-events-auto min-w-[220px] max-w-xs rounded-[var(--radius-md)] px-4 py-3 text-sm font-medium shadow-[var(--shadow-md)]',
            t.type === 'success'
              ? 'bg-[var(--color-brand-primary)] text-white'
              : 'bg-[#dc2626] text-white',
          ].join(' ')}
        >
          {t.message}
        </div>
      ))}
    </div>
  )
}
