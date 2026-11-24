import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import { AppShell } from './AppShell'

vi.mock('@/components/onboarding', () => ({ OnboardingTour: () => null }))
vi.mock('@/components/shell/SidebarRail', () => ({ SidebarRail: () => null }))

describe('AppShell', () => {
  it('identifica o uso do Openverse e a ausência de endosso', () => {
    render(<MemoryRouter><AppShell /></MemoryRouter>)

    expect(screen.getByRole('link', { name: 'Openverse' })).toHaveAttribute('href', 'https://openverse.org/')
    expect(screen.getByText(/não é endossado nem certificado por ele/i)).toBeVisible()
  })
})
