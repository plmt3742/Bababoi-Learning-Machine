import type { AiProvider, AiSettingsUpdate } from '../api/types'
import { parseApiTime } from './time'

export const DEFAULT_AI_MODEL = 'deepseek-flash'
export const MIN_API_KEY_LENGTH = 8

export interface AiSettingsFormInput {
  provider: AiProvider
  base_url: string
  model: string
  api_key: string
}

export type AiSettingsField = 'provider' | 'model' | 'base_url' | 'api_key'

export type AiSettingsFieldErrors = Record<AiSettingsField, string>

export function emptyAiSettingsErrors(): AiSettingsFieldErrors {
  return {
    provider: '',
    model: '',
    base_url: '',
    api_key: '',
  }
}

export function isAiProvider(value: unknown): value is AiProvider {
  return value === 'deepseek' || value === 'openai_compatible'
}

function isHttpsUrl(value: string): boolean {
  try {
    return new URL(value).protocol === 'https:'
  } catch {
    return false
  }
}

export function validateAiSettingsInput(input: AiSettingsFormInput): AiSettingsFieldErrors {
  const errors = emptyAiSettingsErrors()

  if (!isAiProvider(input.provider)) errors.provider = '请选择 API 提供方'

  if (!input.model.trim()) errors.model = '请填写模型名称'

  const baseUrl = input.base_url.trim()
  if (input.provider === 'openai_compatible' && baseUrl && !isHttpsUrl(baseUrl)) {
    errors.base_url = 'Base URL 必须是完整的 https:// 地址'
  }

  const apiKey = input.api_key.trim()
  if (!apiKey) errors.api_key = '请填写 API Key'
  else if (apiKey.length < MIN_API_KEY_LENGTH) {
    errors.api_key = `API Key 至少 ${MIN_API_KEY_LENGTH} 个字符`
  }

  return errors
}

export function hasAiSettingsErrors(errors: AiSettingsFieldErrors): boolean {
  return Object.values(errors).some((message) => message.length > 0)
}

export function toAiSettingsUpdate(input: AiSettingsFormInput): AiSettingsUpdate {
  return {
    provider: input.provider,
    base_url: input.provider === 'openai_compatible' ? input.base_url.trim() || null : null,
    model: input.model.trim(),
    api_key: input.api_key.trim(),
  }
}

export function formatSettingsTime(value: string | null): string {
  if (!value) return ''

  const date = parseApiTime(value)
  if (Number.isNaN(date.getTime())) return ''

  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date)
}
