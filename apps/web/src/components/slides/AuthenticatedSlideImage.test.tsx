import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, waitFor } from '@testing-library/react'
import type { AxiosResponse } from 'axios'
import type { ReactNode } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/api/client', () => ({
  api: {
    get: vi.fn(),
  },
}))

import { api } from '@/api/client'

import { AuthenticatedSlideImage } from './AuthenticatedSlideImage'

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

function mkWrapper() {
  const client = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  return Wrapper
}

function xhrResponse<T>(
  overrides: Partial<AxiosResponse<T>> & Pick<AxiosResponse<T>, 'data'>,
): AxiosResponse<T> {
  return {
    status: 200,
    statusText: 'OK',
    headers: {},
    config: {} as AxiosResponse<T>['config'],
    ...overrides,
  }
}

describe('AuthenticatedSlideImage', () => {
  it('does not render a blob <img> when the server returns 200 with HTML body', async () => {
    vi.mocked(api.get).mockResolvedValue(
      xhrResponse({
        data: new Blob(['<!doctype html><html></html>'], {
          type: 'text/html',
        }),
        headers: { 'content-type': 'text/html; charset=utf-8' },
      }),
    )

    const Wrapper = mkWrapper()
    render(
      <Wrapper>
        <AuthenticatedSlideImage chatId="c1" fileId="f1" alt="Slide 1" />
      </Wrapper>,
    )

    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith('/chats/c1/files/f1', expect.any(Object))
    })

    await waitFor(() => {
      expect(document.querySelector('img[src^="blob:"]')).toBeNull()
    })
  })

  it('renders <img src="blob:…"> when the body starts with JPEG SOI markers', async () => {
    const jpegBytes = new Uint8Array([0xff, 0xd8, 0xff, 0xdb, 0x00])
    vi.mocked(api.get).mockResolvedValue(
      xhrResponse({
        data: new Blob([jpegBytes], { type: 'image/jpeg' }),
        headers: { 'content-type': 'image/jpeg' },
      }),
    )

    const Wrapper = mkWrapper()
    render(
      <Wrapper>
        <AuthenticatedSlideImage chatId="c1" fileId="f2" alt="Slide 2" />
      </Wrapper>,
    )

    await waitFor(() => {
      const img = document.querySelector('img')
      expect(img).not.toBeNull()
      expect(img?.getAttribute('src')).toMatch(/^blob:/)
      expect(img).toHaveAttribute('alt', 'Slide 2')
    })
  })
})
