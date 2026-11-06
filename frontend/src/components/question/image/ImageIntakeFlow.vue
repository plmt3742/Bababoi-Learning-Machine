<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import '@arco-design/web-vue/es/message/style/css.js'
import { IconCheck, IconRefresh } from '@arco-design/web-vue/es/icon'
import EmptyState from '../../common/EmptyState.vue'
import ErrorState from '../../common/ErrorState.vue'
import ImageCropModal from '../../upload/ImageCropModal.vue'
import ImagePicker from '../../upload/ImagePicker.vue'
import ImageItemCard from './ImageItemCard.vue'
import ImageSavedPanel from './ImageSavedPanel.vue'
import { createQuestion, generateQuestions } from '../../../api/questions'
import { extractQuestions, uploadImage } from '../../../api/uploads'
import { normalizeApiError } from '../../../api/errors'
import {
  compressImageFile,
  formatFileSize,
  MAX_UPLOAD_BYTES,
  validateImageFile,
} from '../../../utils/image'
import type { PreparedImage } from '../../../utils/image'
import {
  canSelectImageItem,
  createImageItemDrafts,
  firstDetectedSubject,
  MAX_GENERATE_SELECTION,
  toImageQuestionPayload,
  validateImageItem,
} from '../../../utils/imageIntake'
import type {
  GeneratedImageTask,
  ImageItemDraft,
  SavedImageQuestion,
} from '../../../utils/imageIntake'
import type { ImageExtractionResult } from '../../../api/types'

type IntakeStatus =
  'idle' | 'compressing' | 'uploading' | 'extracting' | 'ready' | 'empty' | 'error'

interface ImagePickerHandle {
  requestGallery: () => void
}

const props = defineProps<{
  active: boolean
  subject: string
  subjects: string[]
}>()

const emit = defineEmits<{
  'update:subject': [value: string]
  'switch-to-text': []
}>()

const router = useRouter()
const pickerRef = ref<ImagePickerHandle>()

const status = ref<IntakeStatus>('idle')
const sourceFile = ref<File | null>(null)
const pendingSourceFile = ref<File | null>(null)
const preparedImage = ref<PreparedImage | null>(null)
const previewUrl = ref('')
const uploadedPath = ref('')
const extractResult = ref<ImageExtractionResult | null>(null)
const items = ref<ImageItemDraft[]>([])
const pickerError = ref('')
const flowError = ref('')
const subjectError = ref('')
const saveAttempted = ref(false)
const saving = ref(false)
const saveNotice = ref('')
const savedItems = ref<SavedImageQuestion[]>([])
const generating = ref(false)
const generatedTasks = ref<GeneratedImageTask[]>([])
const generateError = ref('')
const cropVisible = ref(false)
const cropSource = ref<File | null>(null)
const detectedSubject = ref('')
const subjectAutoFilled = ref(false)
const extractPhase = ref<'reading' | 'structuring'>('reading')
let extractPhaseTimer: ReturnType<typeof setTimeout> | null = null

const busy = computed(
  () =>
    status.value === 'compressing' || status.value === 'uploading' || status.value === 'extracting',
)

const selectedCount = computed(() => items.value.filter((item) => item.selected).length)
const allSelected = computed(
  () =>
    items.value.length > 0 &&
    items.value.every((item) => !canSelectImageItem(item) || item.selected),
)
const extractionWarnings = computed(() => extractResult.value?.warnings ?? [])
const detectedSubjectHint = computed(() => {
  if (!detectedSubject.value) return ''
  return `AI 判断学科：${detectedSubject.value}${
    subjectAutoFilled.value ? '（已自动填入，保存前可修改）' : ''
  }`
})

const statusText = computed(() => {
  if (status.value === 'compressing') return '正在压缩图片…'
  if (status.value === 'uploading') return '正在上传裁剪后的图片…'
  if (status.value === 'extracting') {
    return extractPhase.value === 'structuring'
      ? '正在拆题，整页密排可能需要更久…'
      : '正在认字，通常需要几秒…'
  }
  return ''
})

