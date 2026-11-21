import { describe, expect, it } from 'vitest'
import {
  emptyChangePasswordErrors,
  hasChangePasswordErrors,
  utf8ByteLength,
  validateChangePasswordInput,
} from '../src/utils/password'

const validInput = {
  current_password: 'password123',
  new_password: 'newpassword456',
  confirm_password: 'newpassword456',
}

describe('change password helpers', () => {
  it('accepts a valid change', () => {
    const errors = validateChangePasswordInput(validInput)

    expect(hasChangePasswordErrors(errors)).toBe(false)
    expect(errors).toEqual(emptyChangePasswordErrors())
  })

  it('requires all three fields', () => {
    const errors = validateChangePasswordInput({
      current_password: '',
      new_password: '',
      confirm_password: '',
    })

    expect(errors.current_password).toContain('当前密码')
    expect(errors.new_password).toContain('新密码')
    expect(errors.confirm_password).toContain('再次输入')
  })

  it('rejects a new password shorter than 8 characters', () => {
    const errors = validateChangePasswordInput({
      ...validInput,
      new_password: 'short12',
      confirm_password: 'short12',
    })

    expect(errors.new_password).toContain('至少 8 位')
  })

  it('caps the new password by UTF-8 bytes, not characters', () => {
    // 25 个汉字 = 75 字节，超过 bcrypt 的 72 字节上限。
    const longChinese = '密'.repeat(25)

    expect(utf8ByteLength(longChinese)).toBe(75)
    expect(
      validateChangePasswordInput({
        ...validInput,
        new_password: longChinese,
        confirm_password: longChinese,
      }).new_password,
    ).toContain('72 字节')
  })

  it('rejects reusing the current password', () => {
    const errors = validateChangePasswordInput({
      ...validInput,
      new_password: 'password123',
      confirm_password: 'password123',
    })

    expect(errors.new_password).toContain('不能与当前密码相同')
  })

  it('rejects a mismatched confirmation', () => {
    const errors = validateChangePasswordInput({
      ...validInput,
      confirm_password: 'newpassword457',
    })

    expect(errors.confirm_password).toContain('不一致')
  })
})
