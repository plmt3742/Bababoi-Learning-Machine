<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import {
  IconCheck,
  IconRefresh,
  IconRotateLeft,
  IconRotateRight,
} from '@arco-design/web-vue/es/icon'
import { cropRotateImage, loadImageFromFile } from '../../utils/image'
import type { PixelCropRect } from '../../utils/image'

type DragMode = 'move' | 'nw' | 'n' | 'ne' | 'e' | 'se' | 's' | 'sw' | 'w'

interface CropBox {
  left: number
  top: number
  width: number
  height: number
}

interface DragState {
  mode: DragMode
  startX: number
  startY: number
  rect: CropBox
}

const MIN_CROP_SIZE = 48

const HANDLES: Array<{ mode: Exclude<DragMode, 'move'> }> = [
  { mode: 'nw' },
  { mode: 'n' },
  { mode: 'ne' },
  { mode: 'e' },
  { mode: 'se' },
  { mode: 's' },
  { mode: 'sw' },
  { mode: 'w' },
]

const props = withDefaults(
  defineProps<{
    visible: boolean
    file?: File | null
  }>(),
  { file: null },
)

const emit = defineEmits<{
  cancel: []
  confirm: [file: File]
}>()

const dialogRef = ref<HTMLElement>()
const stageRef = ref<HTMLElement>()
const canvasRef = ref<HTMLCanvasElement>()
const image = shallowRef<HTMLImageElement | null>(null)
const rotation = ref(0)
const stageWidth = ref(0)
const stageHeight = ref(0)
const cropRect = ref<CropBox>({ left: 0, top: 0, width: 0, height: 0 })
const loading = ref(false)
const cropping = ref(false)
const loadError = ref('')
const errorMessage = ref('')

let previousFocus: HTMLElement | null = null
let previousBodyOverflow: string | null = null
let resizeObserver: ResizeObserver | null = null
let dragState: DragState | null = null

const rotatedWidth = computed(() => {
  const source = image.value
  if (!source) return 0
  return rotation.value % 180 === 0 ? source.naturalWidth : source.naturalHeight
})

const rotatedHeight = computed(() => {
  const source = image.value
  if (!source) return 0
  return rotation.value % 180 === 0 ? source.naturalHeight : source.naturalWidth
})

const displayScale = computed(() => {
  if (!rotatedWidth.value || !rotatedHeight.value) return 1
  if (!stageWidth.value || !stageHeight.value) return 1
  return Math.min(stageWidth.value / rotatedWidth.value, stageHeight.value / rotatedHeight.value)
})

const displayRect = computed<CropBox>(() => {
  const width = rotatedWidth.value * displayScale.value
  const height = rotatedHeight.value * displayScale.value
  return {
    left: Math.max(0, (stageWidth.value - width) / 2),
    top: Math.max(0, (stageHeight.value - height) / 2),
    width,
    height,
  }
})

const cropStyle = computed(() => ({
  left: `${cropRect.value.left}px`,
  top: `${cropRect.value.top}px`,
  width: `${cropRect.value.width}px`,
  height: `${cropRect.value.height}px`,
}))

const cropPixelSize = computed(() => {
  const scale = displayScale.value
  if (!scale) return { width: 0, height: 0 }
  return {
    width: Math.max(1, Math.round(cropRect.value.width / scale)),
    height: Math.max(1, Math.round(cropRect.value.height / scale)),
  }
})

const outputSizeLabel = computed(
  () => `${cropPixelSize.value.width} × ${cropPixelSize.value.height} px`,
)

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max)
}

function measureStage(): void {
  const stage = stageRef.value
  if (!stage) return
  stageWidth.value = stage.clientWidth
  stageHeight.value = stage.clientHeight
}

function observeStage(): void {
  resizeObserver?.disconnect()
  const stage = stageRef.value
  if (!stage) return

  resizeObserver = new ResizeObserver(() => measureStage())
  resizeObserver.observe(stage)
}

function resetCrop(): void {
  const bounds = displayRect.value
  if (bounds.width <= 0 || bounds.height <= 0) {
    cropRect.value = { left: 0, top: 0, width: 0, height: 0 }
    return
  }

  cropRect.value = {
    left: bounds.left,
    top: bounds.top,
    width: bounds.width,
    height: bounds.height,
  }
}

