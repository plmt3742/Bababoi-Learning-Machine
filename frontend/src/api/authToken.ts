/** Shared token storage. The API client must not import stores; this is the bridge. */

export const AUTH_TOKEN_KEY = 'bababoi:token'

function getStorage(): Storage | null {
  if (typeof window === 'undefined') return null

  try {
    return window.localStorage
  } catch {
    // Private mode / blocked storage: the app still works for this tab.
    return null
  }
}

export function getAuthToken(): string | null {
  return getStorage()?.getItem(AUTH_TOKEN_KEY) ?? null
}

export function setAuthToken(token: string): void {
  getStorage()?.setItem(AUTH_TOKEN_KEY, token)
}

export function clearAuthToken(): void {
  getStorage()?.removeItem(AUTH_TOKEN_KEY)
}
