<script lang="ts">
type MermaidApi = (typeof import('mermaid'))['default']

let nextDiagramId = 0
let mermaidPromise: Promise<MermaidApi> | null = null

function loadMermaid(): Promise<MermaidApi> {
  if (!mermaidPromise) {
    mermaidPromise = import('mermaid')
      .then(({ default: mermaid }) => {
        mermaid.initialize({
          startOnLoad: false,
          securityLevel: 'strict',
          theme: 'neutral',
          htmlLabels: false,
          flowchart: { useMaxWidth: true },
          sequence: { useMaxWidth: true },
        })
        return mermaid
      })
      .catch((error: unknown) => {
        mermaidPromise = null
        throw error
      })
  }
  return mermaidPromise
}
</script>

<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import DOMPurify from 'dompurify'

const props = defineProps<{
  source: string
}>()

const canvas = ref<HTMLElement | null>(null)
const status = ref<'loading' | 'ready' | 'error'>('loading')

let diagramSequence = 0
let disposed = false

async function renderDiagram(): Promise<void> {
  const token = ++diagramSequence
  const renderId = `mermaid-diagram-${++nextDiagramId}`
  status.value = 'loading'

  try {
    const mermaid = await loadMermaid()
    if (disposed || token !== diagramSequence) return

    const { svg } = await mermaid.render(renderId, props.source)
    if (disposed || token !== diagramSequence) return

    const clean = DOMPurify.sanitize(svg, {
      USE_PROFILES: { svg: true, svgFilters: true },
      ADD_TAGS: ['style'],
      ADD_ATTR: ['style'],
    })
    if (!canvas.value) return

    canvas.value.innerHTML = clean
    status.value = 'ready'
  } catch {
    document.getElementById(`d${renderId}`)?.remove()
    document.getElementById(renderId)?.remove()
    if (disposed || token !== diagramSequence) return
    status.value = 'error'
  }
}

watch(
  () => props.source,
  () => {
    void renderDiagram()
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  disposed = true
  diagramSequence += 1
})
</script>

<template>
  <figure class="mermaid-block" :class="`mermaid-block--${status}`">
    <figcaption class="sr-only">关系图</figcaption>
    <div ref="canvas" class="mermaid-block__canvas" :aria-busy="status === 'loading'" />
    <div v-if="status !== 'ready'" class="mermaid-block__fallback">
      <p class="mermaid-block__note" :role="status === 'error' ? 'status' : undefined">
        {{ status === 'error' ? '图形渲染失败，已显示源码。' : '正在渲染关系图…' }}
      </p>
      <pre class="mermaid-block__source"><code>{{ source }}</code></pre>
    </div>
  </figure>
</template>

<style scoped>
.mermaid-block {
  margin: var(--space-3) 0;
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-subtle);
  overflow-x: auto;
}

.mermaid-block__canvas :deep(svg) {
  display: block;
  max-width: 100%;
  height: auto;
  margin: 0 auto;
}

.mermaid-block__note {
  margin-bottom: var(--space-2);
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.mermaid-block--error .mermaid-block__note {
  color: var(--color-danger-text);
}

.mermaid-block .mermaid-block__source {
  overflow-x: auto;
  margin: 0;
  padding: var(--space-2);
  border: 0;
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text-2);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

@media print {
  .mermaid-block {
    break-inside: avoid;
  }
}
</style>
