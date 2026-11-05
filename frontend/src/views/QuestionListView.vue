<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageHeader from '../components/common/PageHeader.vue'
import EmptyState from '../components/common/EmptyState.vue'
import ErrorState from '../components/common/ErrorState.vue'
import LoadingSkeleton from '../components/common/LoadingSkeleton.vue'
import QuestionCard from '../components/question/QuestionCard.vue'
import { listQuestions } from '../api/questions'
import { normalizeApiError } from '../api/errors'
import type { MasteryStatus, QuestionListItem } from '../api/types'

const PAGE_SIZE = 20
const SUBJECT_OPTIONS = ['高等数学', '线性代数', '概率论与数理统计', '大学物理']
const MASTERY_OPTIONS: { label: string; value: MasteryStatus }[] = [
  { label: '未掌握', value: 'unmastered' },
  { label: '复习中', value: 'reviewing' },
  { label: '已掌握', value: 'mastered' },
]

const route = useRoute()
const router = useRouter()

const keyword = ref('')
const subject = ref('')
const tag = ref('')
const masteryStatus = ref<MasteryStatus | ''>('')
const page = ref(1)

const items = ref<QuestionListItem[]>([])
const total = ref(0)
const loading = ref(true)
const errorMessage = ref('')
const errorCode = ref('')

let requestToken = 0
let searchTimer: ReturnType<typeof setTimeout> | null = null
let pendingQueryKey: string | null = null

const hasActiveFilters = computed(
  () =>
    keyword.value.trim().length > 0 ||
    (subject.value ?? '').length > 0 ||
    tag.value.trim().length > 0 ||
    (masteryStatus.value ?? '').length > 0,
)

const pageCount = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))

const pageNumbers = computed<number[]>(() => {
  const count = pageCount.value
  if (count <= 5) return Array.from({ length: count }, (_, index) => index + 1)

  let start = Math.max(1, page.value - 2)
  const end = Math.min(count, start + 4)
  start = Math.max(1, end - 4)

  return Array.from({ length: end - start + 1 }, (_, index) => start + index)
})

function readQueryValue(value: unknown): string {
  if (Array.isArray(value)) {
    const first = value[0]
    return typeof first === 'string' ? first : ''
  }
  return typeof value === 'string' ? value : ''
}

function readMasteryStatus(value: string): MasteryStatus | '' {
  if (value === 'unmastered' || value === 'reviewing' || value === 'mastered') return value
  return ''
}

const masteryFilter = computed<string>({
  get: () => masteryStatus.value,
  set: (value) => {
    masteryStatus.value = readMasteryStatus(value)
  },
})

function syncFromRoute(): void {
  keyword.value = readQueryValue(route.query.q)
  subject.value = readQueryValue(route.query.subject)
  tag.value = readQueryValue(route.query.tag)
  masteryStatus.value = readMasteryStatus(readQueryValue(route.query.mastery_status))

  const rawPage = Number.parseInt(readQueryValue(route.query.page), 10)
  page.value = Number.isFinite(rawPage) && rawPage > 1 ? rawPage : 1
}

function buildQuery(): Record<string, string> {
  const query: Record<string, string> = {}
  const trimmedKeyword = keyword.value.trim()
  const trimmedTag = tag.value.trim()

  if (trimmedKeyword) query.q = trimmedKeyword
  if (subject.value) query.subject = subject.value
  if (trimmedTag) query.tag = trimmedTag
  if (masteryStatus.value) query.mastery_status = masteryStatus.value
  if (page.value > 1) query.page = String(page.value)

  return query
}

function queryKey(query: Record<string, string>): string {
  return JSON.stringify(
    Object.entries(query)
      .filter(([, value]) => value.length > 0)
      .sort(([left], [right]) => left.localeCompare(right)),
  )
}

function routeQueryKey(): string {
  const entries: [string, string][] = []

  for (const [key, value] of Object.entries(route.query)) {
    const first = Array.isArray(value) ? value[0] : value
    if (typeof first === 'string' && first.length > 0) entries.push([key, first])
  }

  entries.sort(([left], [right]) => left.localeCompare(right))
  return JSON.stringify(entries)
}

function cancelSearchTimer(): void {
  if (searchTimer) {
    clearTimeout(searchTimer)
    searchTimer = null
  }
}

async function fetchQuestions(): Promise<void> {
  const token = ++requestToken
  loading.value = true
  errorMessage.value = ''
  errorCode.value = ''

  try {
    const result = await listQuestions({
      page: page.value,
      page_size: PAGE_SIZE,
      q: keyword.value.trim() || undefined,
      subject: subject.value || undefined,
      tag: tag.value.trim() || undefined,
      mastery_status: masteryStatus.value || undefined,
      sort: 'created_at_desc',
    })

    if (token !== requestToken) return

    items.value = result.items
    total.value = result.total
  } catch (cause) {
    if (token !== requestToken) return

    const apiError = normalizeApiError(cause)
    errorMessage.value = apiError.message
    errorCode.value = apiError.code
    items.value = []
    total.value = 0
  } finally {
    if (token === requestToken) loading.value = false
  }
}

