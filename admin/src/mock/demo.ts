/*
 * Local-only demo adapter.
 *
 * Enabled only when VITE_ADMIN_DEMO=true. It keeps the real API client and
 * stores untouched; requests are intercepted in api/client.ts before fetch().
 * The production path still requires /api/v1/admin/* from the backend.
 */
import type {
  AdminOverview,
  AdminProfile,
  AdminQuestion,
  AdminQuestionDetail,
  AdminSystem,
  AdminTask,
  AdminTaskDetail,
  AdminUser,
  AdminUserDetail,
  AiLog,
  AiLogRawResult,
  AlertItem,
  AuditLog,
  PasswordApproveResult,
  PasswordRequest,
  TaskTimelineItem,
} from '../types'
import type { QueryValue, RequestOptions } from '../api/client'

interface DemoPage<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

const NOW = '11-28 01:20'
const ADMIN: AdminProfile = {
  id: 9001,
  username: 'admin',
  email: 'admin@demo.local',
  role: 'admin',
  must_change_password: false,
}

const users: AdminUser[] = [
  {
    id: 1,
    username: 'student01',
    email: 'student01@example.com',
    status: 'active',
    role: 'student',
    questions: 12,
    generated: 34,
    practice: 41,
    lastLogin: '11-27 21:14',
    createdAt: '10-20 16:00',
    hasPersonalKey: false,
    provider: null,
    model: null,
    keyLast4: null,
    pendingPasswordRequests: 0,
    disabledAt: null,
    disabledReason: null,
  },
  {
    id: 2,
    username: 'student02',
    email: 'student02@example.com',
    status: 'active',
    role: 'student',
    questions: 8,
    generated: 22,
    practice: 28,
    lastLogin: '11-27 20:42',
    createdAt: '10-21 09:12',
    hasPersonalKey: true,
    provider: 'DeepSeek',
    model: 'deepseek-flash',
    keyLast4: '9f3a',
    pendingPasswordRequests: 0,
    disabledAt: null,
    disabledReason: null,
  },
  {
    id: 3,
    username: 'student03',
    email: 'student03@example.com',
    status: 'active',
    role: 'student',
    questions: 5,
    generated: 14,
    practice: 19,
    lastLogin: '11-27 19:30',
    createdAt: '10-22 14:08',
    hasPersonalKey: false,
    provider: null,
    model: null,
    keyLast4: null,
    pendingPasswordRequests: 1,
    disabledAt: null,
    disabledReason: null,
  },
  {
    id: 4,
    username: 'student04',
    email: 'student04@example.com',
    status: 'active',
    role: 'student',
    questions: 15,
    generated: 41,
    practice: 56,
    lastLogin: '11-27 18:02',
    createdAt: '10-23 10:26',
    hasPersonalKey: false,
    provider: null,
    model: null,
    keyLast4: null,
    pendingPasswordRequests: 0,
    disabledAt: null,
    disabledReason: null,
  },
  {
    id: 5,
    username: 'student05',
    email: 'student05@example.com',
    status: 'active',
    role: 'student',
    questions: 3,
    generated: 8,
    practice: 11,
    lastLogin: '11-26 22:18',
    createdAt: '10-24 20:31',
    hasPersonalKey: false,
    provider: null,
    model: null,
    keyLast4: null,
    pendingPasswordRequests: 0,
    disabledAt: null,
    disabledReason: null,
  },
  {
    id: 6,
    username: 'student06',
    email: 'student06@example.com',
    status: 'disabled',
    role: 'student',
    questions: 11,
    generated: 30,
    practice: 38,
    lastLogin: '11-25 16:44',
    createdAt: '10-25 11:05',
    hasPersonalKey: false,
    provider: null,
    model: null,
    keyLast4: null,
    pendingPasswordRequests: 0,
    disabledAt: '11-27 22:12',
    disabledReason: '账号异常登录，临时禁用',
  },
  {
    id: 7,
    username: 'student07',
    email: 'student07@example.com',
    status: 'active',
    role: 'student',
    questions: 7,
    generated: 19,
    practice: 26,
    lastLogin: '11-27 17:26',
    createdAt: '10-26 08:56',
    hasPersonalKey: true,
    provider: 'OpenAI 兼容',
    model: 'gpt-4o-mini',
    keyLast4: 'b71c',
    pendingPasswordRequests: 1,
    disabledAt: null,
    disabledReason: null,
  },
  {
    id: 8,
    username: 'student08',
    email: 'student08@example.com',
    status: 'active',
    role: 'student',
    questions: 2,
    generated: 5,
    practice: 6,
    lastLogin: '11-26 12:03',
    createdAt: '10-27 19:40',
    hasPersonalKey: false,
    provider: null,
    model: null,
    keyLast4: null,
    pendingPasswordRequests: 0,
    disabledAt: null,
    disabledReason: null,
  },
]

