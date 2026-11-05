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

export interface ApiErrorDetail {
  code: string
  message: string
  request_id: string
}

export interface ApiErrorResponse {
  detail: ApiErrorDetail
}
