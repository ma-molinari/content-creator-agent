import { expect, test } from '@playwright/test'

const CHAT_ID = '00000000-0000-4000-8000-000000000001'
const JOB_ID = '00000000-0000-4000-8000-000000000002'
const USER_ID = '00000000-0000-4000-8000-000000000003'
const USER_MSG_ID = '00000000-0000-4000-8000-000000000010'
const ASST_MSG_ID = '00000000-0000-4000-8000-000000000011'
const IMG_ID = '00000000-0000-4000-8000-000000000012'

const iso = '2026-01-15T12:00:00.000Z'

test.describe('chat (mocked API)', () => {
  test('send message → job done → SlideViewer + download ZIP', async ({ page }) => {
    let jobPolls = 0
    let jobDone = false

    await page.route('**/api/**', async (route) => {
      const req = route.request()
      const method = req.method()
      const path = new URL(req.url()).pathname

      if (path === '/api/auth/login' && method === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ accessToken: 'e2e-token' }),
        })
        return
      }
      if (path === '/api/setup/status' && method === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ configured: true }),
        })
        return
      }
      if (path === '/api/chats' && method === 'POST') {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: CHAT_ID,
            userId: USER_ID,
            postType: 'carousel',
            title: 'E2E chat',
            createdAt: iso,
            updatedAt: iso,
            contents: [],
          }),
        })
        return
      }
      if (path === `/api/chats/${CHAT_ID}/messages` && method === 'POST') {
        await route.fulfill({
          status: 202,
          contentType: 'application/json',
          body: JSON.stringify({ jobId: JOB_ID }),
        })
        return
      }
      if (path === `/api/chats/${CHAT_ID}/jobs/${JOB_ID}/status` && method === 'GET') {
        jobPolls++
        const status = jobPolls >= 2 ? 'done' : 'processing'
        if (status === 'done') jobDone = true
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ jobId: JOB_ID, status, error: null }),
        })
        return
      }
      if (path === `/api/chats/${CHAT_ID}` && method === 'GET') {
        if (!jobDone) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              id: CHAT_ID,
              userId: USER_ID,
              postType: 'carousel',
              title: 'E2E chat',
              createdAt: iso,
              updatedAt: iso,
              contents: [],
            }),
          })
          return
        }
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: CHAT_ID,
            userId: USER_ID,
            postType: 'carousel',
            title: 'E2E chat',
            createdAt: iso,
            updatedAt: iso,
            contents: [
              {
                id: USER_MSG_ID,
                chatId: CHAT_ID,
                role: 'user',
                content: 'Olá e2e',
                createdAt: iso,
                updatedAt: iso,
                images: [],
              },
              {
                id: ASST_MSG_ID,
                chatId: CHAT_ID,
                role: 'assistant',
                content: 'Slides prontos.',
                createdAt: iso,
                updatedAt: iso,
                images: [
                  {
                    id: IMG_ID,
                    chatContentId: ASST_MSG_ID,
                    s3Key: 'e2e/slide.jpg',
                    url: 'https://example.com/preview.jpg',
                    slideNumber: 1,
                    createdAt: iso,
                    updatedAt: iso,
                  },
                ],
              },
            ],
          }),
        })
        return
      }
      if (path === `/api/chats/${CHAT_ID}/files` && method === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            {
              id: 'f1',
              fileName: 'slide_1.jpeg',
              mimeType: 'image/jpeg',
              downloadUrl:
                'https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/PNG_transparency_demonstration_1.png/280px-PNG_transparency_demonstration_1.png',
            },
          ]),
        })
        return
      }

      await route.continue()
    })

    await page.goto('/login')
    await page.getByLabel('Email').fill('e2e-chat@example.com')
    await page.locator('#password').fill('password12')
    await page.getByRole('button', { name: 'Entrar' }).click()

    await expect(page).toHaveURL('/')

    await page.getByLabel('Mensagem').fill('Olá e2e')
    await page.getByRole('button', { name: 'Enviar' }).click()

    await expect(page).toHaveURL(new RegExp(`/chat/${CHAT_ID}`))

    await expect(page.getByText('Slides prontos.')).toBeVisible({ timeout: 15_000 })
    await expect(page.locator('img').first()).toBeVisible()

    await expect(page.getByTitle('Baixar todos os slides (ZIP)')).toBeVisible()
  })
})