const passwordRequests: PasswordRequest[] = [
  {
    id: 301,
    username: 'student03',
    email: 'student03@example.com',
    registeredEmail: 'student03@example.com',
    emailMatches: true,
    accountStatus: 'active',
    reason: '忘记密码，原手机号已停用，申请重置后立即修改。',
    status: 'pending',
    submittedAt: '11-27 22:48',
    reviewedBy: null,
    reviewedAt: null,
    reviewNote: null,
    ip: '10.0.3.12',
    expiresAt: null,
    deliveryChannel: null,
    mustChangePassword: false,
  },
  {
    id: 302,
    username: 'student07',
    email: 'student07@example.com',
    registeredEmail: 'student07@example.com',
    emailMatches: true,
    accountStatus: 'active',
    reason: '毕业设计期间换了电脑，旧密码没有同步。',
    status: 'pending',
    submittedAt: '11-27 22:31',
    reviewedBy: null,
    reviewedAt: null,
    reviewNote: null,
    ip: '10.0.3.18',
    expiresAt: null,
    deliveryChannel: null,
    mustChangePassword: false,
  },
  {
    id: 303,
    username: 'student05',
    email: 'student05@example.com',
    registeredEmail: 'student05@example.com',
    emailMatches: true,
    accountStatus: 'active',
    reason: '忘记密码，申请临时密码。',
    status: 'approved',
    submittedAt: '11-27 21:50',
    reviewedBy: 'admin',
    reviewedAt: '11-27 22:49',
    reviewNote: '用户名与注册邮箱一致，已通过。',
    ip: '10.0.3.21',
    expiresAt: '11-28 22:49',
    deliveryChannel: 'wechat',
    mustChangePassword: true,
  },
  {
    id: 304,
    username: 'student02',
    email: 'wrong@example.com',
    registeredEmail: 'student02@example.com',
    emailMatches: false,
    accountStatus: 'active',
    reason: '忘记密码。',
    status: 'rejected',
    submittedAt: '11-27 20:15',
    reviewedBy: 'admin',
    reviewedAt: '11-27 20:20',
    reviewNote: '提交邮箱与账号登记邮箱不一致。',
    ip: '10.0.3.09',
    expiresAt: null,
    deliveryChannel: null,
    mustChangePassword: false,
  },
]

const taskRows: AdminTask[] = [
  {
    id: 2041,
    code: 'T-2041',
    questionId: 1042,
    userId: 1,
    question: '求函数 f(x)=x³-3x+1 的极值。',
    username: 'student01',
    stage: 'analysis',
    targetIndex: null,
    status: 'failed',
    errorCode: 'AI_TIMEOUT',
    errorMessage: 'AI 服务响应超时，请重试',
    retryIndex: 1,
    createdAt: '11-27 22:41:08',
    startedAt: '11-27 22:41:10',
    finishedAt: '11-27 22:41:40',
    duration: '30 秒',
  },
  {
    id: 2039,
    code: 'T-2039',
    questionId: 1041,
    userId: 4,
    question: '设 A=(1 2; 2 1)，求 A 的特征值与特征向量。',
    username: 'student04',
    stage: 'quiz',
    targetIndex: 2,
    status: 'failed',
    errorCode: 'AI_INVALID_OUTPUT',
    errorMessage: '生成结果未通过结构校验',
    retryIndex: 0,
    createdAt: '11-27 22:38:17',
    startedAt: '11-27 22:38:19',
    finishedAt: '11-27 22:38:37',
    duration: '18 秒',
  },
  {
    id: 2038,
    code: 'T-2038',
    questionId: 1040,
    userId: 2,
    question: '设 P(A)=0.6，P(B|A)=0.5，则 P(AB)=（ ）。',
    username: 'student02',
    stage: 'quiz',
    targetIndex: 1,
    status: 'running',
    errorCode: null,
    errorMessage: null,
    retryIndex: 0,
    createdAt: '11-27 22:36:51',
    startedAt: '11-27 22:36:53',
    finishedAt: null,
    duration: '生成中',
  },
  {
    id: 2037,
    code: 'T-2037',
    questionId: 1039,
    userId: 1,
    question: '一飞轮以角速度 ω₀=10 rad/s 转动，经 t=5s 匀减速停止。',
    username: 'student01',
    stage: 'quiz',
    targetIndex: 3,
    status: 'done',
    errorCode: null,
    errorMessage: null,
    retryIndex: 0,
    createdAt: '11-27 22:31:44',
    startedAt: '11-27 22:31:46',
    finishedAt: '11-27 22:32:52',
    duration: '1 分 8 秒',
  },
  {
    id: 2036,
    code: 'T-2036',
    questionId: 1042,
    userId: 8,
    question: '求函数 f(x)=x³-3x+1 的极值。',
    username: 'student08',
    stage: 'analysis',
    targetIndex: null,
    status: 'queued',
    errorCode: null,
    errorMessage: null,
    retryIndex: 0,
    createdAt: '11-27 22:30:06',
    startedAt: null,
    finishedAt: null,
    duration: '等待 75 秒',
  },
  {
    id: 2035,
    code: 'T-2035',
    questionId: 1037,
    userId: 5,
    question: '设 A=(1 2; 2 1)，求 A 的特征值与特征向量。',
    username: 'student05',
    stage: 'quiz',
    targetIndex: 1,
    status: 'canceled',
    errorCode: null,
    errorMessage: null,
    retryIndex: 0,
    createdAt: '11-27 22:22:12',
    startedAt: null,
    finishedAt: '11-27 22:23:27',
    duration: '已取消',
  },
]

