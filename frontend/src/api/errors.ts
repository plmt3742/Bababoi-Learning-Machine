import axios from 'axios'
import type { ApiErrorResponse } from './types'

const FALLBACK_MESSAGE = '请求失败，请稍后重试'

/** Normalized error thrown by every API call. Branch on `code`, never on `message`. */
export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly requestId: string | null

  constructor(status: number, code: string, message: string, requestId: string | null = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.requestId = requestId
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function isApiErrorResponse(value: unknown): value is ApiErrorResponse {
  if (!isRecord(value) || !isRecord(value.detail)) return false

  return typeof value.detail.code === 'string' && typeof value.detail.message === 'string'
}

function readRequestId(headers: unknown): string | null {
  if (!isRecord(headers)) return null

  const headerValue = headers['x-request-id']
  if (typeof headerValue === 'string' && headerValue.length > 0) return headerValue

  const getHeader = headers.get
  if (typeof getHeader !== 'function') return null

  const value = getHeader.call(headers, 'x-request-id')
  return typeof value === 'string' && value.length > 0 ? value : null
}

function fallbackCodeForStatus(status: number): string {
  if (status === 400) return 'VALIDATION_ERROR'
  if (status === 401) return 'AUTH_TOKEN_EXPIRED'
  if (status === 403) return 'FORBIDDEN'
  if (status === 404) return 'NOT_FOUND'
  if (status === 409) return 'CONFLICT'
  if (status === 429) return 'RATE_LIMITED'
  if (status >= 500) return 'INTERNAL_ERROR'
  return 'REQUEST_FAILED'
}

export function normalizeApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error

  if (axios.isAxiosError(error)) {
    const status = error.response?.status ?? 0
    const requestId = readRequestId(error.response?.headers)
    const data: unknown = error.response?.data

    if (isApiErrorResponse(data)) {
      return new ApiError(
        status,
        data.detail.code,
        data.detail.message,
        data.detail.request_id || requestId,
      )
    }

    // FastAPI's default validation body uses an array in `detail`.
    if (isRecord(data) && Array.isArray(data.detail)) {
      return new ApiError(
        status || 422,
        'VALIDATION_ERROR',
        '请求参数有误，请检查后重试',
        requestId,
      )
    }

    if (error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT') {
      return new ApiError(0, 'REQUEST_TIMEOUT', '请求超时，请稍后重试', requestId)
    }

    if (error.code === 'ERR_CANCELED') {
      return new ApiError(0, 'REQUEST_CANCELLED', '请求已取消', requestId)
    }

    if (!error.response) {
      return new ApiError(0, 'NETWORK_ERROR', '网络连接失败，请检查网络后重试', requestId)
    }

    return new ApiError(
      status,
      fallbackCodeForStatus(status),
      error.message || FALLBACK_MESSAGE,
      requestId,
    )
  }

  if (error instanceof Error && error.message) {
    return new ApiError(0, 'UNKNOWN_ERROR', error.message)
  }

  return new ApiError(0, 'UNKNOWN_ERROR', FALLBACK_MESSAGE)
}