function revokePreview(): void {
  if (!previewUrl.value) return
  URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = ''
}

function clearExtractPhaseTimer(): void {
  if (extractPhaseTimer !== null) {
    clearTimeout(extractPhaseTimer)
    extractPhaseTimer = null
  }
}

function startExtractPhaseTimer(): void {
  clearExtractPhaseTimer()
  extractPhase.value = 'reading'
  extractPhaseTimer = setTimeout(() => {
    extractPhase.value = 'structuring'
  }, 8000)
}

function resetSession(): void {
  clearExtractPhaseTimer()
  revokePreview()
  preparedImage.value = null
  uploadedPath.value = ''
  extractResult.value = null
  items.value = []
  pickerError.value = ''
  flowError.value = ''
  subjectError.value = ''
  saveAttempted.value = false
  saveNotice.value = ''
  generateError.value = ''
  detectedSubject.value = ''
  subjectAutoFilled.value = false
  status.value = 'idle'
}

function setPrepared(prepared: PreparedImage): void {
  revokePreview()
  preparedImage.value = prepared
  previewUrl.value = URL.createObjectURL(prepared.file)
}

function handleFileSelected(file: File): void {
  pickerError.value = ''
  const validationError = validateImageFile(file)
  if (validationError) {
    pickerError.value = validationError
    return
  }

  pendingSourceFile.value = file
  cropSource.value = file
  cropVisible.value = true
}

function handleCropCancel(): void {
  cropVisible.value = false
  pendingSourceFile.value = null
}

function handleCropConfirm(file: File): void {
  cropVisible.value = false
  if (pendingSourceFile.value) {
    sourceFile.value = pendingSourceFile.value
    pendingSourceFile.value = null
  }
  void processFile(file)
}

function reopenCrop(): void {
  if (!sourceFile.value) {
    pickerRef.value?.requestGallery()
    return
  }
  if (items.value.length > 0) {
    Message.warning('重新裁剪会重新识别，当前未保存的条目会被替换')
  }
  cropSource.value = sourceFile.value
  cropVisible.value = true
}

function replaceImage(): void {
  pickerRef.value?.requestGallery()
}

async function processFile(file: File): Promise<void> {
  if (busy.value || saving.value) return

  resetSession()
  status.value = 'compressing'

  let prepared: PreparedImage
  try {
    prepared = await compressImageFile(file)
  } catch (cause) {
    flowError.value = cause instanceof Error ? cause.message : '图片处理失败，请换一张重试'
    status.value = 'error'
    return
  }

  if (prepared.file.size > MAX_UPLOAD_BYTES) {
    flowError.value = `压缩后仍有 ${formatFileSize(prepared.file.size)}，超过 10MB 上传限制，请重新裁剪或换一张图片。`
    status.value = 'error'
    return
  }

  setPrepared(prepared)
  status.value = 'uploading'

  try {
    const upload = await uploadImage(prepared.file)
    uploadedPath.value = upload.image_path
  } catch (cause) {
    flowError.value = `图片上传失败：${normalizeApiError(cause).message}`
    status.value = 'error'
    return
  }

  await runExtraction()
}

async function runExtraction(): Promise<void> {
  if (!uploadedPath.value) return

  status.value = 'extracting'
  flowError.value = ''
  startExtractPhaseTimer()

  try {
    const result = await extractQuestions(uploadedPath.value, props.subject)
    extractResult.value = result
    saveAttempted.value = false
    saveNotice.value = ''

    if (result.questions.length === 0) {
      items.value = []
      status.value = 'empty'
      return
    }

    items.value = createImageItemDrafts(result)
    detectedSubject.value = firstDetectedSubject(result)
    subjectAutoFilled.value = false

    if (
      detectedSubject.value &&
      detectedSubject.value !== '待确认' &&
      !props.subject.trim()
    ) {
      emit('update:subject', detectedSubject.value)
      subjectAutoFilled.value = true
    }

    status.value = 'ready'
  } catch (cause) {
    flowError.value = normalizeApiError(cause).message
    status.value = 'error'
  } finally {
    clearExtractPhaseTimer()
  }
}

