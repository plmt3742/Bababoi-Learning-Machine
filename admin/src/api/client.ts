import { handleDemoRequest } from '../mock/demo'

export interface ApiErrorDetail {
  code?: string
  message?: string
  request_id?: string
}

interface ApiErrorBody {
  detail?: ApiErrorDetail | string
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string | null
  readonly requestId: string | null

  constructor(message: string, status: number, code: string | null = null, requestId: string | null = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.requestId = requestId
  }
}

const API_BASE = '/api/v1'
const TOKEN_KEY = 'bababoi:admin-token'
const USER_KEY = 'bababoi:admin-user'
const REQUEST_TIMEOUT_MS = 20_000

export type QueryValue = string | number | boolean | undefined | null

export interface RequestOptions {
  query?: Record<string, QueryValue>
  redirectOnUnauthorized?: boolean
  timeoutMs?: number
}

export function getAdminToken(): string {
  return localStorage.getItem(TOKEN_KEY) ?? ''
}

export function clearAdminSession(): void {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

function adminLoginPath(): string {
  const base = import.meta.env.BASE_URL.replace(/\/+$/, '')
  return `${base}/login`
}

function isOnLoginPath(): boolean {
  const path = window.location.pathname.replace(/\/+$/, '')
  return path === adminLoginPath() || path.endsWith('/login')
}

function buildUrl(path: string, query?: Record<string, QueryValue>): string {
  const url = `${API_BASE}${path}`
  if (!query) return url
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === '') continue
    params.set(key, String(value))
  }
  const serialized = params.toString()
  return serialized ? `${url}?${serialized}` : url
}

async function readError(response: Response): Promise<ApiError> {
  const body = (await response.json().catch(() => null)) as ApiErrorBody | null
  const detail = body?.detail
  let message = `请求失败（${response.status}）`
  let code: string | null = null
  let requestId: string | null = null
  if (detail && typeof detail === 'object') {
    if (typeof detail.message === 'string' && detail.message) message = detail.message
    if (typeof detail.code === 'string') code = detail.code
    if (typeof detail.request_id === 'string') requestId = detail.request_id
  } else if (typeof detail === 'string' && detail) {
    message = detail
  }
  return new ApiError(message, response.status, code, requestId)
}

export async function apiFetch(
  path: string,
  init: RequestInit = {},
  options: RequestOptions = {},
): Promise<Response> {
  const demoResponse = await handleDemoRequest(path, init, options)
  if (demoResponse) return demoResponse

  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), options.timeoutMs ?? REQUEST_TIMEOUT_MS)
  const headers = new Headers(init.headers)
  if (!headers.has('Accept')) headers.set('Accept', 'application/json')
  if (init.body !== undefined && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  const token = getAdminToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)

  let response: Response
  try {
    response = await fetch(buildUrl(path, options.query), { ...init, headers, signal: controller.signal })
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === 'AbortError') {
      throw new ApiError('请求超时，请稍后重试', 0)
    }
    throw new ApiError('网络请求失败，请检查后端服务是否已启动', 0)
  } finally {
    window.clearTimeout(timer)
  }

  if (response.status === 401 && options.redirectOnUnauthorized !== false) {
    clearAdminSession()
    if (!isOnLoginPath()) window.location.assign(adminLoginPath())
    throw new ApiError('登录已过期，请重新登录', 401)
  }
  if (!response.ok) throw await readError(response)
  return response
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
  options: RequestOptions = {},
): Promise<T> {
  const response = await apiFetch(path, init, options)
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export async function apiBlob(path: string, options: RequestOptions = {}): Promise<Blob> {
  const response = await apiFetch(path, {}, options)
  return response.blob()
}
