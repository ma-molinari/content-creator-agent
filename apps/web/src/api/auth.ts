import { useMutation } from '@tanstack/react-query'

import { api } from './client'

type LoginVars = { email: string; password: string }
type LoginResult = { accessToken: string }

export function useLogin() {
  return useMutation<LoginResult, Error, LoginVars>({
    mutationFn: (vars) =>
      api.post<LoginResult>('/auth/login', vars).then((r) => r.data),
  })
}

type RegisterVars = { email: string; password: string }
type RegisterResult = { securityKey: string }

export function useRegister() {
  return useMutation<RegisterResult, Error, RegisterVars>({
    mutationFn: (vars) =>
      api.post<RegisterResult>('/auth/register', vars).then((r) => r.data),
  })
}
