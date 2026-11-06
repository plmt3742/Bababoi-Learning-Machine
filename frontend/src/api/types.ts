/**
 * API contract types (05-architecture §5–§6, snake_case in and out).
 *
 * Keep this file free of runtime code so it can be imported with `import type`
 * from anywhere without pulling Axios into the bundle.
 */

export type QuestionType = 'choice' | 'blank' | 'solve'
export type SourceType = 'text' | 'image'
export type Difficulty = 'easy' | 'medium' | 'hard'
export type MasteryStatus = 'unmastered' | 'reviewing' | 'mastered'
export type TaskStage = 'analysis' | 'quiz'
export type TaskStatus = 'queued' | 'running' | 'done' | 'failed'
export type ValidationStatus = 'valid' | 'invalid' | 'fallback'

export interface User {
  id: number
  username: string
  email: string | null
  created_at: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export interface LoginPayload {
  username: string
  password: string
}

export interface RegisterPayload {
  username: string
  password: string
  email?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface QuestionTag {
  id: number
  name: string
  type: string
}

export interface QuestionOption {
  label: string
  content_md: string
}

export interface QuestionBlank {
  index: number
  answer_md: string
}

export interface Analysis {
  topic_type: string
  difficulty: Difficulty
  knowledge_points: string[]
  error_reasons: string[]
  solution_summary: string
}

export interface Question {
  id: number
  subject: string
  chapter: string | null
  source_type: SourceType
  content_md: string
  answer_md: string | null
  explanation_md: string | null
  question_type: QuestionType
  options: QuestionOption[] | null
  blanks: QuestionBlank[] | null
  analysis: Analysis | null
  difficulty?: Difficulty | null
  mastery_status: MasteryStatus
  tags: QuestionTag[]
  image_path: string | null
  crop_box: number[] | null
  created_at: string
  updated_at: string
}

export interface QuestionListItem {
  id: number
  subject: string
  chapter: string | null
  question_type: QuestionType
  excerpt: string
  mastery_status: MasteryStatus
  tags: QuestionTag[]
  created_at: string
}

export interface QuestionCreate {
  subject: string
  chapter?: string | null
  source_type?: SourceType
  question_type: QuestionType
  content_md: string
  answer_md?: string | null
  explanation_md?: string | null
  options?: QuestionOption[] | null
  blanks?: QuestionBlank[] | null
  tags?: string[]
  image_path?: string | null
}

export interface QuestionUpdate {
  subject?: string
  chapter?: string | null
  content_md?: string
  answer_md?: string | null
  explanation_md?: string | null
  mastery_status?: MasteryStatus
  tags?: string[]
  analysis?: Analysis | null
}

export interface QuestionCreateResult {
  question: Question
  task_id: number
}

export interface GeneratedQuestion {
  id: number
  parent_question_id: number
  content_md: string
  answer_md: string
  explanation_md: string
  question_type: QuestionType | null
  options: QuestionOption[] | null
  blanks: QuestionBlank[] | null
  difficulty: Difficulty | null
  /** FE-023: 1/2/3 for the three-segment generation; null/absent for legacy rows. */
  target_index?: GenerationTargetIndex | null
  model: string | null
  prompt_version: string | null
  validation_status: ValidationStatus
  created_at: string
}

export interface Task {
  id: number
  question_id: number
  stage: TaskStage
  status: TaskStatus
  target_index: number | null
  retry_index: number
  error_code: string | null
  /** FE-023: backend may surface a human-readable failure reason alongside the code. */
  error_message?: string | null
  /** FE-023: difficulty assigned to this generation segment. */
  difficulty?: Difficulty | null
  created_at: string
  started_at: string | null
  finished_at: string | null
}

export interface QuestionDetail extends Question {
  tasks: Task[]
  generated_questions: GeneratedQuestion[]
}

export interface TaskIdResponse {
  task_id: number
}

export interface TaskListResponse {
  items: Task[]
  total?: number
  page?: number
  page_size?: number
}

export interface Draft {
  content: Record<string, unknown>
  version: number
  updated_at: string
}

export interface DraftSavePayload {
  content: Record<string, unknown>
  base_version: number | null
  client_updated_at: string
}

export interface PracticeRecord {
  id: number
  generated_question_id: number
  user_answer: string | null
  is_correct: boolean
  duration_seconds: number
  created_at: string
}

export interface PracticeRecordCreate {
  generated_question_id: number
  user_answer?: string | null
  is_correct: boolean
  duration_seconds: number
}

export interface QuestionListQuery {
  page?: number
  page_size?: number
  subject?: string
  tag?: string
  mastery_status?: MasteryStatus
  q?: string
  sort?: string
}

export interface TaskListQuery {
  question_id?: number
  status?: TaskStatus
}

export interface PracticeRecordListQuery {
  page?: number
  page_size?: number
  generated_question_id?: number
}

export interface StatsWeakKnowledgePoint {
  name: string
  wrong_count: number
  total_count: number
  /** Correct practice ratio for this knowledge point, in the 0–1 range. */
  accuracy: number
}

export interface StatsTrendPoint {
  /** UTC calendar day in `YYYY-MM-DD` form. */
  date: string
  practice_count: number
  correct_count: number
}

export interface StatsOverview {
  total_questions: number
  total_generated_questions: number
  total_practice_records: number
  /** Correct practice ratio across all records, in the 0–1 range. */
  accuracy: number
  mastered_count: number
  reviewing_count: number
  unmastered_count: number
  weak_knowledge_points: StatsWeakKnowledgePoint[]
  recent_trend: StatsTrendPoint[]
  updated_at: string
}

export interface ApiErrorDetail {
  code: string
  message: string
  request_id: string
}

export interface ApiErrorResponse {
  detail: ApiErrorDetail
}

/* ---------------------------------------------------------------------------
 * Image intake v2 (FE-016 / FE-021, 05-architecture §6.2 + ADR-004)
 * ------------------------------------------------------------------------- */

export interface ImageUploadResult {
  /** Relative storage path; send this back to `/questions/from-image`. */
  image_path: string
  /** Preview URL (mock: blob URL; backend: authenticated asset URL). */
  url: string
  width: number
  height: number
}

export interface ExtractedImageQuestion {
  /** 1-based reading-order index; rendered as ① ② ③… */
  index: number
  content_md: string
  question_type: QuestionType
  /** AI 初判学科；前端用于预填保存表单，用户可修改。 */
  subject?: string | null
  /** AI 初判章节；保存时随题目一起提交。 */
  chapter?: string | null
  /** AI 初判难度；当前只展示，分析任务会写入正式难度。 */
  difficulty?: Difficulty | null
  options: QuestionOption[] | null
  blanks: QuestionBlank[] | null
  has_figure: boolean
  warnings: string[]
  /** Backend may flag a partially readable item; editable but highlighted. */
  incomplete?: boolean
}

export interface ImageExtractionResult {
  image_path: string
  questions: ExtractedImageQuestion[]
  warnings: string[]
}

/* -------------------------------------------------------------------------
 * FE-023 · three-segment concurrent generation (ADR-006)
 * Legacy `{ task_id }` responses stay supported via the API normalizer.
 * ---------------------------------------------------------------------- */

export type GenerationTargetIndex = 1 | 2 | 3

export interface GenerateQuestionsPayload {
  /** Whole-group generation: one task per difficulty. */
  difficulties?: Difficulty[]
  /** Single-segment regeneration. */
  difficulty?: Difficulty
}

export interface GenerateTaskRef {
  task_id: number
  target_index: GenerationTargetIndex | null
  difficulty: Difficulty | null
}

export interface GenerateTasksResponse {
  tasks: GenerateTaskRef[]
}

/* ---------------------------------------------------------------------------
 * Personal settings · BYOK (P1; backend stores keys encrypted at rest)
 * GET/PUT /settings/ai return AiSettings; the raw key is never returned.
 * ------------------------------------------------------------------------- */

export type AiProvider = 'deepseek' | 'openai_compatible'

export interface AiSettings {
  configured: boolean
  provider: AiProvider
  base_url: string | null
  model: string
  /** Server-side mask only, e.g. `sk-****abcd`; never the full key. */
  api_key_masked: string | null
  updated_at: string | null
}

export interface AiSettingsUpdate {
  provider: AiProvider
  base_url?: string | null
  model: string
  api_key: string
}
