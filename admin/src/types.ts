export type Tone = 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'running'

/** Authenticated admin profile returned by `/admin/auth/login` and `/admin/me`. */
export interface AdminProfile {
  id: number
  username: string
  email: string
  role: string
  must_change_password: boolean
}

export interface AdminUser {
  id: number
  username: string
  email: string
  status: 'active' | 'disabled'
  role: string
  questions: number
  generated: number
  practice: number
  lastLogin: string
  createdAt: string
  hasPersonalKey: boolean
  provider: string | null
  model: string | null
  keyLast4: string | null
  pendingPasswordRequests: number
  disabledAt: string | null
  disabledReason: string | null
}

export interface AdminUserDetail extends AdminUser {
  recentTasks: AdminTask[]
  passwordRequests: PasswordRequest[]
}

export interface PasswordRequest {
  id: number
  username: string
  email: string
  registeredEmail: string
  emailMatches: boolean
  accountStatus: string
  reason: string
  status: 'pending' | 'approved' | 'rejected'
  submittedAt: string
  reviewedBy: string | null
  reviewedAt: string | null
  reviewNote: string | null
  ip: string
  expiresAt: string | null
  deliveryChannel: string | null
  mustChangePassword: boolean
}

export interface PasswordApproveResult {
  request: PasswordRequest
  temporary_password: string
  must_change_password: boolean
  expires_at: string
  audit_id: number
}

export interface AdminTask {
  id: number
  code: string
  questionId: number
  userId: number
  question: string
  username: string
  stage: 'analysis' | 'quiz'
  targetIndex: number | null
  status: 'queued' | 'running' | 'done' | 'failed' | 'canceled'
  errorCode: string | null
  errorMessage: string | null
  retryIndex: number
  createdAt: string
  startedAt: string | null
  finishedAt: string | null
  duration: string
}

export interface TaskTimelineItem {
  key: string
  title: string
  status: string
  time: string
  meta: string | null
}

export interface AdminTaskDetail extends AdminTask {
  timeline: TaskTimelineItem[]
}

export interface AiLog {
  id: number
  time: string
  username: string
  operation: 'vision' | 'analyze' | 'generate' | 'judge'
  model: string
  promptVersion: string
  status: 'success' | 'error' | 'invalid'
  latency: string
  queueWait: string
  tokens: string
  inputTokens: number | null
  outputTokens: number | null
  keySource: 'system' | 'user' | 'mock'
  errorCode: string | null
  questionId: number | null
  hasRaw: boolean
}

export interface AiLogRawResult {
  raw: string
  truncated: boolean
  audit_id: number
}

export interface AuditLog {
  id: number
  time: string
  admin: string
  action: string
  target: string
  targetType: string | null
  targetId: string | null
  reason: string
  result: 'success' | 'failed'
  ip: string
  requestId: string
  before: Record<string, unknown> | null
  after: Record<string, unknown> | null
  errorMessage: string | null
}

export interface AdminQuestion {
  id: number
  excerpt: string
  username: string
  subject: string
  chapter: string
  type: string
  status: 'active' | 'hidden'
  flagged: boolean
  flagReason: string | null
  createdAt: string
  generated: number
  practice: number
  analysis: string
  hasImage: boolean
}

export interface GeneratedQuestion {
  id: number
  contentMd: string
  answerMd: string
  explanationMd: string
  questionType: string
  difficulty: string
  targetIndex: number
  validationStatus: string
  validationScore: number | null
  model: string
  promptVersion: string
}

export interface AdminQuestionDetail extends AdminQuestion {
  contentMd: string
  answerMd: string
  explanationMd: string
  sourceType: string
  options: unknown
  blanks: unknown
  tags: string[]
  imagePath: string | null
  generatedQuestions: GeneratedQuestion[]
  tasks: AdminTask[]
  recentAudit: AuditLog[]
}

export interface AlertTarget {
  type: string
  label: string
  to: string
}

export interface AlertItem {
  id: string
  severity: 'critical' | 'warning' | 'info'
  title: string
  detail: string
  time: string
  status: 'active' | 'acknowledged'
  acknowledgedBy: string | null
  acknowledgedAt: string | null
  rule: string
  current: number
  threshold: number
  target: AlertTarget | null
}

export interface TrendPoint {
  label: string
  value: number
}

export interface OverviewUserStats {
  total: number
  active: number
  disabled: number
  new_7d: number
}

export interface OverviewContentStats {
  questions: number
  generated: number
  practice: number
  flagged: number
  hidden: number
}

export interface OverviewAiStats {
  calls_24h: number
  success_rate: number
  error_rate: number
  invalid_rate: number
  p50_latency_ms: number
  p95_latency_ms: number
  input_tokens: number
  output_tokens: number
  estimated_cost: number | null
}

export interface OverviewTaskStats {
  queued: number
  running: number
  failed: number
  done_24h: number
  canceled_24h: number
  oldest_queue_seconds: number
}

export interface OverviewPasswordStats {
  pending: number
  approved_today: number
  rejected_today: number
}

export interface AdminOverview {
  generated_at: string
  stats: {
    users: OverviewUserStats
    content: OverviewContentStats
    ai: OverviewAiStats
    tasks: OverviewTaskStats
    password_requests: OverviewPasswordStats
  }
  failed_tasks: AdminTask[]
  pending_password_requests: PasswordRequest[]
  recent_audit: AuditLog[]
  alerts: AlertItem[]
  trend: {
    success: TrendPoint[]
    latency: TrendPoint[]
  }
}

export interface SystemEnvironment {
  app_env: string
  is_demo: boolean
  version: string
  llm_mode: string
  worker_enabled: boolean
  database: string
}

export interface SystemStatus {
  level: string
  summary: string
  active_alerts: number
}

export interface SystemCheck {
  key: string
  name: string
  status: string
  value: string
  detail: string
  checkedAt: string
  meta: string
}

export interface SystemConfigRow {
  label: string
  value: string
  note: string
}

export interface SystemEvent {
  time: string
  title: string
  detail: string
  level: string
}

export interface AdminSystem {
  generated_at: string
  environment: SystemEnvironment
  status: SystemStatus
  checks: SystemCheck[]
  config: SystemConfigRow[]
  events: SystemEvent[]
}
