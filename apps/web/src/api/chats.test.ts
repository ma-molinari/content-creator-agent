import { beforeEach, describe, expect, it, vi } from 'vitest'

const post = vi.hoisted(() => vi.fn())
vi.mock('@/api/client', () => ({ api: { post } }))

import { postChatMessage } from './chats'

beforeEach(() => post.mockReset())

describe('postChatMessage', () => {
  it('sends structured mode and version in JSON', async () => {
    post.mockResolvedValue({ data: { jobId: 'job' } })
    await postChatMessage('chat', 'edite', [], { mode: 'edit', baseVersionId: 'version' })
    expect(post).toHaveBeenCalledWith('/chats/chat/messages', {
      content: 'edite', mode: 'edit', baseVersionId: 'version',
    })
  })

  it('sends structured fields alongside multipart attachments', async () => {
    post.mockResolvedValue({ data: { jobId: 'job' } })
    const file = new File(['image'], 'ref.png', { type: 'image/png' })
    await postChatMessage('chat', 'crie', [file], { mode: 'create' })
    const form = post.mock.calls[0][1] as FormData
    expect(form.get('content')).toBe('crie')
    expect(form.get('mode')).toBe('create')
    expect(form.get('baseVersionId')).toBeNull()
    expect(form.getAll('attachments')).toHaveLength(1)
  })

  it('preserves the legacy payload when mode is absent', async () => {
    post.mockResolvedValue({ data: { jobId: 'job' } })
    await postChatMessage('chat', 'post')
    expect(post).toHaveBeenCalledWith('/chats/chat/messages', { content: 'post' })
  })
})