const aiLogRows: AiLog[] = [
  {
    id: 9001,
    time: '11-27 22:41:08',
    username: 'student01',
    operation: 'analyze',
    model: 'deepseek-flash',
    promptVersion: 'analyze_v3',
    status: 'error',
    latency: '30.0s',
    queueWait: '0.4s',
    tokens: '—',
    inputTokens: null,
    outputTokens: null,
    keySource: 'system',
    errorCode: 'AI_TIMEOUT',
    questionId: 1042,
    hasRaw: true,
  },
  {
    id: 9000,
    time: '11-27 22:38:17',
    username: 'student04',
    operation: 'generate',
    model: 'deepseek-flash',
    promptVersion: 'generate_v3',
    status: 'invalid',
    latency: '18.2s',
    queueWait: '1.1s',
    tokens: '8,420 / 2,104',
    inputTokens: 8420,
    outputTokens: 2104,
    keySource: 'system',
    errorCode: 'AI_INVALID_OUTPUT',
    questionId: 1041,
    hasRaw: true,
  },
  {
    id: 8999,
    time: '11-27 22:36:51',
    username: 'student02',
    operation: 'generate',
    model: 'deepseek-flash',
    promptVersion: 'generate_v3',
    status: 'success',
    latency: '12.7s',
    queueWait: '0.8s',
    tokens: '6,218 / 1,804',
    inputTokens: 6218,
    outputTokens: 1804,
    keySource: 'user',
    errorCode: null,
    questionId: 1040,
    hasRaw: true,
  },
  {
    id: 8998,
    time: '11-27 22:31:44',
    username: 'student01',
    operation: 'generate',
    model: 'deepseek-flash',
    promptVersion: 'generate_v3',
    status: 'success',
    latency: '15.4s',
    queueWait: '0.5s',
    tokens: '7,028 / 1,942',
    inputTokens: 7028,
    outputTokens: 1942,
    keySource: 'system',
    errorCode: null,
    questionId: 1039,
    hasRaw: true,
  },
  {
    id: 8997,
    time: '11-27 22:24:36',
    username: 'student07',
    operation: 'vision',
    model: 'deepseek-flash',
    promptVersion: 'vision_structure_v2',
    status: 'success',
    latency: '26.1s',
    queueWait: '—',
    tokens: '12,580 / 1,242',
    inputTokens: 12580,
    outputTokens: 1242,
    keySource: 'user',
    errorCode: null,
    questionId: null,
    hasRaw: true,
  },
  {
    id: 8996,
    time: '11-27 22:18:09',
    username: 'student03',
    operation: 'analyze',
    model: 'deepseek-flash',
    promptVersion: 'analyze_v3',
    status: 'success',
    latency: '18.4s',
    queueWait: '0.3s',
    tokens: '5,910 / 1,236',
    inputTokens: 5910,
    outputTokens: 1236,
    keySource: 'system',
    errorCode: null,
    questionId: 1038,
    hasRaw: true,
  },
  {
    id: 8995,
    time: '11-27 22:12:55',
    username: 'student05',
    operation: 'generate',
    model: 'deepseek-flash',
    promptVersion: 'generate_v2',
    status: 'success',
    latency: '13.8s',
    queueWait: '0.9s',
    tokens: '6,442 / 1,780',
    inputTokens: 6442,
    outputTokens: 1780,
    keySource: 'system',
    errorCode: null,
    questionId: 1037,
    hasRaw: true,
  },
]

const questionRows: AdminQuestion[] = [
  {
    id: 1042,
    excerpt: '求函数 f(x)=x³-3x+1 的极值。',
    username: 'student01',
    subject: '高等数学',
    chapter: '导数与极值',
    type: 'solve',
    status: 'active',
    flagged: false,
    flagReason: null,
    createdAt: '11-27 21:08',
    generated: 3,
    practice: 8,
    analysis: '考点：导数与极值；难度：中等。错误原因集中在导数为零后未判断符号变化。',
    hasImage: false,
  },
  {
    id: 1041,
    excerpt: '设 A=(1 2; 2 1)，求 A 的特征值与特征向量。',
    username: 'student04',
    subject: '线性代数',
    chapter: '特征值',
    type: 'solve',
    status: 'active',
    flagged: true,
    flagReason: '生成题与原题难度差异过大',
    createdAt: '11-27 20:54',
    generated: 3,
    practice: 5,
    analysis: '考点：矩阵特征值；难度：中等。',
    hasImage: false,
  },
  {
    id: 1040,
    excerpt: '设 P(A)=0.6，P(B|A)=0.5，则 P(AB)=（ ）。',
    username: 'student02',
    subject: '概率论与数理统计',
    chapter: '条件概率',
    type: 'choice',
    status: 'active',
    flagged: false,
    flagReason: null,
    createdAt: '11-27 19:33',
    generated: 3,
    practice: 12,
    analysis: '考点：条件概率与乘法公式；难度：简单。',
    hasImage: false,
  },
  {
    id: 1039,
    excerpt: '一飞轮以角速度 ω₀=10 rad/s 转动，经 t=5s 匀减速停止，求角加速度。',
    username: 'student01',
    subject: '大学物理',
    chapter: '刚体转动',
    type: 'blank',
    status: 'active',
    flagged: false,
    flagReason: null,
    createdAt: '11-27 18:12',
    generated: 3,
    practice: 6,
    analysis: '考点：刚体转动；难度：中等。',
    hasImage: false,
  },
  {
    id: 1038,
    excerpt: '求极限 lim(x→0) (sin x - x)/x³。',
    username: 'student07',
    subject: '高等数学',
    chapter: '极限',
    type: 'solve',
    status: 'hidden',
    flagged: true,
    flagReason: '题干公式渲染异常',
    createdAt: '11-27 16:40',
    generated: 0,
    practice: 2,
    analysis: '考点：泰勒展开/洛必达；难度：中等。',
    hasImage: false,
  },
  {
    id: 1037,
    excerpt: '已知随机变量 X~N(0,1)，求 P(|X|<1)。',
    username: 'student03',
    subject: '概率论与数理统计',
    chapter: '正态分布',
    type: 'solve',
    status: 'active',
    flagged: false,
    flagReason: null,
    createdAt: '11-26 21:22',
    generated: 3,
    practice: 4,
    analysis: '考点：标准正态分布；难度：简单。',
    hasImage: false,
  },
]

