import { describe, expect, it } from 'vitest'
import {
  hasAiSettingsErrors,
  toAiSettingsUpdate,
  validateAiSettingsInput,
} from '../src/utils/settings'

describe('settings helpers', () => {
  it('validates the API key and OpenAI-compatible base URL', () => {
    const errors = validateAiSettingsInput({
      provider: 'openai_compatible',
      base_url: 'http://example.com',
      model: 'gpt',
      api_key: 'short',
    })

    expect(errors.base_url).toContain('https://')
    expect(errors.api_key).toContain('至少 8 个字符')
    expect(hasAiSettingsErrors(errors)).toBe(true)
  })

  it('drops the base URL for DeepSeek', () => {
    expect(
      toAiSettingsUpdate({
        provider: 'deepseek',
        base_url: 'https://example.com',
        model: 'deepseek-flash',
        api_key: 'sk-12345678',
      }),
    ).toEqual({
      provider: 'deepseek',
      base_url: null,
      model: 'deepseek-flash',
      api_key: 'sk-12345678',
    })
  })
})