async function retryIntake(): Promise<void> {
  if (busy.value || saving.value) return

  if (!preparedImage.value) {
    if (sourceFile.value) {
      cropSource.value = sourceFile.value
      cropVisible.value = true
    } else {
      pickerRef.value?.requestGallery()
    }
    return
  }

  if (uploadedPath.value) {
    await runExtraction()
    return
  }

  await processFile(preparedImage.value.file)
}

function handleSubject(value: unknown): void {
  subjectError.value = ''
  subjectAutoFilled.value = false
  emit('update:subject', typeof value === 'string' ? value : '')
}

function handleAllSelected(value: unknown): void {
  const selected = value === true
  items.value = items.value.map((item) => ({
    ...item,
    selected: selected && canSelectImageItem(item),
  }))
}

function handleItemUpdate(next: ImageItemDraft): void {
  const index = items.value.findIndex((item) => item.key === next.key)
  if (index === -1) return
  items.value.splice(index, 1, next)
}

function removeItem(key: string): void {
  items.value = items.value.filter((item) => item.key !== key)
}

async function handleSave(): Promise<void> {
  if (saving.value) return

  const targets = items.value.filter((item) => item.selected)
  if (targets.length === 0) {
    Message.warning('请至少勾选一道题')
    return
  }

  const blocked = targets.find((item) => item.incomplete && !canSelectImageItem(item))
  if (blocked) {
    const position = items.value.findIndex((item) => item.key === blocked.key) + 1
    Message.error(`第 ${position} 道题信息不完整，请先编辑题干再勾选保存`)
    return
  }

  if (!props.subject.trim()) {
    subjectError.value = '请选择学科后再保存'
    Message.error('请选择学科后再保存')
    return
  }

  if (!uploadedPath.value) {
    flowError.value = '图片尚未上传成功，请重新识别'
    status.value = 'error'
    return
  }

  saveAttempted.value = true
  saveNotice.value = ''

  let firstInvalid: ImageItemDraft | null = null
  let firstInvalidMessage = ''

  for (const item of targets) {
    const error = validateImageItem(item)
    item.saveError = error ?? ''
    if (error && !firstInvalid) {
      firstInvalid = item
      firstInvalidMessage = error
    }
  }

  if (firstInvalid) {
    const position = items.value.findIndex((item) => item.key === firstInvalid?.key) + 1
    Message.error(`第 ${position} 道题还不能保存：${firstInvalidMessage}`)
    document
      .getElementById(`image-item-${firstInvalid.key}`)
      ?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    return
  }

  saving.value = true
  let success = 0
  let failed = 0

  for (const item of [...targets]) {
    try {
      const payload = toImageQuestionPayload(item, props.subject, uploadedPath.value)
      const result = await createQuestion(payload)
      savedItems.value = [
        ...savedItems.value,
        { question: result.question, taskId: result.task_id },
      ]
      items.value = items.value.filter((entry) => entry.key !== item.key)
      success += 1
    } catch (cause) {
      failed += 1
      item.saveError = normalizeApiError(cause).message
    }
  }

  saving.value = false
  saveAttempted.value = false

  if (success > 0) {
    Message.success(`已保存 ${success} 道题，分析任务已入队`)
    saveNotice.value =
      failed > 0 ? `已保存 ${success} 道，${failed} 道失败；失败条目已保留，可修改后重试。` : ''
    await nextTick()
    document.getElementById('image-saved-panel')?.scrollIntoView({
      behavior: 'smooth',
      block: 'start',
    })
  }

  if (failed > 0) {
    if (success === 0) Message.error(`${failed} 道题保存失败，请检查后重试`)
    else Message.warning(`${failed} 道题保存失败，已保留在原位`)
  }
}

