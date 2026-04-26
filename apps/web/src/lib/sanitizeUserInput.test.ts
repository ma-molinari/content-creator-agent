import { describe, expect, it } from 'vitest'

import type { ChatContent } from '@/api/chats'

import { sanitizeUserInput, serverUserMessageCoversPending } from './sanitizeUserInput'

const iso = '2026-01-15T12:00:00.000Z'
const CHAT = 'c'

function user(id: string, content: string): ChatContent {
  return {
    id,
    chatId: CHAT,
    role: 'user',
    content,
    createdAt: iso,
    updatedAt: iso,
    images: [],
  }
}

function assistant(id: string, content: string): ChatContent {
  return {
    id,
    chatId: CHAT,
    role: 'assistant',
    content,
    createdAt: iso,
    updatedAt: iso,
    images: [],
  }
}

describe('sanitizeUserInput', () => {
  it('strips HTML tags and trims', () => {
    expect(sanitizeUserInput('  <b>hello</b>  ')).toBe('hello')
  })

  it('removes disallowed control runes; trim strips leading/trailing space including tab', () => {
    expect(sanitizeUserInput('a\u0000b\nc\t')).toBe('ab\nc')
  })
})

describe('serverUserMessageCoversPending', () => {
  it('returns false when the last line is assistant but a prior user matches pending (sanitized)', () => {
    const contents: ChatContent[] = [
      user('1', 'keep'),
      assistant('2', '...'),
    ]
    expect(serverUserMessageCoversPending(contents, 'keep')).toBe(true)
  })

  it('finds the last user from the end when multiple user rows exist', () => {
    const contents: ChatContent[] = [user('1', 'a'), user('2', 'b')]
    expect(serverUserMessageCoversPending(contents, 'b')).toBe(true)
    expect(serverUserMessageCoversPending(contents, 'a')).toBe(true)
  })

  it('matches when pending had HTML and server row is stripped', () => {
    const contents: ChatContent[] = [user('1', 'Hello')]
    expect(serverUserMessageCoversPending(contents, '<p>Hello</p>')).toBe(true)
  })

  it('returns false when no user message matches', () => {
    const contents: ChatContent[] = [user('1', 'other')]
    expect(serverUserMessageCoversPending(contents, 'nomatch')).toBe(false)
  })
})
