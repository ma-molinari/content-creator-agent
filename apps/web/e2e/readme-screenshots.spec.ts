import { mkdirSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { Buffer } from 'node:buffer'

import { expect, test, type Page } from '@playwright/test'

const __dirname = dirname(fileURLToPath(import.meta.url))
const outDir = join(__dirname, '..', '..', '..', 'docs', 'images', 'readme')

const CHAT_ID = '00000000-0000-4000-8000-0000000000a1'
const CHAT_B = '00000000-0000-4000-8000-0000000000a2'
const CHAT_C = '00000000-0000-4000-8000-0000000000a3'
const USER_ID = '00000000-0000-4000-8000-0000000000f0'
const USER_MSG_ID = '00000000-0000-4000-8000-0000000000b1'
const ASST_MSG_ID = '00000000-0000-4000-8000-0000000000b2'
const IMG_ID = '00000000-0000-4000-8000-0000000000b3'
const ISO = '2026-01-15T12:00:00.000Z'

const MIN_JPEG = Buffer.from(
  '/9j/4AAQSkZJRgABAQAASABIAAD/4QBMRXhpZgAATU0AKgAAAAgAAYdpAAQAAAABAAAAGgAAAAAAA6ABAAMAAAABAAEAAKACAAQAAAABAAAAEKADAAQAAAABAAAACgAAAAD/7QA4UGhvdG9zaG9wIDMuMAA4QklNBAQAAAAAAAA4QklNBCUAAAAAABDUHYzZjwCyBOmACZjs+EJ+/8AAEQgACgAQAwEiAAIRAQMRAf/EAB8AAAEFAQEBAQEBAAAAAAAAAAABAgMEBQYHCAkKC//EALUQAAIBAwMCBAMFBQQEAAABfQECAwAEEQUSITFBBhNRYQcicRQygZGhCCNCscEVUtHwJDNicoIJChYXGBkaJSYnKCkqNDU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6g4SFhoeIiYqSk5SVlpeYmZqio6Slpqeoqaqys7S1tre4ubrCw8TFxsfIycrS09TV1tfY2drh4uPk5ebn6Onq8fLz9PX29/j5+v/EAB8BAAMBAQEBAQEBAQEAAAAAAAABAgMEBQYHCAkKC//EALURAAIBAgQEAwQHBQQEAAECdwABAgMRBAUhMQYSQVEHYXETIjKBCBRCkaGxwQkjM1LwFWJy0QoWJDThJfEXGBkaJicoKSo1Njc4OTpDREVGR0hJSlNUVVZXWFlaY2RlZmdoaWpzdHV2d3h5eoKDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uLj5OXm5+jp6vLz9PX29/j5+v/bAEMAExMTExMTIBMTIC0gICAtPS0tLS09TT09PT09TV1NTU1NTU1dXV1dXV1dXXBwcHBwcIODg4ODk5OTk5OTk5OTk//bAEMBFxgYJSMlQCMjQJloVWiZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmZmf/dAAQAAf/aAAwDAQACEQMRAD8A69mkBO1c0B5twygx9amooA//2Q==',
  'base64',
)

const recentChats = [
  {
    id: CHAT_ID,
    userId: USER_ID,
    postType: 'carousel',
    title: 'Guia de autocuidado para profissionais autônomas',
    createdAt: ISO,
    updatedAt: ISO,
    contents: [],
  },
  {
    id: CHAT_B,
    userId: USER_ID,
    postType: 'single',
    title: 'Legenda para lançamento da nova mentoria',
    createdAt: '2026-01-12T09:30:00.000Z',
    updatedAt: '2026-01-12T09:30:00.000Z',
    contents: [],
  },
  {
    id: CHAT_C,
    userId: USER_ID,
    postType: 'carousel',
    title: 'Checklist de branding para Instagram',
    createdAt: '2026-01-08T14:00:00.000Z',
    updatedAt: '2026-01-08T14:00:00.000Z',
    contents: [],
  },
]

const chatWithSlides = {
  id: CHAT_ID,
  userId: USER_ID,
  postType: 'carousel',
  title: 'Guia de autocuidado para profissionais autônomas',
  createdAt: ISO,
  updatedAt: ISO,
  contents: [
    {
      id: USER_MSG_ID,
      chatId: CHAT_ID,
      role: 'user',
      content:
        'Crie um carrossel com 5 slides sobre autocuidado para profissionais autônomas, com tom acolhedor e prático.',
      createdAt: ISO,
      updatedAt: ISO,
      images: [],
    },
    {
      id: ASST_MSG_ID,
      chatId: CHAT_ID,
      role: 'assistant',
      content:
        'Monte um carrossel com abertura forte, dicas práticas e um fechamento com convite para salvar o post.',
      createdAt: ISO,
      updatedAt: ISO,
      images: [
        {
          id: IMG_ID,
          chatContentId: ASST_MSG_ID,
          s3Key: 'readme/slide-1.jpg',
          url: 'https://example.test/readme/slide-1.jpg',
          slideNumber: 1,
          createdAt: ISO,
          updatedAt: ISO,
        },
      ],
    },
  ],
}

const profileResponse = {
  auditText: `Falo com mulheres adultas que querem conciliar trabalho, rotina e bem-estar emocional sem cair em fórmulas prontas.

No meu feed já funcionam conteúdos práticos com títulos claros, linguagem direta e exemplos do dia a dia. Quero melhorar a consistência visual e deixar os carrosséis mais memoráveis.`,
  brandText: `Ajudo profissionais autônomas a comunicar autoridade com acolhimento, clareza e estética editorial.

Cada post deve deixar uma reflexão útil e um próximo passo possível. Evitar tom professoral, promessas milagrosas e clichês genéricos de produtividade.`,
  configured: true,
  references: [],
}

test.beforeAll(() => {
  mkdirSync(outDir, { recursive: true })
})

test.describe('README screenshots (mocked API)', () => {
  test.beforeEach(async ({ page }) => {
    await preparePage(page)
  })

  test('login', async ({ page }) => {
    await page.route('**/api/auth/refresh', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({}),
      })
    })

    await page.goto('/login')
    await expect(page.getByRole('heading', { name: 'Entrar' })).toBeVisible()
    await page.screenshot({ path: join(outDir, 'login.png'), fullPage: true })
  })

  test('profile brand', async ({ page }) => {
    await mockAuthenticatedShell(page)
    await page.route('**/api/profile', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(profileResponse),
      })
    })

    await page.goto('/profile')
    await expect(page.locator('#audit-md')).toHaveValue(/Falo com mulheres adultas/)
    await page.getByRole('button', { name: 'Continuar' }).click()
    await expect(page.locator('#brand-md')).toBeVisible()
    await expect(page.locator('#brand-md')).toHaveValue(/Ajudo profissionais autônomas/)
    await page.screenshot({ path: join(outDir, 'profile-brand.png'), fullPage: true })
  })

  test('chat with slides', async ({ page }) => {
    await mockAuthenticatedShell(page)
    await page.route(`**/api/chats/${CHAT_ID}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(chatWithSlides),
      })
    })
    await page.route(`**/api/chats/${CHAT_ID}/files/${IMG_ID}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'image/jpeg',
        body: MIN_JPEG,
      })
    })

    await page.goto(`/chat/${CHAT_ID}`)
    await expect(page.getByText('Slides prontos')).toBeVisible()
    await expect(page.getByRole('button', { name: /Abrir slide 1 de 1/i })).toBeVisible()
    await page.screenshot({ path: join(outDir, 'chat-slides.png'), fullPage: true })
  })

  test('history', async ({ page }) => {
    await mockAuthenticatedShell(page)

    await page.goto('/history')
    await expect(page.getByRole('heading', { name: 'Histórico' })).toBeVisible()
    await expect(
      page.getByRole('button', {
        name: /Guia de autocuidado para profissionais autônomas Carrossel ·/,
      }),
    ).toBeVisible()
    await page.screenshot({ path: join(outDir, 'history.png'), fullPage: true })
  })
})

async function preparePage(page: Page) {
  await page.setViewportSize({ width: 1440, height: 1200 })
  await page.emulateMedia({ colorScheme: 'dark' })
  await page.addInitScript(() => {
    localStorage.setItem('onboarding:tour_done', '1')
    localStorage.setItem('onboarding:hint:profile-brand', '1')
    localStorage.setItem('onboarding:hint:history-list', '1')
    localStorage.setItem('onboarding:hint:chat-composer', '1')
  })
}

async function mockAuthenticatedShell(page: Page) {
  await page.route('**/api/auth/refresh', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ accessToken: 'readme-fake-access-token' }),
    })
  })
  await page.route('**/api/setup/status', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ configured: true }),
    })
  })
  await page.route('**/api/chats', async (route) => {
    const req = route.request()
    const path = new URL(req.url()).pathname
    if (req.method() === 'GET' && path === '/api/chats') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(recentChats),
      })
      return
    }
    await route.continue()
  })
}
