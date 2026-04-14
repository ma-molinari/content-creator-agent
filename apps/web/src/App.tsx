import { QueryClientProvider } from '@tanstack/react-query'

import { queryClient } from '@/lib/queryClient'
import { AppRouter } from '@/router'
import { ToastContainer } from '@/components/ui/ToastContainer'

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppRouter />
      <ToastContainer />
    </QueryClientProvider>
  )
}