function drawPreview(): void {
  const canvas = canvasRef.value
  const source = image.value
  const width = stageWidth.value
  const height = stageHeight.value
  if (!canvas || !source || width <= 0 || height <= 0) return

  const ratio = window.devicePixelRatio || 1
  canvas.width = Math.max(1, Math.round(width * ratio))
  canvas.height = Math.max(1, Math.round(height * ratio))
  canvas.style.width = `${width}px`
  canvas.style.height = `${height}px`

  const context = canvas.getContext('2d')
  if (!context) return

  context.setTransform(ratio, 0, 0, ratio, 0, 0)
  context.clearRect(0, 0, width, height)

  const rect = displayRect.value
  context.save()
  context.translate(rect.left + rect.width / 2, rect.top + rect.height / 2)
  context.scale(displayScale.value, displayScale.value)
  context.rotate((rotation.value * Math.PI) / 180)
  context.drawImage(source, -source.naturalWidth / 2, -source.naturalHeight / 2)
  context.restore()
}

async function loadSource(): Promise<void> {
  if (!props.file) {
    image.value = null
    loadError.value = '没有可裁剪的图片'
    return
  }

  loading.value = true
  loadError.value = ''
  errorMessage.value = ''
  image.value = null

  try {
    const loaded = await loadImageFromFile(props.file)
    image.value = loaded
    rotation.value = 0
    await nextTick()
    measureStage()
    observeStage()
    resetCrop()
    drawPreview()
    dialogRef.value?.focus()
  } catch (cause) {
    loadError.value = cause instanceof Error ? cause.message : '无法读取这张图片'
  } finally {
    loading.value = false
  }
}

function focusableElements(): HTMLElement[] {
  const dialog = dialogRef.value
  if (!dialog) return []

  const selector =
    'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
  return Array.from(dialog.querySelectorAll<HTMLElement>(selector)).filter(
    (element) => element.offsetParent !== null,
  )
}

function handleWindowKeydown(event: KeyboardEvent): void {
  if (!props.visible || event.key !== 'Escape') return
  event.preventDefault()
  close()
}

function handleDialogKeydown(event: KeyboardEvent): void {
  if (event.key !== 'Tab') return

  const focusable = focusableElements()
  if (!focusable.length) return

  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  const active = document.activeElement
  const dialog = dialogRef.value

  if (event.shiftKey && (active === first || active === dialog)) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && active === last) {
    event.preventDefault()
    first.focus()
  }
}

function close(): void {
  if (cropping.value) return
  emit('cancel')
}

function rotateBy(delta: number): void {
  rotation.value = (rotation.value + delta + 360) % 360
}

function resetAll(): void {
  rotation.value = 0
  resetCrop()
  drawPreview()
}

function beginDrag(event: PointerEvent, mode: DragMode): void {
  if (cropping.value || loading.value) return
  event.preventDefault()

  dragState = {
    mode,
    startX: event.clientX,
    startY: event.clientY,
    rect: { ...cropRect.value },
  }

  window.addEventListener('pointermove', handlePointerMove)
  window.addEventListener('pointerup', handlePointerUp)
  window.addEventListener('pointercancel', handlePointerUp)
}

function handlePointerMove(event: PointerEvent): void {
  const drag = dragState
  if (!drag) return

  const bounds = displayRect.value
  const dx = event.clientX - drag.startX
  const dy = event.clientY - drag.startY
  const start = drag.rect
  let left = start.left
  let top = start.top
  let right = start.left + start.width
  let bottom = start.top + start.height

  if (drag.mode === 'move') {
    left = clamp(start.left + dx, bounds.left, bounds.left + bounds.width - start.width)
    top = clamp(start.top + dy, bounds.top, bounds.top + bounds.height - start.height)
    right = left + start.width
    bottom = top + start.height
  } else {
    if (drag.mode.includes('w')) {
      left = clamp(start.left + dx, bounds.left, right - MIN_CROP_SIZE)
    }
    if (drag.mode.includes('e')) {
      right = clamp(start.left + start.width + dx, left + MIN_CROP_SIZE, bounds.left + bounds.width)
    }
    if (drag.mode.includes('n')) {
      top = clamp(start.top + dy, bounds.top, bottom - MIN_CROP_SIZE)
    }
    if (drag.mode.includes('s')) {
      bottom = clamp(start.top + start.height + dy, top + MIN_CROP_SIZE, bounds.top + bounds.height)
    }
  }

  cropRect.value = {
    left,
    top,
    width: right - left,
    height: bottom - top,
  }
}

function handlePointerUp(): void {
  dragState = null
  window.removeEventListener('pointermove', handlePointerMove)
  window.removeEventListener('pointerup', handlePointerUp)
  window.removeEventListener('pointercancel', handlePointerUp)
}

