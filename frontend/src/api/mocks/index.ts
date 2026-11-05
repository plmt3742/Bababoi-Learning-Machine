import MockAdapter from 'axios-mock-adapter'
import type { AxiosRequestConfig } from 'axios'
import apiClient from '../client'
import type {
  Analysis,
  AuthResponse,
  Draft,
  DraftSavePayload,
  LoginPayload,
  MasteryStatus,
  PracticeRecord,
  PracticeRecordCreate,
  Question,
  QuestionCreate,
  QuestionDetail,
  QuestionListItem,
  QuestionTag,
  QuestionType,
  RegisterPayload,
  Task,
  TaskStatus,
  User,
} from '../types'
import { createMockState, makeExcerpt } from './data'
import type { MockState, MockUser } from './data'

const LATENCY_MS = 320
const QUESTION_TYPES: QuestionType[] = ['choice', 'blank', 'solve']
const TASK_STATUSES: TaskStatus[] = ['queued', 'running', 'done', 'failed']

const genericAnalysis: Analysis = {
  topic_type: '待整理',
  difficulty: 'medium',
  knowledge_points: ['基础概念'],
  error_reasons: ['等待 AI 分析真实错误原因'],
  solution_summary: '此处为 Mock 数据；接入真实后端后会返回结构化分析。',
}

let adapter: MockAdapter | null = null

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function nowIso(): string {
  return new Date().toISOString()
}

function mockRequestId(): string {
  return `req_mock_${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`
}

function apiError(status: number, code: string, message: string): [number, unknown] {
  return [status, { detail: { code, message, request_id: mockRequestId() } }]
}

function unauthorized(): [number, unknown] {
  return apiError(401, 'AUTH_TOKEN_EXPIRED', '登录已过期，请重新登录')
}

function readBody<T>(config: AxiosRequestConfig): T | null {
  if (typeof config.data === 'string') {
    try {
      const parsed: unknown = JSON.parse(config.data)
      return isRecord(parsed) ? (parsed as T) : null
    } catch {
      return null
    }
  }

  if (isRecord(config.data)) return config.data as T
  return null
}

function readQuery(config: AxiosRequestConfig, key: string): string | null {
  const params: unknown = config.params
  if (!isRecord(params)) return null

  const value = params[key]
  if (typeof value === 'string' && value.length > 0) return value
  if (typeof value === 'number') return String(value)
  return null
}

function readPositiveInt(config: AxiosRequestConfig, key: string, fallback: number): number {
  const raw = readQuery(config, key)
  if (raw === null) return fallback

  const value = Number.parseInt(raw, 10)
  return Number.isFinite(value) && value > 0 ? value : fallback
}

function issueToken(user: MockUser): string {
  return `mock-token-${user.id}-${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`
}

function toPublicUser(user: MockUser): User {
  return {
    id: user.id,
    username: user.username,
    email: user.email,
    created_at: user.created_at,
  }
}

function authResponse(user: MockUser): AuthResponse {
  return {
    access_token: issueToken(user),
    token_type: 'bearer',
    user: toPublicUser(user),
  }
}

function authorizedUser(config: AxiosRequestConfig, state: MockState): MockUser | null {
  const headers: unknown = config.headers
  if (!isRecord(headers)) return null

  const getHeader = headers.get
  const raw: unknown =
    typeof getHeader === 'function'
      ? getHeader.call(headers, 'Authorization')
      : (headers.Authorization ?? headers.authorization)

  const header = Array.isArray(raw) ? raw[0] : raw
  if (typeof header !== 'string' || !header.startsWith('Bearer ')) return null

  const match = /^mock-token-(\d+)-[a-z0-9]+$/i.exec(header.slice('Bearer '.length))
  if (!match) return null

  const userId = Number.parseInt(match[1], 10)
  return state.users.find((user) => user.id === userId) ?? null
}

