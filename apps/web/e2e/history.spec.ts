import { expect, test } from '@playwright/test'

const CHAT_A = '00000000-0000-4000-8000-0000000000a1'
const iso = '2026-01-10T10:00:00.000Z'

test.describe('history (mocked API)', () => {
  test('shows list of chats and delete with confirmation', async ({ page }) => {
    let deleteCalls = 0
    let deleted = false

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
      if (path === '/api/chats' && method === 'GET') {
        if (deleted) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify([]),
          })
          return
        }
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            {
              id: CHAT_A,
              userId: '00000000-0000-4000-8000-000000000003',
              postType: 'carousel',
              title: 'Histórico e2e',
              createdAt: iso,
              updatedAt: iso,
              contents: [],
            },
          ]),
        })
        return
      }
      if (path === `/api/chats/${CHAT_A}` && method === 'DELETE') {
        deleteCalls++
        deleted = true
        await route.fulfill({ status: 204 })
        return
      }

      await route.continue()
    })

    await page.goto('/login')
    await page.getByLabel('Email').fill('e2e-hist@example.com')
    await page.locator('#password').fill('password12')
    await page.getByRole('button', { name: 'Entrar' }).click()

    await page.getByRole('link', { name: 'Histórico' }).click()

    await expect(page.getByRole('heading', { name: 'Histórico' })).toBeVisible()
    const historyItem = page.getByRole('button', { name: /Histórico e2e Carrossel ·/ })
    await expect(historyItem).toBeVisible()

    await page.getByTitle('Excluir').first().click()
    await expect(page.getByRole('heading', { name: 'Excluir chat' })).toBeVisible()
    await page.getByRole('alertdialog').getByRole('button', { name: 'Excluir' }).click()

    await expect.poll(() => deleteCalls).toBe(1)
    await expect(historyItem).not.toBeVisible()
  })

  test('clicar em item da lista navega para /chat/:id', async ({ page }) => {
    await page.route('**/api/**', async (route) => {
      const req = route.request()
      const method = req.method()
      const path = new URL(req.url()).pathname

      if (path === '/api/auth/refresh' && method === 'POST') {
        await route.fulfill({ status: 401, contentType: 'application/json', body: '{}' })
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
      if (path === '/api/chats' && method === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            {
              id: CHAT_A,
              userId: '00000000-0000-4000-8000-000000000003',
              postType: 'carousel',
              title: 'Histórico e2e',
              createdAt: iso,
              updatedAt: iso,
              contents: [],
            },
          ]),
        })
        return
      }
      if (path === `/api/chats/${CHAT_A}` && method === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: CHAT_A,
            userId: '00000000-0000-4000-8000-000000000003',
            postType: 'carousel',
            title: 'Histórico e2e',
            createdAt: iso,
            updatedAt: iso,
            contents: [],
          }),
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
      await route.continue()
    })

    await page.goto('/login')
    await page.getByLabel('Email').fill('e2e-hist-nav@example.com')
    await page.locator('#password').fill('password12')
    await page.getByRole('button', { name: 'Entrar' }).click()

    await page.getByRole('link', { name: 'Histórico' }).click()
    const historyItem = page.getByRole('button', { name: /Histórico e2e Carrossel ·/ })
    await expect(historyItem).toBeVisible()

    await historyItem.click()
    await expect(page).toHaveURL(new RegExp(`/chat/${CHAT_A}`))
  })
})
