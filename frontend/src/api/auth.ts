import apiClient from './client'
import type {
  AuthResponse,
  ChangePasswordPayload,
  LoginPayload,
  RegisterPayload,
  User,
} from './types'

export async function login(payload: LoginPayload): Promise<AuthResponse> {
  const { data } = await apiClient.post<AuthResponse>('/auth/login', payload)
  return data
}

export async function register(payload: RegisterPayload): Promise<AuthResponse> {
  const { data } = await apiClient.post<AuthResponse>('/auth/register', payload)
  return data
}

export async function me(): Promise<User> {
  const { data } = await apiClient.get<User>('/auth/me')
  return data
}

/**
 * FE-038: change the password of the signed-in account.
 * 204 on success; a wrong current password is 401 AUTH_INVALID_CREDENTIALS and
 * must NOT be treated as an expired session (see client.ts exemption list).
 */
export async function changePassword(payload: ChangePasswordPayload): Promise<void> {
  await apiClient.post('/auth/change-password', payload)
}
