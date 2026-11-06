<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { IconCamera, IconUpload } from '@arco-design/web-vue/es/icon'
import { formatFileSize, IMAGE_ACCEPT_ATTRIBUTE } from '../../utils/image'

const props = withDefaults(
  defineProps<{
    active?: boolean
    disabled?: boolean
    file?: File | null
    error?: string
  }>(),
  {
    active: true,
    disabled: false,
    file: null,
    error: '',
  },
)

const emit = defineEmits<{ select: [file: File] }>()

const galleryInput = ref<HTMLInputElement>()
const cameraInput = ref<HTMLInputElement>()
const dragging = ref(false)

function requestGallery(): void {
  if (props.disabled) return
  galleryInput.value?.click()
}

function requestCamera(): void {
  if (props.disabled) return
  cameraInput.value?.click()
}

function handleInputChange(event: Event): void {
  const input = event.target as HTMLInputElement | null
  const file = input?.files?.[0]
  if (input) input.value = ''
  if (file) emit('select', file)
}

function handleDrop(event: DragEvent): void {
  dragging.value = false
  if (props.disabled) return

  const file = event.dataTransfer?.files?.[0]
  if (file) emit('select', file)
}

function handlePaste(event: ClipboardEvent): void {
  if (!props.active || props.disabled) return

  const items = event.clipboardData?.items
  if (!items) return

  for (const item of Array.from(items)) {
    if (item.kind !== 'file' || !item.type.startsWith('image/')) continue
    const file = item.getAsFile()
    if (!file) continue
    event.preventDefault()
    emit('select', file)
    return
  }
}

onMounted(() => {
  window.addEventListener('paste', handlePaste)
})

onBeforeUnmount(() => {
  window.removeEventListener('paste', handlePaste)
})

defineExpose({ requestGallery, requestCamera })
</script>

<template>
  <div class="image-picker">
    <input
      ref="galleryInput"
      class="file-input"
      type="file"
      :accept="IMAGE_ACCEPT_ATTRIBUTE"
      tabindex="-1"
      aria-hidden="true"
      @change="handleInputChange"
    />
    <input
      ref="cameraInput"
      class="file-input"
      type="file"
      accept="image/*"
      capture="environment"
      tabindex="-1"
      aria-hidden="true"
      @change="handleInputChange"
    />

    <div
      class="dropzone"
      :class="{ 'dropzone--dragging': dragging, 'dropzone--disabled': disabled }"
      role="button"
      tabindex="0"
      aria-label="选择或拖入图片，也可以直接粘贴截图"
      :aria-disabled="disabled"
      @click="requestGallery"
      @keydown.enter.prevent="requestGallery"
      @keydown.space.prevent="requestGallery"
      @dragover.prevent="dragging = true"
      @dragleave="dragging = false"
      @drop.prevent="handleDrop"
    >
      <span class="dropzone__icon" aria-hidden="true">
        <IconUpload />
      </span>
      <p class="dropzone__title">拖入图片，或点击选择</p>
      <p class="dropzone__hint">电脑可直接 Ctrl+V 粘贴截图 · JPEG / PNG / WebP，原图 ≤20MB</p>
      <p v-if="file" class="dropzone__file">{{ file.name }} · {{ formatFileSize(file.size) }}</p>
    </div>

    <div class="picker-actions">
      <button
        class="btn btn--outline btn--sm"
        type="button"
        :disabled="disabled"
        @click="requestGallery"
      >
        <IconUpload aria-hidden="true" />
        选择图片
      </button>
      <button
        class="btn btn--outline btn--sm"
        type="button"
        :disabled="disabled"
        @click="requestCamera"
      >
        <IconCamera aria-hidden="true" />
        拍照
      </button>
      <span class="picker-actions__hint">
        手机可直接调用相机；非 HTTPS 环境可能只能从相册选择。
      </span>
    </div>

    <p v-if="error" class="field-error" role="alert">{{ error }}</p>
  </div>
</template>

<style scoped>
.image-picker {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.file-input {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
  border: 0;
}

.dropzone {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-1);
  min-height: 168px;
  padding: var(--space-5) var(--space-4);
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-lg);
  background: var(--color-surface-subtle);
  text-align: center;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background-color 0.15s ease;
}

.dropzone:hover,
.dropzone--dragging {
  border-color: var(--color-primary);
  background: var(--color-primary-softer);
}

.dropzone--disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.dropzone__icon {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  margin-bottom: var(--space-1);
  border: 1px solid var(--color-primary-border);
  border-radius: var(--radius-md);
  background: var(--color-primary-soft);
  color: var(--color-primary-active);
}

.dropzone__icon :deep(svg) {
  width: 20px;
  height: 20px;
}

.dropzone__title {
  color: var(--color-text-1);
  font-size: var(--text-base);
  line-height: 24px;
  font-weight: 650;
}

.dropzone__hint {
  max-width: 460px;
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-wrap: pretty;
}

.dropzone__file {
  max-width: 100%;
  margin-top: var(--space-2);
  padding: 4px var(--space-2);
  overflow-wrap: anywhere;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text-2);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: 20px;
}

.picker-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.picker-actions__hint {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-wrap: pretty;
}

@media (max-width: 767px) {
  .dropzone {
    min-height: 148px;
    padding: var(--space-4) var(--space-3);
  }

  .picker-actions .btn {
    flex: 1;
  }

  .picker-actions__hint {
    flex-basis: 100%;
  }
}
</style>
