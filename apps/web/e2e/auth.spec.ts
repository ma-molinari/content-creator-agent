import { expect, test } from '@playwright/test'

test.describe('auth (mocked API)', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/auth/refresh', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({}),
      })
    })
  })

  test('register flow — SecurityKeyModal → login', async ({ page }) => {
    await page.route('**/api/auth/register', async (route) => {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({ securityKey: 'e2e-security-key-00000001' }),
      })
    })

    await page.goto('/register')
    await page.getByLabel('Email').fill('e2e-register@example.com')
    await page.getByLabel('Senha').first().fill('password12')
    await page.getByLabel('Confirmar senha').fill('password12')
    await page.getByRole('button', { name: 'Criar conta' }).click()

    await expect(page.getByRole('alertdialog')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Sua chave de segurança' })).toBeVisible()
    await expect(page.locator('code').filter({ hasText: 'e2e-security-key' })).toBeVisible()

    await page.getByRole('checkbox', { name: /Confirmo que salvei/i }).check()
    await page.getByRole('button', { name: 'Continuar para o login' }).click()

    await expect(page).toHaveURL(/\/login$/)
  })

  test('login flow — redirects to home', async ({ page }) => {
    await page.route('**/api/auth/login', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ accessToken: 'e2e-fake-access-token' }),
      })
    })

    await page.goto('/login')
    await page.getByLabel('Email').fill('e2e-login@example.com')
    await page.locator('#password').fill('password12')
    await page.getByRole('button', { name: 'Entrar' }).click()

    await expect(page).toHaveURL(/\/?$/)
  })
})
