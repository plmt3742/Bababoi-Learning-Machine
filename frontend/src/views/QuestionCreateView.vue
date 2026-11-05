<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import type { FieldRule, FormInstance } from '@arco-design/web-vue'
import { IconCheck } from '@arco-design/web-vue/es/icon'
import '@arco-design/web-vue/es/message/style/css.js'
import PageHeader from '../components/common/PageHeader.vue'
import MarkdownRenderer from '../components/common/MarkdownRenderer.vue'
import { createQuestion } from '../api/questions'
import { normalizeApiError } from '../api/errors'
import type { QuestionCreate } from '../api/types'

const MAX_CONTENT_LENGTH = 5000
const MAX_TAGS = 10
const SUBJECTS = ['高等数学', '线性代数', '概率论与数理统计', '大学物理']

const router = useRouter()
const formRef = ref<FormInstance>()
const submitting = ref(false)
const editMode = ref(true)
const errorMessage = ref('')

const form = reactive({
  subject: '',
  chapter: '',
  content_md: '',
  answer_md: '',
  explanation_md: '',
  tags: [] as string[],
})

const rules: Record<string, FieldRule[]> = {
  subject: [{ required: true, message: '请选择学科' }],
  chapter: [{ maxLength: 100, message: '章节不能超过 100 个字符' }],
  content_md: [
    {
      validator: (value, callback) => {
        if (typeof value !== 'string' || value.trim().length === 0) callback('请输入题干')
        else callback()
      },
    },
    { maxLength: MAX_CONTENT_LENGTH, message: '题干不能超过 5000 个字符' },
  ],
  answer_md: [{ maxLength: MAX_CONTENT_LENGTH, message: '答案不能超过 5000 个字符' }],
  explanation_md: [{ maxLength: MAX_CONTENT_LENGTH, message: '解析不能超过 5000 个字符' }],
  tags: [
    {
      validator: (value, callback) => {
        const tags = Array.isArray(value) ? value : []
        if (tags.length > MAX_TAGS) callback(`最多添加 ${MAX_TAGS} 个标签`)
        else callback()
      },
    },
  ],
}

function normalizedTags(): string[] {
  const seen = new Set<string>()
  const tags: string[] = []

  for (const rawTag of form.tags) {
    const tag = rawTag.trim()
    if (!tag || seen.has(tag)) continue
    seen.add(tag)
    tags.push(tag)
    if (tags.length >= MAX_TAGS) break
  }

  return tags
}

async function handleSubmit(): Promise<void> {
  if (submitting.value || !formRef.value) return

  const validationErrors = await formRef.value.validate()
  if (validationErrors) {
    // Keep the stem error visible when the user submits from preview mode.
    if (validationErrors.content_md) editMode.value = true
    return
  }

  submitting.value = true
  errorMessage.value = ''

  try {
    const payload: QuestionCreate = {
      subject: form.subject,
      chapter: form.chapter.trim() || null,
      source_type: 'text',
      question_type: 'solve',
      content_md: form.content_md.trim(),
      answer_md: form.answer_md.trim() || null,
      explanation_md: form.explanation_md.trim() || null,
      tags: normalizedTags(),
    }

    const result = await createQuestion(payload)

    Message.success({
      content: `已保存，AI 分析任务已入队（#${result.task_id}）`,
      duration: 3500,
    })
    await router.push(`/questions/${result.question.id}`)
  } catch (cause) {
    errorMessage.value = normalizeApiError(cause).message
  } finally {
    submitting.value = false
  }
}

function handleCancel(): void {
  void router.push('/questions')
}
</script>