const auditRows: AuditLog[] = [
  {
    id: 501,
    time: '11-27 22:49:12',
    admin: 'admin',
    action: 'password_request.approve',
    target: 'student05',
    targetType: 'password_request',
    targetId: '303',
    reason: '用户名与注册邮箱一致，审批通过',
    result: 'success',
    ip: '10.0.1.8',
    requestId: 'req_7f3a91',
    before: { status: 'pending' },
    after: { status: 'approved' },
    errorMessage: null,
  },
  {
    id: 500,
    time: '11-27 22:35:02',
    admin: 'admin',
    action: 'task.retry',
    target: 'T-2041',
    targetType: 'task',
    targetId: '2041',
    reason: 'AI 超时，手动重试一次',
    result: 'success',
    ip: '10.0.1.8',
    requestId: 'req_4d1c22',
    before: { status: 'failed' },
    after: { status: 'queued' },
    errorMessage: null,
  },
  {
    id: 499,
    time: '11-27 22:12:48',
    admin: 'admin',
    action: 'user.disable',
    target: 'student06',
    targetType: 'user',
    targetId: '6',
    reason: '账号异常登录，临时禁用',
    result: 'success',
    ip: '10.0.1.8',
    requestId: 'req_9b7e10',
    before: { status: 'active' },
    after: { status: 'disabled' },
    errorMessage: null,
  },
  {
    id: 498,
    time: '11-27 21:58:34',
    admin: 'admin',
    action: 'ai_log.view_raw',
    target: 'log#9000',
    targetType: 'ai_log',
    targetId: '9000',
    reason: '定位生成结构失败原因',
    result: 'success',
    ip: '10.0.1.8',
    requestId: 'req_2a8c31',
    before: null,
    after: null,
    errorMessage: null,
  },
  {
    id: 497,
    time: '11-27 21:40:09',
    admin: 'admin',
    action: 'question.hide',
    target: 'Q-1042',
    targetType: 'question',
    targetId: '1042',
    reason: '题干含乱码，隐藏处理',
    result: 'success',
    ip: '10.0.1.8',
    requestId: 'req_88f0aa',
    before: { status: 'active' },
    after: { status: 'hidden' },
    errorMessage: null,
  },
  {
    id: 496,
    time: '11-27 21:16:26',
    admin: 'admin',
    action: 'admin.login',
    target: 'admin',
    targetType: 'admin',
    targetId: '9001',
    reason: '密码登录成功',
    result: 'success',
    ip: '10.0.1.8',
    requestId: 'req_01aa7c',
    before: null,
    after: null,
    errorMessage: null,
  },
  {
    id: 495,
    time: '11-27 20:42:03',
    admin: 'admin',
    action: 'audit.export',
    target: '审计日志 · 11-27',
    targetType: 'audit',
    targetId: null,
    reason: '日常审计导出',
    result: 'success',
    ip: '10.0.1.8',
    requestId: 'req_c19d2e',
    before: null,
    after: null,
    errorMessage: null,
  },
]

const alertRows: AlertItem[] = [
  {
    id: 'tasks_failed',
    severity: 'critical',
    title: '2 个任务连续失败',
    detail: '最近 15 分钟有 2 个任务失败，最早 22:38。',
    time: '11-27 22:41',
    status: 'active',
    acknowledgedBy: null,
    acknowledgedAt: null,
    rule: '最近 15 分钟失败任务 ≥ 3',
    current: 2,
    threshold: 3,
    target: { type: 'task', label: '查看任务', to: '/tasks?status=failed' },
  },
  {
    id: 'password_pending',
    severity: 'warning',
    title: '2 个密码申请待审批',
    detail: 'student03、student07 等待管理员核验。',
    time: '11-27 22:31',
    status: 'active',
    acknowledgedBy: null,
    acknowledgedAt: null,
    rule: '存在 pending 密码申请',
    current: 2,
    threshold: 1,
    target: { type: 'password_request', label: '去审批', to: '/password-requests' },
  },
  {
    id: 'ai_latency',
    severity: 'warning',
    title: 'P95 延迟接近阈值',
    detail: '过去 1 小时 P95 为 41.2 秒，阈值 45 秒。',
    time: '11-27 22:20',
    status: 'acknowledged',
    acknowledgedBy: 'admin',
    acknowledgedAt: '11-27 22:25',
    rule: '1 小时内 P95 延迟 > 45 秒',
    current: 41.2,
    threshold: 45,
    target: { type: 'ai_log', label: '查看 AI 日志', to: '/ai-logs' },
  },
]

const successTrend = [
  { label: '11-21', value: 96.8 },
  { label: '11-22', value: 97.4 },
  { label: '11-23', value: 96.1 },
  { label: '11-24', value: 97.8 },
  { label: '11-25', value: 98.2 },
  { label: '11-26', value: 97.6 },
  { label: '11-27', value: 97.2 },
]

const latencyTrend = [
  { label: '11-21', value: 34.2 },
  { label: '11-22', value: 38.1 },
  { label: '11-23', value: 42.6 },
  { label: '11-24', value: 36.4 },
  { label: '11-25', value: 31.8 },
  { label: '11-26', value: 39.2 },
  { label: '11-27', value: 41.2 },
]

let nextAuditId = 600
let nextRequestId = 400

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function noContent(): Response {
  return new Response(null, { status: 204 })
}

function failure(status: number, message: string, code = 'VALIDATION_ERROR'): Response {
  return json({ detail: { code, message, request_id: 'demo' } }, status)
}

function bodyOf(init: RequestInit): Record<string, unknown> {
  if (typeof init.body !== 'string') return {}
  try {
    return JSON.parse(init.body) as Record<string, unknown>
  } catch {
    return {}
  }
}

function queryOf(options: RequestOptions): Record<string, QueryValue> {
  return options.query ?? {}
}

function pageOf<T>(items: T[], options: RequestOptions): DemoPage<T> {
  const page = Math.max(1, Number(queryOf(options).page ?? 1))
  const pageSize = Math.max(1, Number(queryOf(options).page_size ?? 100))
  const start = (page - 1) * pageSize
  return {
    items: items.slice(start, start + pageSize),
    total: items.length,
    page,
    page_size: pageSize,
  }
}

