<script setup lang="ts">
import { computed } from 'vue'
import 'katex/dist/katex.min.css'
import { renderMarkdown } from '../../utils/markdown'

const props = withDefaults(
  defineProps<{
    content: string
    /** Keep block spacing tight when rendered inside list items or summaries. */
    compact?: boolean
  }>(),
  { compact: false },
)

const rendered = computed(() => renderMarkdown(props.content))
</script>

<template>
  <!-- rendered HTML is sanitized by DOMPurify in utils/markdown.ts -->
  <!-- eslint-disable vue/no-v-html -->
  <div
    class="markdown-renderer"
    :class="{ 'markdown-renderer--compact': compact }"
    v-html="rendered"
  />
  <!-- eslint-enable vue/no-v-html -->
</template>

<style scoped>
.markdown-renderer {
  overflow-wrap: anywhere;
  color: var(--color-text-1);
  font-size: var(--text-base);
  line-height: var(--text-base-leading);
}

.markdown-renderer :deep(> :first-child) {
  margin-top: 0;
}

.markdown-renderer :deep(> :last-child) {
  margin-bottom: 0;
}

.markdown-renderer :deep(p) {
  margin: 0 0 var(--space-3);
  text-wrap: pretty;
}

.markdown-renderer :deep(h1),
.markdown-renderer :deep(h2),
.markdown-renderer :deep(h3),
.markdown-renderer :deep(h4) {
  margin: var(--space-5) 0 var(--space-2);
  color: var(--color-text-1);
}

.markdown-renderer :deep(h1) {
  font-size: var(--text-xl);
  line-height: var(--text-xl-leading);
}

.markdown-renderer :deep(h2) {
  font-size: var(--text-lg);
  line-height: var(--text-lg-leading);
}

.markdown-renderer :deep(h3),
.markdown-renderer :deep(h4) {
  font-size: var(--text-base);
  line-height: var(--text-base-leading);
}

.markdown-renderer :deep(ul),
.markdown-renderer :deep(ol) {
  margin: 0 0 var(--space-3);
  padding-left: var(--space-5);
}

.markdown-renderer :deep(li + li) {
  margin-top: var(--space-1);
}

.markdown-renderer :deep(a) {
  color: var(--color-primary);
  text-decoration: underline;
  text-underline-offset: 2px;
}

.markdown-renderer :deep(a:hover) {
  color: var(--color-primary-hover);
}

.markdown-renderer :deep(strong) {
  font-weight: 600;
}

.markdown-renderer :deep(code) {
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  background: var(--color-fill);
  color: var(--color-text-1);
  font-family: var(--font-mono);
  font-size: 0.92em;
}

.markdown-renderer :deep(pre) {
  overflow-x: auto;
  margin: 0 0 var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-fill);
}

.markdown-renderer :deep(pre code) {
  padding: 0;
  background: none;
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.markdown-renderer :deep(blockquote) {
  margin: 0 0 var(--space-3);
  padding-left: var(--space-3);
  border-left: 2px solid var(--color-border);
  color: var(--color-text-2);
}

.markdown-renderer :deep(table) {
  width: 100%;
  margin: 0 0 var(--space-3);
  border-collapse: collapse;
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.markdown-renderer :deep(th),
.markdown-renderer :deep(td) {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  text-align: left;
  vertical-align: top;
}

.markdown-renderer :deep(th) {
  background: var(--color-fill);
  color: var(--color-text-1);
  font-weight: 600;
}

.markdown-renderer :deep(hr) {
  margin: var(--space-5) 0;
  border: 0;
  border-top: 1px solid var(--color-border);
}

.markdown-renderer :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: var(--radius-md);
}

.markdown-renderer :deep(.md-math-inline) {
  display: inline-block;
  max-width: 100%;
  vertical-align: baseline;
}

.markdown-renderer :deep(.md-math-block) {
  overflow-x: auto;
  padding: var(--space-2) 0;
  text-align: center;
}

.markdown-renderer :deep(.md-math-display) {
  display: block;
  overflow-x: auto;
  padding: var(--space-2) 0;
}

.markdown-renderer :deep(.katex) {
  font-size: 1.05em;
}

.markdown-renderer :deep(.katex-display) {
  margin: 0;
}

.markdown-renderer :deep(.katex-error) {
  color: var(--color-danger);
  font-family: var(--font-mono);
}

.markdown-renderer :deep(.md-math-fallback) {
  color: var(--color-danger);
}

.markdown-renderer--compact {
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.markdown-renderer--compact :deep(p) {
  margin-bottom: var(--space-1);
}

.markdown-renderer--compact :deep(ul),
.markdown-renderer--compact :deep(ol) {
  margin-bottom: var(--space-1);
  padding-left: var(--space-4);
}
</style>