<template>
  <div class="page">
    <PageHeader
      eyebrow="New entry"
      title="录入错题"
      description="先记录题目原文和答案，保存后 AI 会在后台补全考点分析并生成相似题。"
    />

    <a-alert
      v-if="errorMessage"
      class="page__error"
      type="error"
      show-icon
      closable
      @close="errorMessage = ''"
    >
      {{ errorMessage }}
    </a-alert>

    <a-form
      ref="formRef"
      class="editor-layout"
      :model="form"
      :rules="rules"
      layout="vertical"
      @submit="handleSubmit"
    >
      <div class="editor-main">
        <section class="panel" aria-labelledby="stem-heading">
          <div class="panel__head">
            <h2 id="stem-heading">题干</h2>
            <span class="req">必填</span>
            <div class="seg" role="group" aria-label="题干显示模式">
              <button type="button" :aria-pressed="editMode" @click="editMode = true">编辑</button>
              <button type="button" :aria-pressed="!editMode" @click="editMode = false">
                预览
              </button>
            </div>
          </div>
          <div class="panel__body">
            <div v-show="editMode" class="stem-editor">
              <label class="field-label" for="content-md">题目原文</label>
              <a-form-item field="content_md" hide-label>
                <a-textarea
                  v-model="form.content_md"
                  class="editor-area"
                  placeholder="例如：求函数 $f(x)=x^3-3x+1$ 的极值。"
                  :auto-size="{ minRows: 4, maxRows: 18 }"
                  :max-length="MAX_CONTENT_LENGTH"
                  :textarea-attrs="{ id: 'content-md' }"
                  allow-clear
                />
              </a-form-item>
              <div class="editor-meta">
                <span>支持 Markdown；公式用 $...$ 或 $$...$$ 包裹</span>
                <span class="editor-meta__count">
                  {{ form.content_md.length }} / {{ MAX_CONTENT_LENGTH }}
                </span>
              </div>
              <div class="preview">
                <p class="preview__label">渲染预览</p>
                <div class="preview__body">
                  <MarkdownRenderer v-if="form.content_md.trim()" :content="form.content_md" />
                  <p v-else class="preview__empty">输入题干后，这里会显示渲染结果。</p>
                </div>
              </div>
            </div>

            <div v-if="!editMode" class="preview preview--solo">
              <p class="preview__label">渲染预览</p>
              <div class="preview__body">
                <MarkdownRenderer v-if="form.content_md.trim()" :content="form.content_md" />
                <p v-else class="preview__empty">还没有内容，切换到编辑模式输入题干。</p>
              </div>
            </div>
          </div>
        </section>

        <section class="panel" aria-labelledby="answer-heading">
          <div class="panel__head">
            <h2 id="answer-heading">答案与解析</h2>
            <span class="tag">可选</span>
            <p class="panel__head-hint">留空也可保存</p>
          </div>
          <div class="panel__body">
            <div class="field">
              <label class="field-label" for="answer-md">答案</label>
              <a-form-item field="answer_md" hide-label>
                <a-input
                  v-model="form.answer_md"
                  placeholder="例如：极大值 $f(-1)=3$，极小值 $f(1)=-1$。"
                  :max-length="MAX_CONTENT_LENGTH"
                  :input-attrs="{ id: 'answer-md' }"
                  allow-clear
                />
              </a-form-item>
            </div>

            <div class="field">
              <label class="field-label" for="explanation-md">解析</label>
              <a-form-item field="explanation_md" hide-label>
                <a-textarea
                  v-model="form.explanation_md"
                  placeholder="写下你的解题过程，或留空等待 AI 补全。"
                  :auto-size="{ minRows: 3, maxRows: 12 }"
                  :max-length="MAX_CONTENT_LENGTH"
                  :textarea-attrs="{ id: 'explanation-md' }"
                  allow-clear
                />
              </a-form-item>
            </div>

            <p class="hint">已填写的内容不会被 AI 覆盖；留空时，分析任务会补全考点与解题摘要。</p>
          </div>
        </section>

        <section class="panel" aria-labelledby="structure-heading">
          <div class="panel__head">
            <h2 id="structure-heading">结构与题型</h2>
          </div>
          <div class="panel__body">
            <div class="type-row">
              <span class="type-row__label">题型</span>
              <span class="tag">解答题</span>
            </div>
            <p class="info-note">
              当前版本按解答题结构保存；选择题选项、填空题空位编辑器将在 FE-020 提供，AI
              分析结果不受影响。
            </p>
          </div>
        </section>
      </div>

      <aside class="editor-side" aria-label="题目元信息">
        <section class="panel panel--pad meta-panel" aria-labelledby="meta-heading">
          <h2 id="meta-heading" class="panel__title">题目信息</h2>

          <div class="field">
            <label class="field-label" for="subject">学科 <span class="req-text">必填</span></label>
            <a-form-item field="subject" hide-label>
              <a-select
                id="subject"
                v-model="form.subject"
                placeholder="请选择学科"
                :options="SUBJECTS"
                aria-label="学科"
              />
            </a-form-item>
          </div>

          <div class="field">
            <label class="field-label" for="chapter">章节</label>
            <a-form-item field="chapter" hide-label>
              <a-input
                v-model="form.chapter"
                placeholder="例如：导数与极值"
                :max-length="100"
                :input-attrs="{ id: 'chapter' }"
                allow-clear
              />
            </a-form-item>
          </div>

          <div class="field">
            <label class="field-label" for="tags">知识点标签</label>
            <a-form-item field="tags" hide-label>
              <a-input-tag
                id="tags"
                v-model="form.tags"
                placeholder="输入后按回车添加"
                :max-tag-count="MAX_TAGS"
                :unique-value="true"
                allow-clear
                aria-label="知识点标签"
              />
            </a-form-item>
          </div>

          <p class="hint">
            输入后按回车添加；标签用于筛选与薄弱知识点统计，最多 {{ MAX_TAGS }} 个。
          </p>
        </section>

        <section class="panel panel--pad" aria-labelledby="after-heading">
          <h2 id="after-heading" class="panel__title">保存后会发生什么</h2>
          <ol class="save-steps">
            <li>
              <span class="save-steps__num" aria-hidden="true">1</span>
              <span>错题立即保存到你的错题本。</span>
            </li>
            <li>
              <span class="save-steps__num" aria-hidden="true">2</span>
              <span>后台创建分析任务，补全考点、错因和解题摘要。</span>
            </li>
            <li>
              <span class="save-steps__num" aria-hidden="true">3</span>
              <span>在详情页生成 3 道相似题，并返回任务中心跟踪。</span>
            </li>
          </ol>
        </section>
      </aside>
    </a-form>

    <div class="sticky-actions" role="region" aria-label="录入操作">
      <p>保存后将自动创建分析任务，可在任务中心查看进度。</p>
      <div class="sticky-actions__buttons">
        <button class="btn btn--outline" type="button" @click="handleCancel">取消</button>
        <button
          class="btn btn--primary"
          type="button"
          :disabled="submitting"
          :aria-busy="submitting"
          @click="handleSubmit"
        >
          <IconCheck aria-hidden="true" />
          保存并分析
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
}