function ensureTags(state: MockState, names: string[]): QuestionTag[] {
  const result: QuestionTag[] = []

  for (const rawName of names) {
    const name = rawName.trim()
    if (!name) continue

    let tag = state.tags.find((item) => item.name === name)
    if (!tag) {
      tag = { id: state.nextTagId, name, type: 'knowledge_point' }
      state.nextTagId += 1
      state.tags.push(tag)
    }

    if (!result.some((item) => item.id === tag.id)) result.push(tag)
  }

  return result
}

function toListItem(question: Question): QuestionListItem {
  return {
    id: question.id,
    subject: question.subject,
    chapter: question.chapter,
    question_type: question.question_type,
    excerpt: makeExcerpt(question.content_md),
    mastery_status: question.mastery_status,
    tags: question.tags,
    created_at: question.created_at,
  }
}

function buildDetail(
  question: Question,
  state: MockState,
  includeGenerated: boolean,
): QuestionDetail {
  return {
    ...question,
    tasks: state.tasks.filter((task) => task.question_id === question.id),
    generated_questions: includeGenerated
      ? state.generatedQuestions.filter((item) => item.parent_question_id === question.id)
      : [],
  }
}

function isQuestionType(value: unknown): value is QuestionType {
  return typeof value === 'string' && QUESTION_TYPES.some((type) => type === value)
}

function isMasteryStatus(value: unknown): value is MasteryStatus {
  return value === 'unmastered' || value === 'reviewing' || value === 'mastered'
}

function isTaskStatus(value: unknown): value is TaskStatus {
  return typeof value === 'string' && TASK_STATUSES.some((status) => status === value)
}

function toAnalysis(value: unknown): Analysis | null {
  if (
    !isRecord(value) ||
    typeof value.topic_type !== 'string' ||
    typeof value.difficulty !== 'string' ||
    !Array.isArray(value.knowledge_points) ||
    !Array.isArray(value.error_reasons) ||
    typeof value.solution_summary !== 'string'
  ) {
    return null
  }

  const difficulty = value.difficulty
  if (difficulty !== 'easy' && difficulty !== 'medium' && difficulty !== 'hard') return null

  return {
    topic_type: value.topic_type,
    difficulty,
    knowledge_points: value.knowledge_points.filter(
      (item): item is string => typeof item === 'string',
    ),
    error_reasons: value.error_reasons.filter((item): item is string => typeof item === 'string'),
    solution_summary: value.solution_summary,
  }
}

function scheduleTaskProgress(task: Task, question?: Question): void {
  setTimeout(() => {
    if (task.status === 'queued') {
      task.status = 'running'
      task.started_at = nowIso()
    }
  }, 900)

  setTimeout(() => {
    if (task.status !== 'running') return

    task.status = 'done'
    task.finished_at = nowIso()

    if (question && task.stage === 'analysis' && !question.analysis) {
      question.analysis = genericAnalysis
      question.updated_at = nowIso()
    }
  }, 2400)
}

function findQuestion(state: MockState, id: number): Question | undefined {
  return state.questions.find((question) => question.id === id)
}

