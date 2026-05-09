import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ComposerBar } from './ComposerBar'

afterEach(() => {
  cleanup()
})

describe('ComposerBar', () => {
  it('keeps text when onSend rejects', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn().mockRejectedValue(new Error('fail'))
    render(<ComposerBar onSend={onSend} />)
    const input = screen.getByRole('textbox', { name: /mensagem/i })
    await user.type(input, 'hello')
    await user.click(screen.getByRole('button', { name: /enviar/i }))
    expect(onSend).toHaveBeenCalledWith('hello', [], { postType: 'carousel' })
    expect(input).toHaveValue('hello')
  })

  it('clears text when onSend resolves', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn().mockResolvedValue(undefined)
    render(<ComposerBar onSend={onSend} />)
    const input = screen.getByRole('textbox', { name: /mensagem/i })
    await user.type(input, 'hello')
    await user.click(screen.getByRole('button', { name: /enviar/i }))
    expect(onSend).toHaveBeenCalledWith('hello', [], { postType: 'carousel' })
    expect(input).toHaveValue('')
  })
})