function addAudit(
  action: string,
  target: string,
  targetType: string,
  targetId: string | null,
  reason: string,
  before: Record<string, unknown> | null,
  after: Record<string, unknown> | null,
): number {
  const id = nextAuditId++
  auditRows.unshift({
    id,
    time: NOW,
    admin: 'admin',
    action,
    target,
    targetType,
    targetId,
    reason,
    result: 'success',
    ip: '10.0.1.8',
    requestId: `req_demo_${id}`,
    before,
    after,
    errorMessage: null,
  })
  return id
}

function overview(): AdminOverview {
  const failedTasks = taskRows.filter((task) => task.status === 'failed')
  const pending = passwordRequests.filter((request) => request.status === 'pending')
  const calls = aiLogRows.length
  const successes = aiLogRows.filter((log) => log.status === 'success').length
  return {
    generated_at: NOW,
    stats: {
      users: {
        total: users.length,
        active: users.filter((user) => user.status === 'active').length,
        disabled: users.filter((user) => user.status === 'disabled').length,
        new_7d: 4,
      },
      content: {
        questions: questionRows.length,
        generated: questionRows.reduce((sum, question) => sum + question.generated, 0),
        practice: questionRows.reduce((sum, question) => sum + question.practice, 0),
        flagged: questionRows.filter((question) => question.flagged).length,
        hidden: questionRows.filter((question) => question.status === 'hidden').length,
      },
      ai: {
        calls_24h: calls,
        success_rate: Number(((successes / calls) * 100).toFixed(1)),
        error_rate: 14.3,
        invalid_rate: 14.3,
        p50_latency_ms: 18400,
        p95_latency_ms: 41200,
        input_tokens: aiLogRows.reduce((sum, log) => sum + (log.inputTokens ?? 0), 0),
        output_tokens: aiLogRows.reduce((sum, log) => sum + (log.outputTokens ?? 0), 0),
        estimated_cost: 12.84,
      },
      tasks: {
        queued: taskRows.filter((task) => task.status === 'queued').length,
        running: taskRows.filter((task) => task.status === 'running').length,
        failed: failedTasks.length,
        done_24h: taskRows.filter((task) => task.status === 'done').length,
        canceled_24h: taskRows.filter((task) => task.status === 'canceled').length,
        oldest_queue_seconds: 75,
      },
      password_requests: {
        pending: pending.length,
        approved_today: passwordRequests.filter((request) => request.status === 'approved').length,
        rejected_today: passwordRequests.filter((request) => request.status === 'rejected').length,
      },
    },
    failed_tasks: failedTasks,
    pending_password_requests: pending,
    recent_audit: auditRows.slice(0, 4),
    alerts: alertRows,
    trend: { success: successTrend, latency: latencyTrend },
  }
}

function userDetail(id: number): AdminUserDetail | null {
  const user = users.find((item) => item.id === id)
  if (!user) return null
  return {
    ...user,
    recentTasks: taskRows.filter((task) => task.userId === id).slice(0, 3),
    passwordRequests: passwordRequests.filter((request) => request.username === user.username).slice(0, 3),
  }
}

function taskDetail(id: number): AdminTaskDetail | null {
  const task = taskRows.find((item) => item.id === id)
  if (!task) return null
  const timeline: TaskTimelineItem[] = [
    {
      key: 'queued',
      title: '任务入队',
      status: 'queued',
      time: task.createdAt,
      meta: '已进入队列',
    },
  ]
  if (task.status !== 'queued') {
    timeline.push({
      key: 'started',
      title: task.stage === 'analysis' ? 'AI 分析' : '相似题生成',
      status: task.status === 'running' ? 'running' : 'done',
      time: task.startedAt ?? task.createdAt,
      meta: task.status === 'running' ? '执行中' : '已执行',
    })
  }
  if (task.status === 'done' || task.status === 'failed' || task.status === 'canceled') {
    timeline.push({
      key: 'finished',
      title: task.status === 'done' ? '任务完成' : task.status === 'failed' ? '任务失败' : '任务取消',
      status: task.status,
      time: task.finishedAt ?? task.createdAt,
      meta: task.duration,
    })
  }
  return { ...task, timeline }
}

function questionDetail(id: number): AdminQuestionDetail | null {
  const question = questionRows.find((item) => item.id === id)
  if (!question) return null
  const generatedQuestions = Array.from({ length: Math.max(question.generated, 0) }, (_, index) => ({
    id: question.id * 10 + index + 1,
    contentMd: `相似题 ${index + 1}：${question.excerpt}`,
    answerMd: '参考答案见解析。',
    explanationMd: '按题目条件逐步求解。',
    questionType: question.type,
    difficulty: ['easy', 'medium', 'hard'][index] ?? 'medium',
    targetIndex: index + 1,
    validationStatus: 'valid',
    validationScore: 0.92,
    model: 'deepseek-flash',
    promptVersion: 'generate_v3',
  }))
  return {
    ...question,
    contentMd: question.excerpt,
    answerMd: '参考答案见解析。',
    explanationMd: '按题目条件逐步求解。',
    sourceType: 'text',
    options: null,
    blanks: null,
    tags: [question.chapter, question.subject],
    imagePath: null,
    generatedQuestions,
    tasks: taskRows.filter((task) => task.questionId === question.id),
    recentAudit: auditRows.filter((entry) => entry.target === `Q-${question.id}`).slice(0, 3),
  }
}

const RAW_RESPONSES: Record<number, string> = {
  9001: '{"error":"upstream timeout after 30s"}',
  9000: '{"raw":"生成结果缺少选项 C 的题干","reason":"schema_validation"}',
  8999: '{"question":"...","difficulty":"easy"}',
  8998: '{"question":"...","difficulty":"hard"}',
  8997: '{"questions":3,"chapter":"习题 7.1"}',
  8996: '{"knowledge_points":["导数","极值"]}',
  8995: '{"question":"...","difficulty":"medium"}',
}

