import { mkdirSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { expect, test } from '@playwright/test'

const __dirname = dirname(fileURLToPath(import.meta.url))
const outDir = join(__dirname, '..', 'playwright-output', 'screenshots')

test.beforeAll(() => {
  mkdirSync(outDir, { recursive: true })
})

test.describe('UI — screenshots (build de produção)', () => {
  test('login (desktop)', async ({ page }) => {
    await page.goto('/login')
    await expect(page.getByRole('heading', { name: 'Entrar' })).toBeVisible()
    await page.screenshot({ path: join(outDir, 'login-desktop.png'), fullPage: true })
  })

  test('register (desktop)', async ({ page }) => {
    await page.goto('/register')
    await expect(page.getByRole('heading', { name: 'Criar conta' })).toBeVisible()
    await page.screenshot({ path: join(outDir, 'register-desktop.png'), fullPage: true })
  })

  test('login (mobile)', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/login')
    await expect(page.getByRole('heading', { name: 'Entrar' })).toBeVisible()
    await page.screenshot({ path: join(outDir, 'login-mobile.png'), fullPage: true })
  })

  test('register (mobile)', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/register')
    await expect(page.getByRole('heading', { name: 'Criar conta' })).toBeVisible()
    await page.screenshot({ path: join(outDir, 'register-mobile.png'), fullPage: true })
  })
})