export function setupMocks(): void {
  if (adapter) return

  const state = createMockState()
  adapter = new MockAdapter(apiClient, { delayResponse: LATENCY_MS })

  adapter.onPost('/auth/register').reply((config) => {
    const body = readBody<RegisterPayload>(config)
    if (!body || typeof body.username !== 'string' || typeof body.password !== 'string') {
      return apiError(400, 'VALIDATION_ERROR', '请填写用户名和密码')
    }

    const username = body.username.trim()
    if (username.length < 3 || username.length > 32) {
      return apiError(400, 'VALIDATION_ERROR', '用户名需为 3–32 个字符')
    }
    if (!/^[A-Za-z0-9_\u4e00-\u9fff]+$/.test(username)) {
      return apiError(400, 'VALIDATION_ERROR', '用户名只能包含字母、数字、下划线、中文')
    }
    if (body.password.length < 8) {
      return apiError(400, 'VALIDATION_ERROR', '密码至少 8 位')
    }
    if (state.users.some((user) => user.username === username)) {
      return apiError(409, 'USERNAME_TAKEN', '用户名已被使用')
    }

    const user: MockUser = {
      id: state.nextUserId,
      username,
      password: body.password,
      email: body.email?.trim() || null,
      created_at: nowIso(),
    }
    state.nextUserId += 1
    state.users.push(user)

    return [200, authResponse(user)]
  })

  adapter.onPost('/auth/login').reply((config) => {
    const body = readBody<LoginPayload>(config)
    if (!body || typeof body.username !== 'string' || typeof body.password !== 'string') {
      return apiError(400, 'VALIDATION_ERROR', '请填写用户名和密码')
    }

    const user = state.users.find(
      (item) => item.username === body.username.trim() && item.password === body.password,
    )
    if (!user) {
      return apiError(401, 'AUTH_INVALID_CREDENTIALS', '用户名或密码错误')
    }

    return [200, authResponse(user)]
  })

  adapter.onGet('/auth/me').reply((config) => {
    const user = authorizedUser(config, state)
    if (!user) return unauthorized()

    return [200, toPublicUser(user)]
  })

  adapter.onGet('/questions').reply((config) => {
    if (!authorizedUser(config, state)) return unauthorized()

    const page = readPositiveInt(config, 'page', 1)
    const pageSize = Math.min(readPositiveInt(config, 'page_size', 20), 100)
    const subject = readQuery(config, 'subject')
    const tag = readQuery(config, 'tag')
    const masteryStatus = readQuery(config, 'mastery_status')
    const search = readQuery(config, 'q')?.toLowerCase() ?? null

    const filtered = state.questions.filter((question) => {
      if (subject && question.subject !== subject) return false
      if (tag && !question.tags.some((item) => item.name === tag)) return false
      if (masteryStatus && question.mastery_status !== masteryStatus) return false
      if (search) {
        const searchable = [
          question.content_md,
          question.answer_md ?? '',
          question.explanation_md ?? '',
          ...question.tags.map((item) => item.name),
        ]
          .join(' ')
          .toLowerCase()
        if (!searchable.includes(search)) return false
      }
      return true
    })

    const sorted = [...filtered].sort((a, b) => b.created_at.localeCompare(a.created_at))
    const start = (page - 1) * pageSize

    return [
      200,
      {
        items: sorted.slice(start, start + pageSize).map(toListItem),
        total: sorted.length,
        page,
        page_size: pageSize,
      },
    ]
  })

  adapter.onPost('/questions').reply((config) => {
    if (!authorizedUser(config, state)) return unauthorized()

    const body = readBody<QuestionCreate>(config)
    if (
      !body ||
      typeof body.subject !== 'string' ||
      !body.subject.trim() ||
      typeof body.content_md !== 'string' ||
      !body.content_md.trim() ||
      !isQuestionType(body.question_type)
    ) {
      return apiError(400, 'VALIDATION_ERROR', '学科、题干和题型不能为空')
    }

    const timestamp = nowIso()
    const question: Question = {
      id: state.nextQuestionId,
      subject: body.subject.trim(),
      chapter: body.chapter?.trim() || null,
      source_type: body.source_type === 'image' ? 'image' : 'text',
      content_md: body.content_md,
      answer_md: body.answer_md ?? null,
      explanation_md: body.explanation_md ?? null,
      question_type: body.question_type,
      options: body.options ?? null,
      blanks: body.blanks ?? null,
      analysis: null,
      mastery_status: 'unmastered',
      tags: ensureTags(state, body.tags ?? []),
      image_path: body.image_path ?? null,
      crop_box: null,
      created_at: timestamp,
      updated_at: timestamp,
    }
    state.nextQuestionId += 1
    state.questions.push(question)

    const task: Task = {
      id: state.nextTaskId,
      question_id: question.id,
      stage: 'analysis',
      status: 'queued',
      target_index: null,
      retry_index: 0,
      error_code: null,
      created_at: timestamp,
      started_at: null,
      finished_at: null,
    }
    state.nextTaskId += 1
    state.tasks.push(task)
    scheduleTaskProgress(task, question)

    return [201, { question, task_id: task.id }]
  })

  adapter.onGet(/^\/questions\/\d+$/).reply((config) => {
    if (!authorizedUser(config, state)) return unauthorized()

    const match = /^\/questions\/(\d+)$/.exec(config.url ?? '')
    const question = match ? findQuestion(state, Number.parseInt(match[1], 10)) : undefined
    if (!question) return apiError(404, 'QUESTION_NOT_FOUND', '错题不存在或已删除')

    const includeGenerated = readQuery(config, 'include') === 'generated'
    return [200, buildDetail(question, state, includeGenerated)]
  })

  adapter.onPatch(/^\/questions\/\d+$/).reply((config) => {
    if (!authorizedUser(config, state)) return unauthorized()

    const match = /^\/questions\/(\d+)$/.exec(config.url ?? '')
    const question = match ? findQuestion(state, Number.parseInt(match[1], 10)) : undefined
    if (!question) return apiError(404, 'QUESTION_NOT_FOUND', '错题不存在或已删除')

    const body = readBody<Record<string, unknown>>(config)
    if (!body) return apiError(400, 'VALIDATION_ERROR', '请求体格式不正确')

    if (typeof body.subject === 'string' && body.subject.trim())
      question.subject = body.subject.trim()
    if (typeof body.chapter === 'string') question.chapter = body.chapter.trim() || null
    if (body.chapter === null) question.chapter = null
    if (typeof body.content_md === 'string' && body.content_md.trim()) {
      question.content_md = body.content_md
    }
    if (typeof body.answer_md === 'string') question.answer_md = body.answer_md
    if (body.answer_md === null) question.answer_md = null
    if (typeof body.explanation_md === 'string') question.explanation_md = body.explanation_md
    if (body.explanation_md === null) question.explanation_md = null

    if (isMasteryStatus(body.mastery_status)) question.mastery_status = body.mastery_status

    if (Array.isArray(body.tags)) {
      question.tags = ensureTags(
        state,
        body.tags.filter((tag): tag is string => typeof tag === 'string'),
      )
    }

    if (body.analysis === null) {
      question.analysis = null
    } else if (body.analysis !== undefined) {
      const analysis = toAnalysis(body.analysis)
      if (!analysis) return apiError(400, 'VALIDATION_ERROR', '分析结果格式不正确')
      question.analysis = analysis
    }

    question.updated_at = nowIso()
    return [200, question]
  })

  adapter.onDelete(/^\/questions\/\d+$/).reply((config) => {
    if (!authorizedUser(config, state)) return unauthorized()

    const match = /^\/questions\/(\d+)$/.exec(config.url ?? '')
    const questionId = match ? Number.parseInt(match[1], 10) : null
    if (questionId === null) return apiError(404, 'QUESTION_NOT_FOUND', '错题不存在或已删除')

    const index = state.questions.findIndex((question) => question.id === questionId)
    if (index === -1) return apiError(404, 'QUESTION_NOT_FOUND', '错题不存在或已删除')

    state.questions.splice(index, 1)
    state.generatedQuestions = state.generatedQuestions.filter(
      (item) => item.parent_question_id !== questionId,
    )
    state.tasks = state.tasks.filter((task) => task.question_id !== questionId)

    return [204, null]
  })

  adapter.onPost(/^\/questions\/\d+\/generate$/).reply((config) => {
    if (!authorizedUser(config, state)) return unauthorized()

    const match = /^\/questions\/(\d+)\/generate$/.exec(config.url ?? '')
    const question = match ? findQuestion(state, Number.parseInt(match[1], 10)) : undefined
    if (!question) return apiError(404, 'QUESTION_NOT_FOUND', '错题不存在或已删除')

    const timestamp = nowIso()
    const task: Task = {
      id: state.nextTaskId,
      question_id: question.id,
      stage: 'quiz',
      status: 'queued',
      target_index: null,
      retry_index: 0,
      error_code: null,
      created_at: timestamp,
      started_at: null,
      finished_at: null,
    }
    state.nextTaskId += 1
    state.tasks.push(task)
    scheduleTaskProgress(task, question)

    return [200, { task_id: task.id }]
  })

  adapter.onGet('/tasks').reply((config) => {
    if (!authorizedUser(config, state)) return unauthorized()

    const questionId = readQuery(config, 'question_id')
    const status = readQuery(config, 'status')

    const items = state.tasks
      .filter((task) => {
        if (questionId !== null && task.question_id !== Number.parseInt(questionId, 10))
          return false
        if (status !== null && isTaskStatus(status) && task.status !== status) return false
        return true
      })
      .sort((a, b) => b.created_at.localeCompare(a.created_at))

    return [200, { items }]
  })

  adapter.onPost(/^\/tasks\/\d+\/retry$/).reply((config) => {
    if (!authorizedUser(config, state)) return unauthorized()

    const match = /^\/tasks\/(\d+)\/retry$/.exec(config.url ?? '')
    const task = match
      ? state.tasks.find((item) => item.id === Number.parseInt(match[1], 10))
      : undefined
    if (!task) return apiError(404, 'TASK_NOT_FOUND', '任务不存在')

    task.status = 'queued'
    task.retry_index += 1
    task.error_code = null
    task.started_at = null
    task.finished_at = null
    scheduleTaskProgress(task, findQuestion(state, task.question_id))

    return [200, task]
  })

  adapter.onGet('/drafts/me').reply((config) => {
    const user = authorizedUser(config, state)
    if (!user) return unauthorized()

    const draft = state.drafts.get(user.id)
    return draft ? [200, draft] : [204, null]
  })

  adapter.onPut('/drafts/me').reply((config) => {
    const user = authorizedUser(config, state)
    if (!user) return unauthorized()

    const body = readBody<DraftSavePayload>(config)
    if (!body || !isRecord(body.content)) {
      return apiError(400, 'VALIDATION_ERROR', '草稿内容格式不正确')
    }

    const existing = state.drafts.get(user.id)
    const baseVersion = typeof body.base_version === 'number' ? body.base_version : null
    if (existing && existing.version !== baseVersion) {
      return apiError(409, 'DRAFT_VERSION_CONFLICT', '草稿已在其他位置更新，请刷新后重试')
    }

    const draft: Draft = {
      content: body.content,
      version: existing ? existing.version + 1 : 1,
      updated_at: nowIso(),
    }
    state.drafts.set(user.id, draft)

    return [200, draft]
  })

  adapter.onDelete('/drafts/me').reply((config) => {
    const user = authorizedUser(config, state)
    if (!user) return unauthorized()

    state.drafts.delete(user.id)
    return [204, null]
  })

  adapter.onPost('/practice-records').reply((config) => {
    if (!authorizedUser(config, state)) return unauthorized()

    const body = readBody<PracticeRecordCreate>(config)
    if (
      !body ||
      typeof body.generated_question_id !== 'number' ||
      typeof body.is_correct !== 'boolean' ||
      typeof body.duration_seconds !== 'number' ||
      body.duration_seconds < 0 ||
      body.duration_seconds > 3600
    ) {
      return apiError(400, 'VALIDATION_ERROR', '练习记录参数不正确')
    }

    const record: PracticeRecord = {
      id: state.nextPracticeId,
      generated_question_id: body.generated_question_id,
      user_answer: body.user_answer ?? null,
      is_correct: body.is_correct,
      duration_seconds: body.duration_seconds,
      created_at: nowIso(),
    }
    state.nextPracticeId += 1
    state.practiceRecords.push(record)

    return [201, record]
  })

  adapter.onGet('/practice-records').reply((config) => {
    if (!authorizedUser(config, state)) return unauthorized()

    const page = readPositiveInt(config, 'page', 1)
    const pageSize = Math.min(readPositiveInt(config, 'page_size', 20), 100)
    const generatedQuestionId = readQuery(config, 'generated_question_id')

    const filtered = state.practiceRecords.filter((record) => {
      if (generatedQuestionId === null) return true
      return record.generated_question_id === Number.parseInt(generatedQuestionId, 10)
    })
    const sorted = [...filtered].sort((a, b) => b.created_at.localeCompare(a.created_at))
    const start = (page - 1) * pageSize

    return [
      200,
      {
        items: sorted.slice(start, start + pageSize),
        total: sorted.length,
        page,
        page_size: pageSize,
      },
    ]
  })
}
