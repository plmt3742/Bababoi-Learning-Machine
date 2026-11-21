/**
 * 修改密码的纯校验逻辑（FE-038）。
 *
 * 契约值跟后端 schemas/auth.py 对齐：最少 8 位；bcrypt 只取前 72 字节，
 * 所以上限按 UTF-8 字节算，不按字符数算（中文 1 字 = 3 字节）。
 */

export const MIN_PASSWORD_LENGTH = 8
export const MAX_PASSWORD_BYTES = 72

export interface ChangePasswordInput {
  current_password: string
  new_password: string
  confirm_password: string
}

export type ChangePasswordField = 'current_password' | 'new_password' | 'confirm_password'

export type ChangePasswordErrors = Record<ChangePasswordField, string>

export function emptyChangePasswordErrors(): ChangePasswordErrors {
  return {
    current_password: '',
    new_password: '',
    confirm_password: '',
  }
}

export function utf8ByteLength(value: string): number {
  return new TextEncoder().encode(value).length
}

export function validateChangePasswordInput(
  input: ChangePasswordInput,
): ChangePasswordErrors {
  const errors = emptyChangePasswordErrors()

  if (!input.current_password) {
    errors.current_password = '请输入当前密码'
  }

  const next = input.new_password
  if (!next) {
    errors.new_password = '请输入新密码'
  } else if (next.length < MIN_PASSWORD_LENGTH) {
    errors.new_password = `新密码至少 ${MIN_PASSWORD_LENGTH} 位`
  } else if (utf8ByteLength(next) > MAX_PASSWORD_BYTES) {
    errors.new_password = `新密码最多 ${MAX_PASSWORD_BYTES} 字节（中文约 24 个字）`
  } else if (next === input.current_password) {
    errors.new_password = '新密码不能与当前密码相同'
  }

  if (!input.confirm_password) {
    errors.confirm_password = '请再次输入新密码'
  } else if (input.confirm_password !== next) {
    errors.confirm_password = '两次输入的新密码不一致'
  }

  return errors
}

export function hasChangePasswordErrors(errors: ChangePasswordErrors): boolean {
  return Object.values(errors).some((message) => message.length > 0)
}
