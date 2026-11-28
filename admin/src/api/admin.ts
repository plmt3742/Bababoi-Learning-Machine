import { apiBlob, apiRequest, type QueryValue } from './client'
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
} from '../types'

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface AdminLoginResponse {
  access_token: string
  token_type: string
  user: AdminProfile
}

export interface ListUsersParams {
  q?: string
  status?: string
  page?: number
  page_size?: number
}

export interface ListPasswordRequestsParams {
  status?: string
  q?: string
  page?: number
  page_size?: number
}

export interface ListQuestionsParams {
  q?: string
  status?: string
  flagged?: boolean
  page?: number
  page_size?: number
}

export interface ListTasksParams {
  status?: string
  q?: string
  page?: number
  page_size?: number
}

export interface ListAiLogsParams {
  status?: string
  operation?: string
  q?: string
  page?: number
  page_size?: number
}

export interface ListAuditParams {
  q?: string
  result?: string
  page?: number
  page_size?: number
}

export interface ApprovePasswordPayload {
  reason: string
  verified: boolean
  delivery_channel: string
}

export interface RejectPasswordPayload {
  reason: string
}

export type QuestionModerationPayload =
  | { hidden: boolean; reason?: string }
  | { flagged: boolean; reason?: string }

function toQuery<T extends object>(params: T): Record<string, QueryValue> {
  const query: Record<string, QueryValue> = {}
  for (const [key, value] of Object.entries(params) as [string, unknown][]) {
    if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
      query[key] = value
    }
  }
  return query
}

function postJson(body?: unknown): RequestInit {
  return {
    method: 'POST',
    body: body === undefined ? undefined : JSON.stringify(body),
  }
}

// --- Auth ---------------------------------------------------------------

export function adminLogin(username: string, password: string): Promise<AdminLoginResponse> {
  return apiRequest<AdminLoginResponse>(
    '/admin/auth/login',
    postJson({ username, password }),
    { redirectOnUnauthorized: false },
  )
}

export function adminMe(): Promise<AdminProfile> {
  return apiRequest<AdminProfile>('/admin/me')
}

export function adminLogout(): Promise<void> {
  return apiRequest<void>('/admin/logout', postJson(), { redirectOnUnauthorized: false })
}

// --- Overview -----------------------------------------------------------

export function getOverview(): Promise<AdminOverview> {
  return apiRequest<AdminOverview>('/admin/overview')
}

// --- Users --------------------------------------------------------------

export function listUsers(params: ListUsersParams = {}): Promise<Page<AdminUser>> {
  return apiRequest<Page<AdminUser>>('/admin/users', {}, { query: toQuery(params) })
}

export function getUser(id: number): Promise<AdminUserDetail> {
  return apiRequest<AdminUserDetail>(`/admin/users/${id}`)
}

export interface UserStatusPayload {
  status: 'active' | 'disabled'
  reason?: string
}

export interface UserStatusResult {
  user: AdminUser
  audit_id: number
}

export function setUserStatus(id: number, payload: UserStatusPayload): Promise<UserStatusResult> {
  return apiRequest<UserStatusResult>(`/admin/users/${id}/status`, postJson(payload))
}

export interface ForceLogoutResult {
  status: string
  audit_id: number
}

export function forceLogoutUser(id: number): Promise<ForceLogoutResult> {
  return apiRequest<ForceLogoutResult>(`/admin/users/${id}/force-logout`, postJson())
}

// --- Password reset requests -------------------------------------------

export function listPasswordRequests(
  params: ListPasswordRequestsParams = {},
): Promise<Page<PasswordRequest>> {
  return apiRequest<Page<PasswordRequest>>('/admin/password-requests', {}, { query: toQuery(params) })
}

export function approvePasswordRequest(
  id: number,
  payload: ApprovePasswordPayload,
): Promise<PasswordApproveResult> {
  return apiRequest<PasswordApproveResult>(`/admin/password-requests/${id}/approve`, postJson(payload))
}

export interface PasswordRejectResult {
  request: PasswordRequest
  audit_id: number
}