async function handleGenerate(questionIds: number[]): Promise<void> {
  if (generating.value) return
  if (questionIds.length > MAX_GENERATE_SELECTION) {
    generateError.value = `最多选择 ${MAX_GENERATE_SELECTION} 道题生成相似题`
    return
  }

  const pending = questionIds.filter(
    (questionId) => !generatedTasks.value.some((task) => task.questionId === questionId),
  )
  if (pending.length === 0) return

  generating.value = true
  generateError.value = ''
  const created: GeneratedImageTask[] = []
  const failures: string[] = []

  for (const questionId of pending) {
    try {
      const result = await generateQuestions(questionId)
      if (result.tasks.length === 0) throw new Error('生成任务未返回 task_id')
      created.push({
        questionId,
        taskIds: result.tasks.map((task) => task.task_id),
      })
    } catch (cause) {
      failures.push(`#${questionId} ${normalizeApiError(cause).message}`)
    }
  }

  if (created.length > 0) {
    generatedTasks.value = [...generatedTasks.value, ...created]
  }
  generating.value = false

  const createdTaskCount = created.reduce((count, task) => count + task.taskIds.length, 0)
  if (createdTaskCount > 0) Message.success(`已创建 ${createdTaskCount} 个生成任务`)
  if (failures.length > 0) generateError.value = `部分题目生成失败：${failures.join('；')}`
}

function openQuestion(questionId: number): void {
  void router.push(`/questions/${questionId}`)
}

function goTasks(): void {
  void router.push('/tasks')
}

onBeforeUnmount(() => {
  clearExtractPhaseTimer()
  revokePreview()
})
</script>

