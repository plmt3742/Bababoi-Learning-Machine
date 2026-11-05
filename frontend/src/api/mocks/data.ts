import type {
  Analysis,
  Draft,
  GeneratedQuestion,
  PracticeRecord,
  Question,
  QuestionTag,
  Task,
  User,
} from '../types'

export interface MockUser extends User {
  password: string
}

export interface MockState {
  users: MockUser[]
  questions: Question[]
  tags: QuestionTag[]
  generatedQuestions: GeneratedQuestion[]
  tasks: Task[]
  practiceRecords: PracticeRecord[]
  drafts: Map<number, Draft>
  nextUserId: number
  nextQuestionId: number
  nextTagId: number
  nextGeneratedId: number
  nextTaskId: number
  nextPracticeId: number
}

export function makeExcerpt(contentMd: string, limit = 80): string {
  const compact = contentMd.replace(/\s+/g, ' ').trim()
  return compact.length <= limit ? compact : `${compact.slice(0, limit)}…`
}

const derivativeAnalysis: Analysis = {
  topic_type: '导数与极值',
  difficulty: 'medium',
  knowledge_points: ['导数', '极值', '单调性'],
  error_reasons: ['求导后未判断符号变化', '忽略定义域'],
  solution_summary: String.raw`先求 $f'(x)$，再解 $f'(x)=0$，最后用符号表判断单调性。`,
}

const eigenvalueAnalysis: Analysis = {
  topic_type: '特征值与特征向量',
  difficulty: 'medium',
  knowledge_points: ['特征值', '特征方程', '矩阵运算'],
  error_reasons: ['特征多项式展开符号错误', '忘记求特征向量'],
  solution_summary: String.raw`由 $|A-\lambda I|=0$ 求特征值，再解 $(A-\lambda I)x=0$ 求特征向量。`,
}

const probabilityAnalysis: Analysis = {
  topic_type: '条件概率',
  difficulty: 'easy',
  knowledge_points: ['条件概率', '乘法公式'],
  error_reasons: ['把 $P(B|A)$ 当成 $P(AB)$'],
  solution_summary: String.raw`使用乘法公式 $P(AB)=P(A)P(B|A)$。`,
}

const rotationAnalysis: Analysis = {
  topic_type: '刚体定轴转动',
  difficulty: 'medium',
  knowledge_points: ['角加速度', '匀变速转动'],
  error_reasons: ['角速度单位不统一', '把角加速度方向写反'],
  solution_summary: String.raw`由 $\omega=\omega_0+\alpha t$ 代入末角速度为零求解。`,
}

