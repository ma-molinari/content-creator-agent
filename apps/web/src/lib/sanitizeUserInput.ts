import type { ChatContent } from '@/api/chats'

// Mirrors apps/api/internal/chat/post_message.go (SanitizeUserInput, stripHTML, stripControlChars).

const htmlTagPattern = /<[^>]+>/g

function stripHTML(s: string): string {
  return s.replace(htmlTagPattern, '')
}

function isGoControlRune(r: number): boolean {
  if (r === 0x0a || r === 0x09) return false
  return (r >= 0x0 && r <= 0x1f) || r === 0x7f || (r >= 0x80 && r <= 0x9f)
}

function stripControlChars(s: string): string {
  let out = ''
  for (const ch of s) {
    const cp = ch.codePointAt(0) ?? 0
    if (isGoControlRune(cp)) continue
    out += ch
  }
  return out
}

/** Same semantics as the API: strip HTML tags, remove control runes (keep newline and tab), trim. */
export function sanitizeUserInput(s: string): string {
  let x = stripHTML(s)
  x = stripControlChars(x)
  return x.trim()
}

/**
 * True if some user message in `contents` (searching from the end) already matches the text
 * the server would have stored for this pending send.
 */
export function serverUserMessageCoversPending(
  contents: ChatContent[],
  pendingText: string,
): boolean {
  const normalizedPending = sanitizeUserInput(pendingText)
  if (!normalizedPending) return false
  for (let i = contents.length - 1; i >= 0; i--) {
    if (contents[i].role !== 'user') continue
    if (contents[i].content === normalizedPending) return true
  }
  return false
}