function handleCropKeydown(event: KeyboardEvent): void {
  const directions: Record<string, [number, number]> = {
    ArrowLeft: [-1, 0],
    ArrowRight: [1, 0],
    ArrowUp: [0, -1],
    ArrowDown: [0, 1],
  }
  const direction = directions[event.key]
  if (!direction) return

  event.preventDefault()
  const step = event.shiftKey ? 16 : 4
  const bounds = displayRect.value
  const width = cropRect.value.width
  const height = cropRect.value.height

  cropRect.value = {
    ...cropRect.value,
    left: clamp(
      cropRect.value.left + direction[0] * step,
      bounds.left,
      bounds.left + bounds.width - width,
    ),
    top: clamp(
      cropRect.value.top + direction[1] * step,
      bounds.top,
      bounds.top + bounds.height - height,
    ),
  }
}

async function handleConfirm(): Promise<void> {
  if (!props.file || cropping.value || loading.value) return

  const bounds = displayRect.value
  const scale = displayScale.value
  if (!scale) return

  cropping.value = true
  errorMessage.value = ''

  try {
    const crop: PixelCropRect = {
      x: (cropRect.value.left - bounds.left) / scale,
      y: (cropRect.value.top - bounds.top) / scale,
      width: cropRect.value.width / scale,
      height: cropRect.value.height / scale,
    }
    const file = await cropRotateImage(props.file, rotation.value, crop)
    emit('confirm', file)
  } catch (cause) {
    errorMessage.value = cause instanceof Error ? cause.message : '裁剪失败，请重试'
  } finally {
    cropping.value = false
  }
}

function cleanup(): void {
  resizeObserver?.disconnect()
  resizeObserver = null
  handlePointerUp()
  image.value = null
  loading.value = false
  cropping.value = false
  loadError.value = ''
  errorMessage.value = ''
  rotation.value = 0
  stageWidth.value = 0
  stageHeight.value = 0

  if (previousBodyOverflow !== null) {
    document.body.style.overflow = previousBodyOverflow
    previousBodyOverflow = null
  }
  previousFocus?.focus()
  previousFocus = null
}

watch(
  () => props.visible,
  async (visible) => {
    if (visible) {
      previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
      previousBodyOverflow = document.body.style.overflow
      document.body.style.overflow = 'hidden'
      await nextTick()
      await loadSource()
      return
    }

    cleanup()
  },
)

watch(
  () => props.file,
  () => {
    if (props.visible) void loadSource()
  },
)

watch([rotation, stageWidth, stageHeight], () => {
  if (!image.value) return
  resetCrop()
  drawPreview()
})

onMounted(() => {
  window.addEventListener('keydown', handleWindowKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleWindowKeydown)
  cleanup()
})
</script>

<template>
  <Teleport to="body">
    <Transition name="crop-fade">
      <div v-if="visible" class="crop-backdrop" @click.self="close">
        <div
          ref="dialogRef"
          class="crop-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="crop-title"
          aria-describedby="crop-desc"
          tabindex="-1"
          @keydown="handleDialogKeydown"
        >
          <header class="crop-head">
            <div>
              <p class="kicker">Crop &amp; rotate</p>
              <h2 id="crop-title">裁剪与旋转</h2>
            </div>
            <button class="btn btn--ghost btn--sm" type="button" @click="close">关闭</button>
          </header>

          <p id="crop-desc" class="crop-desc">
            拖动裁剪框调整范围，或用边角手柄缩放。不需要裁剪时，直接确认即可上传整张图片。
          </p>

          <div class="crop-toolbar">
            <button class="btn btn--outline btn--sm" type="button" @click="rotateBy(-90)">
              <IconRotateLeft aria-hidden="true" />
              左转 90°
            </button>
            <button class="btn btn--outline btn--sm" type="button" @click="rotateBy(90)">
              <IconRotateRight aria-hidden="true" />
              右转 90°
            </button>
            <button class="btn btn--ghost btn--sm" type="button" @click="resetAll">
              <IconRefresh aria-hidden="true" />
              重置
            </button>
            <span v-if="image" class="crop-toolbar__size">输出 {{ outputSizeLabel }}</span>
          </div>

          <div ref="stageRef" class="crop-stage">
            <canvas ref="canvasRef" class="crop-canvas" aria-hidden="true" />

            <div
              v-if="!loading && !loadError"
              class="crop-box"
              :style="cropStyle"
              tabindex="0"
              role="group"
              aria-label="裁剪区域，使用方向键移动，按住 Shift 加速"
              @pointerdown.stop.prevent="beginDrag($event, 'move')"
              @keydown="handleCropKeydown"
            >
              <span
                v-for="handle in HANDLES"
                :key="handle.mode"
                class="crop-handle"
                :class="`crop-handle--${handle.mode}`"
                @pointerdown.stop.prevent="beginDrag($event, handle.mode)"
              />
            </div>

            <div v-if="loading" class="crop-state">
              <a-spin :size="20" />
              <span>正在读取图片…</span>
            </div>
            <div v-else-if="loadError" class="crop-state crop-state--error" role="alert">
              {{ loadError }}
            </div>
          </div>

          <p v-if="errorMessage" class="field-error" role="alert">{{ errorMessage }}</p>

          <footer class="crop-actions">
            <button class="btn btn--outline" type="button" :disabled="cropping" @click="close">
              取消
            </button>
            <button
              class="btn btn--primary"
              type="button"
              :disabled="loading || cropping || !!loadError"
              :aria-busy="cropping"
              @click="handleConfirm"
            >
              <IconCheck aria-hidden="true" />
              {{ cropping ? '正在裁剪…' : '使用这张图片' }}
            </button>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.crop-backdrop {
  position: fixed;
  inset: 0;
  z-index: calc(var(--z-drawer) + 1);
  display: grid;
  place-items: center;
  padding: var(--space-4);
  background: var(--color-overlay);
}