async function commitFilters(resetPage: boolean): Promise<void> {
  if (resetPage && page.value !== 1) page.value = 1

  const nextQuery = buildQuery()
  const nextKey = queryKey(nextQuery)

  if (nextKey === routeQueryKey() || nextKey === pendingQueryKey) return

  pendingQueryKey = nextKey
  try {
    await router.replace({ query: nextQuery })
  } finally {
    pendingQueryKey = null
  }
}

function scheduleSearch(): void {
  cancelSearchTimer()
  searchTimer = setTimeout(() => {
    searchTimer = null
    void commitFilters(true)
  }, 300)
}

function clearFilters(): void {
  cancelSearchTimer()
  keyword.value = ''
  subject.value = ''
  tag.value = ''
  masteryStatus.value = ''
  page.value = 1
  void commitFilters(true)
}

function goCreate(): void {
  void router.push('/questions/new')
}

function handlePageChange(current: number): void {
  page.value = current
}

function pageAriaLabel(value: number): string {
  return value === page.value ? `第 ${value} 页，当前页` : `第 ${value} 页`
}

watch([keyword, tag], () => {
  scheduleSearch()
})

watch([subject, masteryStatus], () => {
  cancelSearchTimer()
  void commitFilters(true)
})

watch(page, () => {
  void commitFilters(false)
})

watch(
  () => route.query,
  () => {
    syncFromRoute()
    void fetchQuestions()
  },
)

onMounted(() => {
  syncFromRoute()
  void fetchQuestions()
})

onBeforeUnmount(() => {
  cancelSearchTimer()
  requestToken += 1
})
</script>

<template>
  <div class="page">
    <PageHeader
      eyebrow="Question book"
      title="错题本"
      description="按学科、标签或掌握状态找到错题；点击卡片查看分析、答案与相似题。"
    >
      <template #actions>
        <button class="btn btn--primary" type="button" @click="goCreate">
          <svg
            class="icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
            aria-hidden="true"
          >
            <path d="M12 5v14M5 12h14" />
          </svg>
          录入错题
        </button>
      </template>
    </PageHeader>

    <details class="filter-panel" open>
      <summary class="filter-panel__summary">
        <svg
          class="icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.6"
          stroke-linecap="round"
          aria-hidden="true"
        >
          <path d="M4 7h16M7 12h10M10 17h4" />
        </svg>
        筛选与搜索
        <span class="filter-panel__state">{{ total }} 条结果</span>
        <svg
          class="chev"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </summary>

      <div class="filter-panel__body" role="search" aria-label="筛选错题">
        <div class="search">
          <label class="sr-only" for="question-search">搜索题干或标签</label>
          <svg
            class="icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.7"
            stroke-linecap="round"
            aria-hidden="true"
          >
            <circle cx="11" cy="11" r="7" />
            <path d="m16.5 16.5 4.5 4.5" />
          </svg>
          <input
            id="question-search"
            v-model="keyword"
            class="input"
            type="search"
            placeholder="搜索题干或标签"
            autocomplete="off"
          />
        </div>

        <div class="select-wrap">
          <label class="sr-only" for="subject-filter">按学科筛选</label>
          <select id="subject-filter" v-model="subject" class="select">
            <option value="">全部学科</option>
            <option v-for="option in SUBJECT_OPTIONS" :key="option" :value="option">
              {{ option }}
            </option>
          </select>
          <svg
            class="icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <path d="m6 9 6 6 6-6" />
          </svg>
        </div>

        <div>
          <label class="sr-only" for="tag-filter">按标签筛选</label>
          <input
            id="tag-filter"
            v-model="tag"
            class="input"
            type="text"
            placeholder="按标签筛选"
            autocomplete="off"
          />
        </div>

        <div class="select-wrap">
          <label class="sr-only" for="mastery-filter">按掌握状态筛选</label>
          <select id="mastery-filter" v-model="masteryFilter" class="select">
            <option value="">全部掌握状态</option>
            <option v-for="option in MASTERY_OPTIONS" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
          <svg
            class="icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <path d="m6 9 6 6 6-6" />
          </svg>
        </div>

        <button class="btn btn--quiet" type="button" @click="clearFilters">清空筛选</button>
      </div>
    </details>

    <div class="list-head">
      <h2>
        全部错题 <span>{{ total }}</span>
      </h2>
      <p>按最近录入排序</p>
    </div>

    <LoadingSkeleton v-if="loading" variant="list" :rows="3" label="正在加载错题列表" />

    <ErrorState
      v-else-if="errorMessage"
      title="错题列表加载失败"
      :message="errorMessage"
      :code="errorCode"
      @retry="fetchQuestions"
    />

    <template v-else-if="items.length === 0">
      <EmptyState
        v-if="hasActiveFilters"
        title="没有匹配的错题"
        description="换一个关键词，或清空筛选条件后再试。"
        action-label="清空筛选"
        @action="clearFilters"
      />
      <EmptyState
        v-else
        title="还没有错题"
        description="录入第一道错题后，AI 会分析考点并生成 3 道相似题。"
        action-label="录入错题"
        @action="goCreate"
      />
    </template>

    <template v-else>
      <div class="question-list">
        <QuestionCard v-for="question in items" :key="question.id" :question="question" />
      </div>

      <nav class="pagination" aria-label="错题分页">
        <p>共 {{ total }} 条 · 第 {{ page }} / {{ pageCount }} 页</p>
        <div class="pagination__controls">
          <button
            class="page-btn"
            type="button"
            :disabled="page <= 1"
            aria-label="上一页"
            @click="handlePageChange(page - 1)"
          >
            <svg
              class="icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <path d="m15 6-6 6 6 6" />
            </svg>
          </button>

          <button
            v-for="pageNumber in pageNumbers"
            :key="pageNumber"
            class="page-btn"
            type="button"
            :aria-current="pageNumber === page ? 'page' : undefined"
            :aria-label="pageAriaLabel(pageNumber)"
            @click="handlePageChange(pageNumber)"
          >
            {{ pageNumber }}
          </button>

          <button
            class="page-btn"
            type="button"
            :disabled="page >= pageCount"
            aria-label="下一页"
            @click="handlePageChange(page + 1)"
          >
            <svg
              class="icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <path d="m9 6 6 6-6 6" />
            </svg>
          </button>
        </div>
      </nav>
    </template>
  </div>