export function createMockState(): MockState {
  const tags: QuestionTag[] = [
    { id: 1, name: '导数', type: 'knowledge_point' },
    { id: 2, name: '极值', type: 'knowledge_point' },
    { id: 3, name: '特征值', type: 'knowledge_point' },
    { id: 4, name: '矩阵', type: 'knowledge_point' },
    { id: 5, name: '条件概率', type: 'knowledge_point' },
    { id: 6, name: '乘法公式', type: 'knowledge_point' },
    { id: 7, name: '刚体转动', type: 'knowledge_point' },
    { id: 8, name: '角加速度', type: 'knowledge_point' },
  ]

  const questions: Question[] = [
    {
      id: 101,
      subject: '高等数学',
      chapter: '导数与极值',
      source_type: 'text',
      content_md: '求函数 $f(x)=x^3-3x+1$ 的极值。',
      answer_md: '极大值 $f(-1)=3$，极小值 $f(1)=-1$。',
      explanation_md: String.raw`$f'(x)=3x^2-3=3(x+1)(x-1)$。当 $x<-1$ 时 $f'(x)>0$，当 $-1<x<1$ 时 $f'(x)<0$，当 $x>1$ 时 $f'(x)>0$，所以 $x=-1$ 取极大值，$x=1$ 取极小值。`,
      question_type: 'solve',
      options: null,
      blanks: null,
      analysis: derivativeAnalysis,
      mastery_status: 'reviewing',
      tags: [tags[0], tags[1]],
      image_path: null,
      crop_box: null,
      created_at: '2026-11-05T09:30:00Z',
      updated_at: '2026-11-05T09:35:00Z',
    },
    {
      id: 102,
      subject: '线性代数',
      chapter: '特征值与特征向量',
      source_type: 'text',
      content_md: String.raw`设 $A=\begin{pmatrix}1&2\\2&1\end{pmatrix}$，求 $A$ 的特征值与特征向量。`,
      answer_md: '特征值为 $3$ 与 $-1$。',
      explanation_md: String.raw`由 $|A-\lambda I|=(1-\lambda)^2-4=0$ 得 $\lambda=3$ 或 $\lambda=-1$；再分别解 $(A-\lambda I)x=0$ 得对应特征向量。`,
      question_type: 'solve',
      options: null,
      blanks: null,
      analysis: eigenvalueAnalysis,
      mastery_status: 'unmastered',
      tags: [tags[2], tags[3]],
      image_path: null,
      crop_box: null,
      created_at: '2026-11-04T14:10:00Z',
      updated_at: '2026-11-04T14:12:00Z',
    },
    {
      id: 103,
      subject: '概率论与数理统计',
      chapter: '条件概率',
      source_type: 'text',
      content_md: String.raw`设 $P(A)=0.6$，$P(B\mid A)=0.5$，则 $P(AB)=$（ ）。`,
      answer_md: 'A',
      explanation_md: String.raw`由乘法公式 $P(AB)=P(A)P(B\mid A)=0.6\times 0.5=0.3$。`,
      question_type: 'choice',
      options: [
        { label: 'A', content_md: '$0.3$' },
        { label: 'B', content_md: '$0.5$' },
        { label: 'C', content_md: '$0.8$' },
        { label: 'D', content_md: '$1.1$' },
      ],
      blanks: null,
      analysis: probabilityAnalysis,
      mastery_status: 'mastered',
      tags: [tags[4], tags[5]],
      image_path: null,
      crop_box: null,
      created_at: '2026-11-03T08:20:00Z',
      updated_at: '2026-11-03T08:22:00Z',
    },
    {
      id: 104,
      subject: '大学物理',
      chapter: '刚体定轴转动',
      source_type: 'image',
      content_md: String.raw`一飞轮以角速度 $\omega_0=10\ \mathrm{rad/s}$ 转动，经 $t=5\ \mathrm{s}$ 匀减速停止，则角加速度大小为 ___ $\mathrm{rad/s^2}$。`,
      answer_md: '$2$',
      explanation_md: String.raw`由 $\omega=\omega_0+\alpha t$ 且末角速度为 $0$，得 $\alpha=-2\ \mathrm{rad/s^2}$，大小为 $2\ \mathrm{rad/s^2}$。`,
      question_type: 'blank',
      options: null,
      blanks: [{ index: 1, answer_md: '$2$' }],
      analysis: rotationAnalysis,
      mastery_status: 'unmastered',
      tags: [tags[6], tags[7]],
      image_path: 'uploads/mock/flywheel.png',
      crop_box: [0.08, 0.18, 0.84, 0.4],
      created_at: '2026-11-02T11:05:00Z',
      updated_at: '2026-11-02T11:08:00Z',
    },
  ]

  const generatedQuestions: GeneratedQuestion[] = [
    {
      id: 301,
      parent_question_id: 101,
      content_md: String.raw`求函数 $g(x)=x^3+3x^2-9x$ 的极值。`,
      answer_md: '极大值 $g(-3)=27$，极小值 $g(1)=-5$。',
      explanation_md: String.raw`$g'(x)=3x^2+6x-9=3(x+3)(x-1)$，列表判断符号变化即可。`,
      question_type: 'solve',
      options: null,
      blanks: null,
      difficulty: 'medium',
      model: 'deepseek-flash',
      prompt_version: 'generate_v1',
      validation_status: 'valid',
      created_at: '2026-11-05T09:36:00Z',
    },
    {
      id: 302,
      parent_question_id: 101,
      content_md: String.raw`求函数 $h(x)=x^4-4x^2+3$ 的极值。`,
      answer_md: String.raw`极大值 $h(0)=3$，极小值 $h(\pm\sqrt{2})=-1$。`,
      explanation_md: String.raw`$h'(x)=4x(x^2-2)$，在 $x=-\sqrt{2},0,\sqrt{2}$ 处判断符号变化。`,
      question_type: 'solve',
      options: null,
      blanks: null,
      difficulty: 'hard',
      model: 'deepseek-flash',
      prompt_version: 'generate_v1',
      validation_status: 'valid',
      created_at: '2026-11-05T09:36:10Z',
    },
    {
      id: 303,
      parent_question_id: 101,
      content_md: String.raw`设 $f(x)=x^3-3x+1$，求 $f(x)$ 在区间 $[-2,2]$ 上的最大值与最小值。`,
      answer_md: '最大值为 $3$，最小值为 $-1$。',
      explanation_md: String.raw`比较驻点 $x=\pm 1$ 与端点 $x=\pm 2$ 的函数值：$f(-2)=-1$，$f(-1)=3$，$f(1)=-1$，$f(2)=3$。`,
      question_type: 'solve',
      options: null,
      blanks: null,
      difficulty: 'medium',
      model: 'deepseek-flash',
      prompt_version: 'generate_v1',
      validation_status: 'valid',
      created_at: '2026-11-05T09:36:20Z',
    },
  ]

  const tasks: Task[] = [
    {
      id: 201,
      question_id: 101,
      stage: 'analysis',
      status: 'done',
      target_index: null,
      retry_index: 0,
      error_code: null,
      created_at: '2026-11-05T09:30:05Z',
      started_at: '2026-11-05T09:30:06Z',
      finished_at: '2026-11-05T09:30:24Z',
    },
    {
      id: 202,
      question_id: 101,
      stage: 'quiz',
      status: 'done',
      target_index: null,
      retry_index: 0,
      error_code: null,
      created_at: '2026-11-05T09:35:20Z',
      started_at: '2026-11-05T09:35:22Z',
      finished_at: '2026-11-05T09:36:30Z',
    },
    {
      id: 203,
      question_id: 102,
      stage: 'analysis',
      status: 'failed',
      target_index: null,
      retry_index: 1,
      error_code: 'AI_TIMEOUT',
      created_at: '2026-11-04T14:10:08Z',
      started_at: '2026-11-04T14:10:10Z',
      finished_at: '2026-11-04T14:10:40Z',
    },
    {
      id: 204,
      question_id: 103,
      stage: 'quiz',
      status: 'running',
      target_index: null,
      retry_index: 0,
      error_code: null,
      created_at: '2026-11-03T08:22:10Z',
      started_at: '2026-11-03T08:22:12Z',
      finished_at: null,
    },
  ]

  const practiceRecords: PracticeRecord[] = [
    {
      id: 401,
      generated_question_id: 301,
      user_answer: '极大值 27，极小值 -5',
      is_correct: true,
      duration_seconds: 185,
      created_at: '2026-11-05T10:02:00Z',
    },
    {
      id: 402,
      generated_question_id: 302,
      user_answer: '极大值 3，极小值 -2',
      is_correct: false,
      duration_seconds: 240,
      created_at: '2026-11-05T10:08:00Z',
    },
  ]

  return {
    users: [
      {
        id: 1,
        username: 'student01',
        password: 'password123',
        email: 'student01@example.com',
        created_at: '2026-10-20T08:00:00Z',
      },
    ],
    questions,
    tags,
    generatedQuestions,
    tasks,
    practiceRecords,
    drafts: new Map<number, Draft>(),
    nextUserId: 2,
    nextQuestionId: 105,
    nextTagId: 9,
    nextGeneratedId: 304,
    nextTaskId: 205,
    nextPracticeId: 403,
  }
}
