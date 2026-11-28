<script setup lang="ts">
interface LatexSnippet {
  label: string
  title: string
  template: string
  caretOffset: number
}

const SNIPPETS: LatexSnippet[] = [
  { label: '行内', title: '行内公式 $...$', template: '$ $', caretOffset: 1 },
  { label: '分式', title: '分式 \\frac{分子}{分母}', template: '\\frac{}{}', caretOffset: 6 },
  { label: '根号', title: '根号 \\sqrt{}', template: '\\sqrt{}', caretOffset: 6 },
  { label: '积分', title: '积分 \\int_{下限}^{上限}', template: '\\int_{}^{} ', caretOffset: 6 },
  { label: '极限', title: '极限 \\lim_{x \\to }', template: '\\lim_{x \\to }', caretOffset: 12 },
  { label: '求和', title: '求和 \\sum_{i=1}^{n}', template: '\\sum_{i=1}^{n} ', caretOffset: 12 },
  {
    label: '偏导',
    title: '偏导 \\frac{\\partial}{\\partial x}',
    template: '\\frac{\\partial }{\\partial x}',
    caretOffset: 15,
  },
  { label: '块级', title: '块级公式 $$...$$', template: '\n$$\n\n$$\n', caretOffset: 4 },
]

const emit = defineEmits<{
  insert: [template: string, caretOffset: number]
}>()
</script>

<template>
  <div class="latex-toolbar" role="group" aria-label="常用公式快捷插入">
    <button
      v-for="snippet in SNIPPETS"
      :key="snippet.label"
      class="latex-chip"
      type="button"
      :title="snippet.title"
      @click="emit('insert', snippet.template, snippet.caretOffset)"
    >
      {{ snippet.label }}
    </button>
  </div>
</template>

<style scoped>
.latex-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: var(--space-2);
}

.latex-chip {
  min-height: 28px;
  padding: 0 9px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: 1;
}

.latex-chip:hover {
  border-color: var(--color-border-strong);
  background: var(--color-surface-hover);
  color: var(--color-text-1);
}

.latex-chip:focus-visible {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}
</style>