<template>
  <div class="intake-flow">
    <div class="intake-main">
      <section class="panel" aria-labelledby="image-upload-heading">
        <div class="panel__head">
          <h2 id="image-upload-heading">1 · 选择图片</h2>
          <span class="tag">JPEG / PNG / WebP</span>
          <p class="panel__head-hint">原图 ≤20MB · 压缩到 ≤5MB / 2000px</p>
        </div>

        <div class="panel__body">
          <ImagePicker
            ref="pickerRef"
            :active="active"
            :disabled="busy || saving"
            :file="preparedImage?.file ?? sourceFile"
            :error="pickerError"
            @select="handleFileSelected"
          />

          <div v-if="preparedImage && previewUrl" class="prepared">
            <img class="prepared__image" :src="previewUrl" alt="裁剪后的图片预览" />
            <div class="prepared__body">
              <p class="prepared__name">{{ preparedImage.file.name }}</p>
              <p class="prepared__meta">
                {{ formatFileSize(preparedImage.file.size) }} · {{ preparedImage.width }} ×
                {{ preparedImage.height }} px
              </p>
              <p class="prepared__hint">
                已按最长边 2000px、目标 5MB 压缩；识别前可重新裁剪或换图。
              </p>
              <div class="prepared__actions">
                <button
                  class="btn btn--outline btn--sm"
                  type="button"
                  :disabled="busy || saving"
                  @click="reopenCrop"
                >
                  重新裁剪
                </button>
                <button
                  class="btn btn--ghost btn--sm"
                  type="button"
                  :disabled="busy || saving"
                  @click="retryIntake"
                >
                  <IconRefresh aria-hidden="true" />
                  重新识别
                </button>
                <button
                  class="btn btn--ghost btn--sm"
                  type="button"
                  :disabled="busy || saving"
                  @click="replaceImage"
                >
                  更换图片
                </button>
              </div>
            </div>
          </div>

          <div v-if="busy" class="intake-status" role="status" aria-live="polite">
            <a-spin :size="20" />
            <div>
              <p class="intake-status__title">{{ statusText }}</p>
              <p class="intake-status__hint">请勿关闭页面；识别结果会以可编辑条目展示。</p>
            </div>
          </div>

          <div v-if="status === 'error'" class="intake-error">
            <ErrorState
              title="图片处理失败"
              :message="flowError"
              retry-label="重试"
              @retry="retryIntake"
            >
              <button class="btn btn--ghost btn--sm" type="button" @click="emit('switch-to-text')">
                改文本录入
              </button>
            </ErrorState>
          </div>
        </div>
      </section>

      <section v-if="status === 'empty'" class="panel">
        <div class="panel__body">
          <EmptyState
            title="没有识别出题目"
            description="图片可能太模糊或没有完整题目。可以换一张更清晰的图片，或改用文本录入。"
            action-label="重新识别"
            @action="retryIntake"
          >
            <button class="btn btn--ghost btn--sm" type="button" @click="emit('switch-to-text')">
              改文本录入
            </button>
          </EmptyState>
        </div>
      </section>

      <section
        v-if="status === 'ready' && items.length === 0 && savedItems.length === 0"
        class="panel"
      >
        <div class="panel__body">
          <EmptyState
            title="条目已全部删除"
            description="可以重新识别这张图片，或切换到文本录入继续记录。"
            action-label="重新识别"
            @action="retryIntake"
          >
            <button class="btn btn--ghost btn--sm" type="button" @click="emit('switch-to-text')">
              改文本录入
            </button>
          </EmptyState>
        </div>
      </section>

      <section
        v-if="status === 'ready' && items.length > 0"
        class="panel"
        aria-labelledby="image-items-heading"
      >
        <div class="panel__head">
          <h2 id="image-items-heading">2 · 核对提取结果</h2>
          <span class="tag tag--run">{{ items.length }} 道</span>
          <p class="panel__head-hint">按图片阅读顺序编号 ① ② ③…</p>
        </div>

        <div class="panel__body">
          <div class="items-toolbar">
            <a-checkbox
              :model-value="allSelected"
              :indeterminate="selectedCount > 0 && !allSelected"
              @update:model-value="handleAllSelected"
            >
              全选
            </a-checkbox>
            <span class="items-toolbar__count"
              >已选 {{ selectedCount }} / {{ items.length }} 道保存</span
            >
          </div>

          <div v-if="extractionWarnings.length" class="extraction-warnings" role="status">
            <span v-for="warning in extractionWarnings" :key="warning" class="tag tag--reviewing">
              {{ warning }}
            </span>
          </div>

          <p v-if="saveNotice" class="flow-notice" role="status">{{ saveNotice }}</p>

          <div class="item-list">
            <ImageItemCard
              v-for="(item, index) in items"
              :key="item.key"
              :item="item"
              :position="index + 1"
              :show-validation="saveAttempted"
              :disabled="saving"
              @update="handleItemUpdate"
              @remove="removeItem(item.key)"
            />
          </div>

          <div class="save-bar">
            <p class="save-bar__hint">保存后每题会创建分析任务；未勾选的条目不会入库。</p>
            <button
              class="btn btn--primary"
              type="button"
              :disabled="saving || selectedCount === 0"
              :aria-busy="saving"
              @click="handleSave"
            >
              <IconCheck aria-hidden="true" />
              {{ saving ? '正在保存…' : `保存选中 ${selectedCount} 道` }}
            </button>
          </div>
        </div>
      </section>

      <ImageSavedPanel
        v-if="savedItems.length > 0"
        :saved="savedItems"
        :generating="generating"
        :tasks="generatedTasks"
        :error="generateError"
        @generate="handleGenerate"
        @go-tasks="goTasks"
        @open-question="openQuestion"
      />
    </div>

    <aside class="intake-side" aria-label="图片录入设置">
      <section class="panel panel--pad" aria-labelledby="image-subject-heading">
        <h2 id="image-subject-heading" class="panel__title">题目信息</h2>

        <div class="field">
          <label class="field-label" for="image-subject">
            学科 <span class="req-text">必填</span>
          </label>
          <a-select
            id="image-subject"
            :model-value="subject"
            :options="subjects"
            placeholder="请选择学科"
            aria-label="学科"
            @update:model-value="handleSubject"
          />
          <p v-if="subjectError" class="field-error" role="alert">{{ subjectError }}</p>
          <p v-if="detectedSubjectHint" class="hint">{{ detectedSubjectHint }}</p>
        </div>

        <p class="hint">
          识别后 AI 会自动判断学科、章节、题型和难度；未手选学科时会用 AI 结果预填，保存前请核对。
        </p>
      </section>

      <section class="panel panel--pad" aria-labelledby="image-rules-heading">
        <h2 id="image-rules-heading" class="panel__title">图片要求</h2>
        <ul class="rules">
          <li>支持 JPEG / PNG / WebP，原图不超过 20MB。</li>
          <li>上传前会压缩到最长边 2000px、目标 5MB。</li>
          <li>电脑可粘贴截图；手机可拍照或从相册选择。</li>
          <li>当前阶段只提取文字和公式；含图题会标记提醒。</li>
        </ul>
        <button
          class="btn btn--ghost btn--sm btn--block fallback-button"
          type="button"
          @click="emit('switch-to-text')"
        >
          改文本录入
        </button>
      </section>
    </aside>

    <ImageCropModal
      :visible="cropVisible"
      :file="cropSource"
      @cancel="handleCropCancel"
      @confirm="handleCropConfirm"
    />
  </div>