.crop-dialog {
  display: flex;
  flex-direction: column;
  width: min(920px, 100%);
  max-height: calc(100vh - var(--space-8));
  padding: var(--space-5);
  overflow-y: auto;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-frame);
  background: var(--color-surface);
  box-shadow: var(--shadow-pop);
}

.crop-dialog:focus-visible {
  outline: none;
}

.crop-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
}

.crop-head h2 {
  margin-top: 4px;
  font-size: var(--text-xl);
  line-height: var(--text-xl-leading);
}

.crop-desc {
  margin-top: var(--space-2);
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-wrap: pretty;
}

.crop-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-4);
}

.crop-toolbar__size {
  margin-left: auto;
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-variant-numeric: tabular-nums;
}

.crop-stage {
  position: relative;
  height: clamp(240px, 52vh, 520px);
  margin-top: var(--space-3);
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-page-deep);
  touch-action: none;
}

.crop-canvas {
  position: absolute;
  inset: 0;
  display: block;
}

.crop-box {
  position: absolute;
  z-index: 2;
  border: 1px solid var(--color-surface);
  box-shadow:
    0 0 0 1px var(--color-text-1),
    0 0 0 9999px var(--color-overlay);
  cursor: move;
  touch-action: none;
}

.crop-handle {
  position: absolute;
  width: 14px;
  height: 14px;
  border: 1px solid var(--color-text-3);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  box-shadow: 0 0 0 1px var(--color-surface);
}

.crop-handle--nw {
  top: 0;
  left: 0;
  cursor: nwse-resize;
}

.crop-handle--n {
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  cursor: ns-resize;
}

.crop-handle--ne {
  top: 0;
  right: 0;
  cursor: nesw-resize;
}

.crop-handle--e {
  top: 50%;
  right: 0;
  transform: translateY(-50%);
  cursor: ew-resize;
}

.crop-handle--se {
  right: 0;
  bottom: 0;
  cursor: nwse-resize;
}

.crop-handle--s {
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  cursor: ns-resize;
}

.crop-handle--sw {
  bottom: 0;
  left: 0;
  cursor: nesw-resize;
}

.crop-handle--w {
  top: 50%;
  left: 0;
  transform: translateY(-50%);
  cursor: ew-resize;
}

.crop-state {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  justify-items: center;
  gap: var(--space-2);
  background: var(--color-page-deep);
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.crop-state--error {
  background: var(--color-danger-soft);
  color: var(--color-danger-text);
  text-align: center;
  padding: var(--space-4);
}

.crop-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border);
}

.crop-fade-enter-active,
.crop-fade-leave-active {
  transition: opacity 0.15s ease;
}

.crop-fade-enter-from,
.crop-fade-leave-to {
  opacity: 0;
}

@media (max-width: 767px) {
  .crop-backdrop {
    padding: var(--space-2);
    align-items: end;
  }

  .crop-dialog {
    max-height: calc(100vh - var(--space-4));
    padding: var(--space-4);
    border-radius: var(--radius-frame);
  }

  .crop-stage {
    height: clamp(220px, 42vh, 360px);
  }

  .crop-toolbar__size {
    flex-basis: 100%;
    margin-left: 0;
  }

  .crop-actions .btn {
    flex: 1;
  }
}
</style>
