<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { IconPlus, IconSearch } from '@arco-design/web-vue/es/icon'
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
      eyebrow="QLIST-01"
      title="错题本"
      description="按学科、标签或掌握状态找到错题；点击卡片查看分析、答案与相似题。"
    >
      <template #actions>
        <a-button type="primary" @click="goCreate">
          <template #icon>
            <IconPlus />
          </template>
          录入错题
        </a-button>
      </template>
    </PageHeader>

    <a-card class="filters" :bordered="false">
      <div class="filters__grid">
        <a-input
          v-model="keyword"
          class="filters__search"
          placeholder="搜索题干或标签"
          :input-attrs="{ 'aria-label': '搜索题干或标签' }"
          allow-clear
        >
          <template #prefix>
            <IconSearch />
          </template>
        </a-input>

        <a-select
          v-model="subject"
          placeholder="全部学科"
          aria-label="按学科筛选"
          :options="SUBJECT_OPTIONS"
          allow-clear
        />

        <a-input
          v-model="tag"
          placeholder="按标签筛选"
          :input-attrs="{ 'aria-label': '按标签筛选' }"
          allow-clear
        />

        <a-select
          v-model="masteryStatus"
          placeholder="全部掌握状态"
          aria-label="按掌握状态筛选"
          :options="MASTERY_OPTIONS"
          allow-clear
        />

        <a-button v-if="hasActiveFilters" type="text" @click="clearFilters">清空筛选</a-button>
      </div>
    </a-card>

    <LoadingSkeleton v-if="loading" variant="list" :rows="3" label="正在加载错题列表" />

    <ErrorState
      v-else-if="errorMessage"
      title="错题列表加载失败"
      :message="errorMessage"
      :code="errorCode"
      @retry="fetchQuestions"
    />

    <template v-else-if="items.length === 0">
      <div class="list-state">
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
      </div>
    </template>

    <template v-else>
      <div class="question-list">
        <QuestionCard v-for="question in items" :key="question.id" :question="question" />
      </div>

      <div class="list-footer">
        <p class="list-footer__total">共 {{ total }} 条</p>
        <a-pagination
          :current="page"
          :total="total"
          :page-size="PAGE_SIZE"
          :show-total="false"
          :show-page-size="false"
          :show-jumper="total > 100"
          :hide-on-single-page="false"
          @change="handlePageChange"
        />
      </div>
    </template>
  </div>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.filters {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.filters :deep(.arco-card-body) {
  padding: var(--space-4) var(--space-5);
}

.filters__grid {
  display: grid;
  grid-template-columns: minmax(0, 2fr) repeat(3, minmax(0, 1fr)) auto;
  gap: var(--space-3);
  align-items: center;
}

.filters__search :deep(.arco-input-prefix) {
  color: var(--color-text-3);
}

.list-state {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.question-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.list-footer {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding-top: var(--space-1);
}

.list-footer__total {
  color: var(--color-text-3);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: var(--text-xs-leading);
  font-variant-numeric: tabular-nums;
}

@media (max-width: 1023px) {
  .filters__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .filters__search {
    grid-column: 1 / -1;
  }
}

@media (max-width: 767px) {
  .filters :deep(.arco-card-body) {
    padding: var(--space-4);
  }

  .filters__grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .filters__search {
    grid-column: auto;
  }

  .list-footer {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
