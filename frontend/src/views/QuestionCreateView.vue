<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import type { FieldRule, FormInstance } from '@arco-design/web-vue'
import { IconCheck } from '@arco-design/web-vue/es/icon'
import '@arco-design/web-vue/es/message/style/css.js'
import PageHeader from '../components/common/PageHeader.vue'
import { createQuestion } from '../api/questions'
import { normalizeApiError } from '../api/errors'
import type { QuestionCreate } from '../api/types'

const MAX_CONTENT_LENGTH = 5000
const MAX_TAGS = 10
const SUBJECTS = ['高等数学', '线性代数', '概率论与数理统计', '大学物理']

const router = useRouter()
const formRef = ref<FormInstance>()
const submitting = ref(false)
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
  if (validationErrors) return

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
      eyebrow="QEDIT-01"
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
      <div class="editor-layout__main">
        <a-card class="editor-card" :bordered="false">
          <header class="editor-card__header">
            <div class="editor-card__heading">
              <span class="editor-card__index" aria-hidden="true">01</span>
              <div>
                <h2 class="editor-card__title">题干</h2>
                <p class="editor-card__hint">支持 Markdown；公式用 $...$ 或 $$...$$ 包裹。</p>
              </div>
            </div>
            <a-tag size="small" color="gray">必填</a-tag>
          </header>

          <a-form-item field="content_md" label="题目原文" hide-label>
            <a-textarea
              v-model="form.content_md"
              class="editor-card__input"
              placeholder="例如：求函数 $f(x)=x^3-3x+1$ 的极值。"
              :auto-size="{ minRows: 8, maxRows: 18 }"
              :max-length="MAX_CONTENT_LENGTH"
              show-word-limit
              allow-clear
            />
          </a-form-item>
        </a-card>

        <a-card class="editor-card" :bordered="false">
          <header class="editor-card__header">
            <div class="editor-card__heading">
              <span class="editor-card__index" aria-hidden="true">02</span>
              <div>
                <h2 class="editor-card__title">答案与解析</h2>
                <p class="editor-card__hint">
                  可以留空，AI 分析任务会在后台补全；已填写的内容不会被覆盖。
                </p>
              </div>
            </div>
          </header>

          <a-form-item field="answer_md" label="答案（可选）">
            <a-textarea
              v-model="form.answer_md"
              placeholder="例如：极大值 $f(-1)=3$，极小值 $f(1)=-1$。"
              :auto-size="{ minRows: 3, maxRows: 10 }"
              :max-length="MAX_CONTENT_LENGTH"
              show-word-limit
              allow-clear
            />
          </a-form-item>

          <a-form-item field="explanation_md" label="解析（可选）">
            <a-textarea
              v-model="form.explanation_md"
              placeholder="写下你的解题过程，或留空等待 AI 补全。"
              :auto-size="{ minRows: 4, maxRows: 14 }"
              :max-length="MAX_CONTENT_LENGTH"
              show-word-limit
              allow-clear
            />
          </a-form-item>
        </a-card>

        <a-card class="editor-card" :bordered="false">
          <header class="editor-card__header">
            <div class="editor-card__heading">
              <span class="editor-card__index" aria-hidden="true">03</span>
              <div>
                <h2 class="editor-card__title">结构与题型</h2>
                <p class="editor-card__hint">
                  当前阶段先按解答题保存，选项与空位编辑器在 FE-020 提供。
                </p>
              </div>
            </div>
          </header>

          <div class="question-type-row">
            <span class="question-type-row__label">题型</span>
            <a-tag color="arcoblue" size="medium">解答题</a-tag>
          </div>

          <a-alert type="info" :show-icon="true">
            选择题选项、填空题空位编辑器将在 FE-020 提供；当前按解答题结构保存，AI
            分析结果不受影响。
          </a-alert>
        </a-card>
      </div>

      <aside class="editor-layout__side">
        <a-card class="meta-card" :bordered="false">
          <h2 class="meta-card__title">题目信息</h2>

          <a-form-item field="subject" label="学科">
            <a-select
              v-model="form.subject"
              placeholder="请选择学科"
              :options="SUBJECTS"
              size="large"
            />
          </a-form-item>

          <a-form-item field="chapter" label="章节（可选）">
            <a-input
              v-model="form.chapter"
              placeholder="例如：导数与极值"
              :max-length="100"
              allow-clear
            />
          </a-form-item>

          <a-form-item field="tags" label="标签（可选）">
            <a-input-tag
              v-model="form.tags"
              placeholder="输入后按回车添加"
              :max-tag-count="MAX_TAGS"
              :unique-value="true"
              allow-clear
            />
          </a-form-item>

          <p class="meta-card__hint">标签用于筛选与薄弱知识点统计，最多 {{ MAX_TAGS }} 个。</p>
        </a-card>

        <a-card class="meta-card meta-card--tip" :bordered="false">
          <h2 class="meta-card__title">保存后会发生什么</h2>
          <ol class="meta-card__steps">
            <li>错题立即保存到你的错题本。</li>
            <li>后台创建分析任务，补全考点、难点和解题摘要。</li>
            <li>在详情页可以继续生成 3 道相似题。</li>
          </ol>
        </a-card>
      </aside>
    </a-form>

    <div class="editor-actions" role="region" aria-label="录入操作">
      <div class="editor-actions__inner">
        <a-button @click="handleCancel">取消</a-button>
        <a-button type="primary" :loading="submitting" :disabled="submitting" @click="handleSubmit">
          <template #icon>
            <IconCheck />
          </template>
          保存并分析
        </a-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  padding-bottom: calc(var(--control-height) + var(--space-6));
}