</template>

<style scoped>
.intake-flow {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  align-items: start;
  gap: var(--space-5);
}

.intake-main,
.intake-side {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  min-width: 0;
}

.intake-side {
  position: sticky;
  top: calc(var(--layout-topbar-height) + var(--space-5));
}

.prepared {
  display: grid;
  grid-template-columns: 168px minmax(0, 1fr);
  gap: var(--space-4);
  margin-top: var(--space-4);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface-subtle);
}

.prepared__image {
  width: 100%;
  height: 132px;
  object-fit: contain;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-page-deep);
}

.prepared__body {
  min-width: 0;
}

.prepared__name {
  overflow-wrap: anywhere;
  color: var(--color-text-1);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-weight: 650;
}

.prepared__meta {
  margin-top: 2px;
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-variant-numeric: tabular-nums;
}

.prepared__hint {
  margin-top: var(--space-1);
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-wrap: pretty;
}

.prepared__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-2);
}

.intake-status {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  margin-top: var(--space-4);
  padding: var(--space-3);
  border: 1px solid var(--color-primary-border);
  border-radius: var(--radius-md);
  background: var(--color-primary-softer);
}

.intake-status__title {
  color: var(--color-text-1);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-weight: 650;
}

.intake-status__hint {
  margin-top: 2px;
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.intake-error {
  margin-top: var(--space-4);
}

.items-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.items-toolbar__count {
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-variant-numeric: tabular-nums;
}

.extraction-warnings {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-warning-border);
  border-radius: var(--radius-md);
  background: var(--color-warning-soft);
}

.extraction-warnings .tag {
  height: auto;
  min-height: 26px;
  padding: 3px 8px;
  white-space: normal;
  line-height: 18px;
}

.flow-notice {
  margin-top: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-warning-border);
  border-radius: var(--radius-md);
  background: var(--color-warning-soft);
  color: var(--color-warning-text);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-wrap: pretty;
}

.item-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin-top: var(--space-4);
}

.save-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border);
}

.save-bar__hint {
  max-width: 52ch;
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-wrap: pretty;
}

.rules {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: 0;
  padding-left: var(--space-4);
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-wrap: pretty;
}

.fallback-button {
  margin-top: var(--space-4);
  justify-content: flex-start;
  padding-left: 0;
}

@media (max-width: 1100px) {
  .intake-flow {
    grid-template-columns: minmax(0, 1fr);
  }

  .intake-side {
    position: static;
  }
}

@media (max-width: 767px) {
  .prepared {
    grid-template-columns: minmax(0, 1fr);
  }

  .prepared__image {
    height: 180px;
  }

  .save-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .save-bar .btn {
    width: 100%;
  }

  .prepared__actions .btn {
    flex: 1;
  }
}
</style>