export function rejectPasswordRequest(
  id: number,
  payload: RejectPasswordPayload,
): Promise<PasswordRejectResult> {
  return apiRequest<PasswordRejectResult>(`/admin/password-requests/${id}/reject`, postJson(payload))
}

export function regenerateTempPassword(id: number): Promise<PasswordApproveResult> {
  return apiRequest<PasswordApproveResult>(
    `/admin/password-requests/${id}/regenerate-temp-password`,
    postJson(),
  )
}

// --- Questions ----------------------------------------------------------

export function listQuestions(params: ListQuestionsParams = {}): Promise<Page<AdminQuestion>> {
  return apiRequest<Page<AdminQuestion>>('/admin/questions', {}, { query: toQuery(params) })
}

export function getQuestion(id: number): Promise<AdminQuestionDetail> {
  return apiRequest<AdminQuestionDetail>(`/admin/questions/${id}`)
}

export interface QuestionModerationResult {
  question: AdminQuestion
  audit_id: number
}

export function moderateQuestion(
  id: number,
  payload: QuestionModerationPayload,
): Promise<QuestionModerationResult> {
  return apiRequest<QuestionModerationResult>(`/admin/questions/${id}/moderation`, postJson(payload))
}

// --- Tasks --------------------------------------------------------------

export function listTasks(params: ListTasksParams = {}): Promise<Page<AdminTask>> {
  return apiRequest<Page<AdminTask>>('/admin/tasks', {}, { query: toQuery(params) })
}

export function getTask(id: number): Promise<AdminTaskDetail> {
  return apiRequest<AdminTaskDetail>(`/admin/tasks/${id}`)
}

export interface TaskMutationResult {
  task: AdminTask
  audit_id: number
}

export function retryTask(id: number): Promise<TaskMutationResult> {
  return apiRequest<TaskMutationResult>(`/admin/tasks/${id}/retry`, postJson())
}

export function cancelTask(id: number): Promise<TaskMutationResult> {
  return apiRequest<TaskMutationResult>(`/admin/tasks/${id}/cancel`, postJson())
}

// --- AI logs ------------------------------------------------------------

export function listAiLogs(params: ListAiLogsParams = {}): Promise<Page<AiLog>> {
  return apiRequest<Page<AiLog>>('/admin/ai-logs', {}, { query: toQuery(params) })
}

export function getAiLog(id: number): Promise<AiLog> {
  return apiRequest<AiLog>(`/admin/ai-logs/${id}`)
}

export function revealAiLogRaw(id: number, reason: string): Promise<AiLogRawResult> {
  return apiRequest<AiLogRawResult>(`/admin/ai-logs/${id}/raw`, postJson({ reason }))
}

// --- Audit --------------------------------------------------------------

export function listAudit(params: ListAuditParams = {}): Promise<Page<AuditLog>> {
  return apiRequest<Page<AuditLog>>('/admin/audit', {}, { query: toQuery(params) })
}

export function getAudit(id: number): Promise<AuditLog> {
  return apiRequest<AuditLog>(`/admin/audit/${id}`)
}

export function exportAuditCsv(
  params: Pick<ListAuditParams, 'q' | 'result'> = {},
): Promise<Blob> {
  return apiBlob('/admin/audit/export.csv', { query: toQuery(params) })
}

// --- Alerts -------------------------------------------------------------

export function listAlerts(): Promise<AlertItem[]> {
  return apiRequest<AlertItem[]>('/admin/alerts')
}

export function ackAlert(key: string, note?: string): Promise<AlertItem> {
  return apiRequest<AlertItem>(`/admin/alerts/${encodeURIComponent(key)}/ack`, postJson({ note }))
}

export function unackAlert(key: string): Promise<void> {
  return apiRequest<void>(`/admin/alerts/${encodeURIComponent(key)}/unack`, postJson())
}

// --- System -------------------------------------------------------------

export function getSystem(): Promise<AdminSystem> {
  return apiRequest<AdminSystem>('/admin/system')
}
