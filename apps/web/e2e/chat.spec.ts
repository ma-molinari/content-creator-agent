import { Buffer } from 'node:buffer'

import { expect, test } from '@playwright/test'

const CHAT_ID = '00000000-0000-4000-8000-000000000001'
const JOB_ID = '00000000-0000-4000-8000-000000000002'
const USER_ID = '00000000-0000-4000-8000-000000000003'
const USER_MSG_ID = '00000000-0000-4000-8000-000000000010'
const ASST_MSG_ID = '00000000-0000-4000-8000-000000000011'
const IMG_ID = '00000000-0000-4000-8000-000000000012'

const iso = '2026-01-15T12:00:00.000Z'

/** 1×1 JPEG — SlideViewer now loads slides via GET /chats/:id/files/:fileId (blob). */
const MIN_JPEG = Buffer.from(
  '/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMiIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAf/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAP/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCdABmX/2Q==',
  'base64',
)

test.describe('chat (mocked API)', () => {
  test('send message → job done → SlideViewer + download ZIP', async ({ page }) => {
    let jobPolls = 0
    let jobDone = false
    let userMessagePersisted = false

    await page.route('**/api/**', async (route) => {
      const req = route.request()
      const method = req.method()
      const path = new URL(req.url()).pathname

      if (path === '/api/auth/refresh' && method === 'POST') {
        await route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({}),
        })
        return
      }
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
        userMessagePersisted = true
        await route.fulfill({
          status: 202,
          contentType: 'application/json',
          body: JSON.stringify({ jobId: JOB_ID }),
        })
        return
      }
      if (path === `/api/chats/${CHAT_ID}/files/${IMG_ID}` && method === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'image/jpeg',
          body: MIN_JPEG,
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
        if (userMessagePersisted && !jobDone) {
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
              ],
            }),
          })
          return
        }
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
                    url: 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/PNG_transparency_demonstration_1.png/280px-PNG_transparency_demonstration_1.png',
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
    await expect(page.getByText('Olá e2e', { exact: true })).toHaveCount(1, { timeout: 10_000 })

    await expect(page.getByText('Slides prontos.')).toBeVisible({ timeout: 15_000 })
    await expect(page.locator('img').first()).toBeVisible()

    await expect(page.getByTitle('Baixar todos os slides (ZIP)')).toBeVisible()
  })
})