function systemPayload(): AdminSystem {
  const active = alertRows.filter((alert) => alert.status === 'active').length
  return {
    generated_at: NOW,
    environment: {
      app_env: 'development',
      is_demo: true,
      version: '0.1.0',
      llm_mode: 'mock',
      worker_enabled: true,
      database: 'sqlite',
    },
    status: {
      level: active > 0 ? 'degraded' : 'ok',
      summary: active > 0 ? `${active} 条活跃告警` : '运行正常',
      active_alerts: active,
    },
    checks: [
      {
        key: 'api',
        name: 'API 网关',
        status: 'ok',
        value: '42 ms',
        detail: '健康检查通过 · 过去 24h 可用性 99.98%',
        checkedAt: NOW,
        meta: '探活',
      },
      {
        key: 'database',
        name: '数据库',
        status: 'ok',
        value: '3 ms',
        detail: 'SELECT 1 通过 · 连接池 4 / 20',
        checkedAt: NOW,
        meta: '探活',
      },
      {
        key: 'worker',
        name: '任务 Worker',
        status: 'ok',
        value: '2 / 6',
        detail: '运行中 2 · 排队 1 · 无卡死任务',
        checkedAt: NOW,
        meta: '快照',
      },
      {
        key: 'llm',
        name: 'LLM Provider',
        status: 'warning',
        value: '97.2%',
        detail: '过去 1 小时成功率 · 6 次调用',
        checkedAt: NOW,
        meta: '聚合',
      },
    ],
    config: [
      { label: '应用版本', value: '0.1.0', note: 'demo build' },
      { label: '运行环境', value: 'development', note: 'APP_ENV' },
      { label: 'LLM 模式', value: 'mock', note: 'LLM_MOCK=true' },
      { label: '任务并发', value: '6', note: 'TASK_MAX_CONCURRENCY' },
      { label: '任务硬超时', value: '120s', note: 'TASK_HARD_TIMEOUT_S' },
      { label: '鉴权 Token TTL', value: '8h（建议）', note: '演示模式' },
      { label: '审计保留', value: '180 天', note: '演示模式' },
    ],
    events: [
      {
        time: NOW,
        title: '数据库探活通过',
        detail: 'SELECT 1 · 3ms',
        level: 'ok',
      },
      {
        time: '11-27 22:41',
        title: '任务失败',
        detail: 'T-2041 · AI_TIMEOUT',
        level: 'warning',
      },
      {
        time: '11-27 22:25',
        title: '告警已确认',
        detail: 'P95 延迟 · admin',
        level: 'ok',
      },
    ],
  }
}

const MOCK_TOKEN = 'demo-admin-token'

export function isDemoMode(): boolean {
  return import.meta.env.VITE_ADMIN_DEMO === 'true'
}

