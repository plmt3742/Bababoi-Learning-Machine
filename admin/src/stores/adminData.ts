import { defineStore } from 'pinia'

import {
  ackAlert,
  approvePasswordRequest,
  cancelTask,
  exportAuditCsv,
  forceLogoutUser,
  getAiLog,
  getAudit,
  getOverview,
  getQuestion,
  getSystem,
  getTask,
  getUser,
  listAiLogs,
  listAlerts,
  listAudit,
  listPasswordRequests,
  listQuestions,
  listTasks,
  listUsers,
  moderateQuestion,
  regenerateTempPassword,
  rejectPasswordRequest,
  retryTask,
  revealAiLogRaw,
  setUserStatus,
  unackAlert,
  type ApprovePasswordPayload,
  type ListAiLogsParams,
  type ListAuditParams,
  type ListPasswordRequestsParams,
  type ListQuestionsParams,
  type ListTasksParams,
  type ListUsersParams,
  type QuestionModerationPayload,
  type UserStatusPayload,
} from '../api/admin'
import type {
  AdminOverview,
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

const ALL_PAGE_SIZE = 100

export const useAdminData = defineStore('admin-data', {
  state: () => ({
    users: [] as AdminUser[],
    usersTotal: 0,
    passwordRequests: [] as PasswordRequest[],
    passwordRequestsTotal: 0,
    questions: [] as AdminQuestion[],
    questionsTotal: 0,
    tasks: [] as AdminTask[],
    tasksTotal: 0,
    aiLogs: [] as AiLog[],
    aiLogsTotal: 0,
    auditLogs: [] as AuditLog[],
    auditTotal: 0,
    alerts: [] as AlertItem[],
    overview: null as AdminOverview | null,
    system: null as AdminSystem | null,
  }),
  getters: {
    pendingPasswordCount(state): number {
      return (
        state.overview?.stats.password_requests.pending ??
        state.passwordRequests.filter((request) => request.status === 'pending').length
      )
    },
    activeAlertCount(state): number {
      return state.alerts.filter((alert) => alert.status === 'active').length
    },
    failedTaskCount(state): number {
      return (
        state.overview?.stats.tasks.failed ??
        state.tasks.filter((task) => task.status === 'failed').length
      )
    },
    queuedTaskCount(state): number {
      return (
        state.overview?.stats.tasks.queued ??
        state.tasks.filter((task) => task.status === 'queued').length
      )
    },
  },
  actions: {
    async loadOverview(): Promise<void> {
      this.overview = await getOverview()
    },
    async loadUsers(params: ListUsersParams = {}): Promise<void> {
      const page = await listUsers({ page_size: ALL_PAGE_SIZE, ...params })
      this.users = page.items
      this.usersTotal = page.total
    },
    async loadUserDetail(id: number): Promise<AdminUserDetail> {
      return getUser(id)
    },
    async loadPasswordRequests(params: ListPasswordRequestsParams = {}): Promise<void> {
      const page = await listPasswordRequests({ status: 'all', page_size: ALL_PAGE_SIZE, ...params })
      this.passwordRequests = page.items
      this.passwordRequestsTotal = page.total
    },
    async loadQuestions(params: ListQuestionsParams = {}): Promise<void> {
      const page = await listQuestions({ page_size: ALL_PAGE_SIZE, ...params })
      this.questions = page.items
      this.questionsTotal = page.total
    },
    async loadQuestionDetail(id: number): Promise<AdminQuestionDetail> {
      return getQuestion(id)
    },
    async loadTasks(params: ListTasksParams = {}): Promise<void> {
      const page = await listTasks({ page_size: ALL_PAGE_SIZE, ...params })
      this.tasks = page.items
      this.tasksTotal = page.total
    },
    async loadTaskDetail(id: number): Promise<AdminTaskDetail> {
      return getTask(id)
    },
    async loadAiLogs(params: ListAiLogsParams = {}): Promise<void> {
      const page = await listAiLogs({ page_size: ALL_PAGE_SIZE, ...params })
      this.aiLogs = page.items
      this.aiLogsTotal = page.total
    },
    async loadAiLogDetail(id: number): Promise<AiLog> {
      return getAiLog(id)
    },
    async loadAuditLogs(params: ListAuditParams = {}): Promise<void> {
      const page = await listAudit({ page_size: ALL_PAGE_SIZE, ...params })
      this.auditLogs = page.items
      this.auditTotal = page.total
    },
    async loadAuditDetail(id: number): Promise<AuditLog> {
      return getAudit(id)
    },
    async loadAlerts(): Promise<void> {
      this.alerts = await listAlerts()
    },
    async loadSystem(): Promise<void> {
      this.system = await getSystem()
    },
    async loadAll(): Promise<boolean> {
      const results = await Promise.allSettled([
        this.loadOverview(),
        this.loadUsers(),
        this.loadPasswordRequests(),
        this.loadQuestions(),
        this.loadTasks(),
        this.loadAiLogs(),
        this.loadAuditLogs(),
        this.loadAlerts(),
        this.loadSystem(),
      ])
      return results.every((result) => result.status === 'fulfilled')
    },

    async setUserStatus(id: number, payload: UserStatusPayload): Promise<void> {
      await setUserStatus(id, payload)
      await this.refreshUserViews()
    },
    async forceLogoutUser(id: number): Promise<void> {
      await forceLogoutUser(id)
      await this.refreshUserViews()
    },
    async refreshUserViews(): Promise<void> {
      await Promise.allSettled([this.loadUsers(), this.loadOverview(), this.loadAlerts()])
    },

    async approvePasswordRequest(id: number, payload: ApprovePasswordPayload): Promise<PasswordApproveResult> {
      const result = await approvePasswordRequest(id, payload)
      await this.refreshPasswordViews()
      return result
    },
    async rejectPasswordRequest(id: number, reason: string): Promise<void> {
      await rejectPasswordRequest(id, { reason })
      await this.refreshPasswordViews()
    },
    async regenerateTempPassword(id: number): Promise<PasswordApproveResult> {
      const result = await regenerateTempPassword(id)
      await this.refreshPasswordViews()
      return result
    },
    async refreshPasswordViews(): Promise<void> {
      await Promise.allSettled([
        this.loadPasswordRequests(),
        this.loadOverview(),
        this.loadAlerts(),
      ])
    },

    async moderateQuestion(id: number, payload: QuestionModerationPayload): Promise<void> {
      await moderateQuestion(id, payload)
      await Promise.allSettled([this.loadQuestions(), this.loadOverview(), this.loadAlerts()])
    },

    async retryTask(id: number): Promise<void> {
      await retryTask(id)
      await this.refreshTaskViews()
    },
    async cancelTask(id: number): Promise<void> {
      await cancelTask(id)
      await this.refreshTaskViews()
    },
    async refreshTaskViews(): Promise<void> {
      await Promise.allSettled([this.loadTasks(), this.loadOverview(), this.loadAlerts()])
    },

    async revealAiLogRaw(id: number, reason: string): Promise<AiLogRawResult> {
      const result = await revealAiLogRaw(id, reason)
      await Promise.allSettled([this.loadAuditLogs()])
      return result
    },

    async ackAlert(key: string, note?: string): Promise<void> {
      await ackAlert(key, note)
      await Promise.allSettled([this.loadAlerts(), this.loadOverview()])
    },
    async unackAlert(key: string): Promise<void> {
      await unackAlert(key)
      await Promise.allSettled([this.loadAlerts(), this.loadOverview()])
    },

    exportAuditCsv(params: Pick<ListAuditParams, 'q' | 'result'> = {}): Promise<Blob> {
      return exportAuditCsv(params)
    },
  },
})
