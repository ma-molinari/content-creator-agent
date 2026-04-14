import { useCallback, useEffect, useState } from 'react'

export type ToastType = 'success' | 'error'

export type Toast = {
  id: number
  message: string
  type: ToastType
}

type Listener = (toasts: Toast[]) => void

let _toasts: Toast[] = []
let _nextId = 0
const _listeners = new Set<Listener>()

function _emit() {
  _listeners.forEach((l) => l([..._toasts]))
}

function _add(message: string, type: ToastType, duration: number) {
  const id = ++_nextId
  _toasts = [..._toasts, { id, message, type }]
  _emit()
  setTimeout(() => {
    _toasts = _toasts.filter((t) => t.id !== id)
    _emit()
  }, duration)
}

export const toast = {
  success: (message: string) => _add(message, 'success', 3_500),
  error: (message: string) => _add(message, 'error', 4_500),
}

export function useToasts(): Toast[] {
  const [list, setList] = useState<Toast[]>([..._toasts])
  const stable = useCallback((t: Toast[]) => setList(t), [])

  useEffect(() => {
    _listeners.add(stable)
    return () => {
      _listeners.delete(stable)
    }
  }, [stable])

  return list
}
