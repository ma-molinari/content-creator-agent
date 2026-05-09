import { Buffer } from 'node:buffer'

import { expect, test, type Page } from '@playwright/test'

const REF_ID = '00000000-0000-4000-8000-000000000001'

const emptyProfile = {
  auditText: '',
  brandText: '',
  configured: false,
  references: [] as Array<{ id: string; url: string }>,
}

async function bootstrapAsAuthenticated(page: Page) {
  await page.route('**/api/auth/refresh', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ accessToken: 'e2e-profile-token' }),
    })
  })
  await page.route('**/api/chats', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    })
  })
}

test.describe('profile (API mockada)', () => {
  test('carrega perfil existente com campos preenchidos', async ({ page }) => {
    await bootstrapAsAuthenticated(page)
    await page.route('**/api/profile', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          auditText: '# Auditoria\nConteúdo do audit',
          brandText: '# Marca\nConteúdo do brand',
          configured: true,
          references: [],
        }),
      })
    })

    await page.goto('/profile')
    await expect(page.locator('#audit-md')).toHaveValue('# Auditoria\nConteúdo do audit')
    await page.getByRole('button', { name: 'Continuar' }).click()
    await expect(page.locator('#brand-md')).toHaveValue('# Marca\nConteúdo do brand')
  })

  test('salva perfil com sucesso e exibe toast de confirmação', async ({ page }) => {
    await page.route('**/api/**', async (route) => {
      const req = route.request()
      const method = req.method()
      const path = new URL(req.url()).pathname

      if (path === '/api/auth/refresh' && method === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ accessToken: 'e2e-token' }),
        })
        return
      }
      if (path === '/api/profile' && method === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(emptyProfile),
        })
        return
      }
      if (path === '/api/chats' && method === 'GET') {
        await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
        return
      }
      if (path === '/api/profile' && method === 'PUT') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ ...emptyProfile, auditText: 'Meu audit', brandText: 'Minha marca', configured: true }),
        })
        return
      }
      await route.continue()
    })

    await page.goto('/profile')
    await page.locator('#audit-md').fill('Meu audit')
    await page.getByRole('button', { name: 'Continuar' }).click()
    await page.locator('#brand-md').fill('Minha marca')
    await page.getByRole('button', { name: 'Continuar' }).click()
    await page.getByRole('button', { name: 'Salvar perfil' }).click()

    await expect(page.getByRole('status')).toContainText('Perfil salvo.')
  })

  test('exibe erro quando salvar falha', async ({ page }) => {
    await page.route('**/api/**', async (route) => {
      const req = route.request()
      const method = req.method()
      const path = new URL(req.url()).pathname

      if (path === '/api/auth/refresh' && method === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ accessToken: 'e2e-token' }),
        })
        return
      }
      if (path === '/api/profile' && method === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(emptyProfile),
        })
        return
      }
      if (path === '/api/chats' && method === 'GET') {
        await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
        return
      }
      if (path === '/api/profile' && method === 'PUT') {
        await route.fulfill({ status: 500 })
        return
      }
      await route.continue()
    })

    await page.goto('/profile')
    await page.locator('#audit-md').fill('Texto qualquer')
    await page.getByRole('button', { name: 'Continuar' }).click()
    await page.locator('#brand-md').fill('Marca qualquer')
    await page.getByRole('button', { name: 'Continuar' }).click()
    await page.getByRole('button', { name: 'Salvar perfil' }).click()

    await expect(page.getByRole('status')).toContainText('Não foi possível salvar.')
  })

  test('upload de referência exibe thumbnail na lista', async ({ page }) => {
    let hasRef = false

    await page.route('**/api/**', async (route) => {
      const req = route.request()
      const method = req.method()
      const path = new URL(req.url()).pathname

      if (path === '/api/auth/refresh' && method === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ accessToken: 'e2e-token' }),
        })
        return
      }
      if (path === '/api/profile' && method === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(
            hasRef
              ? { ...emptyProfile, references: [{ id: REF_ID, url: 'https://placehold.co/100x100/png' }] }
              : emptyProfile,
          ),
        })
        return
      }
      if (path === '/api/chats' && method === 'GET') {
        await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
        return
      }
      if (path === '/api/profile/references' && method === 'POST') {
        hasRef = true
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            ...emptyProfile,
            references: [{ id: REF_ID, url: 'https://placehold.co/100x100/png' }],
          }),
        })
        return
      }
      await route.continue()
    })

    await page.goto('/profile')
    await page.getByRole('button', { name: /Referências/ }).click()

    const fakeImage = Buffer.from(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
      'base64',
    )
    await page.locator('input[type="file"][accept*="image"]').setInputFiles({
      name: 'ref.png',
      mimeType: 'image/png',
      buffer: fakeImage,
    })

    await expect(page.locator('img[src*="placehold.co"]')).toBeVisible({ timeout: 5_000 })
  })

  test('delete de referência remove imagem da lista', async ({ page }) => {
    let deleted = false

    await page.route('**/api/**', async (route) => {
      const req = route.request()
      const method = req.method()
      const path = new URL(req.url()).pathname

      if (path === '/api/auth/refresh' && method === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ accessToken: 'e2e-token' }),
        })
        return
      }
      if (path === '/api/profile' && method === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(
            deleted
              ? emptyProfile
              : { ...emptyProfile, references: [{ id: REF_ID, url: 'https://placehold.co/100x100/png' }] },
          ),
        })
        return
      }
      if (path === '/api/chats' && method === 'GET') {
        await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
        return
      }
      if (path === `/api/profile/references/${REF_ID}` && method === 'DELETE') {
        deleted = true
        await route.fulfill({ status: 204 })
        return
      }
      await route.continue()
    })

    await page.goto('/profile')
    await page.getByRole('button', { name: /Referências/ }).click()
    await expect(page.locator('img[src*="placehold.co"]')).toBeVisible()

    await page.getByTitle('Remover').click()
    await page.getByRole('button', { name: 'Remover' }).last().click()

    await expect(page.locator('img[src*="placehold.co"]')).not.toBeVisible({ timeout: 5_000 })
  })

  test('link "Perfil" no sidebar navega para /profile', async ({ page }) => {
    await bootstrapAsAuthenticated(page)
    await page.route('**/api/setup/status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ configured: true }),
      })
    })
    await page.route('**/api/profile', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(emptyProfile),
      })
    })

    await page.goto('/')
    await page.getByRole('link', { name: 'Perfil' }).click()

    await expect(page).toHaveURL(/\/profile$/)
    await expect(page.getByRole('heading', { name: 'Perfil da marca' })).toBeVisible()
  })
})
