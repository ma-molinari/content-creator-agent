import { QueryClientProvider } from '@tanstack/react-query'

import { AuthProvider } from '@/components/auth/AuthProvider'
import { queryClient } from '@/lib/queryClient'
import { AppRouter } from '@/router'
import { ToastContainer } from '@/components/ui/ToastContainer'

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <AppRouter />
      </AuthProvider>
      <ToastContainer />
    </QueryClientProvider>
  )
}
