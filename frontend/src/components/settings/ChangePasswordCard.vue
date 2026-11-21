<script setup lang="ts">
import { nextTick, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { changePassword } from '../../api/auth'
import { normalizeApiError } from '../../api/errors'
import { useAuthStore } from '../../stores/auth'
import {
  emptyChangePasswordErrors,
  hasChangePasswordErrors,
  validateChangePasswordInput,
} from '../../utils/password'
import type { ChangePasswordField } from '../../utils/password'

const FIELD_IDS: Record<ChangePasswordField, string> = {
  current_password: 'change-password-current',
  new_password: 'change-password-new',
  confirm_password: 'change-password-confirm',
}

const FIELD_ORDER: ChangePasswordField[] = [
  'current_password',
  'new_password',
  'confirm_password',
]

const router = useRouter()
const auth = useAuthStore()

const form = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: '',
})
const errors = reactive(emptyChangePasswordErrors())
const saving = ref(false)
const unavailable = ref(false)
const errorText = ref('')

function clearFieldError(field: ChangePasswordField): void {
  errors[field] = ''
  errorText.value = ''
}

function focusFirstError(): void {
  const field = FIELD_ORDER.find((item) => errors[item])
  if (!field) return
  document.getElementById(FIELD_IDS[field])?.focus()
}

async function handleSubmit(): Promise<void> {
  if (saving.value || unavailable.value) return

  errorText.value = ''
  Object.assign(
    errors,
    validateChangePasswordInput({
      current_password: form.currentPassword,
      new_password: form.newPassword,
      confirm_password: form.confirmPassword,
    }),
  )

  if (hasChangePasswordErrors(errors)) {
    await nextTick()
    focusFirstError()
    return
  }

  saving.value = true

  try {
    await changePassword({
      current_password: form.currentPassword,
      new_password: form.newPassword,
    })
    form.currentPassword = ''
    form.newPassword = ''
    form.confirmPassword = ''
    auth.logout()
    await router.replace({ name: 'login', query: { password_changed: '1' } })
  } catch (cause) {
    const apiError = normalizeApiError(cause)

    if (apiError.status === 404 || apiError.status === 405) {
      unavailable.value = true
      errorText.value = '后端尚未提供修改密码接口（BE-029）；接口上线后此表单可直接使用。'
    } else if (apiError.code === 'AUTH_INVALID_CREDENTIALS') {
      errors.current_password = '当前密码不正确'
      await nextTick()
      document.getElementById(FIELD_IDS.current_password)?.focus()
    } else if (apiError.status === 401) {
      auth.logout()
      await router.replace({ name: 'login', query: { redirect: '/settings' } })
    } else {
      errorText.value = apiError.code
        ? `${apiError.message}（${apiError.code}）`
        : apiError.message
    }
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <section class="panel" aria-labelledby="change-password-title">
    <header class="panel__head">
      <h2 id="change-password-title">重置密码</h2>
      <span class="panel__head-hint">Security</span>
    </header>

    <div class="panel__body change-password">
      <p class="hint change-password__intro">
        输入当前密码即可重置为新密码。重置成功后当前登录会退出，请用新密码重新登录。忘记当前密码请联系项目管理员授权重置。
      </p>

      <div v-if="unavailable" class="change-password__alert" role="status">
        <span class="change-password__alert-mark" aria-hidden="true"></span>
        <span>{{ errorText }}</span>
      </div>
      <div v-else-if="errorText" class="change-password__alert change-password__alert--danger" role="alert">
        <span class="change-password__alert-mark" aria-hidden="true"></span>
        <span>{{ errorText }}</span>
      </div>

      <form class="change-password__form" novalidate @submit.prevent="handleSubmit">
        <div class="field">
          <label class="field-label" for="change-password-current">
            当前密码
            <span class="req-text" aria-hidden="true">*</span>
          </label>
          <input
            id="change-password-current"
            v-model="form.currentPassword"
            class="input"
            type="password"
            required
            maxlength="128"
            autocomplete="current-password"
            :aria-invalid="errors.current_password ? 'true' : 'false'"
            :aria-describedby="
              errors.current_password ? 'change-password-current-error' : undefined
            "
            @input="clearFieldError('current_password')"
          />
          <p
            v-if="errors.current_password"
            id="change-password-current-error"
            class="field-error"
          >
            {{ errors.current_password }}
          </p>
        </div>

        <div class="field">
          <label class="field-label" for="change-password-new">
            新密码
            <span class="req-text" aria-hidden="true">*</span>
          </label>
          <input
            id="change-password-new"
            v-model="form.newPassword"
            class="input"
            type="password"
            required
            maxlength="128"
            autocomplete="new-password"
            aria-describedby="change-password-new-hint"
            :aria-invalid="errors.new_password ? 'true' : 'false'"
            @input="clearFieldError('new_password')"
          />
          <p id="change-password-new-hint" class="hint change-password__hint">
            至少 8 位，最多 72 字节（中文约 24 个字），不能与当前密码相同。
          </p>
          <p v-if="errors.new_password" id="change-password-new-error" class="field-error">
            {{ errors.new_password }}
          </p>
        </div>

        <div class="field">
          <label class="field-label" for="change-password-confirm">
            确认新密码
            <span class="req-text" aria-hidden="true">*</span>
          </label>
          <input
            id="change-password-confirm"
            v-model="form.confirmPassword"
            class="input"
            type="password"
            required
            maxlength="128"
            autocomplete="new-password"
            :aria-invalid="errors.confirm_password ? 'true' : 'false'"
            :aria-describedby="
              errors.confirm_password ? 'change-password-confirm-error' : undefined
            "
            @input="clearFieldError('confirm_password')"
          />
          <p
            v-if="errors.confirm_password"
            id="change-password-confirm-error"
            class="field-error"
          >
            {{ errors.confirm_password }}
          </p>
        </div>

        <div class="change-password__actions">
          <button
            class="btn btn--primary"
            type="submit"
            :disabled="saving || unavailable"
            :aria-busy="saving"
          >
            {{ saving ? '重置中…' : '重置密码' }}
          </button>
        </div>
      </form>
    </div>
  </section>
</template>

<style scoped>
.change-password {
  max-width: 560px;
}

.change-password__intro {
  margin-bottom: var(--space-4);
  text-wrap: pretty;
}

.change-password__form {
  display: grid;
  gap: var(--space-4);
}

.change-password__hint {
  margin-top: 6px;
}

.change-password__actions {
  padding-top: var(--space-1);
}

.change-password__alert {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
  padding: 10px var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-subtle);
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.change-password__alert--danger {
  border-color: var(--color-danger-border);
  background: var(--color-danger-soft);
  color: var(--color-danger-text);
}

.change-password__alert-mark {
  flex: none;
  width: 6px;
  height: 6px;
  margin-top: 8px;
  background: currentColor;
}
</style>