</template>

<style scoped>
.page {
  display: block;
}

.filter-panel {
  margin-bottom: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.filter-panel__summary {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 46px;
  padding: 0 var(--space-4);
  border-radius: var(--radius-lg);
  color: var(--color-text-1);
  font-size: 15px;
  line-height: 22px;
  font-weight: 600;
  cursor: pointer;
  list-style: none;
}

.filter-panel__summary::-webkit-details-marker {
  display: none;
}

.filter-panel__summary > .icon {
  width: 17px;
  height: 17px;
  flex: none;
  color: var(--color-text-3);
}

.filter-panel__summary .chev {
  width: 16px;
  height: 16px;
  margin-left: 2px;
  color: var(--color-text-3);
  transition: transform 0.15s ease;
}

.filter-panel[open] .filter-panel__summary {
  border-bottom: 1px solid var(--color-border);
}

.filter-panel[open] .filter-panel__summary .chev {
  transform: rotate(180deg);
}

.filter-panel__state {
  margin-left: auto;
  color: var(--color-text-3);
  font-size: var(--text-sm);
  font-weight: 400;
}

.filter-panel__body {
  display: grid;
  grid-template-columns:
    minmax(190px, 1.7fr) minmax(140px, 1fr) minmax(130px, 1fr) minmax(150px, 1fr)
    auto;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4) var(--space-4);
}

.filter-panel__body .btn {
  min-height: var(--control-height);
}

.list-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-3);
  margin: var(--space-5) 2px var(--space-3);
}

.list-head h2 {
  font-size: var(--text-base);
  line-height: 24px;
  font-weight: 650;
}

.list-head h2 span {
  margin-left: 6px;
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  font-weight: 400;
}

.list-head p {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.question-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-top: var(--space-4);
  padding-top: var(--space-2);
}

.pagination > p {
  color: var(--color-text-3);
  font-size: var(--text-sm);
  line-height: var(--text-sm-leading);
}

.pagination__controls {
  display: flex;
  align-items: center;
  gap: 6px;
}

.page-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 36px;
  height: 36px;
  padding: 0 8px;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text-2);
  font-size: var(--text-sm);
  line-height: 1;
  transition:
    border-color 0.15s ease,
    background-color 0.15s ease,
    color 0.15s ease;
}

.page-btn:hover:not(:disabled) {
  border-color: var(--color-text-3);
  color: var(--color-text-1);
}

.page-btn[aria-current='page'] {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  color: var(--color-primary-active);
  font-weight: 650;
}

.page-btn:disabled {
  border-color: var(--color-border);
  background: var(--color-surface-subtle);
  color: var(--color-text-3);
  cursor: not-allowed;
}

.page-btn .icon {
  width: 16px;
  height: 16px;
}

@media (max-width: 1023px) {
  .filter-panel__body {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .filter-panel__body .search {
    grid-column: 1 / -1;
  }

  .filter-panel__body .btn {
    justify-self: start;
  }
}

@media (max-width: 767px) {
  .filter-panel__summary {
    min-height: 48px;
    padding: 0 var(--space-3);
  }

  .filter-panel__body {
    grid-template-columns: minmax(0, 1fr);
    padding: 10px var(--space-3) var(--space-3);
  }

  .filter-panel__body .search {
    grid-column: auto;
  }

  .filter-panel__body .btn {
    width: 100%;
  }

  .list-head {
    margin-top: var(--space-4);
  }

  .pagination {
    align-items: flex-start;
    flex-direction: column;
  }

  .pagination__controls {
    align-self: flex-end;
  }
}
</style>
