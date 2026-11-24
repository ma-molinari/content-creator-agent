import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { MessageAssistant } from './MessageAssistant'

afterEach(cleanup)

describe('créditos das imagens', () => {
  it('mostra links de origem e licença sem incluir separadores no endereço', () => {
    const content = 'Foto — https://commons.wikimedia.org/wiki/File:Exemplo — https://creativecommons.org/publicdomain/zero/1.0/; outra'
    render(<MessageAssistant isLatestVersion message={{ id: 'a', chatId: 'c', role: 'assistant', content, images: [], createdAt: '2026-01-01T00:00:00Z', updatedAt: '2026-01-01T00:00:00Z' }} />)
    const links = screen.getAllByRole('link')
    expect(links).toHaveLength(2)
    expect(links[0].getAttribute('href')).toBe('https://commons.wikimedia.org/wiki/File:Exemplo')
    expect(links[1].getAttribute('href')).toBe('https://creativecommons.org/publicdomain/zero/1.0/')
    expect(links[1].getAttribute('rel')).toContain('noopener')
  })
})