export async function handleDemoRequest(
  path: string,
  init: RequestInit,
  options: RequestOptions,
): Promise<Response | null> {
  if (!isDemoMode() || !path.startsWith('/admin/')) return null
  const method = (init.method ?? 'GET').toUpperCase()

  if (path === '/admin/auth/login' && method === 'POST') {
    const body = bodyOf(init)
    if (body.username === 'admin' && body.password === 'admin123') {
      return json({ access_token: MOCK_TOKEN, token_type: 'bearer', user: ADMIN })
    }
    return failure(401, '用户名或密码错误', 'AUTH_INVALID_CREDENTIALS')
  }
  if (path === '/admin/me') return json(ADMIN)
  if (path === '/admin/logout') return noContent()

  const userId = path.match(/^\/admin\/users\/(\d+)$/)
  if (userId && method === 'GET') {
    const detail = userDetail(Number(userId[1]))
    return detail ? json(detail) : failure(404, '用户不存在', 'NOT_FOUND')
  }
  const userStatus = path.match(/^\/admin\/users\/(\d+)\/status$/)
  if (userStatus && method === 'POST') {
    const id = Number(userStatus[1])
    const target = users.find((user) => user.id === id)
    if (!target) return failure(404, '用户不存在', 'NOT_FOUND')
    const body = bodyOf(init)
    const status = body.status === 'disabled' ? 'disabled' : 'active'
    const before = { status: target.status }
    target.status = status
    target.disabledAt = status === 'disabled' ? NOW : null
    target.disabledReason = status === 'disabled' ? String(body.reason ?? '') : null
    const auditId = addAudit(
      status === 'disabled' ? 'user.disable' : 'user.enable',
      target.username,
      'user',
      String(target.id),
      String(body.reason ?? ''),
      before,
      { status },
    )
    return json({ user: target, audit_id: auditId })
  }
  const forceLogout = path.match(/^\/admin\/users\/(\d+)\/force-logout$/)
  if (forceLogout && method === 'POST') {
    const target = users.find((user) => user.id === Number(forceLogout[1]))
    if (!target) return failure(404, '用户不存在', 'NOT_FOUND')
    const auditId = addAudit('user.force_logout', target.username, 'user', String(target.id), '管理员强制下线', null, null)
    return json({ status: 'ok', audit_id: auditId })
  }

  if (path === '/admin/users' && method === 'GET') {
    const query = queryOf(options)
    const q = String(query.q ?? '').toLowerCase()
    const status = String(query.status ?? 'all')
    const filtered = users.filter((user) => {
      if (status !== 'all' && user.status !== status) return false
      if (!q) return true
      return `${user.username} ${user.email}`.toLowerCase().includes(q)
    })
    return json(pageOf(filtered, options))
  }

  if (path === '/admin/password-requests' && method === 'GET') {
    const query = queryOf(options)
    const status = String(query.status ?? 'all')
    const filtered = passwordRequests.filter((request) => status === 'all' || request.status === status)
    return json(pageOf(filtered, options))
  }
  const approve = path.match(/^\/admin\/password-requests\/(\d+)\/approve$/)
  if (approve && method === 'POST') {
    const request = passwordRequests.find((item) => item.id === Number(approve[1]))
    if (!request) return failure(404, '申请不存在', 'NOT_FOUND')
    if (request.status !== 'pending') return failure(400, '该申请已处理')
    const body = bodyOf(init)
    const auditId = addAudit(
      'password_request.approve',
      request.username,
      'password_request',
      String(request.id),
      String(body.reason ?? ''),
      { status: 'pending' },
      { status: 'approved' },
    )
    request.status = 'approved'
    request.reviewedBy = 'admin'
    request.reviewedAt = NOW
    request.reviewNote = String(body.reason ?? '')
    request.expiresAt = '11-29 01:20'
    request.deliveryChannel = String(body.delivery_channel ?? 'wechat')
    request.mustChangePassword = true
    return json({
      request,
      temporary_password: 'K7m2P9q4R6s8',
      must_change_password: true,
      expires_at: '11-29 01:20',
      audit_id: auditId,
    } satisfies PasswordApproveResult)
  }
  const reject = path.match(/^\/admin\/password-requests\/(\d+)\/reject$/)
  if (reject && method === 'POST') {
    const request = passwordRequests.find((item) => item.id === Number(reject[1]))
    if (!request) return failure(404, '申请不存在', 'NOT_FOUND')
    const body = bodyOf(init)
    const auditId = addAudit(
      'password_request.reject',
      request.username,
      'password_request',
      String(request.id),
      String(body.reason ?? ''),
      { status: request.status },
      { status: 'rejected' },
    )
    request.status = 'rejected'
    request.reviewedBy = 'admin'
    request.reviewedAt = NOW
    request.reviewNote = String(body.reason ?? '')
    return json({ request, audit_id: auditId })
  }
  const regenerate = path.match(/^\/admin\/password-requests\/(\d+)\/regenerate-temp-password$/)
  if (regenerate && method === 'POST') {
    const request = passwordRequests.find((item) => item.id === Number(regenerate[1]))
    if (!request) return failure(404, '申请不存在', 'NOT_FOUND')
    const auditId = addAudit(
      'password_request.regenerate',
      request.username,
      'password_request',
      String(request.id),
      '重新生成临时密码',
      null,
      null,
    )
    request.expiresAt = '11-29 01:20'
    request.mustChangePassword = true
    return json({
      request,
      temporary_password: 'R8n4Q2w7T5y9',
      must_change_password: true,
      expires_at: '11-29 01:20',
      audit_id: auditId,
    } satisfies PasswordApproveResult)
  }

  if (path === '/admin/questions' && method === 'GET') {
    const query = queryOf(options)
    const q = String(query.q ?? '').toLowerCase()
    const status = String(query.status ?? 'all')
    const flagged = query.flagged === true || query.flagged === 'true'
    const filtered = questionRows.filter((question) => {
      if (status !== 'all' && question.status !== status) return false
      if (flagged && !question.flagged) return false
      if (!q) return true
      return `${question.id} ${question.excerpt} ${question.username}`.toLowerCase().includes(q)
    })
    return json(pageOf(filtered, options))
  }
  const questionDetailMatch = path.match(/^\/admin\/questions\/(\d+)$/)
  if (questionDetailMatch && method === 'GET') {
    const detail = questionDetail(Number(questionDetailMatch[1]))
    return detail ? json(detail) : failure(404, '内容不存在', 'NOT_FOUND')
  }
  const moderation = path.match(/^\/admin\/questions\/(\d+)\/moderation$/)
  if (moderation && method === 'POST') {
    const question = questionRows.find((item) => item.id === Number(moderation[1]))
    if (!question) return failure(404, '内容不存在', 'NOT_FOUND')
    const body = bodyOf(init)
    const before = { status: question.status, flagged: question.flagged }
    if (typeof body.hidden === 'boolean') {
      question.status = body.hidden ? 'hidden' : 'active'
    }
    if (typeof body.flagged === 'boolean') {
      question.flagged = body.flagged
      question.flagReason = body.flagged ? String(body.reason ?? '') : null
    }
    const action = typeof body.hidden === 'boolean'
      ? body.hidden ? 'question.hide' : 'question.restore'
      : body.flagged ? 'question.flag' : 'question.unflag'
    const auditId = addAudit(
      action,
      `Q-${question.id}`,
      'question',
      String(question.id),
      String(body.reason ?? ''),
      before,
      { status: question.status, flagged: question.flagged },
    )
    return json({ question, audit_id: auditId })
  }

  if (path === '/admin/tasks' && method === 'GET') {
    const query = queryOf(options)
    const q = String(query.q ?? '').toLowerCase()
    const status = String(query.status ?? 'all')
    const filtered = taskRows.filter((task) => {
      if (status !== 'all' && task.status !== status) return false
      if (!q) return true
      return `${task.code} ${task.question} ${task.username} ${task.errorCode ?? ''}`.toLowerCase().includes(q)
    })
    return json(pageOf(filtered, options))
  }
  const taskDetailMatch = path.match(/^\/admin\/tasks\/(\d+)$/)
  if (taskDetailMatch && method === 'GET') {
    const detail = taskDetail(Number(taskDetailMatch[1]))
    return detail ? json(detail) : failure(404, '任务不存在', 'NOT_FOUND')
  }
  const retry = path.match(/^\/admin\/tasks\/(\d+)\/retry$/)
  if (retry && method === 'POST') {
    const task = taskRows.find((item) => item.id === Number(retry[1]))
    if (!task) return failure(404, '任务不存在', 'NOT_FOUND')
    if (task.status !== 'failed') return failure(400, '只有失败的任务可以重试')
    if (task.retryIndex >= 3) return failure(400, '已达重试上限')
    task.status = 'queued'
    task.errorCode = null
    task.errorMessage = null
    task.retryIndex += 1
    task.duration = '等待中'
    const auditId = addAudit('task.retry', task.code, 'task', String(task.id), '管理员重试', null, null)
    return json({ task, audit_id: auditId })
  }
  const cancel = path.match(/^\/admin\/tasks\/(\d+)\/cancel$/)
  if (cancel && method === 'POST') {
    const task = taskRows.find((item) => item.id === Number(cancel[1]))
    if (!task) return failure(404, '任务不存在', 'NOT_FOUND')
    if (task.status !== 'queued') return failure(400, '只有排队中的任务可以取消')
    task.status = 'canceled'
    task.finishedAt = NOW
    task.duration = '已取消'
    const auditId = addAudit('task.cancel', task.code, 'task', String(task.id), '管理员取消排队', null, null)
    return json({ task, audit_id: auditId })
  }

  if (path === '/admin/ai-logs' && method === 'GET') {
    const query = queryOf(options)
    const q = String(query.q ?? '').toLowerCase()
    const status = String(query.status ?? 'all')
    const operation = String(query.operation ?? 'all')
    const filtered = aiLogRows.filter((log) => {
      if (status !== 'all' && log.status !== status) return false
      if (operation !== 'all' && log.operation !== operation) return false
      if (!q) return true
      return `${log.id} ${log.username} ${log.model} ${log.promptVersion} ${log.errorCode ?? ''}`.toLowerCase().includes(q)
    })
    return json(pageOf(filtered, options))
  }
  const aiLogDetail = path.match(/^\/admin\/ai-logs\/(\d+)$/)
  if (aiLogDetail && method === 'GET') {
    const log = aiLogRows.find((item) => item.id === Number(aiLogDetail[1]))
    return log ? json(log) : failure(404, '日志不存在', 'NOT_FOUND')
  }
  const raw = path.match(/^\/admin\/ai-logs\/(\d+)\/raw$/)
  if (raw && method === 'POST') {
    const log = aiLogRows.find((item) => item.id === Number(raw[1]))
    if (!log) return failure(404, '日志不存在', 'NOT_FOUND')
    const auditId = addAudit(
      'ai_log.view_raw',
      `log#${log.id}`,
      'ai_log',
      String(log.id),
      String(bodyOf(init).reason ?? '查看原始输出'),
      null,
      null,
    )
    const result: AiLogRawResult = {
      raw: RAW_RESPONSES[log.id] ?? '{"raw":"demo"}',
      truncated: false,
      audit_id: auditId,
    }
    return json(result)
  }

  if (path === '/admin/audit' && method === 'GET') {
    const query = queryOf(options)
    const q = String(query.q ?? '').toLowerCase()
    const result = String(query.result ?? 'all')
    const filtered = auditRows.filter((log) => {
      if (result !== 'all' && log.result !== result) return false
      if (!q) return true
      return `${log.admin} ${log.action} ${log.target} ${log.reason} ${log.ip} ${log.requestId}`.toLowerCase().includes(q)
    })
    return json(pageOf(filtered, options))
  }
  const auditDetail = path.match(/^\/admin\/audit\/(\d+)$/)
  if (auditDetail && method === 'GET') {
    const log = auditRows.find((item) => item.id === Number(auditDetail[1]))
    return log ? json(log) : failure(404, '审计记录不存在', 'NOT_FOUND')
  }
  if (path === '/admin/audit/export.csv' && method === 'GET') {
    const header = '时间,管理员,动作,对象,原因,结果,IP,请求编号\n'
    const lines = auditRows.map((log) =>
      [log.time, log.admin, log.action, log.target, log.reason, log.result, log.ip, log.requestId]
        .map((value) => `"${String(value).replace(/"/g, '""')}"`)
        .join(','),
    )
    return new Response(`\uFEFF${header}${lines.join('\n')}`, {
      status: 200,
      headers: { 'Content-Type': 'text/csv; charset=utf-8' },
    })
  }

  if (path === '/admin/alerts' && method === 'GET') {
    return json(alertRows)
  }
  const ack = path.match(/^\/admin\/alerts\/([^/]+)\/ack$/)
  if (ack && method === 'POST') {
    const alert = alertRows.find((item) => item.id === decodeURIComponent(ack[1]))
    if (!alert) return failure(404, '告警不存在', 'NOT_FOUND')
    alert.status = 'acknowledged'
    alert.acknowledgedBy = 'admin'
    alert.acknowledgedAt = NOW
    alertRows.forEach((item) => { if (item.id === alert.id) item.status = 'acknowledged' })
    const auditId = addAudit('alert.acknowledge', alert.title, 'alert', alert.id, '标记已处理', null, null)
    return json({ ...alert, audit_id: auditId })
  }
  const unack = path.match(/^\/admin\/alerts\/([^/]+)\/unack$/)
  if (unack && method === 'POST') {
    const alert = alertRows.find((item) => item.id === decodeURIComponent(unack[1]))
    if (!alert) return failure(404, '告警不存在', 'NOT_FOUND')
    alert.status = 'active'
    alert.acknowledgedBy = null
    alert.acknowledgedAt = null
    addAudit('alert.unacknowledge', alert.title, 'alert', alert.id, '取消确认', null, null)
    return noContent()
  }

  if (path === '/admin/overview' && method === 'GET') return json(overview())
  if (path === '/admin/system' && method === 'GET') return json(systemPayload())

  return failure(404, `Demo 模式未实现 ${method} ${path}`, 'NOT_FOUND')
}
