import { expect, test } from '@playwright/test'

test.describe('auth — erros de formulário (API mockada)', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/auth/refresh', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({}),
      })
    })
  })

  test('login com credenciais inválidas exibe mensagem de erro', async ({ page }) => {
    await page.route('**/api/auth/login', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'invalid credentials' }),
      })
    })

    const refresh = page.waitForResponse((res) => res.url().includes('/api/auth/refresh'))
    await page.goto('/login')
    await refresh
    await page.getByLabel('Email').fill('wrong@example.com')
    await page.locator('#password').fill('wrongpassword')
    await page.getByRole('button', { name: 'Entrar' }).click()

    await expect(page.getByRole('alert')).toContainText('Email ou senha incorretos.')
  })

  test('register com email duplicado (409) exibe mensagem de erro', async ({ page }) => {
    await page.route('**/api/auth/register', async (route) => {
      await route.fulfill({
        status: 409,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'email already exists' }),
      })
    })

    await page.goto('/register')
    await page.getByLabel('Email').fill('existing@example.com')
    await page.locator('#password').fill('password12')
    await page.locator('#confirm').fill('password12')
    await page.getByRole('button', { name: 'Criar conta' }).click()

    await expect(page.getByRole('alert')).toContainText('Este email já está cadastrado.')
  })

  test('register com senhas divergentes exibe erro de validação', async ({ page }) => {
    await page.goto('/register')
    await page.getByLabel('Email').fill('new@example.com')
    await page.locator('#password').fill('password12')
    await page.locator('#confirm').fill('different12')
    await page.getByRole('button', { name: 'Criar conta' }).click()

    await expect(page.getByRole('alert')).toContainText('As senhas não coincidem.')
  })
})

test.describe('auth — route guards (API mockada)', () => {
  test('acesso a rota protegida sem token redireciona para /login', async ({ page }) => {
    await page.route('**/api/auth/refresh', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({}),
      })
    })

    await page.goto('/history')
    await expect(page).toHaveURL(/\/login$/)
  })

  test('acesso a /login com sessão ativa redireciona para /', async ({ page }) => {
    await page.route('**/api/auth/refresh', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ accessToken: 'e2e-active-token' }),
      })
    })
    await page.route('**/api/setup/status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ configured: true }),
      })
    })

    await page.goto('/login')
    await expect(page).toHaveURL('/')
  })
})