.editor-actions {
  position: fixed;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: var(--z-topbar);
  padding: var(--space-3) var(--layout-gutter);
  border-top: 1px solid var(--color-border-strong);
  background: var(--color-surface);
}

.editor-actions__inner {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  width: 100%;
  max-width: var(--layout-content-max);
  margin: 0 auto;
}

.page__error {
  align-items: flex-start;
}

.editor-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: var(--space-5);
  align-items: start;
}

.editor-layout__main,
.editor-layout__side {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  min-width: 0;
}

.editor-layout__side {
  position: sticky;
  top: calc(var(--layout-topbar-height) + var(--space-4));
}

.editor-card,
.meta-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.editor-card :deep(.arco-card-body),
.meta-card :deep(.arco-card-body) {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-5);
}

.editor-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
}

.editor-card__heading {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  min-width: 0;
}

.editor-card__index {
  flex: none;
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: var(--text-xs-leading);
  letter-spacing: 0.06em;
}

.editor-card__title,
.meta-card__title {
  font-size: var(--text-lg);
  line-height: var(--text-lg-leading);
}

.editor-card__hint,
.meta-card__hint {
  margin-top: var(--space-1);
  color: var(--color-text-3);
  font-size: var(--text-xs);
  line-height: var(--text-xs-leading);
  text-wrap: pretty;
}

.editor-card :deep(.arco-form-item) {
  margin-bottom: 0;
}

.editor-card :deep(.arco-textarea-wrapper) {
  border-radius: var(--radius-md);
}

.editor-card__input :deep(.arco-textarea) {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.question-type-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.question-type-row__label {
  color: var(--color-text-2);
  font-size: var(--text-sm);
  font-weight: 500;
}

.meta-card :deep(.arco-form-item) {
  margin-bottom: var(--space-4);
}

.meta-card :deep(.arco-form-item:last-of-type) {
  margin-bottom: 0;
}

.meta-card--tip :deep(.arco-card-body) {
  gap: var(--space-3);
}

.meta-card__steps {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  margin: 0;
  padding-left: var(--space-5);
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.meta-card__steps li::marker {
  color: var(--color-primary);
}

@media (min-width: 1200px) {
  .editor-actions {
    left: var(--layout-sidebar-width);
  }
}

@media (max-width: 1023px) {
  .editor-layout {
    grid-template-columns: minmax(0, 1fr);
  }

  .editor-layout__side {
    position: static;
  }
}

@media (max-width: 767px) {
  .editor-card :deep(.arco-card-body),
  .meta-card :deep(.arco-card-body) {
    padding: var(--space-4);
  }

  .editor-actions {
    bottom: calc(var(--layout-bottom-nav-height) + env(safe-area-inset-bottom));
    padding: var(--space-3) var(--layout-gutter-mobile);
  }
}
</style>
