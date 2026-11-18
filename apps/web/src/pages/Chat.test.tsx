import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  send: vi.fn(), get: vi.fn(),
  status: { value: undefined as undefined | { status: string; error: string; errorCode: string } },
  chat: { value: { id: 'chat', userId: 'user', postType: 'single', postFormat: 'structured_v1', currentVersionId: 'v1', title: 'Post', contents: [] } },
}))

vi.mock('@/api/client', () => ({ api: { get: mocks.get } }))
vi.mock('@/api/chats', () => ({
  fetchChatFilesZip: vi.fn(),
  postChatMessage: mocks.send,
  useChat: () => ({ data: mocks.chat.value, isLoading: false }),
  useDeleteChat: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useSetupStatus: () => ({ data: { configured: true } }),
  useJobStatus: (_chatId: string | null, jobId: string | null) => ({ data: jobId ? mocks.status.value : undefined }),
}))
vi.mock('@/components/chat/ChatThread', () => ({
  ChatThread: ({ onRetry }: { onRetry?: () => void }) => onRetry ? <button onClick={onRetry}>Reenviar</button> : null,
}))
vi.mock('@/components/onboarding', () => ({ OnboardingHint: () => null }))
vi.mock('@/lib/toast', () => ({ toast: { error: vi.fn(), success: vi.fn() } }))

import Chat from './Chat'

function renderChat() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><MemoryRouter initialEntries={['/chat/chat']}><Routes><Route path="/chat/:id" element={<Chat />} /></Routes></MemoryRouter></QueryClientProvider>)
}

beforeEach(() => {
  mocks.send.mockReset().mockResolvedValue({ jobId: 'job' })
  mocks.get.mockReset().mockResolvedValue({ data: { ...mocks.chat.value, currentVersionId: 'v2' } })
  mocks.status.value = undefined
  mocks.chat.value.postFormat = 'structured_v1'
  mocks.chat.value.currentVersionId = 'v1'
})
afterEach(cleanup)

describe('structured chat', () => {
  it('sends the current version for an edit and allows choosing creation', async () => {
    const user = userEvent.setup()
    renderChat()
    await user.click(screen.getByRole('radio', { name: /criar novo post/i }))
    await user.type(screen.getByRole('textbox', { name: /mensagem/i }), 'Crie outro')
    await user.click(screen.getByRole('button', { name: /enviar/i }))
    await waitFor(() => expect(mocks.send).toHaveBeenCalledWith('chat', 'Crie outro', [], { mode: 'create' }))
  })

  it('uses the refreshed base only when the user chooses to resend after conflict', async () => {
    const user = userEvent.setup()
    const view = renderChat()
    await user.type(screen.getByRole('textbox', { name: /mensagem/i }), 'Mude o fundo')
    await user.click(screen.getByRole('button', { name: /enviar/i }))
    await waitFor(() => expect(mocks.send).toHaveBeenCalledWith('chat', 'Mude o fundo', [], { mode: 'edit', baseVersionId: 'v1' }))
    mocks.status.value = { status: 'failed', error: 'A versão mudou', errorCode: 'VERSION_CONFLICT' }
    view.rerender(<QueryClientProvider client={new QueryClient()}><MemoryRouter initialEntries={['/chat/chat']}><Routes><Route path="/chat/:id" element={<Chat />} /></Routes></MemoryRouter></QueryClientProvider>)
    await user.click(await screen.findByRole('button', { name: /reenviar/i }))
    await waitFor(() => expect(mocks.send).toHaveBeenLastCalledWith('chat', 'Mude o fundo', [], { mode: 'edit', baseVersionId: 'v2' }))
    expect(mocks.send).toHaveBeenCalledTimes(2)
  })
})