.page__error {
  align-items: flex-start;
  margin-bottom: var(--space-5);
}

.editor-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  align-items: start;
  gap: var(--space-5);
}

.editor-main,
.editor-side {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  min-width: 0;
}

.editor-side {
  position: sticky;
  top: calc(var(--layout-topbar-height) + var(--space-5));
}

/* Segmented edit / preview control */
.seg {
  display: inline-flex;
  margin-left: auto;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.seg button {
  min-height: 32px;
  padding: 0 11px;
  border: 0;
  background: var(--color-surface);
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: 1;
}

.seg button + button {
  border-left: 1px solid var(--color-border);
}

.seg button:hover {
  background: var(--color-bg);
}

.seg button[aria-pressed='true'] {
  background: var(--color-primary-soft);
  color: var(--color-primary-active);
  font-weight: 650;
}

/* Stem editor */
.editor-area.editor-area :deep(.arco-textarea) {
  min-height: 138px;
  padding: 13px var(--space-4);
  background: var(--color-surface);
  font-size: var(--text-base);
  line-height: var(--text-base-leading);
  resize: vertical;
}

.panel__body.panel__body :deep(.arco-form-item) {
  margin-bottom: 0;
}

.editor-meta {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  margin-top: 7px;
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.editor-meta__count {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.preview {
  margin-top: var(--space-4);
  padding-top: 13px;
  border-top: 1px dashed var(--color-border-strong);
}

.preview--solo {
  margin-top: 0;
  padding-top: 0;
  border-top: 0;
}

.preview__label {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  font-weight: 600;
  letter-spacing: 0.06em;
}

.preview__body {
  max-width: 46em;
  margin-top: var(--space-1);
}

.preview__empty {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

/* Answer + structure */
.field + .field {
  margin-top: var(--space-3);
}

.panel__head .tag {
  flex: none;
}

.type-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.type-row__label {
  color: var(--color-text-2);
  font-size: var(--text-sm);
  font-weight: 600;
}

.info-note {
  margin-top: var(--space-4);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-subtle);
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  text-wrap: pretty;
}

/* Side metadata */
.meta-panel.meta-panel :deep(.arco-form-item) {
  margin-bottom: 0;
}

.meta-panel :deep(.arco-form-item-message) {
  margin-top: var(--space-1);
}

.meta-panel :deep(.arco-input-tag) {
  gap: 6px;
  padding: 4px 7px;
}

.save-steps {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin: 0;
  list-style: none;
}

.save-steps li {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.save-steps__num {
  display: grid;
  place-items: center;
  flex: none;
  width: 24px;
  height: 24px;
  border: 1px solid var(--color-border-strong);
  border-radius: 50%;
  background: var(--color-surface);
  color: var(--color-primary-active);
  font-family: var(--font-math);
  font-size: var(--text-sm);
  line-height: 1;
}

/* Sticky save bar */
.sticky-actions {
  position: sticky;
  bottom: var(--space-4);
  z-index: var(--z-sidebar);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-top: var(--space-5);
  padding: 11px var(--space-4);
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-bar);
}

.sticky-actions > p {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.sticky-actions__buttons {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

@media (max-width: 1100px) {
  .editor-layout {
    grid-template-columns: minmax(0, 1fr);
  }

  .editor-side {
    position: static;
  }
}

@media (max-width: 767px) {
  .panel__head {
    padding: 12px var(--space-4);
  }

  .panel__body,
  .panel--pad {
    padding: var(--space-4);
  }

  .editor-meta {
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
  }

  .sticky-actions {
    bottom: calc(var(--layout-bottom-nav-height) + env(safe-area-inset-bottom) + var(--space-2));
    flex-direction: column;
    align-items: stretch;
    padding: 10px var(--space-3);
  }

  .sticky-actions > p {
    display: none;
  }

  .sticky-actions__buttons {
    width: 100%;
  }

  .sticky-actions__buttons .btn {
    flex: 1;
    min-height: 44px;
  }
}
</style>
