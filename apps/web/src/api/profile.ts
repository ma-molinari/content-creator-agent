import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from './client'

export type ReferenceItem = {
  id: string
  url: string
}

export type ProfileResponse = {
  auditText: string
  brandText: string
  configured: boolean
  references: ReferenceItem[]
}

function postMultipartProfile(url: string, data: FormData) {
  return api.post<ProfileResponse>(url, data, {
    transformRequest: [
      (body, headers) => {
        if (body instanceof FormData) {
          if (headers && typeof headers === 'object' && 'Content-Type' in headers) {
            delete (headers as Record<string, string>)['Content-Type']
          }
        }
        return body
      },
    ],
  })
}

export function useProfile() {
  return useQuery({
    queryKey: ['profile'],
    queryFn: () => api.get<ProfileResponse>('/profile').then((r) => r.data),
    staleTime: 30_000,
  })
}

export function useSaveProfile() {
  const qc = useQueryClient()
  return useMutation<ProfileResponse, Error, { auditText: string; brandText: string }>({
    mutationFn: (vars) => api.put<ProfileResponse>('/profile', vars).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['profile'] })
      qc.invalidateQueries({ queryKey: ['setup-status'] })
    },
  })
}

export function useUploadReference() {
  const qc = useQueryClient()
  return useMutation<ProfileResponse, Error, File>({
    mutationFn: (file) => {
      const formData = new FormData()
      formData.append('file', file)
      return postMultipartProfile('/profile/references', formData).then((r) => r.data)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['profile'] })
    },
  })
}

export function useDeleteReference() {
  const qc = useQueryClient()
  return useMutation<void, Error, string>({
    mutationFn: (id) => api.delete(`/profile/references/${id}`).then(() => undefined),
    onSuccess: (_data, id) => {
      qc.setQueryData<ProfileResponse>(['profile'], (current) => {
        if (!current) return current
        return {
          ...current,
          references: current.references.filter((ref) => ref.id !== id),
        }
      })
      qc.invalidateQueries({ queryKey: ['profile'] })
    },
  })
}
