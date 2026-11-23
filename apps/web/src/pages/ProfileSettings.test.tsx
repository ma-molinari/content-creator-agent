import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({ save: vi.fn() }))
vi.mock('@/api/profile', () => ({
  useProfile: () => ({ isLoading: false, data: { auditText: '', brandText: '', references: [], configured: false } }),
  useSaveProfile: () => ({ mutateAsync: mocks.save, isPending: false }),
  useUploadReference: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDeleteReference: () => ({ mutateAsync: vi.fn(), isPending: false }),
}))
vi.mock('@/components/onboarding', () => ({ OnboardingHint: () => null }))
vi.mock('@/lib/toast', () => ({ toast: { error: vi.fn(), success: vi.fn() } }))

import ProfileSettings from './ProfileSettings'

beforeEach(() => mocks.save.mockReset().mockResolvedValue({}))
afterEach(() => { cleanup(); vi.restoreAllMocks() })

describe('exemplos de perfil', () => {
  it.each([
    ['Bem-estar', 'saúde emocional', 'nomear emoções'],
    ['Educação', 'aprender habilidades', 'ensina conceitos'],
    ['Negócio local', 'negócio local', 'atendimento atencioso'],
  ])('preenche os dois campos para %s e permite editar antes de salvar', async (label, audit, brand) => {
    const user = userEvent.setup()
    render(<MemoryRouter><ProfileSettings /></MemoryRouter>)
    await user.click(screen.getByText('Escolher um exemplo'))
    await user.click(screen.getByRole('button', { name: new RegExp(label, 'i') }))
    const auditInput = screen.getByRole('textbox', { name: /como é o seu perfil hoje/i })
    expect((auditInput as HTMLTextAreaElement).value).toContain(audit)
    await user.clear(auditInput)
    await user.type(auditInput, 'Meu perfil personalizado')
    await user.click(screen.getByRole('button', { name: 'Continuar' }))
    expect((screen.getByRole('textbox', { name: /o que é a sua marca/i }) as HTMLTextAreaElement).value).toContain(brand)
    await user.click(screen.getByRole('button', { name: 'Salvar perfil' }))
    expect(mocks.save).toHaveBeenCalledWith({ auditText: 'Meu perfil personalizado', brandText: expect.stringContaining(brand) })
  })

  it('preserva os dois textos quando a substituição é cancelada', async () => {
    const user = userEvent.setup()
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    render(<MemoryRouter><ProfileSettings /></MemoryRouter>)
    await user.click(screen.getByText('Escolher um exemplo'))
    await user.click(screen.getByRole('button', { name: /educação/i }))
    await user.click(screen.getByRole('button', { name: /negócio local/i }))
    expect(confirm).toHaveBeenCalledOnce()
    expect((screen.getByRole('textbox', { name: /como é o seu perfil hoje/i }) as HTMLTextAreaElement).value).toContain('aprender habilidades')
    await user.click(screen.getByRole('button', { name: 'Continuar' }))
    expect((screen.getByRole('textbox', { name: /o que é a sua marca/i }) as HTMLTextAreaElement).value).toContain('ensina conceitos')
  })

  it('substitui ambos os textos quando a troca é confirmada', async () => {
    const user = userEvent.setup()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    render(<MemoryRouter><ProfileSettings /></MemoryRouter>)
    await user.click(screen.getByText('Escolher um exemplo'))
    await user.click(screen.getByRole('button', { name: /educação/i }))
    await user.click(screen.getByRole('button', { name: /negócio local/i }))
    expect((screen.getByRole('textbox', { name: /como é o seu perfil hoje/i }) as HTMLTextAreaElement).value).toContain('negócio local')
    await user.click(screen.getByRole('button', { name: 'Continuar' }))
    expect((screen.getByRole('textbox', { name: /o que é a sua marca/i }) as HTMLTextAreaElement).value).toContain('atendimento atencioso')
  })
})
